"""
Minimal Database Models for Drawback Chess Engine

Stripped-down models storing only essential data: FEN, legal moves, and drawback information.
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Game(Base):
    """Minimal game record - only essential metadata."""
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    result = Column(String(20), nullable=True)  # 'white_win', 'black_win', 'draw'
    opponent_type = Column(String(20), nullable=True)  # 'human', 'engine', 'self_play'
    engine_version = Column(String(50), nullable=True)
    white_drawback = Column(Text, nullable=True)  # Full description of White's rule
    black_drawback = Column(Text, nullable=True)  # Full description of Black's rule
    total_moves = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    positions = relationship("Position", back_populates="game", cascade="all, delete-orphan")
    drawbacks = relationship("Drawback", back_populates="game", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_games_result', 'result'),
    )


class Position(Base):
    """Position with FEN and legal moves - the core training data."""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    move_number = Column(Integer, nullable=False)  # Ply number
    fen = Column(Text, nullable=False)  # Complete position (using Text for safety)
    move_uci = Column(String(10), nullable=True)  # The move played in this position
    legal_moves = Column(Text, nullable=False)  # JSON array of legal UCI moves
    active_side = Column(String(10), nullable=True) # 'white' or 'black'
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="positions")
    drawbacks = relationship("Drawback", back_populates="position", cascade="all, delete-orphan")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('game_id', 'move_number', name='uq_game_move'),
        Index('idx_positions_game_id', 'game_id'),
        Index('idx_positions_move_uci', 'move_uci'),
    )
    
    def get_legal_moves(self) -> List[str]:
        """Parse legal moves JSON array."""
        return json.loads(self.legal_moves)
    
    def set_legal_moves(self, moves: List[str]):
        """Set legal moves from list."""
        self.legal_moves = json.dumps(moves)


class Drawback(Base):
    """Drawback detection data - only stored when detected."""
    __tablename__ = 'drawbacks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    drawback_type = Column(String(50), nullable=False)  # e.g., 'Knight_Immobility'
    drawback_description = Column(Text, nullable=True)  # Explain what it does
    severity = Column(Float, default=0.0)  # 0.0 to 1.0
    legal_moves_response = Column(Text, nullable=False)  # JSON: legal moves available when drawback detected
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="drawbacks")
    position = relationship("Position", back_populates="drawbacks")
    
    # Indexes
    __table_args__ = (
        Index('idx_drawbacks_position_id', 'position_id'),
        Index('idx_drawbacks_type', 'drawback_type'),
        Index('idx_drawbacks_severity', 'severity'),
    )
    
    def get_legal_moves_response(self) -> Dict[str, Any]:
        """Parse legal moves response JSON."""
        return json.loads(self.legal_moves_response)
    
    def set_legal_moves_response(self, response_data: Dict[str, Any]):
        """Set legal moves response from dictionary."""
        self.legal_moves_response = json.dumps(response_data)
