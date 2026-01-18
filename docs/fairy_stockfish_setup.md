# Fairy-Stockfish Setup Guide

## Overview

Fairy-Stockfish is **NOT** pre-installed. You need to download and install it separately to use the Drawback Chess Engine's high-performance move generation.

## Why Fairy-Stockfish?

- **C++ Performance**: Thousands of times faster than Python libraries
- **Variant Support**: Built-in support for chess variants like Drawback Chess
- **UCI Protocol**: Standard interface for chess engines
- **Perft Command**: Perfect for generating pseudo-legal moves

## Installation Options

### Option 1: Download Pre-compiled Binary (Recommended)

#### Windows

1. Go to [Fairy-Stockfish Releases](https://github.com/fairy-stockfish/Fairy-Stockfish/releases)
2. Download the latest `fairy-stockfish-x86_64.exe` or similar
3. Extract to a folder (e.g., `C:\fairy-stockfish\`)
4. Add to PATH or specify full path in code

#### Linux

1. Download latest `fairy-stockfish-x86_64` from releases
2. Make executable: `chmod +x fairy-stockfish-x86_64`
3. Move to PATH: `sudo mv fairy-stockfish-x86_64 /usr/local/bin/fairy-stockfish`

#### macOS

1. Download latest `fairy-stockfish-macos` from releases
2. Make executable: `chmod +x fairy-stockfish-macos`
3. Move to PATH: `sudo mv fairy-stockfish-macos /usr/local/bin/fairy-stockfish`

### Option 2: Compile from Source

#### Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install build-essential g++ make

# macOS (with Homebrew)
brew install gcc make

# Windows (with Visual Studio)
# Install Visual Studio Build Tools
```

#### Compilation

```bash
git clone https://github.com/fairy-stockfish/Fairy-Stockfish.git
cd Fairy-Stockfish/src

# Compile with optimization
make build ARCH=x86-64-modern

# Binary will be in ../stockfish
```

## Configuration

### Method 1: Add to System PATH

Add Fairy-Stockfish directory to your system PATH so the code can find it with just "stockfish" or "fairy-stockfish".

### Method 2: Specify Path in Code

```python
from src.engine.fairy_stockfish_interface import create_fairy_interface

# Specify full path
fs = create_fairy_interface("C:/fairy-stockfish/fairy-stockfish.exe")

# Or relative path
fs = create_fairy_interface("./engines/fairy-stockfish")
```

### Method 3: Environment Variable

```bash
# Set environment variable
export FAIRY_STOCKFISH_PATH="/path/to/fairy-stockfish"

# Use in code
import os
stockfish_path = os.getenv('FAIRY_STOCKFISH_PATH', 'stockfish')
fs = create_fairy_interface(stockfish_path)
```

## Verification

### Test Installation

```bash
# Test from command line
fairy-stockfish

# Should output something like:
# Fairy-Stockfish ...
# uciok
# readyok
```

### Test with Python

```python
from src.engine.fairy_stockfish_interface import test_fairy_interface

# Run the built-in test
test_fairy_interface()
```

### Test Performance

```python
from src.engine.fairy_stockfish_interface import get_base_moves_fast

# Quick performance test
fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
moves = get_base_moves_fast(fen)
print(f"Found {len(moves)} base moves")
```

## Drawback Chess Variant Support

Fairy-Stockfish has built-in support for custom variants. The Drawback Chess variant should be available, but if not:

### Check Available Variants

```python
from src.engine.fairy_stockfish_interface import create_fairy_interface

with create_fairy_interface() as fs:
    fs._send_command("setoption name UCI_Variant")
    # Check output for available variants
```

### Custom Variant Configuration

If Drawback Chess isn't built-in, you may need to define it in a configuration file.

## Troubleshooting

### Common Issues

#### "Fairy-Stockfish not found"

**Solution**: Ensure the executable is in PATH or specify full path

#### "Permission denied"

**Solution**: Make the file executable (Linux/macOS): `chmod +x fairy-stockfish`

#### "Variant not supported"

**Solution**: Check if Drawback Chess variant is available, or use standard chess for testing

#### "Engine not responding"

**Solution**: Check if the executable is correct and not corrupted

### Debug Mode

Enable debug output to troubleshoot:

```python
from src.engine.fairy_stockfish_interface import create_fairy_interface

fs = create_fairy_interface()
fs.start_engine()

# Test basic communication
fs._send_command("uci")
print(fs._wait_for_response("uciok"))
```

## Performance Expectations

Once properly installed, you should see:

- **10,000+ queries/second** for move generation
- **<1ms per query** for simple positions
- **Consistent performance** across different positions

## Integration with Drawback Chess Engine

### Update Configuration

Edit your configuration to point to Fairy-Stockfish:

```python
# In your main config
STOCKFISH_PATH = "C:/engines/fairy-stockfish.exe"  # Windows
# STOCKFISH_PATH = "/usr/local/bin/fairy-stockfish"  # Linux/macOS
```

### Use in Pipeline

```python
from src.reconstruction.retroactive_reconstructor import RetroactiveReconstructor

# Initialize with correct path
reconstructor = RetroactiveReconstructor(stockfish_path=STOCKFISH_PATH)
```

## Minimum Requirements

- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **RAM**: 64MB (very minimal)
- **CPU**: x86-64 or ARM64
- **Disk**: 10MB for the executable

## Alternative: Fallback Mode

If Fairy-Stockfish installation fails, the code includes a fallback mode using python-chess, but it will be **much slower**:

```python
# Fallback (slow) mode
from src.engine.fairy_stockfish_interface import get_base_moves_fallback

moves = get_base_moves_fallback(fen)  # Uses python-chess
```

This fallback is suitable for development but not for production use due to the massive performance difference.
