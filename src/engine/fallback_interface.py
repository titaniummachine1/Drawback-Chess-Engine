"""
Fallback Interface for Drawback Chess Engine

Provides python-chess based fallback when Fairy-Stockfish is not available.
Much slower but functional for development/testing.
"""

import chess
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class FallbackMoveResult:
    """Result from fallback move generation."""
    base_moves: List[str]
    position_fen: str
    player_to_move: str
    generation_time_ms: float
    is_fallback: bool = True


class FallbackInterface:
    """Fallback interface using python-chess library."""
    
    def __init__(self):
        """Initialize fallback interface."""
        self.total_queries = 0
        self.total_time_ms = 0
    
    def get_base_moves(self, fen: str) -> FallbackMoveResult:
        """
        Get base moves using python-chess (slow fallback).
        
        Args:
            fen: Position in FEN format
            
        Returns:
            FallbackMoveResult with legal moves
        """
        import time
        start_time = time.time()
        
        try:
            # Create chess board from FEN
            board = chess.Board(fen)
            
            # Get legal moves
            legal_moves = [move.uci() for move in board.legal_moves]
            
            # Extract player from FEN
            player = self._extract_player_from_fen(fen)
            
            generation_time = (time.time() - start_time) * 1000
            
            # Update stats
            self.total_queries += 1
            self.total_time_ms += generation_time
            
            return FallbackMoveResult(
                base_moves=legal_moves,
                position_fen=fen,
                player_to_move=player,
                generation_time_ms=generation_time
            )
            
        except Exception as e:
            print(f"Error in fallback move generation: {e}")
            return FallbackMoveResult(
                base_moves=[],
                position_fen=fen,
                player_to_move="white",
                generation_time_ms=0
            )
    
    def _extract_player_from_fen(self, fen: str) -> str:
        """Extract current player from FEN."""
        try:
            fen_parts = fen.split()
            return "white" if fen_parts[1] == 'w' else "black"
        except (IndexError, ValueError):
            return "white"
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        avg_time = self.total_time_ms / self.total_queries if self.total_queries > 0 else 0
        queries_per_second = 1000 / avg_time if avg_time > 0 else 0
        
        return {
            "total_queries": self.total_queries,
            "total_time_ms": self.total_time_ms,
            "avg_time_ms": avg_time,
            "queries_per_second": queries_per_second,
            "interface_type": "fallback_python_chess"
        }


def get_base_moves_fallback(fen: str) -> List[str]:
    """
    Fast fallback function for getting base moves.
    
    Args:
        fen: Position in FEN format
        
    Returns:
        List of legal moves in UCI format
    """
    fallback = FallbackInterface()
    result = fallback.get_base_moves(fen)
    return result.base_moves


def test_fallback_interface():
    """Test the fallback interface."""
    print("=== Testing Fallback Interface (python-chess) ===")
    
    try:
        import chess
        print("python-chess library available")
    except ImportError:
        print("python-chess not available - fallback will not work")
        return
    
    # Test position
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    fallback = FallbackInterface()
    result = fallback.get_base_moves(fen)
    
    print(f"Position: {fen}")
    print(f"Player: {result.player_to_move}")
    print(f"Moves found: {len(result.base_moves)}")
    print(f"Generation time: {result.generation_time_ms:.2f}ms")
    print(f"Sample moves: {result.base_moves[:5]}")
    
    # Performance stats
    stats = fallback.get_performance_stats()
    print(f"Performance: {stats['queries_per_second']:.1f} queries/second")
    print("Note: This is much slower than Fairy-Stockfish!")


if __name__ == "__main__":
    test_fallback_interface()
