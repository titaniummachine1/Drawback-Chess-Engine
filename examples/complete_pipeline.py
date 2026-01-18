#!/usr/bin/env python3
"""
Complete Pipeline Example for Drawback Chess Engine

Demonstrates the full workflow:
1. Record games (AI vs AI + AI vs Human)
2. Capture drawback reveal packets
3. Retroactive reconstruction with Fairy-Stockfish
4. Create unified training format
5. Train two-head architecture
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.recording.game_recorder import get_recorder, start_ai_vs_ai_game, record_move, capture_game_end_packet
from src.recording.packet_monitor import get_packet_monitor, setup_recorder_integration, ManualPacketCapture
from src.reconstruction.retroactive_reconstructor import RetroactiveReconstructor, reconstruct_all_recorded_games
from src.training.unified_format import create_unified_dataset, load_unified_dataset


def simulate_ai_vs_ai_game():
    """Simulate an AI vs AI game with perfect information."""
    print("\n=== Simulating AI vs AI Game ===")
    
    # Start recording
    game_id = start_ai_vs_ai_game("No_Castling", "Knight_Immobility")
    
    # Simulate moves
    moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f2f4"]
    
    for i, move in enumerate(moves):
        player = "white" if i % 2 == 0 else "black"
        record_move(player, move)
        time.sleep(0.1)  # Simulate thinking time
    
    # End game with result
    result = "white_win"
    final_game_id = capture_game_end_packet(
        ManualPacketCapture.simulate_reveal_packet("No_Castling", "Knight_Immobility", result),
        result
    )
    
    print(f"AI vs AI game completed: {final_game_id}")
    return final_game_id


def simulate_ai_vs_human_game():
    """Simulate an AI vs Human game with hidden information."""
    print("\n=== Simulating AI vs Human Game ===")
    
    from src.recording.game_recorder import get_recorder
    recorder = get_recorder()
    
    # Start recording (no initial drawbacks known)
    game_id = recorder.start_new_game(game_type='ai_vs_human', opponent_type='human')
    
    # Simulate moves (only know our own moves)
    ai_moves = ["e2e4", "g1f3", "f2f4"]  # White (AI) moves
    human_moves = ["e7e5", "b8c6"]  # Black (Human) moves - we only see these after they're played
    
    # Record the game as it unfolds
    for i in range(len(ai_moves) + len(human_moves)):
        if i < len(ai_moves) * 2:  # AI moves are on even ply numbers
            if i % 2 == 0:  # White's turn (AI)
                record_move("white", ai_moves[i // 2])
            else:  # Black's turn (Human) - we see the move after it's played
                record_move("black", human_moves[i // 2])
        else:
            break
        
        time.sleep(0.1)
    
    # Game ends - we capture the reveal packet
    reveal_packet = ManualPacketCapture.simulate_reveal_packet("Queen_Capture_Ban", "Pawn_Immunity", "draw")
    
    final_game_id = capture_game_end_packet(reveal_packet, "draw")
    
    print(f"AI vs Human game completed: {final_game_id}")
    return final_game_id


def demonstrate_packet_monitoring():
    """Demonstrate packet monitoring for drawback reveals."""
    print("\n=== Demonstrating Packet Monitoring ===")
    
    # Set up integration between monitor and recorder
    setup_recorder_integration()
    
    # Start monitoring
    monitor = get_packet_monitor()
    monitor.start_monitoring()
    
    # Simulate some packets
    packets = [
        {"type": "game_update", "move": "e2e4"},
        {"type": "game_update", "move": "e7e5"},
        ManualPacketCapture.simulate_reveal_packet("No_Castling", "Knight_Immobility", "white_win"),
        {"type": "other", "data": "irrelevant"}
    ]
    
    for packet in packets:
        monitor.add_packet(packet)
        time.sleep(0.1)
    
    # Stop monitoring
    monitor.stop_monitoring()
    
    # Show captured packets
    captured = monitor.get_captured_packets()
    print(f"Captured {len(captured)} packets")
    
    # Export for analysis
    monitor.export_packets("data/captured_packets.json")


def demonstrate_reconstruction():
    """Demonstrate retroactive reconstruction."""
    print("\n=== Demonstrating Retroactive Reconstruction ===")
    
    # Note: This would require Fairy-Stockfish to be installed
    # For demonstration, we'll show the structure
    
    try:
        # Get recorded games
        recorder = get_recorder()
        games = recorder.get_games_with_revealed_drawbacks()
        
        print(f"Found {len(games)} games with revealed drawbacks")
        
        if games:
            # Reconstruct all games
            reconstructed_games = reconstruct_all_recorded_games("data/reconstructed")
            print(f"Reconstructed {len(reconstructed_games)} games")
            
            return reconstructed_games
        else:
            print("No games with revealed drawbacks found")
            return []
    
    except Exception as e:
        print(f"Reconstruction demo failed (expected if Fairy-Stockfish not installed): {e}")
        return []


def demonstrate_unified_format(reconstructed_games):
    """Demonstrate unified training format creation."""
    print("\n=== Demonstrating Unified Format ===")
    
    if not reconstructed_games:
        print("No reconstructed games to convert")
        return
    
    # Create unified dataset
    dataset_path = create_unified_dataset(reconstructed_games, "data/unified")
    print(f"Created unified dataset at {dataset_path}")
    
    # Load and show sample
    train_games, val_games, test_games = load_unified_dataset(dataset_path)
    
    print(f"Loaded dataset:")
    print(f"  Train: {len(train_games)} games")
    print(f"  Val: {len(val_games)} games")
    print(f"  Test: {len(test_games)} games")
    
    # Show sample training data
    if train_games:
        sample_game = train_games[0]
        print(f"\nSample game {sample_game.game_id}:")
        print(f"  Meta: {sample_game.meta}")
        print(f"  Samples: {len(sample_game.training_samples)}")
        
        if sample_game.training_samples:
            sample = sample_game.training_samples[0]
            print(f"  First sample:")
            print(f"    FEN: {sample.fen[:40]}...")
            print(f"    Player: {sample.player}")
            print(f"    Move: {sample.move_played}")
            print(f"    Base moves: {len(sample.base_moves)}")
            print(f"    Legality mask: {sample.legality_mask[:5]}...")
            print(f"    Drawback ID: {sample.active_drawback_id}")


def demonstrate_two_head_training():
    """Demonstrate the two-head training architecture."""
    print("\n=== Demonstrating Two-Head Training Architecture ===")
    
    print("The two-head architecture uses the same unified data for different purposes:")
    print()
    
    print("HEAD A: Physics Engine (The Mask)")
    print("- Input: Board State + Drawback Label")
    print("- Output: Probability Mask for base_moves")
    print("- Goal: Learn which moves are illegal given a drawback")
    print("- Training: Uses legality_mask as target")
    print()
    
    print("HEAD B: Detective (The Guesser)")
    print("- Input: Board State + Move History")
    print("- Output: Probability of each drawback")
    print("- Goal: Guess opponent's drawback from their behavior")
    print("- Training: Uses active_drawback_id as target")
    print()
    
    print("Training Loop:")
    print("1. Load unified dataset")
    print("2. For each sample:")
    print("   - Head A: Predict legality_mask from fen + drawback_id")
    print("   - Head B: Predict drawback_id from fen + move_history")
    print("3. Backpropagate both heads")
    print("4. Repeat")
    print()
    
    print("Inference Loop:")
    print("1. Head B analyzes opponent's move history")
    print("2. Predicts: 80% Knight_Immobility, 15% No_Castling, 5% other")
    print("3. Feed 'Knight_Immobility' to Head A")
    print("4. Head A generates subtractive mask")
    print("5. MCTS uses mask to search for winning move")


def main():
    """Run the complete pipeline demonstration."""
    print("=== Drawback Chess Engine - Complete Pipeline Demo ===")
    
    # Ensure data directories exist
    Path("data").mkdir(exist_ok=True)
    Path("data/raw_games").mkdir(exist_ok=True)
    Path("data/reconstructed").mkdir(exist_ok=True)
    Path("data/unified").mkdir(exist_ok=True)
    
    # Step 1: Record games
    simulate_ai_vs_ai_game()
    simulate_ai_vs_human_game()
    
    # Step 2: Packet monitoring
    demonstrate_packet_monitoring()
    
    # Step 3: Retroactive reconstruction
    reconstructed_games = demonstrate_reconstruction()
    
    # Step 4: Unified format
    demonstrate_unified_format(reconstructed_games)
    
    # Step 5: Two-head architecture explanation
    demonstrate_two_head_training()
    
    print("\n=== Pipeline Demo Complete ===")
    print("Next steps:")
    print("1. Install Fairy-Stockfish for actual reconstruction")
    print("2. Set up real packet monitoring for live games")
    print("3. Implement the two-head neural network architecture")
    print("4. Train on the unified dataset")


if __name__ == "__main__":
    main()
