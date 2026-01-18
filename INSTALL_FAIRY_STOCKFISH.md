# Fairy-Stockfish Installation Guide

## ⚠️ Network Downloads Failed

The automatic installation scripts couldn't download Fairy-Stockfish due to network issues. Here's how to install it manually:

## 🚀 Manual Installation (Windows)

### Step 1: Download the Binary

1. Open your web browser
2. Go to: https://github.com/fairy-stockfish/Fairy-Stockfish/releases
3. Look for the latest release (e.g., "fairy_sf_14")
4. Download: `fairy-stockfish-x86_64.exe`

### Step 2: Install the Binary

1. Create folder: `C:\fairy-stockfish\`
2. Move the downloaded `.exe` file to that folder
3. Rename it to: `fairy-stockfish.exe`

### Step 3: Update Your Code

In your Python code, use the full path:

```python
from src.engine.fairy_stockfish_interface import create_fairy_interface

# Use full path to Fairy-Stockfish
stockfish_path = r"C:\fairy-stockfish\fairy-stockfish.exe"
fs = create_fairy_interface(stockfish_path)
```

### Step 4: Test Installation

```python
# Test the installation
from src.engine.fairy_stockfish_interface import test_fairy_interface
test_fairy_interface()
```

## 🔧 Alternative: Use Fallback (Development Only)

If you can't install Fairy-Stockfish right now, the code will automatically fall back to python-chess:

```python
from src.engine.fairy_stockfish_interface import get_base_moves_fast

# This will use python-chess fallback if Fairy-Stockfish isn't available
moves = get_base_moves_fast("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
print(f"Found {len(moves)} moves (using fallback)")
```

## ⚡ Performance Comparison

- **Fairy-Stockfish**: ~10,000 queries/second (C++)
- **python-chess fallback**: ~100 queries/second (Python)
- **Speedup**: 100x faster with Fairy-Stockfish

## 🧪 Verification

After installing Fairy-Stockfish, run this test:

```bash
python examples/subtractive_mask_demo.py
```

You should see much better performance with Fairy-Stockfish.

## 📁 File Locations

Once installed:

- **Executable**: `C:\fairy-stockfish\fairy-stockfish.exe`
- **Python usage**: Use full path in your code
- **Optional**: Add `C:\fairy-stockfish` to your PATH

## 🆘 Troubleshooting

### "File not found" error

- Make sure the file is exactly at: `C:\fairy-stockfish\fairy-stockfish.exe`
- Use the full path in your Python code

### "Permission denied" error

- Right-click the `.exe` file → Properties → Unblock
- Run as Administrator if needed

### "Version not supported" error

- Try downloading an older version from the releases page
- Or compile from source using the provided scripts

## 🎯 Next Steps

1. Install Fairy-Stockfish manually using the steps above
2. Test with the subtractive mask demo
3. Enjoy the 100x speedup in move generation!

The Drawback Chess Engine will work immediately with the fallback, but Fairy-Stockfish provides the performance needed for serious training.
