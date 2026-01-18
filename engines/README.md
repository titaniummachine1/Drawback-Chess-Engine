# Embedded Chess Engines

This directory contains chess engines used by the Drawback Chess Engine.

## Structure

```
engines/
├── stockfish.exe          # Fairy-Stockfish executable (Windows)
├── stockfish               # Fairy-Stockfish executable (Linux/macOS)
└── README.md              # This file
```

## Installation

### Windows

1. Download `fairy-stockfish-largeboard_x86-64-bmi2.exe` from:
   https://github.com/fairy-stockfish/Fairy-Stockfish/releases
2. Place it in this directory as `stockfish.exe`

### Linux/macOS

1. Download `fairy-stockfish-largeboard_x86-64-bmi2` from releases
2. Place it in this directory as `stockfish`
3. Make executable: `chmod +x stockfish`

## Usage in Code

The engines are automatically detected by the Drawback Chess Engine:

```python
from src.engine.fairy_stockfish_interface import create_fairy_interface

# Automatically finds engines/stockfish.exe or engines/stockfish
fs = create_fairy_interface("engines/stockfish.exe")
```

## Performance

- **Windows**: Use BMI2 version for best performance
- **Linux/macOS**: Use BMI2 version for modern CPUs
- **Fallback**: Uses python-chess if engine not found

## Versions

- **Recommended**: fairy-stockfish-largeboard_x86-64-bmi2
- **Compatibility**: fairy-stockfish-largeboard_x86-64
- **Size**: ~23MB per executable
