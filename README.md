# Drawback Chess AI

Local development repository for the Drawback-Chess-Engine project.

## About Drawback Chess

Drawback Chess is a chess variant where each player has a **hidden drawback** that affects their legal moves. You cannot see your opponent's drawback, and they cannot see yours. The drawbacks are enforced by the game engine.

### Key Differences from Standard Chess

- **No checkmate or stalemate** - Win by capturing the king or opponent having no legal moves
- **Hidden drawbacks** - Each player has secret movement/capture restrictions
- **King safety ignored** - Legal to move into check, ignore threats, move pinned pieces
- **Special king captures** - Kings can be captured en passant and after castling through check
- **Asymmetric rules** - Players may have different drawbacks with scoring adjustments

See [Drawback Chess Rules](docs/drawback_chess_rules.md) for complete details.

## Upstream Repository

This repository is wired to: https://github.com/titaniummachine1/Drawback-Chess-Engine

## Project Architecture

### Retroactive Reconstruction Pipeline

This project implements a novel training approach that turns hidden information into a data advantage:

1. **Record Games**: Capture moves during gameplay (AI vs AI + AI vs Human)
2. **Capture Reveal**: Get opponent's drawback at game end via network packet
3. **Reconstruct**: Replay game locally with Fairy-Stockfish + revealed drawback
4. **Generate Data**: Create perfect legal move information for every position
5. **Train**: Two-head neural network on unified dataset

### Two-Head Neural Architecture

- **Physics Engine Head**: Learns which moves are illegal given a known drawback
- **Detective Head**: Predicts opponent's drawback from move history patterns

### Storage Efficiency

- **Minimal schema**: Only FEN + legal moves + drawback data (500MB vs 5GB)
- **On-demand generation**: Complex training data generated from minimal storage
- **Legal move preservation**: Critical data that cannot be deduced without drawbacks

## Development Setup

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: Install Fairy-Stockfish for retroactive reconstruction
# Download from: https://github.com/fairy-stockfish/Fairy-Stockfish
```

### Project Structure

```
src/
├── db/                    # Database and storage
│   ├── minimal_models.py   # 3-table minimal schema
│   ├── minimal_storage.py  # Ultra-efficient storage
│   └── training_extractor.py # On-demand training data
├── recording/              # Game capture system
│   ├── game_recorder.py    # Raw game + reveal capture
│   └── packet_monitor.py   # Network packet monitoring
├── reconstruction/         # Retroactive reconstruction
│   └── retroactive_reconstructor.py # Fairy-Stockfish integration
├── training/               # Neural network training
│   ├── unified_format.py   # JSONL training data format
│   └── two_head_model.py   # Physics + Detective heads
└── engine/                 # Chess engine logic
    └── chess_engine.py     # MCTS implementation

examples/
└── complete_pipeline.py    # Full workflow demonstration

docs/
├── drawback_chess_rules.md # Complete game rules
└── minimal_database_schema.md # Storage design
```

## Quick Start

### 1. Run the Complete Pipeline Demo

```bash
python examples/complete_pipeline.py
```

This demonstrates:

- Game recording (AI vs AI + AI vs Human scenarios)
- Packet monitoring for drawback reveals
- Retroactive reconstruction with Fairy-Stockfish
- Unified training data creation
- Two-head model training

### 2. Record Your First Game

```python
from src.recording.game_recorder import start_ai_vs_human_game, record_move

# Start recording a game against human
game_id = start_ai_vs_human_game()

# Record moves as they happen
record_move("white", "e2e4")
record_move("black", "e7e5")

# Game ends - capture the reveal packet
from src.recording.game_recorder import capture_game_end_packet
reveal_packet = {"players": {"white": {"drawback": "No_Castling"}}}
final_id = capture_game_end_packet(reveal_packet, "white_win")
```

### 3. Reconstruct and Train

```python
from src.reconstruction.retroactive_reconstructor import reconstruct_all_recorded_games
from src.training.unified_format import create_unified_dataset

# Reconstruct games with legal move data
games = reconstruct_all_recorded_games("data/reconstructed")

# Create unified training dataset
create_unified_dataset(games, "data/unified")
```

## Key Features

### 🎯 Retroactive Reconstruction

- Turns hidden information into perfect training data
- Works for both AI vs AI (perfect info) and AI vs Human (hidden info)
- Generates legal move masks for every position

### 📊 Two-Head Architecture

- **Physics Head**: Learns move legality for known drawbacks
- **Detective Head**: Predicts drawbacks from move patterns
- Shared encoder for efficient training

### 💾 Minimal Storage

- 10x reduction (500MB vs 5GB)
- Stores only essential data: FEN + legal moves + drawbacks
- On-demand complex data generation

### 🌐 Network Integration

- Automatic packet monitoring for drawback reveals
- Support for multiple packet formats
- Real-time game recording

## Training Data Format

The unified JSONL format works for both training scenarios:

```json
{
  "game_id": "uuid_555",
  "meta": {
    "white_drawback": "Knight_Immobility",
    "black_drawback": "Queen_Capture_Ban"
  },
  "training_samples": [
    {
      "ply": 12,
      "fen": "r1bqk2r/pppp1ppp/...",
      "base_moves": ["e1g1", "e1f1", "d2d4", ...],
      "legality_mask": [0, 1, 1, ...],  // TARGET 1: Physics Engine
      "active_drawback_id": 5          // TARGET 2: Detective
    }
  ]
}
```

## Contributing

This repository follows the upstream project's contribution guidelines. Focus areas:

1. **Packet Monitoring**: Improve network capture for different clients
2. **Reconstruction**: Enhance Fairy-Stockfish integration
3. **Training**: Optimize two-head model architecture
4. **Storage**: Further optimize minimal database schema

## License

Follows the upstream Drawback-Chess-Engine project license.
