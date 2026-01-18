# Installation Scripts for Fairy-Stockfish

Choose the appropriate script for your platform and run it from the command line.

## Windows (PowerShell)

```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\install_fairy_stockfish.ps1
```

## Linux/macOS

### Option 1: Download Pre-compiled Binary (Recommended)

```bash
# Make executable and run
chmod +x scripts/install_fairy_stockfish.sh
./scripts/install_fairy_stockfish.sh
```

### Option 2: Compile from Source

```bash
# Make executable and run
chmod +x scripts/compile_fairy_stockfish.sh
./scripts/compile_fairy_stockfish.sh
```

## Quick Test

After installation, test it works:

```bash
# Test from command line
fairy-stockfish --version

# Or test with Python
python examples/subtractive_mask_demo.py
```

## Manual Installation (if scripts fail)

### Windows

1. Go to https://github.com/fairy-stockfish/Fairy-Stockfish/releases
2. Download `fairy-stockfish-x86_64.exe`
3. Place it in `C:\fairy-stockfish\`
4. Add to PATH or use full path

### Linux/macOS

```bash
# Download latest binary
wget https://github.com/fairy-stockfish/Fairy-Stockfish/releases/latest/download/fairy-stockfish-x86_64
chmod +x fairy-stockfish-x86_64
sudo mv fairy-stockfish-x86_64 /usr/local/bin/fairy-stockfish
```

## Troubleshooting

### Permission Denied (Linux/macOS)

```bash
chmod +x scripts/*.sh
```

### PowerShell Execution Policy (Windows)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Network Issues

If downloads fail, download manually from GitHub releases and place the binary in your desired location.

### Compilation Issues

Make sure you have build tools installed:

```bash
# Ubuntu/Debian
sudo apt-get install build-essential g++ make git

# macOS (with Homebrew)
brew install gcc make git

# Windows
# Install Visual Studio Build Tools or MinGW
```

## Verification

After installation, verify it works with the Drawback Chess Engine:

```python
from src.engine.fairy_stockfish_interface import test_fairy_interface
test_fairy_interface()
```

You should see performance statistics showing thousands of queries per second.
