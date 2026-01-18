"""
Database Models for Drawback Chess Engine

SQLAlchemy models for storing games, positions, moves, and sensor data.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()


class Game(Base):
    """Represents a complete chess game."""
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime, nullable=True)
    result = Column(String(20), nullable=True)  # 'white_win', 'black_win', 'draw'
    time_control = Column(String(50), nullable=True)
    engine_version = Column(String(50), nullable=True)
    opponent_type = Column(String(20), nullable=True)  # 'human', 'engine', 'self_play'
    opponent_info = Column(Text, nullable=True)  # JSON string
    total_moves = Column(Integer, nullable=True)
    total_time_seconds = Column(Float, nullable=True)
    drawback_analysis = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    positions = relationship("Position", back_populates="game", cascade="all, delete-orphan")
    moves = relationship("Move", back_populates="game", cascade="all, delete-orphan")
    sensor_readings = relationship("SensorReading", back_populates="game", cascade="all, delete-orphan")
    training_samples = relationship("TrainingSample", back_populates="game", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_games_started_at', 'started_at'),
        Index('idx_games_result', 'result'),
    )
    
    def get_opponent_info(self) -> Dict[str, Any]:
        """Parse opponent info JSON."""
        if self.opponent_info:
            return json.loads(self.opponent_info)
        return {}
    
    def set_opponent_info(self, info: Dict[str, Any]):
        """Set opponent info from dictionary."""
        self.opponent_info = json.dumps(info)
    
    def get_drawback_analysis(self) -> Dict[str, Any]:
        """Parse drawback analysis JSON."""
        if self.drawback_analysis:
            return json.loads(self.drawback_analysis)
        return {}
    
    def set_drawback_analysis(self, analysis: Dict[str, Any]):
        """Set drawback analysis from dictionary."""
        self.drawback_analysis = json.dumps(analysis)


class Position(Base):
    """Represents a chess position within a game."""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    move_number = Column(Integer, nullable=False)  # Ply number
    fen = Column(String(100), nullable=False)
    turn = Column(String(5), nullable=False)  # 'white' or 'black'
    castling_rights = Column(Text, nullable=True)  # JSON string
    en_passant_square = Column(String(2), nullable=True)
    halfmove_clock = Column(Integer, nullable=False)
    fullmove_number = Column(Integer, nullable=False)
    position_hash = Column(String(64), nullable=True)  # Zobrist hash
    evaluation = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="positions")
    legal_moves = relationship("LegalMove", back_populates="position", cascade="all, delete-orphan")
    moves = relationship("Move", back_populates="position", cascade="all, delete-orphan")
    sensor_readings = relationship("SensorReading", back_populates="position", cascade="all, delete-orphan")
    training_samples = relationship("TrainingSample", back_populates="position", cascade="all, delete-orphan")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('game_id', 'move_number', name='uq_game_move'),
        Index('idx_positions_game_id', 'game_id'),
        Index('idx_positions_fen', 'fen'),
        Index('idx_positions_hash', 'position_hash'),
    )
    
    def get_castling_rights(self) -> Dict[str, bool]:
        """Parse castling rights JSON."""
        if self.castling_rights:
            return json.loads(self.castling_rights)
        return {"K": False, "Q": False, "k": False, "q": False}
    
    def set_castling_rights(self, rights: Dict[str, bool]):
        """Set castling rights from dictionary."""
        self.castling_rights = json.dumps(rights)


class LegalMove(Base):
    """Represents a legal move from a specific position."""
    __tablename__ = 'legal_moves'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    move_uci = Column(String(10), nullable=False)
    move_san = Column(String(10), nullable=True)
    piece_type = Column(String(1), nullable=True)  # 'P', 'N', 'B', 'R', 'Q', 'K'
    from_square = Column(String(2), nullable=False)
    to_square = Column(String(2), nullable=False)
    is_capture = Column(Boolean, default=False)
    is_promotion = Column(Boolean, default=False)
    promotion_piece = Column(String(1), nullable=True)
    is_castling = Column(Boolean, default=False)
    is_en_passant = Column(Boolean, default=False)
    move_priority = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    position = relationship("Position", back_populates="legal_moves")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('position_id', 'move_uci', name='uq_position_move'),
        Index('idx_legal_moves_position_id', 'position_id'),
    )


class Move(Base):
    """Represents an actual move played in a game."""
    __tablename__ = 'moves'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    move_number = Column(Integer, nullable=False)
    move_uci = Column(String(10), nullable=False)
    move_san = Column(String(10), nullable=True)
    time_spent_seconds = Column(Float, nullable=True)
    engine_search_depth = Column(Integer, nullable=True)
    engine_nodes_searched = Column(Integer, nullable=True)
    engine_confidence = Column(Float, nullable=True)
    was_best_move = Column(Boolean, default=False)
    alternative_moves = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="moves")
    position = relationship("Position", back_populates="moves")
    sensor_readings = relationship("SensorReading", back_populates="move", cascade="all, delete-orphan")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('game_id', 'move_number', name='uq_game_move_number'),
        Index('idx_moves_game_id', 'game_id'),
    )
    
    def get_alternative_moves(self) -> List[Dict[str, Any]]:
        """Parse alternative moves JSON."""
        if self.alternative_moves:
            return json.loads(self.alternative_moves)
        return []
    
    def set_alternative_moves(self, moves: List[Dict[str, Any]]):
        """Set alternative moves from list."""
        self.alternative_moves = json.dumps(moves)


class SensorReading(Base):
    """Stores sensor data for drawback detection."""
    __tablename__ = 'sensor_readings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    move_id = Column(Integer, ForeignKey('moves.id'), nullable=True)
    sensor_type = Column(String(50), nullable=False)
    sensor_version = Column(String(20), nullable=False)
    raw_data = Column(Text, nullable=False)  # JSON string
    processed_data = Column(Text, nullable=True)  # JSON string
    confidence_score = Column(Float, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    drawback_detected = Column(Boolean, default=False)
    drawback_type = Column(String(50), nullable=True)
    drawback_severity = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="sensor_readings")
    position = relationship("Position", back_populates="sensor_readings")
    move = relationship("Move", back_populates="sensor_readings")
    
    # Indexes
    __table_args__ = (
        Index('idx_sensor_readings_game_id', 'game_id'),
        Index('idx_sensor_readings_position_id', 'position_id'),
    )
    
    def get_raw_data(self) -> Dict[str, Any]:
        """Parse raw data JSON."""
        return json.loads(self.raw_data)
    
    def set_raw_data(self, data: Dict[str, Any]):
        """Set raw data from dictionary."""
        self.raw_data = json.dumps(data)
    
    def get_processed_data(self) -> Dict[str, Any]:
        """Parse processed data JSON."""
        if self.processed_data:
            return json.loads(self.processed_data)
        return {}
    
    def set_processed_data(self, data: Dict[str, Any]):
        """Set processed data from dictionary."""
        self.processed_data = json.dumps(data)


class TrainingSample(Base):
    """Prepared training data for ML model."""
    __tablename__ = 'training_samples'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    input_encoding = Column(Text, nullable=False)  # JSON string
    target_value = Column(Float, nullable=False)
    target_policy = Column(Text, nullable=False)  # JSON string
    legal_moves_mask = Column(Text, nullable=False)  # JSON string
    sensor_features = Column(Text, nullable=True)  # JSON string
    sample_weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="training_samples")
    position = relationship("Position", back_populates="training_samples")
    
    # Indexes
    __table_args__ = (
        Index('idx_training_samples_game_id', 'game_id'),
    )
    
    def get_input_encoding(self) -> Dict[str, Any]:
        """Parse input encoding JSON."""
        return json.loads(self.input_encoding)
    
    def set_input_encoding(self, encoding: Dict[str, Any]):
        """Set input encoding from dictionary."""
        self.input_encoding = json.dumps(encoding)
    
    def get_target_policy(self) -> Dict[str, float]:
        """Parse target policy JSON."""
        return json.loads(self.target_policy)
    
    def set_target_policy(self, policy: Dict[str, float]):
        """Set target policy from dictionary."""
        self.target_policy = json.dumps(policy)
    
    def get_legal_moves_mask(self) -> Dict[str, bool]:
        """Parse legal moves mask JSON."""
        return json.loads(self.legal_moves_mask)
    
    def set_legal_moves_mask(self, mask: Dict[str, bool]):
        """Set legal moves mask from dictionary."""
        self.legal_moves_mask = json.dumps(mask)
    
    def get_sensor_features(self) -> Dict[str, Any]:
        """Parse sensor features JSON."""
        if self.sensor_features:
            return json.loads(self.sensor_features)
        return {}
    
    def set_sensor_features(self, features: Dict[str, Any]):
        """Set sensor features from dictionary."""
        self.sensor_features = json.dumps(features)


class DrawbackPattern(Base):
    """Learned drawback patterns and their effectiveness."""
    __tablename__ = 'drawback_patterns'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_name = Column(String(100), unique=True, nullable=False)
    pattern_type = Column(String(20), nullable=False)  # 'tactical', 'positional', 'timing'
    pattern_signature = Column(Text, nullable=False)  # JSON string
    detection_rules = Column(Text, nullable=False)  # JSON string
    effectiveness_score = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, default=func.now())
    
    def get_pattern_signature(self) -> Dict[str, Any]:
        """Parse pattern signature JSON."""
        return json.loads(self.pattern_signature)
    
    def set_pattern_signature(self, signature: Dict[str, Any]):
        """Set pattern signature from dictionary."""
        self.pattern_signature = json.dumps(signature)
    
    def get_detection_rules(self) -> Dict[str, Any]:
        """Parse detection rules JSON."""
        return json.loads(self.detection_rules)
    
    def set_detection_rules(self, rules: Dict[str, Any]):
        """Set detection rules from dictionary."""
        self.detection_rules = json.dumps(rules)
    
    def update_effectiveness(self, success: bool):
        """Update effectiveness metrics."""
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.effectiveness_score = self.success_count / self.usage_count if self.usage_count > 0 else 0.0
        self.last_updated = func.now()
