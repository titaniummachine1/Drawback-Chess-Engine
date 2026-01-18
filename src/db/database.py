"""
Database Management for Drawback Chess Engine

Handles database connection, initialization, and high-level operations.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base, Game, Position, LegalMove, Move, SensorReading, TrainingSample, DrawbackPattern


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to data/ directory in project root
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "chess_games.db"
        
        self.db_path = Path(db_path)
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables."""
        # Create SQLite engine with optimizations for chess data
        engine_url = f"sqlite:///{self.db_path}"
        
        self.engine = create_engine(
            engine_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,  # 30 second timeout
                "isolation_level": None,  # Autocommit mode
            },
            echo=False,  # Set to True for SQL logging
        )
        
        # Enable foreign key constraints
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
            cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
            cursor.close()
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_game(self, **kwargs) -> Game:
        """Create a new game record."""
        with self.get_session() as session:
            game = Game(**kwargs)
            session.add(game)
            session.flush()  # Get the ID
            session.refresh(game)
            return game
    
    def get_game(self, game_id: int) -> Optional[Game]:
        """Get a game by ID."""
        with self.get_session() as session:
            return session.query(Game).filter(Game.id == game_id).first()
    
    def get_game_by_uuid(self, game_uuid: str) -> Optional[Game]:
        """Get a game by UUID."""
        with self.get_session() as session:
            return session.query(Game).filter(Game.uuid == game_uuid).first()
    
    def list_games(self, limit: int = 100, offset: int = 0, 
                   result_filter: Optional[str] = None) -> List[Game]:
        """List games with optional filtering."""
        with self.get_session() as session:
            query = session.query(Game)
            
            if result_filter:
                query = query.filter(Game.result == result_filter)
            
            return query.order_by(Game.started_at.desc()).offset(offset).limit(limit).all()
    
    def create_position(self, game_id: int, **kwargs) -> Position:
        """Create a new position record."""
        with self.get_session() as session:
            position = Position(game_id=game_id, **kwargs)
            session.add(position)
            session.flush()
            session.refresh(position)
            return position
    
    def add_legal_moves(self, position_id: int, legal_moves: List[Dict[str, Any]]) -> List[LegalMove]:
        """Add legal moves for a position."""
        with self.get_session() as session:
            moves = []
            for move_data in legal_moves:
                legal_move = LegalMove(position_id=position_id, **move_data)
                session.add(legal_move)
                moves.append(legal_move)
            
            session.flush()
            return moves
    
    def create_move(self, game_id: int, position_id: int, **kwargs) -> Move:
        """Create a new move record."""
        with self.get_session() as session:
            move = Move(game_id=game_id, position_id=position_id, **kwargs)
            session.add(move)
            session.flush()
            session.refresh(move)
            return move
    
    def add_sensor_reading(self, game_id: int, position_id: int, 
                          move_id: Optional[int], sensor_data: Dict[str, Any]) -> SensorReading:
        """Add a sensor reading."""
        with self.get_session() as session:
            reading = SensorReading(
                game_id=game_id,
                position_id=position_id,
                move_id=move_id,
                **sensor_data
            )
            session.add(reading)
            session.flush()
            session.refresh(reading)
            return reading
    
    def create_training_sample(self, game_id: int, position_id: int, 
                             training_data: Dict[str, Any]) -> TrainingSample:
        """Create a training sample."""
        with self.get_session() as session:
            sample = TrainingSample(
                game_id=game_id,
                position_id=position_id,
                **training_data
            )
            session.add(sample)
            session.flush()
            session.refresh(sample)
            return sample
    
    def get_positions_for_training(self, limit: int = 10000, 
                                 result_filter: Optional[str] = None,
                                 min_confidence: float = 0.5) -> List[Position]:
        """Get positions suitable for training."""
        with self.get_session() as session:
            query = session.query(Position).join(Game)
            
            if result_filter:
                query = query.filter(Game.result == result_filter)
            
            # Filter positions with high-confidence sensor readings
            query = query.join(SensorReading).filter(
                SensorReading.confidence_score >= min_confidence
            )
            
            return query.order_by(func.random()).limit(limit).all()
    
    def get_drawback_patterns(self, pattern_type: Optional[str] = None) -> List[DrawbackPattern]:
        """Get drawback patterns, optionally filtered by type."""
        with self.get_session() as session:
            query = session.query(DrawbackPattern)
            
            if pattern_type:
                query = query.filter(DrawbackPattern.pattern_type == pattern_type)
            
            return query.order_by(DrawbackPattern.effectiveness_score.desc()).all()
    
    def create_or_update_pattern(self, pattern_name: str, pattern_type: str,
                               signature: Dict[str, Any], rules: Dict[str, Any]) -> DrawbackPattern:
        """Create or update a drawback pattern."""
        with self.get_session() as session:
            pattern = session.query(DrawbackPattern).filter(
                DrawbackPattern.pattern_name == pattern_name
            ).first()
            
            if pattern:
                pattern.set_pattern_signature(signature)
                pattern.set_detection_rules(rules)
                pattern.last_updated = func.now()
            else:
                pattern = DrawbackPattern(
                    pattern_name=pattern_name,
                    pattern_type=pattern_type
                )
                pattern.set_pattern_signature(signature)
                pattern.set_detection_rules(rules)
                session.add(pattern)
            
            session.flush()
            session.refresh(pattern)
            return pattern
    
    def get_game_statistics(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        with self.get_session() as session:
            stats = {}
            
            # Game statistics
            stats['total_games'] = session.query(Game).count()
            stats['white_wins'] = session.query(Game).filter(Game.result == 'white_win').count()
            stats['black_wins'] = session.query(Game).filter(Game.result == 'black_win').count()
            stats['draws'] = session.query(Game).filter(Game.result == 'draw').count()
            
            # Position statistics
            stats['total_positions'] = session.query(Position).count()
            stats['unique_positions'] = session.query(Position.position_hash).distinct().count()
            
            # Sensor statistics
            stats['total_sensor_readings'] = session.query(SensorReading).count()
            stats['drawback_detections'] = session.query(SensorReading).filter(
                SensorReading.drawback_detected == True
            ).count()
            
            # Training statistics
            stats['training_samples'] = session.query(TrainingSample).count()
            
            # Pattern statistics
            stats['drawback_patterns'] = session.query(DrawbackPattern).count()
            
            return stats
    
    def export_training_data(self, output_path: str, limit: Optional[int] = None):
        """Export training data to JSON file."""
        import json
        
        with self.get_session() as session:
            query = session.query(TrainingSample)
            
            if limit:
                query = query.limit(limit)
            
            samples = []
            for sample in query.all():
                sample_data = {
                    'game_id': sample.game_id,
                    'position_id': sample.position_id,
                    'input_encoding': sample.get_input_encoding(),
                    'target_value': sample.target_value,
                    'target_policy': sample.get_target_policy(),
                    'legal_moves_mask': sample.get_legal_moves_mask(),
                    'sensor_features': sample.get_sensor_features(),
                    'sample_weight': sample.sample_weight,
                    'created_at': sample.created_at.isoformat()
                }
                samples.append(sample_data)
            
            with open(output_path, 'w') as f:
                json.dump(samples, f, indent=2)
            
            logger.info(f"Exported {len(samples)} training samples to {output_path}")
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old game data to manage database size."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        with self.get_session() as session:
            # Delete old games and related data
            old_games = session.query(Game).filter(Game.started_at < cutoff_date).all()
            
            for game in old_games:
                session.delete(game)  # Cascade delete will handle related records
            
            deleted_count = len(old_games)
            logger.info(f"Cleaned up {deleted_count} old games from before {cutoff_date}")
    
    def vacuum_database(self):
        """Optimize database size and performance."""
        with self.get_session() as session:
            session.execute("VACUUM")
            session.execute("ANALYZE")
            logger.info("Database vacuumed and analyzed")


# Global database instance
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(db_path: Optional[str] = None) -> DatabaseManager:
    """Initialize the global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    return _db_manager
