"""
Embedded engine path detection for Drawback Chess Engine
"""

import platform
from pathlib import Path


def get_embedded_engine_path() -> str:
    """Get the path to the embedded Fairy-Stockfish engine."""
    
    # Try different possible locations
    possible_paths = []
    
    if platform.system() == "Windows":
        possible_paths = [
            Path("c:/GitHubProjekty/engines/stockfish.exe"),  # Where it was downloaded
            Path(__file__).parent.parent.parent / "engines" / "stockfish.exe",  # Project relative
            Path("engines/stockfish.exe"),  # Relative to current working directory
        ]
    else:
        possible_paths = [
            Path("/usr/local/bin/fairy-stockfish"),  # Common installation
            Path(__file__).parent.parent.parent / "engines" / "stockfish",  # Project relative
            Path("engines/stockfish"),  # Relative to current working directory
        ]
    
    for path in possible_paths:
        if path.exists():
            print(f"Found embedded Fairy-Stockfish: {path}")
            return str(path)
    
    # If not found, return default (will trigger fallback)
    print("Embedded Fairy-Stockfish not found, will use fallback")
    return "stockfish"


def test_embedded_engine():
    """Test if the embedded engine works."""
    engine_path = get_embedded_engine_path()
    
    if engine_path != "stockfish":
        try:
            import subprocess
            result = subprocess.run([engine_path], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 or "Fairy-Stockfish" in result.stderr:
                print("✅ Embedded engine test passed!")
                return True
        except Exception as e:
            print(f"❌ Embedded engine test failed: {e}")
    
    return False


if __name__ == "__main__":
    test_embedded_engine()
