"""
Game Storage System for Drawback Chess Engine

High-level interface for storing and retrieving complete games with all associated data.
"""

import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass, asdict

from .database import get_database
from .models import Game, Position, LegalMove, Move, SensorReading
from ..engine.chess_engine import ChessMove, GameState


@dataclass
class GameRecord:
    """Complete game record for storage."""
    uuid: str
    started_at: datetime
    ended_at: Optional[datetime]
    result: Optional[str]
    time_control: str
    engine_version: str
    opponent_type: str
    opponent_info: Dict[str, Any]
    positions: List['PositionRecord']
    moves: List['MoveRecord']
    sensor_readings: List['SensorRecord']
    drawback_analysis: Dict[str, Any]


@dataclass
class PositionRecord:
    """Position record within a game."""
    move_number: int
    fen: str
    turn: str
    castling_rights: Dict[str, bool]
    en_passant_square: Optional[str]
    halfmove_clock: int
    fullmove_number: int
    position_hash: Optional[str]
    evaluation: Optional[float]
    legal_moves: List['LegalMoveRecord']


@dataclass
class LegalMoveRecord:
    """Legal move record for a position."""
    move_uci: str
    move_san: Optional[str]
    piece_type: Optional[str]
    from_square: str
    to_square: str
    is_capture: bool
    is_promotion: bool
    promotion_piece: Optional[str]
    is_castling: bool
    is_en_passant: bool
    move_priority: float


@dataclass
class MoveRecord:
    """Actual move played in a game."""
    move_number: int
    move_uci: str
    move_san: Optional[str]
    time_spent_seconds: Optional[float]
    engine_search_depth: Optional[int]
    engine_nodes_searched: Optional[int]
    engine_confidence: Optional[float]
    was_best_move: bool
    alternative_moves: List[Dict[str, Any]]


@dataclass
class SensorRecord:
    """Sensor reading record."""
    sensor_type: str
    sensor_version: str
    raw_data: Dict[str, Any]
    processed_data: Dict[str, Any]
    confidence_score: Optional[float]
    processing_time_ms: Optional[float]
    drawback_detected: bool
    drawback_type: Optional[str]
    drawback_severity: float
    position_number: Optional[int] = None
    move_number: Optional[int] = None


