"""
Self-Play Automation with "No-Lag" Engine Architecture.
Hosts two browser instances, plays a game using a persistent engine + MCTS stub.
"""

import string
import chess
import re
from src.interface.packet_parser import PacketParser
from src.engine.stockfish_wrapper import StockfishWrapper
from playwright.async_api import async_playwright
from pathlib import Path
import json
import asyncio
import logging
import random
import sys
import os

# Ensure the project root is in sys.path for "src" imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        # Store session details for packet sending: { 'white': {...}, 'black': {...} }
        self.session_data = {}

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

            # 3. Attach Listeners & Play (EARLY to catch init traffic)
            # We need to track the latest "Server Truth"
            self.server_legal_moves = {}  # game_id -> list of moves

            # Hook up packet capture for Reality Check
            await self.attach_listeners(page_a, "white")
            await self.attach_listeners(page_b, "black")

            # 2. Setup Game (Simplified)
            # Window A creates the game
            game_url = await self.create_game(page_a)

            # Window B joins as black
            await self.join_game(page_b, game_url)

            # Game Loop
            # We track whose turn it is from the intercepted packets
            self.current_turn_color = None
            self.latest_fen = None
            self.last_move_uci = None

            loop_counter = 0
            while True:
                await asyncio.sleep(0.1)
                loop_counter += 1

                # Check whose turn?
                # This needs to be updated by handle_response
                if self.latest_fen and self.current_turn_color:
                    if loop_counter % 50 == 0:
                        logger.info(
                            f"Loop State: Turn={self.current_turn_color}, FEN={self.latest_fen[:20]}...")

                    # Decide move
                    move = await self.decide_move(self.latest_fen)
                    if move:
                        # logger.info(f"Decided move: {move}") # Verbose
                        if self.current_turn_color == "white":
                            await self.execute_move(page_a, move)
                        else:
                            await self.execute_move(page_b, move)

                        # Wait for next turn (reset state to avoid spam)
                        self.latest_fen = None

                elif loop_counter % 50 == 0:  # Log every 5s approx
                    logger.info("Waiting for game state/turn...")
                    logger.debug(f"Session Data: {self.session_data}")

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
        """Handle ELO selection and 'How to Play' notice."""
        # 1. Check for 'How to Play' and RELOAD if found
        try:
            # Check for the distinct "CLOSE" button or title
            if await page.get_by_text("How To Play").is_visible(timeout=3000):
                logger.info(
                    "Found 'How to Play' notice. Reloading page to bypass...")
                await page.reload()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
        except:
            pass

        # 2. Handle ELO selection if it appears (after reload)
        try:
            intermediate = page.get_by_text("Intermediate")
            if await intermediate.is_visible(timeout=3000):
                logger.info("Setting ELO to Intermediate...")
                await intermediate.click()
                await asyncio.sleep(1)
        except:
            pass

    async def create_game(self, page):
        logger.info("Creating game via 'Play vs Friend' Flow (Visual)...")
        await page.goto(SITE_URL)

        # Handle first-time popups with Reload strategy
        await self.handle_initial_popups(page)

        # 1. Click Play vs Friend
        # Use more robust waiting
        try:
            pvf_btn = page.get_by_text("Play vs Friend")
            await pvf_btn.wait_for(state="visible", timeout=5000)
            await pvf_btn.click()
        except Exception:
            # Maybe we need to reload again or it's already there?
            logger.warning(
                "Play vs Friend not found immediately, checking popups again...")
            await self.handle_initial_popups(page)
            await page.get_by_text("Play vs Friend").click()

        # 2. Click HOST GAME button
        logger.info("Clicking 'HOST GAME'...")
        host_btn = page.get_by_text("HOST GAME")
        await host_btn.wait_for(state="visible", timeout=5000)
        await host_btn.click()

        # 3. Select White Piece
        logger.info("Selecting 'White' piece...")
        white_piece = page.get_by_alt_text("White King")
        await white_piece.wait_for(state="visible", timeout=5000)
        await white_piece.click()

        # 4. Wait for URL to change to /game/...
        logger.info("Waiting for game session...")
        await page.wait_for_url("**/game/**", timeout=15000)
        game_url = page.url
        logger.info(f"Game created: {game_url}")

        # Note: We rely on attach_listeners to capture session_data (username/id)
        # from the network traffic generated by these clicks.

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
        # Try to close popups by reloading or clicking if this is the join flow
        await self.handle_initial_popups(page)

    async def attach_listeners(self, page, side):
        # Capture outgoing requests to steal 'username' and 'app_prefix'
        page.on("request", lambda req: asyncio.create_task(
            self.handle_request(req, side)))

        # Capture responses for Game State
        page.on("response", lambda res: asyncio.create_task(
            self.handle_response(res, side)))

    async def handle_request(self, request, side):
        try:
            url = request.url
            # Capture username from query params (most reliable source)
            if "username=" in url and side not in self.session_data:
                match = re.search(r"username=([^&]+)", url)
                if match:
                    username = match.group(1)
                    if side not in self.session_data:
                        self.session_data[side] = {}
                    self.session_data[side]['username'] = username
                    logger.info(f"Captured {side} username: {username}")

            # Capture game_id and app_prefix from "game?" requests
            # e.g. .../app15/game?id=...
            if "/game?" in url and "app" in url:
                # Extract app prefix (e.g. app15)
                app_match = re.search(r"drawbackchess\.com/(app\d+)/game", url)
                if app_match:
                    if side not in self.session_data:
                        self.session_data[side] = {}
                    self.session_data[side]['prefix'] = app_match.group(1)

                # Extract game ID
                id_match = re.search(r"id=([a-f0-9]+)", url)
                if id_match:
                    if side not in self.session_data:
                        self.session_data[side] = {}
                    self.session_data[side]['game_id'] = id_match.group(1)
        except:
            pass

    async def execute_move(self, page, move_uci):
        # 1. Determine side from page url or context
        # We passed 'page_a' (white) or 'page_b' (black) in the loop
        # Check session data
        side = None
        if "/white" in page.url:
            side = "white"
        elif "/black" in page.url:
            side = "black"

        if not side or side not in self.session_data:
            logger.error(f"Cannot execute move: No session data for {side}")
            return

        data = self.session_data[side]
        username = data.get('username')
        game_id = data.get('game_id')
        prefix = data.get('prefix', 'app15')  # Default to app15 if missing

        if not username or not game_id:
            logger.error("Missing username or game_id for packet!")
            return

        # 2. Build Payload
        # UCI "e2e4" -> start="E2", stop="E4"
        start_sq = move_uci[:2].upper()
        stop_sq = move_uci[2:4].upper()

        payload = {
            "id": game_id,
            "start": start_sq,
            "stop": stop_sq,
            "username": username,
            "color": side
        }

        # Promotion Helper
        if len(move_uci) == 5:
            # e.g. a7a8q
            promo_map = {'q': 'queen', 'r': 'rook',
                         'b': 'bishop', 'n': 'knight'}
            promo_char = move_uci[4]
            payload["promotion"] = promo_map.get(promo_char, 'queen')

        target_url = f"https://www.drawbackchess.com/{prefix}/move"

        logger.info(f"🚀 SENDING PACKET MOVE: {move_uci} -> {target_url}")

        # 3. Send Request
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://www.drawbackchess.com",
            "Referer": "https://www.drawbackchess.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            # We use the page's request context to ensure cookies/headers match (if needed)
            # though username/auth seems to be in the body/query.
            await page.request.post(target_url, data=payload, headers=headers)
        except Exception as e:
            logger.error(f"Move packet failed: {e}")

    async def handle_response(self, response, side):
        # Capture legal moves "Reality Check"
        try:
            # Widen heuristic: check for 'game' in URL, but also just check body for 'moves' structure
            # to capture polling/updates that might not be POST or strictly named 'game'
            if "game" in response.url or "poll" in response.url:
                try:
                    body = await response.text()
                except:
                    return

                if "moves" in body and "handicaps" in body:
                    data = json.loads(body)
                    parsed = PacketParser.parse_game_state(data)
                    self.server_legal_moves[parsed['game_id']
                                            ] = parsed['legal_moves']

                    # ROBUST SESSION DATA CAPTURE
                    # We have the game ID from the packet, and prefix from the URL.
                    # This ensures we can send moves even if we missed the init request.
                    if side not in self.session_data:
                        self.session_data[side] = {}

                    self.session_data[side]['game_id'] = parsed['game_id']

                    # Extract prefix from response URL: .../app9/game
                    app_match = re.search(r"/(app\d+)/", response.url)
                    if app_match:
                        self.session_data[side]['prefix'] = app_match.group(1)

                    # We might still miss username if we didn't catch the query param,
                    # but usually handle_request catches that.

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
                    await self.run_learning_step(fen, parsed['legal_moves'], parsed.get('revealed_drawbacks', {}))
        except:
            pass

    async def run_learning_step(self, fen, truth_moves, revealed_drawbacks=None):
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
            "timestamp": "TODO",  # Add timestamp
            "revealed_drawbacks": revealed_drawbacks or {}
        }

        # Append to JSONL
        with open(self.training_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(sample) + "\n")

        logger.info(
            f"Learned from position. Physical: {len(physical_moves)}, Legal: {len(truth_moves)}")


if __name__ == "__main__":
    controller = SelfPlayController()
    asyncio.run(controller.start())
