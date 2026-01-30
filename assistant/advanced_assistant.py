"""Advanced Chess Assistant with UI controls, move quality analysis, and threat detection."""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import chess.engine
import socketio
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.interface.packet_parser import PacketParser
from src.engine.variant_loader import load_drawback_config

ASSISTANT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = ASSISTANT_ROOT / "data"
SELECTOR_PATH = DATA_ROOT / "selectors.json"
PACKET_LOG_PATH = DATA_ROOT / "captured_packets.jsonl"
BEST_MOVE_LOG_PATH = DATA_ROOT / "best_moves.jsonl"
STATE_SNAPSHOT_PATH = DATA_ROOT / "assistant_state.json"


def load_selectors() -> Dict[str, str]:
    if not SELECTOR_PATH.exists():
        raise FileNotFoundError(f"Selector config missing: {SELECTOR_PATH}")
    with SELECTOR_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    required = {"board_root", "square_template", "overlay_id"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Selector config missing keys: {missing}")
    return data


def detect_engine() -> Path:
    # Prioritize Fairy-Stockfish for Drawback Chess variant support
    candidates = [
        REPO_ROOT / "engines" / "fairy-stockfish_x86-64.exe",
        REPO_ROOT / "engines" / "fairy-stockfish.exe",
        REPO_ROOT / "engines" / "fairy-stockfish",
        REPO_ROOT / "engines" / "stockfish.exe",
        REPO_ROOT / "engines" / "stockfish",
    ]
    for candidate in candidates:
        if candidate.exists():
            print(f"[ENGINE] Using: {candidate.name}")
            return candidate
    raise FileNotFoundError("No chess engine found in engines/ directory. Please install fairy-stockfish")


def calculate_port(game_id: str) -> int:
    """Calculate Socket.IO port from game ID (matches GamePage.js logic)."""
    hash_val = 0
    for char in game_id:
        hash_val = ((hash_val << 5) - hash_val) + ord(char)
        hash_val = hash_val & 0xFFFFFFFF
    
    while hash_val >= 2**32:
        hash_val -= 2**32
    
    return 5001 + (hash_val % 16)


class MoveQuality:
    """Move quality classification based on centipawn loss."""
    BEST = "best"
    EXCELLENT = "excellent"
    GOOD = "good"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"
    
    @staticmethod
    def classify(cp_loss: float) -> str:
        """Classify move quality based on centipawn loss from best move."""
        if cp_loss <= 0:
            return MoveQuality.BEST
        elif cp_loss <= 25:
            return MoveQuality.EXCELLENT
        elif cp_loss <= 75:
            return MoveQuality.GOOD
        elif cp_loss <= 150:
            return MoveQuality.INACCURACY
        elif cp_loss <= 300:
            return MoveQuality.MISTAKE
        else:
            return MoveQuality.BLUNDER
    
    @staticmethod
    def get_color(quality: str) -> str:
        """Get color for move quality."""
        colors = {
            MoveQuality.BEST: "#00ff00",        # Bright green
            MoveQuality.EXCELLENT: "#90ee90",   # Light green
            MoveQuality.GOOD: "#ffff00",        # Yellow
            MoveQuality.INACCURACY: "#ffa500",  # Orange
            MoveQuality.MISTAKE: "#ff6347",     # Tomato
            MoveQuality.BLUNDER: "#ff0000",     # Red
        }
        return colors.get(quality, "#ffffff")


class AdvancedAssistant:
    def __init__(self, engine_path: Optional[Path] = None, dual_browser: bool = True):
        self.selectors = load_selectors()
        self.engine_path = engine_path or detect_engine()
        self.engine = chess.engine.SimpleEngine.popen_uci(str(self.engine_path))
        self.variant_config = load_drawback_config()
        self._apply_variant_config()
        
        self.playwright = None
        self.browser = None
        self.page = None
        self.sio = None
        self.secondary_browser = None
        
        self.game_id = None
        self.player_color = None
        self.username = None
        self.port = None
        self.socket_connecting = False
        self.last_socket_failure = None
        self.secondary_page = None
        self.dual_browser = dual_browser
        
        self.latest_state = {}
        self.last_highlighted_fen = None
        self.shutdown_requested = False
        self.game_result = None
        
        # Advanced features configuration
        self.show_for_player = True
        self.show_for_opponent = False
        self.show_move_quality = False  # Heatmap (piece selection)
        self.show_threats = True
        self.show_best_move = True
        self.auto_play = False  # Auto-play best move
        self.search_depth = 14
        self.search_time = 2.0  # Default 2 seconds
        
        # Caching
        self.move_cache = {}
        self.move_quality_cache = {}
        self.threat_cache = {}
        self.response_cache = {}
        
        # Current analysis state
        self.current_legal_moves = []
        self.current_move_evaluations = {}
        self.current_threats = []
        self.current_fen = None
        self.selected_piece_square = None
        
    async def run(self, url: str) -> None:
        async with async_playwright() as playwright:
            self.playwright = playwright
            self.browser = await playwright.chromium.launch(headless=False)
            context = await self.browser.new_context()
            self.page = await context.new_page()
            
            self.page.on("response", lambda res: asyncio.create_task(self._handle_response(res)))
            self.page.on("close", lambda: asyncio.create_task(self._handle_page_close()))
            
            print(f"[ASSIST] Navigating to {url}")
            await self.page.goto(url)
            
            print("[ASSIST] Waiting for game to start...")
            
            try:
                while True:
                    if self.page.is_closed():
                        print("[ASSIST] Main browser closed by user, shutting down...")
                        break
                    
                    if self.secondary_page and self.secondary_page.is_closed():
                        print("[ASSIST] Secondary browser closed by user")
                        self.secondary_page = None
                        if self.secondary_browser:
                            try:
                                await self.secondary_browser.close()
                            except:
                                pass
                            self.secondary_browser = None
                    
                    await self._ensure_overlay(self.page)
                    await self._ensure_ui_panel(self.page)
                    
                    if self.game_id and self.player_color and not self.sio and not self.socket_connecting:
                        if self._can_attempt_socket_connect():
                            await self._connect_socketio()

                    if self.dual_browser and self.secondary_page is None and self.game_id and self.player_color:
                        await self._ensure_dual_browser(context)
                    
                    # Check for piece selections
                    await self._check_piece_selection()
                    
                    # Update settings from UI
                    await self._sync_ui_settings()
                    
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                print("[ASSIST] Cancelled by user")
            except Exception as e:
                if "Target page, context or browser has been closed" in str(e) or "Browser closed" in str(e):
                    print("[ASSIST] Browser closed by user, shutting down...")
                else:
                    print(f"[ERROR] Unexpected error: {e}")
                    raise
            finally:
                print("[ASSIST] Cleaning up...")
                if self.sio:
                    try:
                        await self.sio.disconnect()
                    except:
                        pass
                if self.secondary_browser:
                    try:
                        await self.secondary_browser.close()
                    except:
                        pass
                try:
                    await context.close()
                except:
                    pass
        
        self.engine.close()
        print("[ASSIST] Shutdown complete")

    async def _handle_page_close(self):
        """Handle main page close event."""
        print("[ASSIST] Main page closed, requesting shutdown...")
        self.shutdown_requested = True
    
    def _can_attempt_socket_connect(self) -> bool:
        if self.last_socket_failure is None:
            return True
        return (time.monotonic() - self.last_socket_failure) > 5

    async def _ensure_dual_browser(self, context) -> None:
        if not self.game_id or not self.player_color or not self.playwright:
            return

        opposite_color = "black" if self.player_color == "white" else "white"
        url = f"https://www.drawbackchess.com/game/{self.game_id}/{opposite_color}"
        
        print(f"[ASSIST] Launching separate browser for opposite color...")
        self.secondary_browser = await self.playwright.chromium.launch(headless=False)
        secondary_context = await self.secondary_browser.new_context()
        self.secondary_page = await secondary_context.new_page()
        
        print(f"[ASSIST] Opening opposite color view: {url}")
        await self.secondary_page.goto(url)
    
    async def _connect_socketio(self):
        """Connect to Socket.IO server."""
        self.port = calculate_port(self.game_id)
        self.socket_connecting = True
        
        print(f"[SOCKET.IO] Connecting to port {self.port} for game {self.game_id}")
        
        self.sio = socketio.AsyncClient()
        
        @self.sio.event
        async def connect():
            print(f"[SOCKET.IO] Connected to server")
            await self.sio.emit('join', {'room': self.game_id})
            if self.username:
                await self.sio.emit('join', {'room': f"{self.game_id}-{self.username}"})
            print(f"[SOCKET.IO] Joined game room: {self.game_id}")
        
        @self.sio.event
        async def disconnect():
            print("[SOCKET.IO] Disconnected from server")
        
        @self.sio.event
        async def update(data):
            print(f"[SOCKET.IO] Received 'update' event")
            await self._process_game_update(data)
        
        @self.sio.event
        async def message(data):
            print(f"[MESSAGE] {data.get('message')}")
        
        try:
            await self.sio.connect(
                "https://www.drawbackchess.com",
                socketio_path=f"/app{self.port - 5000}/socket.io",
                transports=["websocket"],
            )
        except Exception as e:
            print(f"[ERROR] Socket.IO connection failed: {e}")
            self.last_socket_failure = time.monotonic()
            self.sio = None
        finally:
            self.socket_connecting = False
    
    async def _process_game_update(self, data: dict):
        """Process Socket.IO 'update' event with advanced analysis."""
        game_data = data.get('game')
        if not game_data:
            print("[DEBUG] Update event has no game data")
            return
        
        await self._persist_packet({'game': game_data, 'success': True})
        
        board_state = game_data.get('board')
        turn = game_data.get('turn')
        ply = game_data.get('ply', 0)
        result = game_data.get('result')
        
        # Update game result and clear highlights if game ended
        if result and result != self.game_result:
            self.game_result = result
            print(f"[GAME] Game ended: {result}")
            await self._clear_all_overlays()
            return
        
        if not board_state or not turn or not self.player_color:
            print(f"[DEBUG] Incomplete data")
            return
        
        # Clear stale overlays on every update
        await self._clear_all_overlays()

        # Check if we should show assistance for this turn
        should_assist = (
            (turn == self.player_color and self.show_for_player) or
            (turn != self.player_color and self.show_for_opponent)
        )
        
        if not should_assist:
            await self._clear_all_overlays()
            print(f"[DEBUG] Not showing assistance (turn={turn}, player={self.player_color}, show_player={self.show_for_player}, show_opp={self.show_for_opponent})")
            return
        
        current_moves = game_data.get('moves', {})
        legal_moves = []
        for start_sq, destinations in current_moves.items():
            for move_obj in destinations:
                stop_sq = move_obj.get('stop')
                if start_sq and stop_sq:
                    legal_moves.append(f"{start_sq}{stop_sq}".lower())
        
        print(f"[UPDATE] Ply {ply}: {len(legal_moves)} legal moves, turn={turn}")
        
        if not legal_moves:
            return
        
        fen = PacketParser.board_to_fen(board_state, turn)
        
        if self.last_highlighted_fen == fen:
            return
        
        self.current_legal_moves = legal_moves
        self.current_fen = fen
        
        # Clear old overlays when position changes
        await self._clear_all_overlays()
        
        # Only do lightweight analysis by default
        await self._analyze_position_fast(fen, legal_moves, board_state, turn)
        
        self.last_highlighted_fen = fen
    
    async def _analyze_position_fast(self, fen: str, legal_moves: List[str], board_state: dict, turn: str):
        """Fast analysis - only find best move and threats."""
        print(f"[ANALYSIS] Fast analysis...")
        
        # 1. Find best move only (single evaluation)
        best_move, best_score = self._score_moves(fen, legal_moves)
        
        if not best_move:
            return
        
        print(f"[ASSIST] Best move: {best_move} ({best_score:.2f} cp)")
        
        # 2. Detect threats (cached)
        threats = await self._detect_threats(fen, turn)
        self.current_threats = threats
        
        # 3. Update UI
        if self.show_best_move:
            await self._highlight_best_move(best_move, best_score)
        
        if self.show_threats and threats:
            await self._show_threats(threats)
        
        # 4. Log analysis
        parsed = PacketParser.parse_game_state({'game': {'board': board_state, 'turn': turn, 'ply': 0}, 'success': True})
        await self._record_analysis(parsed, best_move, best_score, {}, threats)
    
    async def _analyze_selected_piece(self, square: str):
        """Analyze moves for a specific piece with progressive deepening."""
        if not self.current_fen or not self.current_legal_moves:
            return
        
        # Find moves from this square
        piece_moves = [m for m in self.current_legal_moves if m[:2].upper() == square.upper()]
        
        if not piece_moves:
            print(f"[DEBUG] No moves from {square}")
            return
        
        print(f"[ANALYSIS] Progressive analysis of {len(piece_moves)} moves from {square}...")
        
        # Use progressive deepening with MultiPV
        move_evals = await self._evaluate_moves_progressive(self.current_fen, piece_moves)
        
        if not move_evals:
            return
        
        # Find best overall move for comparison
        best_overall, best_score = self._score_moves(self.current_fen, self.current_legal_moves)
        
        # Classify quality
        move_qualities = {}
        turn = "white" if chess.Board(self.current_fen).turn == chess.WHITE else "black"
        
        for move, score in move_evals.items():
            cp_loss = abs(best_score - score)
            quality = MoveQuality.classify(cp_loss)
            move_qualities[move] = quality
        
        # Show quality overlays
        await self._show_move_qualities(move_qualities)
        
        print(f"[QUALITY] Final: {len(move_qualities)} move qualities for {square}")
    
    def _score_moves(self, fen: str, uci_moves: List[str]) -> Tuple[str, float]:
        """Find best move from list using Stockfish."""
        cache_key = f"{fen}:{','.join(sorted(uci_moves))}"
        if cache_key in self.move_cache:
            return self.move_cache[cache_key]
        
        board = chess.Board(fen)
        moves = []
        for move_str in uci_moves:
            try:
                # For Drawback Chess, ignore standard chess move validation
                # Just ensure the UCI format is valid
                move = chess.Move.from_uci(move_str)
                moves.append(move)
            except ValueError:
                continue
        if not moves:
            return None, 0.0
        
        # Build limit with depth and/or time (whichever hits first)
        limit_kwargs = {}
        if self.search_depth:
            limit_kwargs['depth'] = self.search_depth
        if self.search_time:
            limit_kwargs['time'] = self.search_time
        
        limit = chess.engine.Limit(**limit_kwargs) if limit_kwargs else chess.engine.Limit(depth=14)
        info = self.engine.analyse(board, limit, root_moves=moves)
        move = info.get("pv", [None])[0]
        if move is None:
            return None, 0.0
        score = info["score"].white().score(mate_score=10000)
        result = (move.uci(), float(score))
        
        # Cache result
        self.move_cache[cache_key] = result
        return result
    
    async def _evaluate_moves_progressive(self, fen: str, legal_moves: List[str]) -> Dict[str, float]:
        """Progressive deepening analysis - show results immediately and deepen."""
        cache_key = f"{fen}:{','.join(sorted(legal_moves))}"
        if cache_key in self.move_quality_cache:
            print(f"[CACHE] Using cached evaluation")
            return self.move_quality_cache[cache_key]
        
        board = chess.Board(fen)
        chess_moves = []
        for move_str in legal_moves:
            try:
                move = chess.Move.from_uci(move_str)
                if move in board.legal_moves:
                    chess_moves.append(move)
            except ValueError:
                continue
        
        if not chess_moves:
            return {}
        
        move_scores = {}
        num_moves = len(chess_moves)
        
        print(f"[PROGRESSIVE] Analyzing {num_moves} moves progressively...")
        
        # Analyze each move sequentially with progressive deepening
        max_depth = min(self.search_depth if self.search_depth else 14, 10)
        
        for depth in [1, 3, 6, max_depth]:
            if depth > max_depth:
                continue
                
            for move in chess_moves:
                try:
                    board.push(move)
                    
                    limit = chess.engine.Limit(depth=depth)
                    if self.search_time and depth == max_depth:
                        limit = chess.engine.Limit(depth=depth, time=self.search_time)
                    
                    info = self.engine.analyse(board, limit)
                    score = info["score"].white().score(mate_score=10000)
                    move_scores[move.uci()] = float(score)
                    
                    board.pop()
                except Exception as e:
                    if board.move_stack:
                        board.pop()
                    continue
            
            # Update UI at each depth milestone
            if move_scores and depth >= 3:
                print(f"[DEPTH {depth}] {len(move_scores)} moves evaluated")
                
                best_overall, best_score = self._score_moves(self.current_fen, self.current_legal_moves)
                turn = "white" if board.turn == chess.WHITE else "black"
                
                temp_qualities = {}
                for move, score in move_scores.items():
                    cp_loss = abs(best_score - score)
                    quality = MoveQuality.classify(cp_loss)
                    temp_qualities[move] = quality
                
                await self._show_move_qualities(temp_qualities)
        
        # Cache final results
        self.move_quality_cache[cache_key] = move_scores
        return move_scores
    
    async def _evaluate_all_moves(self, fen: str, legal_moves: List[str]) -> Dict[str, float]:
        """Evaluate specific moves and return scores."""
        cache_key = f"{fen}:{','.join(sorted(legal_moves))}"
        if cache_key in self.move_quality_cache:
            print(f"[CACHE] Using cached evaluation for {len(legal_moves)} moves")
            return self.move_quality_cache[cache_key]
        
        board = chess.Board(fen)
        move_scores = {}
        
        print(f"[EVAL] Evaluating {len(legal_moves)} moves (depth={self.search_depth}, time={self.search_time}s)...")
        
        for move_str in legal_moves:
            try:
                move = chess.Move.from_uci(move_str)
                if move not in board.legal_moves:
                    continue
                
                # Make move
                board.push(move)
                
                # Build limit with BOTH depth and time (whichever hits first)
                limit_kwargs = {}
                if self.search_depth:
                    limit_kwargs['depth'] = self.search_depth
                if self.search_time:
                    limit_kwargs['time'] = self.search_time
                
                limit = chess.engine.Limit(**limit_kwargs) if limit_kwargs else chess.engine.Limit(depth=14)
                info = self.engine.analyse(board, limit)
                score = info["score"].white().score(mate_score=10000)
                
                move_scores[move_str] = float(score)
                
                # Undo move
                board.pop()
                
            except Exception as e:
                print(f"[ERROR] Failed to evaluate {move_str}: {e}")
                continue
        
        self.move_quality_cache[cache_key] = move_scores
        return move_scores
    
    async def _detect_threats(self, fen: str, turn: str) -> List[Dict]:
        """Detect opponent threats (pieces attacking our pieces)."""
        cache_key = f"{fen}:threats"
        if cache_key in self.threat_cache:
            return self.threat_cache[cache_key]
        
        board = chess.Board(fen)
        threats = []
        
        our_color = chess.WHITE if turn == "white" else chess.BLACK
        opp_color = chess.BLACK if turn == "white" else chess.WHITE
        
        # Find all our pieces
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == our_color:
                # Check if any opponent piece attacks this square
                attackers = board.attackers(opp_color, square)
                for attacker_sq in attackers:
                    threats.append({
                        'from': chess.square_name(attacker_sq).upper(),
                        'to': chess.square_name(square).upper(),
                        'target_piece': piece.symbol()
                    })
        
        self.threat_cache[cache_key] = threats
        return threats
    
    async def _highlight_best_move(self, uci_move: str, score: float):
        """Highlight best move with green arrow and borders."""
        if not self.page:
            return
        
        start = uci_move[:2].upper()
        stop = uci_move[2:4].upper()
        
        try:
            await self.page.evaluate(f"""
                () => {{
                    if (window.assistantHighlightBest) {{
                        window.assistantHighlightBest('{start}', '{stop}');
                    }}
                    if (window.assistantShowBestArrow) {{
                        window.assistantShowBestArrow('{start}', '{stop}');
                    }}
                }}
            """)
            print(f"[HIGHLIGHT] Best: {start} -> {stop}")
            
            if self.auto_play:
                await self._auto_play_move(uci_move)
        except Exception as e:
            print(f"[ERROR] Failed to highlight best move: {e}")
    
    async def _show_move_qualities(self, move_qualities: Dict[str, str]):
        """Show color-coded move quality overlays."""
        if not self.page:
            return
        
        try:
            # Build quality map for JavaScript
            quality_data = {}
            for move, quality in move_qualities.items():
                stop_sq = move[2:4].upper()
                color = MoveQuality.get_color(quality)
                quality_data[stop_sq] = {'quality': quality, 'color': color}
            
            await self.page.evaluate(f"""
                (data) => {{
                    if (window.assistantShowQualities) {{
                        window.assistantShowQualities(data);
                    }}
                }}
            """, quality_data)
            
            print(f"[QUALITY] Showing {len(quality_data)} move qualities")
        except Exception as e:
            print(f"[ERROR] Failed to show move qualities: {e}")
    
    async def _show_threats(self, threats: List[Dict]):
        """Show threat arrows."""
        if not self.page:
            return
        
        try:
            await self.page.evaluate("""
                () => {
                    if (window.assistantClearArrows) {
                        window.assistantClearArrows();
                    }
                }
            """)
            
            await self.page.evaluate(f"""
                (threats) => {{
                    if (window.assistantShowThreats) {{
                        window.assistantShowThreats(threats);
                    }}
                }}
            """, threats)
            
            print(f"[THREATS] Showing {len(threats)} threats")
        except Exception as e:
            print(f"[ERROR] Failed to show threats: {e}")
    
    async def _sync_ui_settings(self):
        """Sync settings from UI checkboxes."""
        if not self.page:
            return
        
        try:
            settings = await self.page.evaluate("""
                () => {
                    return {
                        autoPlay: document.getElementById('assist-auto-play')?.checked || false,
                        showPlayer: document.getElementById('assist-show-player')?.checked || true,
                        showOpponent: document.getElementById('assist-show-opponent')?.checked || false,
                        showThreats: document.getElementById('assist-show-threats')?.checked || true,
                        showBest: document.getElementById('assist-show-best')?.checked || true,
                        showHeatmap: document.getElementById('assist-show-heatmap')?.checked || false,
                        depth: parseInt(document.getElementById('assist-depth')?.value || '14'),
                        time: parseFloat(document.getElementById('assist-time')?.value || '2.0')
                    };
                }
            """)
            
            if settings:
                if self.auto_play != settings['autoPlay']:
                    self.auto_play = settings['autoPlay']
                    print(f"[CONFIG] Auto-play: {self.auto_play}")
                
                self.show_for_player = settings['showPlayer']
                self.show_for_opponent = settings['showOpponent']
                if self.show_threats != settings['showThreats']:
                    self.show_threats = settings['showThreats']
                    if not self.show_threats:
                        await self._clear_all_overlays()
                if self.show_best_move != settings['showBest']:
                    self.show_best_move = settings['showBest']
                    if not self.show_best_move:
                        await self._clear_all_overlays()
                if self.show_move_quality != settings['showHeatmap']:
                    self.show_move_quality = settings['showHeatmap']
                    if not self.show_move_quality:
                        await self._clear_all_overlays()
                self.search_depth = settings['depth']
                self.search_time = settings['time']
        except Exception as e:
            pass
    
    async def _check_piece_selection(self):
        """Check if user selected a piece for analysis."""
        if not self.page or not self.current_fen or not self.show_move_quality:
            return
        
        try:
            selected = await self.page.evaluate("""
                () => {
                    if (window.assistantGetSelectedSquare) {
                        return window.assistantGetSelectedSquare();
                    }
                    return null;
                }
            """)
            
            if selected:
                print(f"[PIECE] Selected: {selected}")
                await self._analyze_selected_piece(selected)
                # Clear the selection flag
                await self.page.evaluate("""
                    () => {
                        if (window.assistantClearSelectedSquare) {
                            window.assistantClearSelectedSquare();
                        }
                    }
                """)
        except Exception as e:
            pass
    
    async def _auto_play_move(self, uci_move: str):
        """Auto-play the best move."""
        if not self.page:
            return
        
        start = uci_move[:2].upper()
        stop = uci_move[2:4].upper()
        
        try:
            print(f"[AUTO-PLAY] Making move: {start} -> {stop}")
            
            await self.page.evaluate(f"""
                () => {{
                    const startSq = document.querySelector('.square[data-square="{start}"]');
                    if (startSq) startSq.click();
                }}
            """)
            
            await asyncio.sleep(0.2)
            
            await self.page.evaluate(f"""
                () => {{
                    const stopSq = document.querySelector('.square[data-square="{stop}"]');
                    if (stopSq) stopSq.click();
                }}
            """)
            
            print(f"[AUTO-PLAY] Move executed")
        except Exception as e:
            print(f"[ERROR] Auto-play failed: {e}")
    
    async def _clear_all_overlays(self):
        """Clear all visual overlays."""
        if not self.page:
            return
        
        try:
            await self.page.evaluate("""
                () => {
                    if (window.assistantClearAll) {
                        window.assistantClearAll();
                    }
                    document.querySelectorAll('[data-assistant-arrow="true"]').forEach(el => el.remove());
                }
            """)
            print(f"[CLEAR] Cleared all overlays")
        except Exception as e:
            print(f"[DEBUG] Failed to clear overlays: {e}")
    
    async def _handle_response(self, response):
        """Capture HTTP responses to detect game ID and player color."""
        url = response.url
        if "/game?" not in url:
            return
        
        try:
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type and "text/plain" not in content_type:
                return
            
            body = await response.text()
            data = json.loads(body)
            
            if isinstance(data, dict) and "game" in data and data.get("success"):
                print(f"[DEBUG] HTTP response from {url}")
                
                if self.player_color is None:
                    if "color" in data:
                        self.player_color = data["color"]
                        print(f"[ASSIST] Detected player color: {self.player_color}")
                    elif "/game?" in url and "color=" in url:
                        import re
                        match = re.search(r"color=(\w+)", url)
                        if match:
                            self.player_color = match.group(1)
                            print(f"[ASSIST] Detected player color from URL: {self.player_color}")
                
                game_id = data.get("game", {}).get("id")
                if not game_id and "/game?" in url and "id=" in url:
                    import re
                    match = re.search(r"id=([a-f0-9]+)", url)
                    if match:
                        game_id = match.group(1)
                
                if game_id and game_id != self.game_id:
                    if self.game_id:
                        print(f"[ASSIST] New game detected: {game_id}")
                        if self.sio:
                            await self.sio.disconnect()
                            self.sio = None
                        self.last_socket_failure = None
                        self.socket_connecting = False
                    else:
                        print(f"[ASSIST] Detected game ID: {game_id}")
                    self.game_id = game_id
                    self.last_highlighted_fen = None
                    self.latest_state = {}
                    self.game_result = None
                    self.move_cache.clear()
                    self.move_quality_cache.clear()
                    self.threat_cache.clear()
                    self.response_cache.clear()
                    if self.secondary_browser:
                        await self.secondary_browser.close()
                        self.secondary_browser = None
                        self.secondary_page = None
                
                if "/game?" in url and "username=" in url:
                    import re
                    match = re.search(r"username=([^&]+)", url)
                    if match:
                        self.username = match.group(1)
                        print(f"[ASSIST] Detected username: {self.username}")
                
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[ERROR] Failed to process response: {e}")
    
    def _apply_variant_config(self) -> None:
        if not self.variant_config or not self.variant_config.loaded:
            return
        
        option_map = {
            "victoryState": self.variant_config.get_victory_condition(),
            "illegalChecks": self.variant_config.is_illegal_checks(),
            "stalemateValue": self.variant_config.get_stalemate_value(),
            "castlingOutofCheck": self.variant_config.can_castle_out_of_check(),
            "castlingThroughCheck": self.variant_config.can_castle_through_check(),
        }
        
        available_options = self.engine.options
        payload = {}
        for key, value in option_map.items():
            if key not in available_options or value is None:
                continue
            payload[key] = value
        
        if not payload:
            return
        
        try:
            self.engine.configure(payload)
            print(f"[ASSIST] Applied Drawback variant options")
        except chess.engine.EngineError as exc:
            print(f"[WARN] Failed to configure variant options: {exc}")
    
    async def _persist_packet(self, packet: Dict[str, object]) -> None:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "packet": packet,
        }
        PACKET_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PACKET_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    
    async def _record_analysis(self, parsed_state: Dict, best_move: str, score: float, 
                               move_qualities: Dict, threats: List[Dict]) -> None:
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "game_id": self.game_id,
            "best_move": best_move,
            "score_cp": score,
            "move_qualities": move_qualities,
            "threats": threats,
        }
        
        BEST_MOVE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with BEST_MOVE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot) + "\n")
        
        self.latest_state = snapshot
        with STATE_SNAPSHOT_PATH.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
    
    async def _ensure_overlay(self, page):
        """Inject advanced overlay system with move quality and threat visualization."""
        board_selector = self.selectors["board_root"]
        
        try:
            board_count = await page.locator(board_selector).count()
            if board_count == 0:
                return
            
            is_injected = await page.evaluate("() => !!window.assistantAdvanced")
            if is_injected:
                return
            
            print(f"[ASSIST] Injecting advanced overlay system...")
        except Exception as e:
            print(f"[DEBUG] Overlay check failed: {e}")
            return
        
        # Inject comprehensive overlay system
        js_code = self._get_overlay_javascript(board_selector)
        
        try:
            await page.add_script_tag(content=js_code)
            print(f"[ASSIST] Advanced overlay injected successfully")
        except Exception as e:
            print(f"[WARN] Failed to inject overlay: {e}")
    
    def _get_overlay_javascript(self, board_selector: str) -> str:
        """Generate JavaScript for advanced overlay system."""
        return f"""
(() => {{
  if (window.assistantAdvanced) return;
  
  const root = document.querySelector('{board_selector}');
  if (!root) return;
  
  // Ensure square IDs
  const ensureSquareIds = () => {{
    const squares = Array.from(root.querySelectorAll('.square'));
    if (!squares.length) return false;
    const files = ['a','b','c','d','e','f','g','h'];
    for (let idx = 0; idx < squares.length; idx++) {{
      const sq = squares[idx];
      if (!sq.dataset.square) {{
        const file = files[idx % 8];
        const rank = 8 - Math.floor(idx / 8);
        sq.dataset.square = `${{file}}${{rank}}`.toUpperCase();
      }}
    }}
    return true;
  }};
  
  if (!ensureSquareIds()) return;
  
  // Style injection
  const style = document.createElement('style');
  style.textContent = `
    .assistant-best-highlight {{
      position: absolute;
      inset: 0;
      border: 3px solid rgba(0, 255, 0, 0.9);
      box-shadow: inset 0 0 15px rgba(0, 255, 0, 0.6);
      pointer-events: none;
      z-index: 10000;
    }}
    
    .assistant-quality-overlay {{
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 9999;
      opacity: 0.4;
    }}
    
    .assistant-threat-arrow {{
      position: absolute;
      pointer-events: none;
      z-index: 9998;
    }}
  `;
  document.head.appendChild(style);
  
  // Clear functions
  const clearBestHighlight = () => {{
    document.querySelectorAll('.assistant-best-highlight').forEach(el => el.remove());
  }};
  
  const clearQualityOverlays = () => {{
    document.querySelectorAll('.assistant-quality-overlay').forEach(el => el.remove());
  }};
  
  const clearThreatArrows = () => {{
    document.querySelectorAll('.assistant-threat-arrow').forEach(el => el.remove());
  }};
  
  // Highlight best move
  window.assistantHighlightBest = (start, stop) => {{
    ensureSquareIds();
    clearBestHighlight();
    
    [start, stop].forEach(sq => {{
      const target = root.querySelector(`.square[data-square="${{sq}}"]`);
      if (!target) return;
      
      const computedStyle = window.getComputedStyle(target);
      if (computedStyle.position === 'static') {{
        target.style.position = 'relative';
      }}
      
      const overlay = document.createElement('div');
      overlay.className = 'assistant-best-highlight';
      target.appendChild(overlay);
    }});
  }};
  
  // Show move quality overlays
  window.assistantShowQualities = (qualityData) => {{
    ensureSquareIds();
    clearQualityOverlays();
    
    Object.entries(qualityData).forEach(([square, data]) => {{
      const target = root.querySelector(`.square[data-square="${{square}}"]`);
      if (!target) return;
      
      const computedStyle = window.getComputedStyle(target);
      if (computedStyle.position === 'static') {{
        target.style.position = 'relative';
      }}
      
      const overlay = document.createElement('div');
      overlay.className = 'assistant-quality-overlay';
      overlay.style.backgroundColor = data.color;
      target.appendChild(overlay);
    }});
  }};
  
  // Helper to get edge point between two squares
  const getEdgePoint = (fromRect, toRect) => {{
    const fromCenterX = fromRect.left + fromRect.width / 2;
    const fromCenterY = fromRect.top + fromRect.height / 2;
    const toCenterX = toRect.left + toRect.width / 2;
    const toCenterY = toRect.top + toRect.height / 2;
    
    const dx = toCenterX - fromCenterX;
    const dy = toCenterY - fromCenterY;
    const angle = Math.atan2(dy, dx);
    
    const offset = Math.min(fromRect.width, fromRect.height) * 0.35;
    
    return {{
      x: fromCenterX + Math.cos(angle) * offset,
      y: fromCenterY + Math.sin(angle) * offset
    }};
  }};
  
  // Draw arrow between two squares
  const drawArrow = (fromSquare, toSquare, color, className) => {{
    const fromEl = root.querySelector(`.square[data-square="${{fromSquare}}"]`);
    const toEl = root.querySelector(`.square[data-square="${{toSquare}}"]`);
    if (!fromEl || !toEl) return;
    
    const fromRect = fromEl.getBoundingClientRect();
    const toRect = toEl.getBoundingClientRect();
    
    const from = getEdgePoint(fromRect, toRect);
    const to = getEdgePoint(toRect, fromRect);
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.className = className;
    svg.dataset.assistantArrow = 'true';
    svg.style.position = 'fixed';
    svg.style.top = '0';
    svg.style.left = '0';
    svg.style.width = '100%';
    svg.style.height = '100%';
    svg.style.pointerEvents = 'none';
    svg.style.zIndex = '9998';
    
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const markerId = 'arrow-' + color.replace('#', '') + '-' + Math.random();
    const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    marker.setAttribute('id', markerId);
    marker.setAttribute('markerWidth', '10');
    marker.setAttribute('markerHeight', '10');
    marker.setAttribute('refX', '5');
    marker.setAttribute('refY', '5');
    marker.setAttribute('orient', 'auto');
    
    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('points', '0 0, 10 5, 0 10');
    polygon.setAttribute('fill', color);
    marker.appendChild(polygon);
    defs.appendChild(marker);
    svg.appendChild(defs);
    
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', from.x);
    line.setAttribute('y1', from.y);
    line.setAttribute('x2', to.x);
    line.setAttribute('y2', to.y);
    line.setAttribute('stroke', color);
    line.setAttribute('stroke-width', '5');
    line.setAttribute('marker-end', `url(#${{markerId}})`);
    line.setAttribute('opacity', '0.8');
    svg.appendChild(line);
    
    document.body.appendChild(svg);
  }};
  
  // Show threat arrows
  window.assistantShowThreats = (threats) => {{
    ensureSquareIds();
    threats.forEach(threat => {{
      drawArrow(threat.from, threat.to, '#ff0000', 'assistant-threat-arrow');
    }});
  }};
  
  // Show best move arrow
  window.assistantShowBestArrow = (start, stop) => {{
    ensureSquareIds();
    drawArrow(start, stop, '#00ff00', 'assistant-best-arrow');
  }};
  
  // Clear all arrows
  window.assistantClearArrows = () => {{
    document.querySelectorAll('.assistant-threat-arrow').forEach(el => el.remove());
    document.querySelectorAll('.assistant-best-arrow').forEach(el => el.remove());
  }};
  
  // Clear all
  window.assistantClearAll = () => {{
    clearBestHighlight();
    clearQualityOverlays();
    if (window.assistantClearArrows) {{
      window.assistantClearArrows();
    }}
  }};
  
  // Add click listener to clear overlays when moves are made
  let lastPly = null;
  const checkForMoveChange = () => {{
    // This will be called periodically to detect when a move is made
    // We clear overlays when the board changes
  }};
  
  // Track selected piece for move quality analysis
  let selectedSquare = null;
  let pendingSelection = null;
  
  // Functions to get/clear selected square
  window.assistantGetSelectedSquare = () => {{
    const result = pendingSelection;
    return result;
  }};
  
  window.assistantClearSelectedSquare = () => {{
    pendingSelection = null;
  }};
  
  // Listen for clicks on squares
  root.addEventListener('click', (e) => {{
    const square = e.target.closest('.square');
    if (!square || !square.dataset.square) return;
    
    const squareName = square.dataset.square;
    const hasPiece = square.querySelector('[class*="piece"]') || square.querySelector('img');
    
    // If clicking a piece, mark for analysis
    if (hasPiece && squareName !== selectedSquare) {{
      selectedSquare = squareName;
      pendingSelection = squareName;
      console.log('[ASSIST] Piece selected:', squareName);
    }} else {{
      // Clicking empty square or same square - likely making a move
      selectedSquare = null;
      pendingSelection = null;
      // Clear overlays after move animation
      setTimeout(() => {{
        if (window.assistantClearAll) {{
          window.assistantClearAll();
        }}
      }}, 400);
    }}
  }});
  
  window.assistantAdvanced = true;
  console.log('ASSIST: Advanced overlay system ready');
}})();
"""
    
    async def _ensure_ui_panel(self, page):
        """Inject UI control panel."""
        try:
            is_injected = await page.evaluate("() => !!window.assistantUIPanel")
            if is_injected:
                return
            
            print(f"[UI] Injecting control panel...")
        except Exception as e:
            return
        
        ui_code = self._get_ui_panel_javascript()
        
        try:
            await page.add_script_tag(content=ui_code)
            print(f"[UI] Control panel injected")
        except Exception as e:
            print(f"[WARN] Failed to inject UI panel: {e}")
    
    def _get_ui_panel_javascript(self) -> str:
        """Generate JavaScript for UI control panel."""
        return """
(() => {
  if (window.assistantUIPanel) return;
  
  const panel = document.createElement('div');
  panel.id = 'assistant-ui-panel';
  panel.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    background: rgba(0, 0, 0, 0.85);
    color: white;
    padding: 15px;
    border-radius: 8px;
    font-family: Arial, sans-serif;
    font-size: 12px;
    z-index: 100000;
    min-width: 220px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
  `;
  
  panel.innerHTML = `
    <div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">Chess Assistant</div>
    <div style="margin-bottom: 8px;">
      <label><input type="checkbox" id="assist-show-player" checked> Show for Player</label>
    </div>
    <div style="margin-bottom: 8px;">
      <label><input type="checkbox" id="assist-show-opponent"> Show for Opponent</label>
    </div>
    <div style="margin-bottom: 8px;">
      <label><input type="checkbox" id="assist-show-threats" checked> Show Threats</label>
    </div>
    <div style="margin-bottom: 8px;">
      <label><input type="checkbox" id="assist-show-best" checked> Best Move</label>
    </div>
    <div style="margin-bottom: 8px;">
      <label><input type="checkbox" id="assist-show-heatmap"> Heatmap</label>
    </div>
    <div style="margin-bottom: 8px;">
      <label><input type="checkbox" id="assist-auto-play"> Auto-Play</label>
    </div>
    <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid #555;">
      <div style="margin-bottom: 4px; font-size: 11px; color: #aaa;">Click piece to see move quality</div>
    </div>
    <div style="margin-top: 8px;">
      <div style="margin-bottom: 4px;">Max Depth: <span id="depth-value">14</span></div>
      <input type="range" id="assist-depth" min="1" max="20" value="14" style="width: 100%;">
    </div>
    <div style="margin-top: 8px;">
      <div style="margin-bottom: 4px;">Max Time: <span id="time-value">2.0</span>s</div>
      <input type="range" id="assist-time" min="0.5" max="10" step="0.5" value="2.0" style="width: 100%;">
    </div>
    <div style="margin-top: 8px; font-size: 10px; color: #888;">
      Uses whichever limit is hit first
    </div>
  `;
  
  document.body.appendChild(panel);
  
  // Event listeners
  document.getElementById('assist-depth').addEventListener('input', (e) => {
    document.getElementById('depth-value').textContent = e.target.value;
  });
  
  document.getElementById('assist-time').addEventListener('input', (e) => {
    document.getElementById('time-value').textContent = e.target.value;
  });
  
  window.assistantUIPanel = true;
  console.log('ASSIST: UI panel ready');
})();
"""


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Drawback Chess Assistant")
    parser.add_argument("url", nargs="?", default="https://www.drawbackchess.com", help="Game URL")
    parser.add_argument("--dual-browser", action="store_true", default=True, help="Open opposite color window")
    parser.add_argument("--no-dual-browser", action="store_true", help="Disable opposite color window")
    args = parser.parse_args()
    
    dual_browser = args.dual_browser and not args.no_dual_browser
    assistant = AdvancedAssistant(dual_browser=dual_browser)
    
    try:
        asyncio.run(assistant.run(args.url))
    except KeyboardInterrupt:
        print("\nAssistant stopped")


if __name__ == "__main__":
    main()
