"""Live site assistant that captures legal moves, queries Stockfish, and highlights the best move."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import chess
import chess.engine
from playwright.async_api import TimeoutError, async_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.interface.packet_parser import PacketParser  # noqa: E402
from src.engine.variant_loader import load_drawback_config  # noqa: E402

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


class LegalMoveAssistant:
    def __init__(self, engine_path: Optional[Path] = None):
        self.selectors = load_selectors()
        self.engine_path = engine_path or detect_engine()
        self.engine = chess.engine.SimpleEngine.popen_uci(str(self.engine_path))
        self.variant_config = load_drawback_config()
        self._apply_variant_config()
        self.browser = None
        self.page = None
        self.latest_state = {}
        self.player_color = None
        self.last_highlighted_fen = None
        self.game_id = None
        self.polling_task = None

    async def run(self, url: str) -> None:
        async with async_playwright() as playwright:
            self.browser = await playwright.chromium.launch(headless=False)
            context = await self.browser.new_context()
            self.page = await context.new_page()

            self._attach_socket_logger(self.page)

            print(f"[ASSIST] Navigating to {url}")
            await self.page.goto(url)

            print("[ASSIST] Waiting for game board...")
            try:
                while True:
                    await self._ensure_overlay(self.page)
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                if self.polling_task:
                    self.polling_task.cancel()
                await context.close()
        self.engine.close()

    def _attach_socket_logger(self, page):
        def handle_socket(ws):
            ws.on(
                "framereceived",
                lambda payload: asyncio.create_task(self._handle_payload(payload)),
            )

        page.on("socket", handle_socket)
        page.on("response", lambda res: asyncio.create_task(self._handle_response(res)))

    async def _handle_response(self, response):
        url = response.url
        if "/game" not in url and "/move" not in url and "/new_game" not in url:
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
                        print(f"[ASSIST] New game detected: {game_id} (was {self.game_id})")
                    else:
                        print(f"[ASSIST] Detected game ID: {game_id}")
                    self.game_id = game_id
                    self.last_highlighted_fen = None
                    self.latest_state = {}
                
                await self._process_game_data(data)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[ERROR] Failed to process response from {url}: {e}")

    async def _handle_payload(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return

        if not isinstance(data, dict) or "game" not in data or not data.get("success"):
            return

        ply = data.get("game", {}).get("ply", "?")
        turn = data.get("game", {}).get("turn", "?")
        print(f"[DEBUG] WebSocket packet: ply={ply}, turn={turn}")
        await self._process_game_data(data)

    async def _process_game_data(self, data: dict) -> None:
        await self._persist_packet(data)
        
        game_data = data.get("game", {})
        board_state = game_data.get("board")
        turn = game_data.get("turn")
        last_move = game_data.get("lastMove")
        ply = game_data.get("ply", 0)
        
        if not board_state or not turn or not self.player_color:
            print(f"[DEBUG] Skipping: board={bool(board_state)}, turn={turn}, player={self.player_color}")
            return
        
        if turn != self.player_color:
            print(f"[DEBUG] Waiting for your turn (current: {turn})")
            return
        
        current_moves = game_data.get("moves", {})
        legal_moves = []
        for start_sq, destinations in current_moves.items():
            for move_obj in destinations:
                stop_sq = move_obj.get("stop")
                if start_sq and stop_sq:
                    legal_moves.append(f"{start_sq}{stop_sq}".lower())
        
        print(f"[DEBUG] Ply {ply}: {len(legal_moves)} legal moves, turn={turn}, lastMove={last_move}")
        
        if not legal_moves:
            print(f"[DEBUG] Waiting for server to send legal moves (moves field is empty)")
            return

        fen = PacketParser.board_to_fen(board_state, turn)
        
        if self.last_highlighted_fen == fen:
            print(f"[DEBUG] Skipping: position unchanged")
            return
        
        print(f"[DEBUG] FEN: {fen[:50]}...")
        print(f"[DEBUG] Evaluating {len(legal_moves)} legal moves with Stockfish...")
        
        best_move, score = self._score_moves(fen, legal_moves)
        if not best_move:
            print(f"[ERROR] Stockfish found no valid move from {len(legal_moves)} legal moves")
            print(f"[ERROR] Sample moves: {legal_moves[:5]}")
            return

        print(f"[ASSIST] Best move: {best_move} ({score:.2f} cp)")
        
        parsed = PacketParser.parse_game_state(data)
        await self._record_best_move(parsed, best_move, score, legal_moves)
        await self._highlight_move(best_move, score)
        print(f"[DEBUG] Highlight attempted for {best_move}")
        
        self.last_highlighted_fen = fen
    
    async def _poll_game_state(self):
        """Actively poll game state for AI games where opponent moves don't trigger HTTP responses"""
        print(f"[ASSIST] Starting active polling for game {self.game_id}")
        
        import random
        poll_count = 0
        last_ply = None
        
        while True:
            try:
                await asyncio.sleep(2)
                poll_count += 1
                
                if not self.page or not self.game_id or not self.player_color:
                    print(f"[POLL #{poll_count}] Skipping: page/game_id/player_color not ready")
                    continue
                
                app_num = random.randint(1, 16)
                url = f"https://www.drawbackchess.com/app{app_num}/game?id={self.game_id}&color={self.player_color}"
                
                try:
                    response = await self.page.request.get(url)
                    if response.status != 200:
                        print(f"[POLL #{poll_count}] HTTP {response.status}")
                        continue
                    
                    body = await response.text()
                    data = json.loads(body)
                    
                    if isinstance(data, dict) and "game" in data and data.get("success"):
                        ply = data.get('game', {}).get('ply', '?')
                        turn = data.get('game', {}).get('turn', '?')
                        
                        if ply != last_ply:
                            print(f"[POLL #{poll_count}] New state: ply={ply}, turn={turn}")
                            last_ply = ply
                            await self._process_game_data(data)
                    else:
                        print(f"[POLL #{poll_count}] Invalid response: success={data.get('success')}, has_game={('game' in data)}")
                except json.JSONDecodeError as e:
                    print(f"[POLL #{poll_count}] JSON decode failed: {e}")
                except Exception as e:
                    print(f"[POLL #{poll_count}] Request failed: {e}")
                    
            except asyncio.CancelledError:
                print(f"[ASSIST] Polling stopped after {poll_count} polls")
                break
            except Exception as e:
                print(f"[ERROR] Polling error: {e}")
                await asyncio.sleep(5)

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
            if await page.locator(board_selector).count() == 0:
                return
            
            is_injected = await page.evaluate("() => !!window.assistantHighlight")
            if is_injected:
                return
            
            print(f"[ASSIST] Board found ({board_selector}), injecting overlay...")

        except Exception:
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
            print("[DEBUG] No page available for highlight")
            return
        start = uci_move[:2].upper()
        stop = uci_move[2:4].upper()
        
        for attempt in range(10):
            try:
                is_ready = await self.page.evaluate("() => typeof window.assistantHighlight === 'function'")
                if is_ready:
                    await self.page.evaluate(f"window.assistantHighlight('{start}', '{stop}')")
                    print(f"[DEBUG] Highlight call succeeded: {start} -> {stop}")
                    return
            except Exception:
                pass
            await asyncio.sleep(0.1)
        
        print(f"[DEBUG] Highlight call failed: overlay not ready after 1s")

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
            print(f"[ASSIST] Applied Drawback variant options from {self.variant_config.config_file}")
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

    parser = argparse.ArgumentParser(description="Drawback site assistant")
    parser.add_argument("url", nargs="?", default="https://www.drawbackchess.com", help="Target game URL or lobby")
    args = parser.parse_args()

    assistant = LegalMoveAssistant()

    try:
        asyncio.run(assistant.run(args.url))
    except KeyboardInterrupt:
        print("\nAssistant stopped")


if __name__ == "__main__":
    main()
