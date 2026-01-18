#!/usr/bin/env python3
"""
Subtractive Mask Demo for Drawback Chess Engine

Demonstrates the core pipeline:
1. Fairy-Stockfish generates base moves (C++ speed)
2. AI applies subtractive mask (Python logic)
3. MCTS uses filtered moves for search
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.engine.fairy_stockfish_interface import create_fairy_interface, get_base_moves_fast
from src.training.two_head_model import TwoHeadChessModel, create_two_head_model


class SubtractiveMaskPipeline:
    """Core pipeline: Fairy-Stockfish + AI Subtractive Mask."""
    
    def __init__(self, stockfish_path: str = "stockfish"):
        """Initialize the pipeline."""
        self.fairy_interface = create_fairy_interface(stockfish_path)
        self.ai_model = create_two_head_model()
        
        # Performance tracking
        self.total_positions = 0
        self.total_base_moves = 0
        self.total_filtered_moves = 0
    
    def process_position(self, fen: str, suspected_drawback: str = None) -> dict:
        """
        Process a single position through the complete pipeline.
        
        Args:
            fen: Position in FEN format
            suspected_drawback: AI's guess about opponent's drawback
            
        Returns:
            Dictionary with pipeline results
        """
        start_time = time.time()
        
        # Step 1: Fairy-Stockfish generates base moves (C++ speed!)
        fairy_result = self.fairy_interface.get_base_moves(fen)
        base_moves = fairy_result.base_moves
        
        # Step 2: AI predicts drawback if not provided
        if suspected_drawback is None:
            # Use Detective Head to predict drawback
            # For demo, we'll use a simple heuristic
            suspected_drawback = self._predict_drawback_simple(fen)
        
        # Step 3: AI generates subtractive mask
        drawback_id = self._get_drawback_id(suspected_drawback)
        legality_probs = self.ai_model.predict_legality(fen, drawback_id)
        
        # Step 4: Apply subtractive mask to base moves
        filtered_moves = self._apply_subtractive_mask(base_moves, legality_probs)
        
        # Step 5: Prepare results
        processing_time = (time.time() - start_time) * 1000
        
        result = {
            "fen": fen,
            "player": fairy_result.player_to_move,
            "base_moves": base_moves,
            "base_move_count": len(base_moves),
            "suspected_drawback": suspected_drawback,
            "legality_probabilities": legality_probs.squeeze().tolist()[:len(base_moves)],
            "filtered_moves": filtered_moves,
            "filtered_move_count": len(filtered_moves),
            "fairy_generation_time_ms": fairy_result.generation_time_ms,
            "ai_processing_time_ms": processing_time - fairy_result.generation_time_ms,
            "total_time_ms": processing_time
        }
        
        # Update stats
        self.total_positions += 1
        self.total_base_moves += len(base_moves)
        self.total_filtered_moves += len(filtered_moves)
        
        return result
    
    def _predict_drawback_simple(self, fen: str) -> str:
        """Simple drawback prediction (placeholder for AI model)."""
        # This would use the Detective Head in production
        # For demo, we'll use a simple heuristic based on position
        
        # Extract some simple features from FEN
        if "rnbqkbnr" in fen:  # Starting position
            return "none"
        elif "pppppppp" not in fen:  # Pawns have moved
            return "Knight_Immobility"
        else:
            return "No_Castling"
    
    def _get_drawback_id(self, drawback_name: str) -> int:
        """Convert drawback name to ID."""
        drawback_map = {
            "none": 0,
            "No_Castling": 1,
            "Knight_Immobility": 2,
            "Queen_Capture_Ban": 3,
            "Pawn_Immunity": 4
        }
        return drawback_map.get(drawback_name, 0)
    
    def _apply_subtractive_mask(self, base_moves: List[str], 
                              legality_probs: List[float]) -> List[str]:
        """
        Apply subtractive mask to base moves.
        
        This is the core of the AI's decision-making process.
        """
        filtered_moves = []
        
        for i, move in enumerate(base_moves):
            if i < len(legality_probs):
                # Use probability threshold (could be dynamic)
                prob = legality_probs[i]
                if prob > 0.1:  # 10% threshold
                    filtered_moves.append(move)
        
        return filtered_moves
    
    def get_performance_stats(self) -> dict:
        """Get pipeline performance statistics."""
        avg_base_moves = self.total_base_moves / self.total_positions if self.total_positions > 0 else 0
        avg_filtered_moves = self.total_filtered_moves / self.total_positions if self.total_positions > 0 else 0
        filter_ratio = avg_filtered_moves / avg_base_moves if avg_base_moves > 0 else 0
        
        return {
            "total_positions": self.total_positions,
            "avg_base_moves": avg_base_moves,
            "avg_filtered_moves": avg_filtered_moves,
            "filter_ratio": filter_ratio,
            "fairy_stats": self.fairy_interface.get_performance_stats()
        }


def demo_subtractive_mask():
    """Demonstrate the subtractive mask pipeline."""
    print("=== Subtractive Mask Pipeline Demo ===")
    print("Fairy-Stockfish (C++) + AI (Python) = Perfect Combination!")
    print()
    
    # Initialize pipeline
    try:
        pipeline = SubtractiveMaskPipeline()
    except Exception as e:
        print(f"Failed to initialize pipeline (Fairy-Stockfish needed): {e}")
        print("Please install Fairy-Stockfish to run this demo")
        return
    
    # Test positions
    test_positions = [
        {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "description": "Starting position"
        },
        {
            "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "description": "After 1.e4 e5"
        },
        {
            "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            "description": "After 2.Nf3 Nc6"
        }
    ]
    
    # Process each position
    for i, test_pos in enumerate(test_positions):
        print(f"--- Position {i+1}: {test_pos['description']} ---")
        
        # Test with different suspected drawbacks
        drawbacks_to_test = ["none", "No_Castling", "Knight_Immobility"]
        
        for drawback in drawbacks_to_test:
            print(f"\nTesting with suspected drawback: {drawback}")
            
            result = pipeline.process_position(test_pos["fen"], drawback)
            
            print(f"  Base moves: {result['base_move_count']}")
            print(f"  Filtered moves: {result['filtered_move_count']}")
            print(f"  Filter ratio: {result['filtered_move_count']/result['base_move_count']:.2%}")
            print(f"  Fairy time: {result['fairy_generation_time_ms']:.2f}ms")
            print(f"  AI time: {result['ai_processing_time_ms']:.2f}ms")
            print(f"  Total time: {result['total_time_ms']:.2f}ms")
            
            # Show some example moves
            if result['base_moves']:
                print(f"  Sample base moves: {result['base_moves'][:5]}")
            if result['filtered_moves']:
                print(f"  Sample filtered moves: {result['filtered_moves'][:5]}")
        
        print()
    
    # Show overall performance
    stats = pipeline.get_performance_stats()
    print("=== Overall Performance ===")
    print(f"Positions processed: {stats['total_positions']}")
    print(f"Average base moves: {stats['avg_base_moves']:.1f}")
    print(f"Average filtered moves: {stats['avg_filtered_moves']:.1f}")
    print(f"Average filter ratio: {stats['filter_ratio']:.2%}")
    
    fairy_stats = stats['fairy_stats']
    print(f"Fairy-Stockfish performance: {fairy_stats['queries_per_second']:.1f} queries/second")
    print(f"Fairy-Stockfish avg time: {fairy_stats['avg_time_ms']:.2f}ms")


def demo_speed_comparison():
    """Demonstrate the speed advantage of Fairy-Stockfish vs Python."""
    print("\n=== Speed Comparison Demo ===")
    
    test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    iterations = 10
    
    # Test Fairy-Stockfish speed
    print(f"Testing Fairy-Stockfish speed ({iterations} iterations)...")
    try:
        start_time = time.time()
        for _ in range(iterations):
            moves = get_base_moves_fast(test_fen)
        fairy_time = (time.time() - start_time) * 1000
        
        print(f"Fairy-Stockfish: {fairy_time:.2f}ms total, {fairy_time/iterations:.2f}ms per query")
        print(f"Fairy-Stockfish: {iterations/(fairy_time/1000):.1f} queries/second")
        print(f"Moves found: {len(moves)}")
        
    except Exception as e:
        print(f"Fairy-Stockfish test failed: {e}")
        return
    
    # Test Python chess library speed (if available)
    try:
        import chess
        
        print(f"\nTesting python-chess speed ({iterations} iterations)...")
        start_time = time.time()
        for _ in range(iterations):
            board = chess.Board(test_fen)
            moves = [move.uci() for move in board.legal_moves]
        python_time = (time.time() - start_time) * 1000
        
        print(f"python-chess: {python_time:.2f}ms total, {python_time/iterations:.2f}ms per query")
        print(f"python-chess: {iterations/(python_time/1000):.1f} queries/second")
        print(f"Moves found: {len(moves)}")
        
        # Calculate speedup
        if python_time > 0:
            speedup = python_time / fairy_time
            print(f"\nSpeedup: {speedup:.1f}x faster with Fairy-Stockfish!")
        
    except ImportError:
        print("python-chess not available for comparison")
    except Exception as e:
        print(f"python-chess test failed: {e}")


def main():
    """Run the complete subtractive mask demo."""
    print("Drawback Chess Engine - Subtractive Mask Pipeline Demo")
    print("=" * 60)
    
    # Main demo
    demo_subtractive_mask()
    
    # Speed comparison
    demo_speed_comparison()
    
    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("1. Fairy-Stockfish generates base moves in C++ (blazing fast)")
    print("2. AI applies subtractive mask in Python (smart filtering)")
    print("3. Combined approach gives both speed AND intelligence")
    print("4. This is the core of the Drawback Chess AI strategy!")


if __name__ == "__main__":
    main()
