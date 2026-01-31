"""Advanced Chess Assistant - Modular Refactor Entry Point."""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

import chess
from playwright.async_api import async_playwright

# Fix imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.interface.packet_parser import PacketParser
from src.engine.variant_loader import load_drawback_config

from assistant.core.settings import SettingsManager
from assistant.core.engine import EngineManager
from assistant.core.visuals import VisualManager
from assistant.core.socket_manager import SocketManager
from assistant.core.move_manager import MoveManager

class ModularAssistant:
    def __init__(self, dual_browser: bool = False):
        self.repo_root = REPO_ROOT
        from assistant.advanced_assistant import load_selectors
        self.selectors = load_selectors()
        self.settings_mgr = SettingsManager(REPO_ROOT / "assistant" / "settings.json")
        self.engine_mgr = EngineManager(self._detect_engine(), load_drawback_config(), self.settings_mgr)
        
        self.game_id = None
        self.player_color = None
        self.username = None
        self.port = None
        self.current_ply = 0
        self.current_fen = None
        self.current_legal_moves = []
        
        self.dual_browser = dual_browser
        self.socket_mgr: Optional[SocketManager] = None
        self.visual_mgr: Optional[VisualManager] = None
        self.move_mgr: Optional[MoveManager] = None
        
        self.last_fen_processed = None

    def _detect_engine(self) -> Path:
        candidates = [
            self.repo_root / "engines" / "fairy-stockfish_x86-64.exe",
            self.repo_root / "engines" / "fairy-stockfish.exe",
            self.repo_root / "engines" / "fairy-stockfish",
            self.repo_root / "engines" / "stockfish.exe",
        ]
        for c in candidates:
            if c.exists(): return c
        raise FileNotFoundError("No engine found")

    async def run(self, url: str):
        async with async_playwright() as p:
            user_data_dir = self.repo_root / "assistant" / "browser_data"
            user_data_dir.mkdir(exist_ok=True)
            
            context = await p.chromium.launch_persistent_context(
                str(user_data_dir),
                headless=False,
                args=['--start-maximized'],
                viewport=None,
                no_viewport=True
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            self.visual_mgr = VisualManager(page, self.selectors.get("board_root", ".board"))
            self.move_mgr = MoveManager(page)
            
            page.on("response", self._handle_http_response)
            page.on("console", lambda m: print(f"[BROWSER] {m.type}: {m.text}") if m.type in ["error", "warning"] else None)
            
            print(f"[ASSIST] Navigating to {url}")
            await page.goto(url)
            
            try:
                while not page.is_closed():
                    # 1. Inject UI and Overlays
                    await self.visual_mgr.inject_ui_panel()
                    await self.visual_mgr.inject_visuals()
                    
                    # 2. Sync Settings
                    ui_settings = await self.visual_mgr.get_ui_settings()
                    if ui_settings:
                        self.settings_mgr.update(ui_settings)
                    
                    # 3. Handle Auto-Queue
                    if self.settings_mgr.settings.get("auto_queue") and not self.game_id:
                        await self.move_mgr.auto_join_queue(self.username)
                    
                    # 4. Socket Connection Logic
                    if self.game_id and not self.socket_mgr:
                        self.port = self._calculate_port(self.game_id)
                        self.socket_mgr = SocketManager(self.game_id, self.port, self._on_game_update)
                        await self.socket_mgr.connect(self.username)
                    
                    # 5. Check Piece Selection
                    selected = await self.visual_mgr.get_selected_square()
                    if selected and self.settings_mgr.settings.get("show_move_quality"):
                        await self._analyze_selected_piece(selected)
                        await self.visual_mgr.clear_selected_square()
                    
                    await asyncio.sleep(0.5)
            finally:
                if self.socket_mgr: await self.socket_mgr.disconnect()
                self.engine_mgr.close()
                await context.close()

    def _calculate_port(self, game_id: str) -> int:
        hash_val = 0
        for char in game_id:
            hash_val = ((hash_val << 5) - hash_val) + ord(char)
            hash_val &= 0xFFFFFFFF
        return 5001 + (hash_val % 16)

    async def _handle_http_response(self, response):
        if "/game?" in response.url:
            try:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(response.url)
                params = parse_qs(parsed.query)
                
                gid = params.get('id', [None])[0]
                color = params.get('color', [None])[0]
                user = params.get('username', [None])[0]
                
                if gid and (gid != self.game_id):
                    print(f"[ASSIST] New Game: {gid} ({color})")
                    self.game_id = gid
                    self.player_color = color
                    self.username = user
                    if self.socket_mgr:
                        await self.socket_mgr.disconnect()
                        self.socket_mgr = None
            except: pass

    async def _on_game_update(self, data: dict):
        game = data.get('game', {})
        if not game: return
        
        turn = game.get('turn')
        ply = game.get('ply', 0)
        board_state = game.get('board')
        result = game.get('result')
        
        # Reset game ID if game ended to allow auto-queue
        if result:
            print(f"[GAME] Ended: {result}")
            self.game_id = None
            self.last_fen_processed = None
            await self.visual_mgr.clear_all()
            return

        if not board_state or not turn: return
        
        fen = PacketParser.board_to_fen(board_state, turn)
        if fen == self.last_fen_processed: 
            # Even if FEN is same, we might need to refresh threats if turn changed
            # or if overlays were cleared by some other event
            return
            
        self.last_fen_processed = fen
        self.current_fen = fen
        self.current_ply = ply
        
        # Extract legal moves
        moves_data = game.get('moves', {})
        self.current_legal_moves = []
        for start, targets in moves_data.items():
            for t in targets:
                self.current_legal_moves.append(f"{start}{t.get('stop')}".lower())
        
        await self.visual_mgr.clear_all()
        
        # Analyze
        best_move, score = self.engine_mgr.score_moves(fen, self.current_legal_moves)
        if not best_move: return
        
        print(f"[ANALYSIS] Best: {best_move} ({score})")
        
        # Always detect and show threats when enabled
        if self.settings_mgr.settings.get("show_threats"):
            threats = self._detect_threats_sync(fen, turn)
            print(f"[THREATS] Found {len(threats)} threats")
            await self.visual_mgr.show_threats(threats)

        # Show Best Move for our turn
        if self.settings_mgr.settings.get("show_best_move") and turn == self.player_color:
            await self.visual_mgr.highlight_best_move(best_move[:2], best_move[2:4])
            
        # Handle Auto-Play
        if self.settings_mgr.settings.get("auto_play") and turn == self.player_color:
            await self.move_mgr.submit_move(self.game_id, self.player_color, self.username, self.port, best_move, ply)

    def _detect_threats_sync(self, fen: str, turn: str) -> list:
        board = chess.Board(fen)
        threats = []
        our_color = chess.WHITE if self.player_color == "white" else chess.BLACK
        opp_color = chess.BLACK if our_color == chess.WHITE else chess.WHITE
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == our_color:
                attackers = board.attackers(opp_color, square)
                for attacker_sq in attackers:
                    threats.append({
                        'from': chess.square_name(attacker_sq).upper(),
                        'to': chess.square_name(square).upper()
                    })
        return threats

    async def _analyze_selected_piece(self, square: str):
        if not self.current_fen or not self.current_legal_moves: return
        
        piece_moves = [m for m in self.current_legal_moves if m[:2].upper() == square.upper()]
        if not piece_moves: return
        
        print(f"[QUALITY] Analyzing moves from {square}...")
        
        async def update_qualities(move_scores):
            best_overall, best_score = self.engine_mgr.score_moves(self.current_fen, self.current_legal_moves)
            quality_data = {}
            for move, score in move_scores.items():
                cp_loss = abs(best_score - score)
                # Map cp_loss to quality strings (simplified for now)
                color = "#00ff00" if cp_loss < 50 else "#ffff00" if cp_loss < 150 else "#ff0000"
                quality_data[move[2:4].upper()] = {"color": color}
            await self.visual_mgr.show_move_qualities(quality_data)

        await self.engine_mgr.evaluate_moves_progressive(self.current_fen, piece_moves, callback=update_qualities)


if __name__ == "__main__":
    assistant = ModularAssistant()
    asyncio.run(assistant.run("https://www.drawbackchess.com"))
