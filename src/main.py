#!/usr/bin/env python3
"""
Drawback Chess Engine - Main Entry Point

MCTS-based chess engine using machine learning for move probability prediction.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.engine.chess_engine import ChessEngine
from src.ml.model_manager import ModelManager


def main():
    """Main entry point for the Drawback Chess Engine."""
    print("Drawback Chess Engine Starting...")
    
    # Initialize components
    model_manager = ModelManager()
    engine = ChessEngine(model_manager)
    
    # Start the engine
    engine.run()


if __name__ == "__main__":
    main()
