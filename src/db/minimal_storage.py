"""
Minimal Game Storage System

Ultra-lightweight storage for FEN positions, legal moves, and drawback data.
Designed for 500MB storage instead of 5GB.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass

from .minimal_models import Base, Game, Position, Drawback
from .database import get_database


@dataclass
class MinimalGame:
    """Minimal game record for storage."""
    uuid: str
    result: Optional[str]
    opponent_type: str
    engine_version: str
    positions: List['MinimalPosition']
    drawbacks: List['MinimalDrawback']


@dataclass
class MinimalPosition:
    """Position with FEN and legal moves."""
    move_number: int
    fen: str
    legal_moves: List[str]


@dataclass
class MinimalDrawback:
    """Drawback detection data."""
    position_move_number: int
    drawback_type: str
    severity: float
    legal_moves_available: List[str]
    metadata: Dict[str, Any]  # Additional data like affected pieces, threat squares


class MinimalStorage:
    """Ultra-minimal storage system for chess games."""
    
    def __init__(self):
        self.db = get_database()
        # Use minimal models
        Base.metadata.create_all(bind=self.db.engine)
    
    def store_game(self, game_data: MinimalGame) -> int:
        """
        Store a game with minimal data.
        
        Args:
            game_data: Minimal game containing positions and drawbacks
            
        Returns:
            Database ID of stored game
        """
        with self.db.get_session() as session:
            # Create game record
            game = Game(
                uuid=game_data.uuid,
                result=game_data.result,
                opponent_type=game_data.opponent_type,
                engine_version=game_data.engine_version,
                total_moves=len(game_data.positions)
            )
            session.add(game)
            session.flush()
            game_id = game.id
            
            # Store positions
            position_map = {}  # move_number -> position_id
            for pos in game_data.positions:
                position = Position(
                    game_id=game_id,
                    move_number=pos.move_number,
                    fen=pos.fen,
                    legal_moves=pos.legal_moves  # Will be auto-serialized
                )
                session.add(position)
                session.flush()
                position_map[pos.move_number] = position.id
            
            # Store drawbacks
            for drawback in game_data.drawbacks:
                position_id = position_map.get(drawback.position_move_number)
                if position_id is None:
                    continue  # Skip if position not found
                
                # Prepare legal moves response data
                response_data = {
                    "legal_moves": drawback.legal_moves_available,
                    **drawback.metadata
                }
                
                drawback_record = Drawback(
                    game_id=game_id,
                    position_id=position_id,
                    drawback_type=drawback.drawback_type,
                    severity=drawback.severity,
                    legal_moves_response=response_data  # Will be auto-serialized
                )
                session.add(drawback_record)
            
            session.commit()
            return game_id
    
    def get_game(self, game_id: int) -> Optional[MinimalGame]:
        """Retrieve a minimal game record."""
        with self.db.get_session() as session:
            game = session.query(Game).filter(Game.id == game_id).first()
            if game is None:
                return None
            
            # Get positions
            positions = session.query(Position).filter(
                Position.game_id == game_id
            ).order_by(Position.move_number).all()
            
            # Get drawbacks
            drawbacks = session.query(Drawback).filter(
                Drawback.game_id == game_id
            ).all()
            
            # Convert to minimal format
            minimal_positions = [
                MinimalPosition(
                    move_number=pos.move_number,
                    fen=pos.fen,
                    legal_moves=pos.get_legal_moves()
                )
                for pos in positions
            ]
            
            minimal_drawbacks = [
                MinimalDrawback(
                    position_move_number=drawback.position.move_number,
                    drawback_type=drawback.drawback_type,
                    severity=drawback.severity,
                    legal_moves_available=drawback.get_legal_moves_response().get("legal_moves", []),
                    metadata={k: v for k, v in drawback.get_legal_moves_response().items() if k != "legal_moves"}
                )
                for drawback in drawbacks
            ]
            
            return MinimalGame(
                uuid=game.uuid,
                result=game.result,
                opponent_type=game.opponent_type or "unknown",
                engine_version=game.engine_version or "unknown",
                positions=minimal_positions,
                drawbacks=minimal_drawbacks
            )
    
    def get_training_positions(self, limit: int = 10000, 
                             with_drawbacks_only: bool = False) -> Iterator[tuple]:
        """
        Get positions for training.
        
        Yields tuples of (fen, legal_moves, drawback_info)
        """
        with self.db.get_session() as session:
            query = session.query(Position, Game.result)
            
            if with_drawbacks_only:
                query = query.join(Drawback).filter(Drawback.severity > 0.5)
            
            query = query.join(Game).order_by(func.random()).limit(limit)
            
            for position, result in query.all():
                # Get drawback info if any
                drawback_info = None
                drawback = session.query(Drawback).filter(
                    Drawback.position_id == position.id
                ).first()
                
                if drawback:
                    drawback_info = {
                        "type": drawback.drawback_type,
                        "severity": drawback.severity,
                        "legal_moves_response": drawback.get_legal_moves_response()
                    }
                
                yield (position.fen, position.get_legal_moves(), drawback_info, result)
    
    def get_drawback_training_data(self, min_severity: float = 0.5) -> List[Dict[str, Any]]:
        """Get all drawback data for training."""
        with self.db.get_session() as session:
            drawbacks = session.query(Drawback, Position.fen, Position.legal_moves).join(
                Position, Drawback.position_id == Position.id
            ).filter(Drawback.severity >= min_severity).all()
            
            training_data = []
            for drawback, fen, legal_moves in drawbacks:
                training_data.append({
                    "fen": fen,
                    "legal_moves": json.loads(legal_moves),
                    "drawback_type": drawback.drawback_type,
                    "severity": drawback.severity,
                    "response_data": drawback.get_legal_moves_response()
                })
            
            return training_data
    
    def find_games_with_drawbacks(self, drawback_type: Optional[str] = None,
                                 min_severity: float = 0.5) -> List[int]:
        """Find game IDs that contain specific drawbacks."""
        with self.db.get_session() as session:
            query = session.query(Drawback.game_id).filter(
                Drawback.severity >= min_severity
            )
            
            if drawback_type:
                query = query.filter(Drawback.drawback_type == drawback_type)
            
            return [game_id for game_id, in query.distinct().all()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        with self.db.get_session() as session:
            stats = {}
            
            # Game stats
            stats['total_games'] = session.query(Game).count()
            stats['white_wins'] = session.query(Game).filter(Game.result == 'white_win').count()
            stats['black_wins'] = session.query(Game).filter(Game.result == 'black_win').count()
            stats['draws'] = session.query(Game).filter(Game.result == 'draw').count()
            
            # Position stats
            stats['total_positions'] = session.query(Position).count()
            
            # Drawback stats
            stats['total_drawbacks'] = session.query(Drawback).count()
            stats['high_severity_drawbacks'] = session.query(Drawback).filter(
                Drawback.severity >= 0.7
            ).count()
            
            # Drawback type distribution
            drawback_types = session.query(
                Drawback.drawback_type,
                func.count(Drawback.id).label('count')
            ).group_by(Drawback.drawback_type).order_by(
                func.count(Drawback.id).desc()
            ).all()
            
            stats['drawback_types'] = [
                {"type": drawback_type, "count": count}
                for drawback_type, count in drawback_types
            ]
            
            return stats
    
    def export_training_data(self, output_path: str, limit: Optional[int] = None):
        """Export all training data to JSON file."""
        import json
        
        training_data = []
        
        for fen, legal_moves, drawback_info, result in self.get_training_positions(limit=limit):
            sample = {
                "fen": fen,
                "legal_moves": legal_moves,
                "game_result": result,
                "has_drawback": drawback_info is not None
            }
            
            if drawback_info:
                sample.update(drawback_info)
            
            training_data.append(sample)
        
        with open(output_path, 'w') as f:
            json.dump(training_data, f, indent=2)
    
    def cleanup_old_games(self, keep_count: int = 10000):
        """Keep only the most recent N games to save space."""
        with self.db.get_session() as session:
            # Get IDs of games to keep (most recent)
            games_to_keep = session.query(Game.id).order_by(
                Game.created_at.desc()
            ).limit(keep_count).all()
            
            keep_ids = [game_id for game_id, in games_to_keep]
            
            # Delete old games
            session.query(Game).filter(~Game.id.in_(keep_ids)).delete(synchronize_session=False)
            session.commit()


# Global minimal storage instance
_minimal_storage: Optional[MinimalStorage] = None


def get_minimal_storage() -> MinimalStorage:
    """Get the global minimal storage instance."""
    global _minimal_storage
    if _minimal_storage is None:
        _minimal_storage = MinimalStorage()
    return _minimal_storage