class GameStorage:
    """High-level game storage and retrieval system."""
    
    def __init__(self):
        self.db = get_database()
    
    def store_game(self, game_record: GameRecord) -> int:
        """
        Store a complete game with all associated data.
        
        Args:
            game_record: Complete game record to store
            
        Returns:
            Database ID of the stored game
        """
        # Create main game record
        game = self.db.create_game(
            uuid=game_record.uuid,
            started_at=game_record.started_at,
            ended_at=game_record.ended_at,
            result=game_record.result,
            time_control=game_record.time_control,
            engine_version=game_record.engine_version,
            opponent_type=game_record.opponent_type,
            opponent_info=game_record.opponent_info,
            total_moves=len(game_record.moves),
            total_time_seconds=sum(m.time_spent_seconds or 0 for m in game_record.moves),
            drawback_analysis=game_record.drawback_analysis
        )
        
        # Store positions and legal moves
        position_map = {}  # move_number -> position_id
        for pos_record in game_record.positions:
            position = self.db.create_position(
                game_id=game.id,
                move_number=pos_record.move_number,
                fen=pos_record.fen,
                turn=pos_record.turn,
                castling_rights=pos_record.castling_rights,
                en_passant_square=pos_record.en_passant_square,
                halfmove_clock=pos_record.halfmove_clock,
                fullmove_number=pos_record.fullmove_number,
                position_hash=pos_record.position_hash,
                evaluation=pos_record.evaluation
            )
            
            # Store legal moves for this position
            if pos_record.legal_moves:
                legal_moves_data = [asdict(lm) for lm in pos_record.legal_moves]
                self.db.add_legal_moves(position.id, legal_moves_data)
            
            position_map[pos_record.move_number] = position.id
        
        # Store moves
        move_map = {}  # move_number -> move_id
        for move_record in game_record.moves:
            position_id = position_map.get(move_record.move_number)
            if position_id is None:
                raise ValueError(f"No position found for move {move_record.move_number}")
            
            move = self.db.create_move(
                game_id=game.id,
                position_id=position_id,
                move_number=move_record.move_number,
                move_uci=move_record.move_uci,
                move_san=move_record.move_san,
                time_spent_seconds=move_record.time_spent_seconds,
                engine_search_depth=move_record.engine_search_depth,
                engine_nodes_searched=move_record.engine_nodes_searched,
                engine_confidence=move_record.engine_confidence,
                was_best_move=move_record.was_best_move,
                alternative_moves=move_record.alternative_moves
            )
            move_map[move_record.move_number] = move.id
        
        # Store sensor readings
        for sensor_record in game_record.sensor_readings:
            position_id = None
            move_id = None
            
            if sensor_record.position_number is not None:
                position_id = position_map.get(sensor_record.position_number)
            if sensor_record.move_number is not None:
                move_id = move_map.get(sensor_record.move_number)
            
            sensor_data = {
                'sensor_type': sensor_record.sensor_type,
                'sensor_version': sensor_record.sensor_version,
                'raw_data': sensor_record.raw_data,
                'processed_data': sensor_record.processed_data,
                'confidence_score': sensor_record.confidence_score,
                'processing_time_ms': sensor_record.processing_time_ms,
                'drawback_detected': sensor_record.drawback_detected,
                'drawback_type': sensor_record.drawback_type,
                'drawback_severity': sensor_record.drawback_severity
            }
            
            self.db.add_sensor_reading(
                game_id=game.id,
                position_id=position_id,
                move_id=move_id,
                sensor_data=sensor_data
            )
        
        return game.id
    
    def retrieve_game(self, game_id: int) -> Optional[GameRecord]:
        """
        Retrieve a complete game record by ID.
        
        Args:
            game_id: Database ID of the game
            
        Returns:
            Complete game record or None if not found
        """
        game = self.db.get_game(game_id)
        if game is None:
            return None
        
        # Get all positions for this game
        with self.db.get_session() as session:
            positions = session.query(Position).filter(
                Position.game_id == game_id
            ).order_by(Position.move_number).all()
            
            # Get all moves
            moves = session.query(Move).filter(
                Move.game_id == game_id
            ).order_by(Move.move_number).all()
            
            # Get all sensor readings
            sensor_readings = session.query(SensorReading).filter(
                SensorReading.game_id == game_id
            ).all()
        
        # Convert to record format
        position_records = []
        for pos in positions:
            # Get legal moves for this position
            with self.db.get_session() as session:
                legal_moves = session.query(LegalMove).filter(
                    LegalMove.position_id == pos.id
                ).all()
            
            legal_move_records = [
                LegalMoveRecord(
                    move_uci=lm.move_uci,
                    move_san=lm.move_san,
                    piece_type=lm.piece_type,
                    from_square=lm.from_square,
                    to_square=lm.to_square,
                    is_capture=lm.is_capture,
                    is_promotion=lm.is_promotion,
                    promotion_piece=lm.promotion_piece,
                    is_castling=lm.is_castling,
                    is_en_passant=lm.is_en_passant,
                    move_priority=lm.move_priority
                )
                for lm in legal_moves
            ]
            
            position_records.append(PositionRecord(
                move_number=pos.move_number,
                fen=pos.fen,
                turn=pos.turn,
                castling_rights=pos.get_castling_rights(),
                en_passant_square=pos.en_passant_square,
                halfmove_clock=pos.halfmove_clock,
                fullmove_number=pos.fullmove_number,
                position_hash=pos.position_hash,
                evaluation=pos.evaluation,
                legal_moves=legal_move_records
            ))
        
        move_records = [
            MoveRecord(
                move_number=move.move_number,
                move_uci=move.move_uci,
                move_san=move.move_san,
                time_spent_seconds=move.time_spent_seconds,
                engine_search_depth=move.engine_search_depth,
                engine_nodes_searched=move.engine_nodes_searched,
                engine_confidence=move.engine_confidence,
                was_best_move=move.was_best_move,
                alternative_moves=move.get_alternative_moves()
            )
            for move in moves
        ]
        
        sensor_records = [
            SensorRecord(
                sensor_type=reading.sensor_type,
                sensor_version=reading.sensor_version,
                raw_data=reading.get_raw_data(),
                processed_data=reading.get_processed_data(),
                confidence_score=reading.confidence_score,
                processing_time_ms=reading.processing_time_ms,
                drawback_detected=reading.drawback_detected,
                drawback_type=reading.drawback_type,
                drawback_severity=reading.drawback_severity
            )
            for reading in sensor_readings
        ]
        
        return GameRecord(
            uuid=game.uuid,
            started_at=game.started_at,
            ended_at=game.ended_at,
            result=game.result,
            time_control=game.time_control,
            engine_version=game.engine_version,
            opponent_type=game.opponent_type,
            opponent_info=game.get_opponent_info(),
            positions=position_records,
            moves=move_records,
            sensor_readings=sensor_records,
            drawback_analysis=game.get_drawback_analysis()
        )
    
    def find_games_by_result(self, result: str, limit: int = 100) -> List[GameRecord]:
        """Find games by result (white_win, black_win, draw)."""
        games = self.db.list_games(limit=limit, result_filter=result)
        return [self.retrieve_game(game.id) for game in games if game.id is not None]
    
    def find_games_with_drawbacks(self, drawback_type: Optional[str] = None, 
                                 min_severity: float = 0.5, limit: int = 100) -> List[GameRecord]:
        """Find games that contain specific drawback patterns."""
        with self.db.get_session() as session:
            query = session.query(Game).join(SensorReading).filter(
                SensorReading.drawback_detected == True,
                SensorReading.drawback_severity >= min_severity
            )
            
            if drawback_type:
                query = query.filter(SensorReading.drawback_type == drawback_type)
            
            games = query.limit(limit).all()
            return [self.retrieve_game(game.id) for game in games if game.id is not None]
    
    def get_training_positions(self, limit: int = 10000, 
                             include_drawbacks: bool = True) -> Iterator[GameRecord]:
        """Get positions suitable for training, optionally filtered by drawback presence."""
        with self.db.get_session() as session:
            query = session.query(Game)
            
            if include_drawbacks:
                # Only games with sensor readings
                query = query.join(SensorReading)
            
            games = query.order_by(func.random()).limit(limit).all()
            
            for game in games:
                game_record = self.retrieve_game(game.id)
                if game_record:
                    yield game_record
    
    def export_game_pgn(self, game_id: int) -> Optional[str]:
        """Export a game in PGN format."""
        game_record = self.retrieve_game(game_id)
        if game_record is None:
            return None
        
        # Build PGN header
        headers = [
            f'[Event "Drawback Chess Game"]',
            f'[Site "Local Engine"]',
            f'[Date "{game_record.started_at.strftime("%Y.%m.%d")}"]',
            f'[White "{game_record.opponent_type}"]',
            f'[Black "{game_record.engine_version}"]',
            f'[Result "{self._result_to_pgn(game_record.result)}"]',
            f'[TimeControl "{game_record.time_control}"]',
            f'[UUID "{game_record.uuid}"]'
        ]
        
        # Build move list
        moves = []
        for i, move in enumerate(game_record.moves):
            if i % 2 == 0:  # White's turn
                move_number = i // 2 + 1
                moves.append(f"{move_number}.{move.move_san or move.move_uci}")
            else:  # Black's turn
                moves.append(move.move_san or move.move_uci)
        
        # Combine header and moves
        pgn = "\n".join(headers) + "\n\n" + " ".join(moves)
        
        if game_record.result:
            pgn += f" {self._result_to_pgn(game_record.result)}"
        
        return pgn
    
    def _result_to_pgn(self, result: Optional[str]) -> str:
        """Convert internal result format to PGN format."""
        if result == 'white_win':
            return "1-0"
        elif result == 'black_win':
            return "0-1"
        elif result == 'draw':
            return "1/2-1/2"
        else:
            return "*"
    
    def get_game_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about stored games."""
        stats = self.db.get_game_statistics()
        
        # Add additional computed statistics
        with self.db.get_session() as session:
            # Average game length
            avg_length = session.query(func.avg(Game.total_moves)).scalar()
            stats['average_game_length'] = avg_length or 0
            
            # Games with drawbacks
            games_with_drawbacks = session.query(Game).join(SensorReading).filter(
                SensorReading.drawback_detected == True
            ).distinct().count()
            stats['games_with_drawbacks'] = games_with_drawbacks
            
            # Most common drawback types
            drawback_counts = session.query(
                SensorReading.drawback_type,
                func.count(SensorReading.id).label('count')
            ).filter(
                SensorReading.drawback_detected == True
            ).group_by(SensorReading.drawback_type).order_by(
                func.count(SensorReading.id).desc()
            ).limit(10).all()
            
            stats['top_drawback_types'] = [
                {'type': drawback_type, 'count': count}
                for drawback_type, count in drawback_counts
            ]
        
        return stats


# Global game storage instance
_game_storage: Optional[GameStorage] = None


def get_game_storage() -> GameStorage:
    """Get the global game storage instance."""
    global _game_storage
    if _game_storage is None:
        _game_storage = GameStorage()
    return _game_storage
