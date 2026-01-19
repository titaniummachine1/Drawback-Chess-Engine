"""
Data Handler for storing intercepted chess games.
Converts parsed network data into database records.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .database import get_database
from .models import Game, Position
from .drawback_manager import DrawbackManager
from ..interface.packet_parser import PacketParser

logger = logging.getLogger(__name__)


class DataHandler:
    def __init__(self):
        self.db = get_database()
        self.drawback_manager = DrawbackManager()
        self.active_games = {}  # Maps site game_id to DB game record ID

    def process_parsed_data(self, data: Dict[str, Any]):
        """Decide what to do with data coming from the monitor."""
        data_type = data.get("type")

        if data_type == "game_state":
            self._handle_game_state(data)
        elif data_type == "local_move":
            self._handle_local_move(data)
        elif data_type == "game_over":
            self._handle_game_over(data)

    def _handle_game_state(self, data: Dict[str, Any]):
        """Update or create a game and store the current position + legal moves."""
        game_id = data["game_id"]

        with self.db.get_session() as session:
            # 1. Get or Create Game
            game_record = session.query(Game).filter_by(uuid=game_id).first()
            if not game_record:
                game_record = Game(
                    uuid=game_id,
                    white_drawback=data["white_drawback"],
                    black_drawback=data["black_drawback"]
                )
                session.add(game_record)
                session.flush()  # Get the ID
                logger.info(f"Created new game record: {game_id}")

            # 2. Update drawbacks and Register in Manager
            if data["white_drawback"]:
                if not game_record.white_drawback:
                    game_record.white_drawback = data["white_drawback"]
                # Assumes name:description format or just the text
                self.drawback_manager.register_drawback(
                    data["white_drawback"].split(":")[0], data["white_drawback"])

            if data["black_drawback"]:
                if not game_record.black_drawback:
                    game_record.black_drawback = data["black_drawback"]
                self.drawback_manager.register_drawback(
                    data["black_drawback"].split(":")[0], data["black_drawback"])

            # 3. Store the Position (Training Data)
            fen = PacketParser.board_to_fen(data["board"], data["turn"])

            # Check if this ply already exists
            existing_pos = session.query(Position).filter_by(
                game_id=game_record.id,
                move_number=data["ply"]
            ).first()

            if not existing_pos:
                pos = Position(
                    game_id=game_record.id,
                    move_number=data["ply"],
                    fen=fen,
                    active_side=data["turn"]
                )
                pos.set_legal_moves(data["legal_moves"])
                session.add(pos)
                logger.debug(
                    f"Stored position for ply {data['ply']} in game {game_id}")

    def _handle_local_move(self, data: Dict[str, Any]):
        """Update the last position with the move that was actually played."""
        game_id = data["game_id"]
        uci = data["uci"]

        with self.db.get_session() as session:
            game_record = session.query(Game).filter_by(uuid=game_id).first()
            if not game_record:
                return

            # Find the latest position for this game that doesn't have a move yet
            # Usually it's the position where it was the active side's turn
            pos = session.query(Position).filter_by(
                game_id=game_record.id,
                active_side=data["color"]
            ).order_by(Position.move_number.desc()).first()

            if pos and not pos.move_uci:
                pos.move_uci = uci
                logger.info(f"Recorded move {uci} for game {game_id}")

    def _handle_game_over(self, data: Dict[str, Any]):
        """Store the final result of the game."""
        game_id = data["game_id"]
        result = data["result"]

        with self.db.get_session() as session:
            game_record = session.query(Game).filter_by(uuid=game_id).first()
            if game_record:
                game_record.result = result
                # Calculate total moves from positions
                game_record.total_moves = session.query(
                    Position).filter_by(game_id=game_record.id).count()
                logger.info(f"Game {game_id} ended. Result: {result}")
