"""
Self-Play Automation with "No-Lag" Engine Architecture.
Hosts two browser instances, plays a game using a persistent engine + MCTS stub.
"""

import asyncio
import logging
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright
from src.engine.stockfish_wrapper import StockfishWrapper
from src.interface.packet_parser import PacketParser

import chess
import sys
import os

# Ensure the project root is in sys.path for "src" imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# CONFIG
ENGINE_PATH = "C:/GitHubProjekty/drawbackChessAi/engines/stockfish.exe"
SITE_URL = "https://drawbackchess.com"
TRAINING_FILE = "data/training_data.jsonl"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DummyNetwork:
    """Placeholder for the 'Ingot Brain'."""

    def predict_legality_mask(self, fen: str, history: list) -> float:
        # Return probability 0.0-1.0
        return random.random()


class SelfPlayController:
    def __init__(self):
        self.engine = None
        self.network = DummyNetwork()
        self.training_file = Path(TRAINING_FILE)
        self.training_file.parent.mkdir(exist_ok=True)

    async def start(self):
        try:
            self.engine = StockfishWrapper(ENGINE_PATH)
        except Exception as e:
            logger.error(f"Could not start engine: {e}")
            logger.warning(
                "Continuing without engine (will crash on move gen)...")

        async with async_playwright() as p:
            # 1. Launch Dual Browsers
            browser_a = await p.chromium.launch(headless=False, args=["--window-position=0,0", "--window-size=800,800"])
            context_a = await browser_a.new_context()
            page_a = await context_a.new_page()

            browser_b = await p.chromium.launch(headless=False, args=["--window-position=800,0", "--window-size=800,800"])
            context_b = await browser_b.new_context()
            page_b = await context_b.new_page()

            # 2. Setup Game (Simplified)
            # Window A creates the game
            game_url = await self.create_game(page_a)

            # Window B joins as black
            await self.join_game(page_b, game_url)

            # 3. Attach Listeners & Play
            # We need to track the latest "Server Truth"
            self.server_legal_moves = {}  # game_id -> list of moves

            # Hook up packet capture for Reality Check
            await self.attach_listeners(page_a, "WHITE")
            await self.attach_listeners(page_b, "BLACK")

            # Game Loop
            # We track whose turn it is from the intercepted packets
            self.current_turn_color = None
            self.latest_fen = None
            self.last_move_uci = None

            while True:
                await asyncio.sleep(0.1)

                # Check whose turn?
                # This needs to be updated by handle_response
                if self.latest_fen and self.current_turn_color:
                    # Decide move
                    move = await self.decide_move(self.latest_fen)
                    if move:
                        if self.current_turn_color == "white":
                            await self.execute_move(page_a, move)
                        else:
                            await self.execute_move(page_b, move)

                        # Wait for next turn (reset state to avoid spam)
                        self.latest_fen = None

    async def decide_move(self, fen: str):
        """
        Decision Logic:
        1. Get Physical Moves
        2. Check Special Rules (King En Passant)
        3. Filter by AI (Subtractive Mask) - TODO
        4. Pick best Eval from remaining
        """
        if not self.engine:
            return None

        # 1. Physical Moves (via Engine)
        potential_moves = self.engine.get_physical_moves(fen)
        if not potential_moves:
            return None
        candidates = set(potential_moves)

        # 1.5 Special Rule: King En Passant Capture
        # We only check this if the opponent just castled to save calculation time.
        is_king_capture_possible = False
        if self.last_move_uci in ["e1g1", "e1c1", "e8g8", "e8c8"]:
            is_king_capture_possible = True

        if is_king_capture_possible:
            board = chess.Board(fen)
            opponent = not board.turn
            opp_king_sq = board.king(opponent)

            # Define 'Ghost' squares where the King can be captured
            ghost_squares = []
            if opponent == chess.WHITE:
                if self.last_move_uci == "e1g1":
                    ghost_squares = [chess.F1, chess.E1]
                elif self.last_move_uci == "e1c1":
                    ghost_squares = [chess.D1, chess.E1]
            else:
                if self.last_move_uci == "e8g8":
                    ghost_squares = [chess.F8, chess.E8]
                elif self.last_move_uci == "e8c8":
                    ghost_squares = [chess.D8, chess.E8]

            winning_moves = []
            for move_uci in candidates:
                to_sq = chess.parse_square(move_uci[2:4])
                if to_sq in ghost_squares:
                    winning_moves.append(move_uci)

            if winning_moves:
                logger.info(
                    f"FOUND WINNING MOVES (King Capture): {winning_moves}")
                return winning_moves[0]

        # 3. Eval & Pick
        # Simple Random fallback for now until Policy Network is active
        final_candidates = list(candidates)
        # TODO: Use wrapper.get_eval(fen_after_move)
        return random.choice(final_candidates) if final_candidates else None

    async def handle_initial_popups(self, page):
        """Handle ELO selection and 'How to Play' notice that appear on first visit."""
        # 1. Handle ELO selection if it appears
        try:
            intermediate = page.get_by_text("Intermediate")
            if await intermediate.is_visible(timeout=3000):
                logger.info("Setting ELO to Intermediate...")
                await intermediate.click()
        except:
            pass

        # 2. Handle 'How to Play' notice (often has a 'Close' button or 'X')
        try:
            close_btn = page.get_by_role("button", name="Close")
            if await close_btn.is_visible(timeout=2000):
                logger.info("Closing 'How to Play' notice...")
                await close_btn.click()
        except:
            pass

    async def create_game(self, page):
        logger.info("Creating game via 'Play vs Friend' Flow...")
        await page.goto(SITE_URL)

        # Handle first-time popups
        await self.handle_initial_popups(page)

        # 1. Click Play vs Friend
        await page.get_by_text("Play vs Friend").click()

        # 2. Click HOST GAME button (blue button in image)
        logger.info("Clicking 'HOST GAME'...")
        host_btn = page.get_by_text("HOST GAME")
        await host_btn.wait_for(state="visible", timeout=5000)
        await host_btn.click()

        # 3. Select White Piece at the bottom of the dialog
        # The white piece is the left-most icon in the piece selection
        logger.info("Selecting 'White' piece...")
        white_piece = page.get_by_alt_text("White King")
        await white_piece.wait_for(state="visible", timeout=5000)
        await white_piece.click()

        # 4. Wait for URL to change to /game/...
        logger.info("Waiting for game session...")
        await page.wait_for_url("**/game/**", timeout=15000)
        game_url = page.url
        logger.info(f"Game created: {game_url}")
        return game_url

    async def join_game(self, page, url):
        # The user's trick: replace /white with /black
        join_url = url
        if "/white" in url:
            join_url = url.replace("/white", "/black")
        elif "/black" in url:
            join_url = url.replace("/black", "/white")

        logger.info(f"Joining opposite side at {join_url}...")
        await page.goto(join_url)
        await self.handle_initial_popups(page)

    async def attach_listeners(self, page, side):
        page.on("response", lambda res: asyncio.create_task(
            self.handle_response(res, side)))

    async def handle_response(self, response, side):
        # Capture legal moves "Reality Check"
        try:
            if "game" in response.url and response.request.method == "POST":  # Heuristic
                body = await response.text()
                if "moves" in body:
                    data = json.loads(body)
                    parsed = PacketParser.parse_game_state(data)
                    self.server_legal_moves[parsed['game_id']
                                            ] = parsed['legal_moves']

                    # Convert to FEN for Engine/AI
                    fen = PacketParser.board_to_fen(
                        parsed['board'], parsed['turn'])

                    self.current_turn_color = parsed['turn']
                    self.latest_fen = fen
                    # Track last move to optimize King En Passant logic
                    last_move_obj = data.get("game", {}).get("lastMove")
                    if last_move_obj:
                        self.last_move_uci = (last_move_obj.get(
                            "start", "") + last_move_obj.get("stop", "")).lower()

                    # TRIGGER LEARNING HERE
                    await self.run_learning_step(fen, parsed['legal_moves'])
        except:
            pass

    async def run_learning_step(self, fen, truth_moves):
        """
        The Core Learning Loop:
        1. Get Physical Moves (Engine)
        2. Get AI Prediction
        3. Save Truth for Training
        """
        if not self.engine:
            return

        # 1. Physics (What COLD happen?)
        try:
            physical_moves = self.engine.get_physical_moves(fen)
        except Exception:
            # Engine might be busy or crashed
            return

        # 2. Prediction (What we THOUGHT would happen)
        # For now, just a dummy value
        prediction_mask = self.network.predict_legality_mask(fen, [])

        # 3. Save Data (The Lesson)
        sample = {
            "fen": fen,
            "physical_moves": physical_moves,
            "legal_moves": truth_moves,
            "prediction_mask": prediction_mask,
            "timestamp": "TODO"  # Add timestamp
        }

        # Append to JSONL
        with open(self.training_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(sample) + "\n")

        logger.info(
            f"Learned from position. Physical: {len(physical_moves)}, Legal: {len(truth_moves)}")


if __name__ == "__main__":
    controller = SelfPlayController()
    asyncio.run(controller.start())
