#!/usr/bin/env python3
"""
Minimal Drawback Chess Engine - Main Entry Point

Ultra-lightweight version focused on FEN storage and legal move preservation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db.minimal_storage import get_minimal_storage, MinimalGame, MinimalPosition, MinimalDrawback
from src.db.training_extractor import TrainingExtractor


def main():
    """Main entry point for minimal Drawback Chess Engine."""
    print("Minimal Drawback Chess Engine Starting...")
    
    # Initialize storage
    storage = get_minimal_storage()
    
    # Example: Store a sample game
    sample_game = MinimalGame(
        uuid="sample-game-123",
        result="white_win",
        opponent_type="engine",
        engine_version="1.0.0",
        positions=[
            MinimalPosition(
                move_number=0,
                fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                legal_moves=["e2e4", "d2d4", "g1f3", "b1c3"]
            ),
            MinimalPosition(
                move_number=1,
                fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                legal_moves=["e7e5", "e7e6", "d7d5", "g8f6"]
            )
        ],
        drawbacks=[
            MinimalDrawback(
                position_move_number=1,
                drawback_type="center_control",
                severity=0.3,
                legal_moves_available=["e7e5", "d7d5"],
                metadata={"affected_pieces": ["pawn"], "threat_squares": ["e5", "d5"]}
            )
        ]
    )
    
    # Store the game
    game_id = storage.store_game(sample_game)
    print(f"Stored sample game with ID: {game_id}")
    
    # Extract training data
    extractor = TrainingExtractor()
    training_samples = list(extractor.extract_training_samples(limit=10))
    
    print(f"Generated {len(training_samples)} training samples")
    for i, sample in enumerate(training_samples[:3]):
        print(f"Sample {i+1}: {sample.fen[:20]}... | Drawback: {sample.has_drawback}")
    
    # Show storage statistics
    stats = storage.get_statistics()
    print(f"\nStorage Statistics:")
    print(f"Total games: {stats['total_games']}")
    print(f"Total positions: {stats['total_positions']}")
    print(f"Total drawbacks: {stats['total_drawbacks']}")
    
    print("\nMinimal Drawback Chess Engine ready!")


if __name__ == "__main__":
    main()
