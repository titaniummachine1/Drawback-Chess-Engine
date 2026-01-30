"""Chess assistant using Socket.IO for real-time game state updates."""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
    candidates = [
        REPO_ROOT / "engines" / "stockfish.exe",
        REPO_ROOT / "engines" / "stockfish",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No Stockfish binary found in engines/ directory")


def calculate_port(game_id: str) -> int:
    """Calculate Socket.IO port from game ID (matches GamePage.js logic)."""
    hash_val = 0
    for char in game_id:
        hash_val = ((hash_val << 5) - hash_val) + ord(char)
        hash_val = hash_val & 0xFFFFFFFF
    
    while hash_val >= 2**32:
        hash_val -= 2**32
    
    return 5001 + (hash_val % 16)


class SocketIOAssistant:
    def __init__(self, engine_path: Optional[Path] = None, dual_browser: bool = True):
        self.selectors = load_selectors()
        self.engine_path = engine_path or detect_engine()
        self.engine = chess.engine.SimpleEngine.popen_uci(str(self.engine_path))
        self.variant_config = load_drawback_config()
        self._apply_variant_config()
        
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
        
    async def run(self, url: str) -> None:
        async with async_playwright() as playwright:
            self.browser = await playwright.chromium.launch(headless=False)
            context = await self.browser.new_context()
            self.page = await context.new_page()
            
            self.page.on("response", lambda res: asyncio.create_task(self._handle_response(res)))
            
            print(f"[ASSIST] Navigating to {url}")
            await self.page.goto(url)
            
            print("[ASSIST] Waiting for game to start...")
            
            try:
                while True:
                    await self._ensure_overlay(self.page)
                    
                    if self.game_id and self.player_color and not self.sio and not self.socket_connecting:
                        if self._can_attempt_socket_connect():
                            await self._connect_socketio()

                    if self.dual_browser and self.secondary_page is None:
                        await self._ensure_dual_browser(context)
                    
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                if self.sio:
                    await self.sio.disconnect()
                if self.secondary_browser:
                    await self.secondary_browser.close()
                await context.close()
        
        self.engine.close()

    def _can_attempt_socket_connect(self) -> bool:
        if self.last_socket_failure is None:
            return True
        return (time.monotonic() - self.last_socket_failure) > 5

    async def _ensure_dual_browser(self, context) -> None:
        if not self.game_id or not self.player_color:
            return

        opposite_color = "black" if self.player_color == "white" else "white"
        url = f"https://www.drawbackchess.com/game/{self.game_id}/{opposite_color}"
        
        print(f"[ASSIST] Launching separate browser for opposite color...")
        playwright = context._browser._playwright
        self.secondary_browser = await playwright.chromium.launch(headless=False)
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
        """Process Socket.IO 'update' event."""
        game_data = data.get('game')
        if not game_data:
            print("[DEBUG] Update event has no game data")
            return
        
        await self._persist_packet({'game': game_data, 'success': True})
        
        board_state = game_data.get('board')
        turn = game_data.get('turn')
        ply = game_data.get('ply', 0)
        
        if not board_state or not turn or not self.player_color:
            print(f"[DEBUG] Incomplete data: board={bool(board_state)}, turn={turn}, player={self.player_color}")
            return
        
        if turn != self.player_color:
            print(f"[DEBUG] Waiting for your turn (current: {turn})")
            return
        
        current_moves = game_data.get('moves', {})
        legal_moves = []
        for start_sq, destinations in current_moves.items():
            for move_obj in destinations:
                stop_sq = move_obj.get('stop')
                if start_sq and stop_sq:
                    legal_moves.append(f"{start_sq}{stop_sq}".lower())
        
        print(f"[UPDATE] Ply {ply}: {len(legal_moves)} legal moves, turn={turn}")
        print(f"[DEBUG] Legal moves: {legal_moves[:10]}{'...' if len(legal_moves) > 10 else ''}")
        
        if not legal_moves:
            print(f"[DEBUG] No legal moves available")
            return
        
        fen = PacketParser.board_to_fen(board_state, turn)
        
        if self.last_highlighted_fen == fen:
            print(f"[DEBUG] Position unchanged, skipping")
            return
        
        print(f"[DEBUG] FEN: {fen[:50]}...")
        print(f"[DEBUG] Evaluating {len(legal_moves)} legal moves with Stockfish...")
        
        best_move, score = self._score_moves(fen, legal_moves)
        if not best_move:
            print(f"[ERROR] Stockfish found no valid move")
            return
        
        print(f"[ASSIST] Best move: {best_move} ({score:.2f} cp)")
        
        parsed = PacketParser.parse_game_state({'game': game_data, 'success': True})
        await self._record_best_move(parsed, best_move, score, legal_moves)
        await self._highlight_move(best_move, score)
        
        self.last_highlighted_fen = fen
    
    async def _handle_response(self, response):
        """Capture HTTP responses to detect game ID and player color."""
        url = response.url
        if "/game" not in url and "/new_game" not in url:
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
                    else:
                        print(f"[ASSIST] Detected game ID: {game_id}")
                    self.game_id = game_id
                    self.last_highlighted_fen = None
                    self.latest_state = {}
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
    
    def _score_moves(self, fen: str, uci_moves: List[str]):
        board = chess.Board(fen)
        moves = []
        for move_str in uci_moves:
            try:
                moves.append(chess.Move.from_uci(move_str))
            except ValueError:
                continue
        if not moves:
            return None, 0.0
        
        limit = chess.engine.Limit(depth=14)
        info = self.engine.analyse(board, limit, root_moves=moves)
        move = info.get("pv", [None])[0]
        if move is None:
            return None, 0.0
        score = info["score"].white().score(mate_score=10000)
        return move.uci(), float(score)
    
    async def _ensure_overlay(self, page):
        board_selector = self.selectors["board_root"]
        square_template = self.selectors["square_template"]
        overlay_id = self.selectors["overlay_id"]
        
        try:
            board_count = await page.locator(board_selector).count()
            if board_count == 0:
                return
            
            is_injected = await page.evaluate("() => !!window.assistantHighlight")
            if is_injected:
                return
            
            print(f"[ASSIST] Board found ({board_selector}), injecting overlay...")
        except Exception as e:
            print(f"[DEBUG] Overlay check failed: {e}")
            return
        
        js_helper = f"""
(() => {{
  if (window.assistantHighlight) {{
    return;
  }}

  const root = document.querySelector('{board_selector}');
  if (!root) {{
    return;
  }}

  const ensureSquareIds = () => {{
    const squares = Array.from(root.querySelectorAll('.square'));
    if (!squares.length) {{
      return false;
    }}
    const files = ['a','b','c','d','e','f','g','h'];
    for (let idx = 0; idx < squares.length; idx += 1) {{
      const sq = squares[idx];
      if (!sq.dataset.square) {{
        const file = files[idx % 8];
        const rank = 8 - Math.floor(idx / 8);
        sq.dataset.square = `${{file}}${{rank}}`.toUpperCase();
      }}
    }}
    return true;
  }};

  if (!ensureSquareIds()) {{
    console.warn('ASSIST: Square nodes missing inside board root');
    return;
  }}

  const existing = document.getElementById('{overlay_id}');
  if (existing) {{
    existing.remove();
  }}

  const style = document.createElement('style');
  style.id = '{overlay_id}-style';
  style.textContent = `
    .assistant-highlight {{
      position: absolute;
      inset: 0;
      border: 3px solid rgba(0, 255, 0, 0.9);
      box-shadow: inset 0 0 15px rgba(0, 255, 0, 0.6);
      pointer-events: none;
      z-index: 10000;
    }}
  `;
  document.head.appendChild(style);

  function clearHighlights() {{
    document.querySelectorAll('.assistant-highlight').forEach((node) => node.remove());
  }}

  function highlightSquare(square) {{
    const selector = `{square_template}`.replace('%s', square.toUpperCase());
    const target = document.querySelector(selector);
    if (!target) {{
      console.warn('ASSIST: Square not found for highlight:', square);
      return;
    }}
    
    const computedStyle = window.getComputedStyle(target);
    if (computedStyle.position === 'static') {{
        target.style.position = 'relative';
    }}

    const overlay = document.createElement('div');
    overlay.className = 'assistant-highlight';
    target.appendChild(overlay);
  }}

  window.assistantHighlight = (start, stop) => {{
    ensureSquareIds();
    clearHighlights();
    highlightSquare(start);
    highlightSquare(stop);
  }};
  
  console.log('ASSIST: Overlay injected successfully');
}})();
"""
        try:
            await page.add_script_tag(content=js_helper)
        except Exception as e:
            print(f"[WARN] Failed to inject overlay: {e}")
    
    async def _highlight_move(self, uci_move: str, score: float):
        if not self.page:
            return
        
        start = uci_move[:2].upper()
        stop = uci_move[2:4].upper()
        
        for attempt in range(10):
            try:
                is_ready = await self.page.evaluate("() => typeof window.assistantHighlight === 'function'")
                if is_ready:
                    await self.page.evaluate(f"window.assistantHighlight('{start}', '{stop}')")
                    print(f"[DEBUG] Highlighted: {start} -> {stop}")
                    return
            except Exception:
                pass
            await asyncio.sleep(0.1)
        
        print(f"[DEBUG] Highlight failed: overlay not ready")
    
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
    
    async def _record_best_move(self, parsed_state: Dict[str, object], best_move: str, score: float, legal_moves: List[str]) -> None:
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "game_id": parsed_state.get("game_id"),
            "turn": parsed_state.get("turn"),
            "ply": parsed_state.get("ply"),
            "best_move": best_move,
            "score_cp": score,
            "legal_moves": legal_moves,
            "drawbacks": {
                "white": parsed_state.get("white_drawback"),
                "black": parsed_state.get("black_drawback"),
                "revealed": parsed_state.get("revealed_drawbacks"),
            },
        }
        
        BEST_MOVE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with BEST_MOVE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot) + "\n")
        
        self.latest_state = snapshot
        with STATE_SNAPSHOT_PATH.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Drawback Chess Socket.IO Assistant")
    parser.add_argument("url", nargs="?", default="https://www.drawbackchess.com", help="Game URL")
    parser.add_argument("--dual-browser", action="store_true", default=True, help="Open opposite color window")
    parser.add_argument("--no-dual-browser", action="store_true", help="Disable opposite color window")
    args = parser.parse_args()
    
    dual_browser = args.dual_browser and not args.no_dual_browser
    assistant = SocketIOAssistant(dual_browser=dual_browser)
    
    try:
        asyncio.run(assistant.run(args.url))
    except KeyboardInterrupt:
        print("\nAssistant stopped")


if __name__ == "__main__":
    main()
