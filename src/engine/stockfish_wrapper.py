"""
Persistent wrapper for Fairy-Stockfish engine.
Handles process management and communication via pipes to avoid startup overhead.
"""

import subprocess
import time
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class StockfishWrapper:
    def __init__(self, engine_path: str):
        self.engine_path = engine_path
        self.process = None
        self._start_engine()

    def _start_engine(self):
        """Start the engine process with pipes."""
        try:
            self.process = subprocess.Popen(
                self.engine_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            # Initialize UCI
            self._send_command("uci")
            self._read_until("uciok")
            logger.info(f"Fairy-Stockfish started: {self.engine_path}")
        except FileNotFoundError:
            logger.error(f"Engine not found at {self.engine_path}")
            raise

    def _send_command(self, command: str):
        """Send a command to the engine."""
        if not self.process:
            return
        logger.debug(f">> {command}")
        self.process.stdin.write(f"{command}\n")
        self.process.stdin.flush()

    def _read_until(self, target: str, timeout: float = 2.0) -> List[str]:
        """Read output until a target string is found."""
        lines = []
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout waiting for '{target}'")
                break

            line = self.process.stdout.readline().strip()
            if not line:
                continue

            lines.append(line)
            # logger.debug(f"<< {line}")

            if target in line:
                break
        return lines

    def get_physical_moves(self, fen: str) -> List[str]:
        """
        Get all physically possible moves (pseudo-legal + illegal allowed by physics).
        For Fairy-Stockfish, standard 'go perft 1' gives us the move list efficiently.
        """
        self._send_command(f"position fen {fen}")
        self._send_command("go perft 1")

        lines = self._read_until("Nodes searched")

        moves = []
        for line in lines:
            # Output format: "e2e4: 1"
            if ": 1" in line and not line.startswith("Nodes"):
                parts = line.split(":")
                if len(parts) > 0:
                    moves.append(parts[0].strip())
        return moves

    def get_eval(self, fen: str) -> int:
        """Get static evaluation of the position in centipawns."""
        self._send_command(f"position fen {fen}")
        self._send_command("eval")

        lines = self._read_until("Final evaluation")

        # Parse 'Final evaluation: 0.35 (white side)' or similar
        for line in lines:
            if "Final evaluation" in line:
                try:
                    # Very rough parsing, depends on exact engine output format
                    # Example: "Final evaluation: +0.25"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "evaluation:":
                            val_str = parts[i+1]
                            return int(float(val_str) * 100)
                except:
                    return 0
        return 0

    def close(self):
        """Terminate the engine process."""
        if self.process:
            self._send_command("quit")
            self.process.terminate()
            self.process = None
