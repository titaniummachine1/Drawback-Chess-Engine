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

    async def run(self, url: str) -> None:
        async with async_playwright() as playwright:
            self.browser = await playwright.chromium.launch(headless=False)
            context = await self.browser.new_context()
            self.page = await context.new_page()

            await self._inject_overlay(self.page)
            self._attach_socket_logger(self.page)

            print(f"[ASSIST] Navigating to {url}")
            await self.page.goto(url)

            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await context.close()
        self.engine.close()

    def _attach_socket_logger(self, page):
        def handle_socket(ws):
            ws.on(
                "framereceived",
                lambda payload: asyncio.create_task(self._handle_payload(payload)),
            )

        page.on("socket", handle_socket)

    async def _handle_payload(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return

        if not isinstance(data, dict) or "game" not in data:
            return

        await self._persist_packet(data)

        parsed = PacketParser.parse_game_state(data)
        legal_moves = parsed.get("legal_moves") or []
        board_state = parsed.get("board")
        turn = parsed.get("turn")
        if not legal_moves or not board_state or not turn:
            return

        fen = PacketParser.board_to_fen(board_state, turn)
        best_move, score = self._score_moves(fen, legal_moves)
        if not best_move:
            return

        print(f"[ASSIST] Best move: {best_move} ({score:.2f} cp)")
        await self._record_best_move(parsed, best_move, score, legal_moves)
        await self._highlight_move(best_move, score)

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

    async def _inject_overlay(self, page):
        board_selector = self.selectors["board_root"]
        square_template = self.selectors["square_template"]
        overlay_id = self.selectors["overlay_id"]

        js_helper = f"""
(() => {{
  if (window.assistantHighlight) {{
    return;
  }}

  const root = document.querySelector('{board_selector}');
  if (!root) {{
    throw new Error('Board root not found for selector {board_selector}');
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
      border: 3px solid rgba(0, 200, 0, 0.8);
      box-shadow: inset 0 0 10px rgba(0, 255, 0, 0.5);
      pointer-events: none;
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
      throw new Error('Square not found: ' + square);
    }}
    const container = target.closest('[data-square], .square, div');
    const rectTarget = container || target;
    const overlay = document.createElement('div');
    overlay.className = 'assistant-highlight';
    const parent = rectTarget;
    parent.style.position = parent.style.position || 'relative';
    parent.appendChild(overlay);
  }}

  window.assistantHighlight = (start, stop) => {{
    clearHighlights();
    highlightSquare(start);
    highlightSquare(stop);
  }};
}})();
"""
        await page.add_script_tag(content=js_helper)

    async def _highlight_move(self, uci_move: str, score: float):
        if not self.page:
            return
        start = uci_move[:2]
        stop = uci_move[2:4]
        await self.page.evaluate("(start, stop) => window.assistantHighlight(start, stop)", start, stop)

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
