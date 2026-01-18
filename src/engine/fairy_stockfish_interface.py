"""
Fairy-Stockfish Interface for Drawback Chess Engine

Optimized interface using perft 1 command for ultra-fast move generation.
This is the heart of the move-selection logic.
"""

import subprocess
import time
import platform
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .embedded_path import get_embedded_engine_path
from .drawback_bridge import DrawbackBridge


@dataclass
class MoveGenerationResult:
    """Result from Fairy-Stockfish move generation."""
    base_moves: List[str]  # All pseudo-legal moves from perft 1
    position_fen: str
    player_to_move: str
    generation_time_ms: float


class FairyStockfishInterface:
    """High-performance interface to Fairy-Stockfish for Drawback Chess."""
    
    def __init__(self, stockfish_path: str = "stockfish", variant: str = "drawback"):
        """Initialize Fairy-Stockfish interface.
        
        Args:
            stockfish_path: Path to Fairy-Stockfish executable
            variant: Chess variant to use (default: drawback)
        """
        self.stockfish_path = stockfish_path
        self.variant = variant
        self.process = None
        self.is_initialized = False
        
        # Initialize Drawback bridge for special rules
        self.drawback_bridge = DrawbackBridge()
        
        # Performance tracking
        self.total_queries = 0
        self.total_time_ms = 0
    
    def start_engine(self):
        """Start Fairy-Stockfish engine with optimal settings."""
        if self.process is not None:
            return
        
        try:
            # Start Fairy-Stockfish with optimized settings
            self.process = subprocess.Popen(
                [self.stockfish_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Initialize UCI mode
            self._send_command("uci")
            self._wait_for_response("uciok", timeout=5.0)
            
            # Set variant to drawback chess
            self._send_command(f"setoption name UCI_Variant value {self.variant}")
            
            # Optimize for speed (disable hash tables, etc.)
            self._send_command("setoption name Hash value 1")  # Minimal hash
            self._send_command("setoption name Threads value 1")  # Single thread
            self._send_command("setoption name Ponder value false")  # No pondering
            
            # Set ready
            self._send_command("isready")
            self._wait_for_response("readyok", timeout=5.0)
            
            self.is_initialized = True
            print(f"Fairy-Stockfish initialized for {self.variant} variant")
            
        except Exception as e:
            raise RuntimeError(f"Failed to start Fairy-Stockfish: {e}")
    
    def get_base_moves(self, fen: str, previous_move: Optional[str] = None) -> MoveGenerationResult:
        """
        Get base moves using perft 1 command - the core of the pipeline.
        
        Args:
            fen: FEN string of the position (empty string or None for default)
            previous_move: The move just played (for king capture en passant context)
            
        Returns:
            MoveGenerationResult with base moves including Drawback Chess rules
        """
        if self.process is None:
            self.start_engine()
        
        start_time = time.time()
        
        # Set position (use Fairy-Stockfish built-in default if fen is empty or None)
        if fen and fen.strip():
            self._send_command(f"position fen {fen.strip()}")
            actual_fen = fen.strip()
        else:
            # Use Fairy-Stockfish built-in default starting position
            self._send_command("position startpos")
            actual_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # Standard starting position
        
        # Get base moves using perft 1
        base_moves = self._execute_perft_1()
        
        # Apply Drawback Chess-specific rules via the bridge
        enhanced_moves = self.drawback_bridge.apply_drawback_rules(base_moves, actual_fen, previous_move)
        
        # Extract player from FEN
        player = self._extract_player_from_fen(actual_fen)
        
        # Track performance
        generation_time = (time.time() - start_time) * 1000
        self.total_queries += 1
        self.total_time_ms += generation_time
        
        return MoveGenerationResult(
            base_moves=enhanced_moves,
            position_fen=actual_fen,
            player_to_move=player,
            generation_time_ms=generation_time
        )
    
    def get_current_fen(self) -> str:
        """Get the current FEN from the engine."""
        self._send_command("d")  # 'd' command in stockfish displays board + FEN
        response = self._wait_for_response("Fen:", timeout=2.0)
        for line in response.split('\n'):
            if line.startswith("Fen:"):
                return line.replace("Fen:", "").strip()
        return ""

    def make_moves(self, start_fen: str, moves: List[str]) -> str:
        """Apply a sequence of moves to a FEN and return the resulting FEN."""
        if not moves:
            return start_fen
            
        cmd = f"position fen {start_fen} moves {' '.join(moves)}"
        self._send_command(cmd)
        return self.get_current_fen()
    
    def _execute_perft_1(self) -> List[str]:
        """Execute perft 1 and parse moves - the heart of the system."""
        # Clear any pending output
        self._clear_output_buffer()
        
        # Send perft 1 command
        self._send_command("perft 1")
        
        # Parse the output
        moves = self._parse_perft_output()
        
        return moves
    
    def _parse_perft_output(self) -> List[str]:
        """Parse perft output with robust error handling."""
        moves = []
        output_lines = []
        
        # Collect all output until we get the result
        start_time = time.time()
        while time.time() - start_time < 2.0:  # 2 second timeout
            if self.process and self.process.stdout.readable():
                try:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    
                    line = line.strip()
                    output_lines.append(line)
                    
                    # Stop when we see the final result
                    if line.startswith("nodes searched"):
                        break
                
                except Exception:
                    continue
            
            time.sleep(0.001)  # Minimal delay
        
        # Parse moves from collected output
        for line in output_lines:
            move = self._extract_move_from_line(line)
            if move and self._is_valid_uci_move(move):
                moves.append(move)
        
        # Remove duplicates and sort for consistency
        moves = sorted(list(set(moves)))
        return moves
    
    def _extract_move_from_line(self, line: str) -> Optional[str]:
        """Extract move from a perft output line."""
        # Skip non-move lines
        if (line.startswith("info") or 
            line.startswith("Nodes") or 
            line.startswith("nodes searched") or
            not line or ":" not in line):
            return None
        
        # Parse move:count format
        parts = line.split(":")
        if len(parts) >= 2:
            move_part = parts[0].strip()
            # Remove any leading/trailing whitespace
            move_part = move_part.strip()
            
            # Validate move format
            if self._is_valid_uci_move(move_part):
                return move_part
        
        return None
    
    def _is_valid_uci_move(self, move: str) -> bool:
        """Validate UCI move format with strict checking."""
        if len(move) < 4 or len(move) > 6:
            return False
        
        # Basic UCI format validation
        if len(move) >= 4:
            # Source square (file + rank)
            if not (move[0] in 'abcdefgh' and move[1] in '12345678'):
                return False
            # Destination square (file + rank)
            if not (move[2] in 'abcdefgh' and move[3] in '12345678'):
                return False
            # Optional promotion
            if len(move) == 5:
                if move[4] not in 'nbrq':
                    return False
            elif len(move) == 6:
                # Handle cases like "e7e8q" (some engines output this)
                if move[4] not in 'nbrq' or move[5] not in 'nbrq':
                    return False
        
        return True
    
    def _extract_player_from_fen(self, fen: str) -> str:
        """Extract current player from FEN."""
        try:
            fen_parts = fen.split()
            return "white" if fen_parts[1] == 'w' else "black"
        except (IndexError, ValueError):
            return "white"
    
    def _send_command(self, command: str):
        """Send command to Fairy-Stockfish."""
        if self.process is None:
            raise RuntimeError("Engine not started")
        
        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        except Exception as e:
            raise RuntimeError(f"Failed to send command '{command}': {e}")
    
    def _wait_for_response(self, expected: str, timeout: float = 5.0) -> str:
        """Wait for specific response from engine."""
        start_time = time.time()
        response = ""
        
        while time.time() - start_time < timeout:
            if self.process and self.process.stdout.readable():
                try:
                    line = self.process.stdout.readline()
                    if not line:
                        continue
                    
                    response += line
                    if expected in line:
                        return response
                
                except Exception:
                    continue
            
            time.sleep(0.001)
        
        raise TimeoutError(f"Did not receive expected response: {expected}")
    
    def _clear_output_buffer(self):
        """Clear any pending output from engine."""
        if self.process and self.process.stdout.readable():
            try:
                # Read and discard pending output
                while True:
                    line = self.process.stdout.readline(timeout=0.01)
                    if not line:
                        break
            except:
                pass
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        avg_time = self.total_time_ms / self.total_queries if self.total_queries > 0 else 0
        queries_per_second = 1000 / avg_time if avg_time > 0 else 0
        
        return {
            "total_queries": self.total_queries,
            "total_time_ms": self.total_time_ms,
            "avg_time_ms": avg_time,
            "queries_per_second": queries_per_second
        }
    
    def stop_engine(self):
        """Stop Fairy-Stockfish engine."""
        if self.process is not None:
            try:
                self._send_command("quit")
                self.process.wait(timeout=3)
            except:
                self.process.terminate()
                self.process.wait(timeout=1)
            
            self.process = None
            self.is_initialized = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_engine()


# Convenience functions for the pipeline
def create_fairy_interface(stockfish_path: str = None) -> FairyStockfishInterface:
    """Create a new Fairy-Stockfish interface."""
    if stockfish_path is None:
        # Use the embedded engine path detection
        stockfish_path = get_embedded_engine_path()
    
    return FairyStockfishInterface(stockfish_path)


def get_base_moves_fast(fen: str, stockfish_path: str = None, previous_move: Optional[str] = None) -> List[str]:
    """
    Fast function to get base moves - core of the subtractive mask pipeline.
    
    Falls back to python-chess if Fairy-Stockfish is not available.
    
    Args:
        fen: FEN string of the position
        stockfish_path: Path to Fairy-Stockfish executable (optional)
        previous_move: The move just played (for king capture en passant)
        
    Returns:
        List of legal moves including Drawback Chess rules
    """
    try:
        if stockfish_path is None:
            # Use the embedded engine path detection
            stockfish_path = get_embedded_engine_path()
        
        with create_fairy_interface(stockfish_path) as fs:
            result = fs.get_base_moves(fen, previous_move)
            return result.base_moves
    except Exception as e:
        print(f"Fairy-Stockfish not available ({e}), using fallback")
        from .fallback_interface import get_base_moves_fallback
        return get_base_moves_fallback(fen)


# Example usage and testing
def test_fairy_interface():
    """Test the Fairy-Stockfish interface."""
    print("=== Testing Fairy-Stockfish Interface ===")
    
    # Test position
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    try:
        with create_fairy_interface() as fs:
            # Test move generation
            result = fs.get_base_moves(fen)
            
            print(f"Position: {fen}")
            print(f"Player: {result.player_to_move}")
            print(f"Base moves ({len(result.base_moves)}): {result.base_moves[:10]}...")
            print(f"Generation time: {result.generation_time_ms:.2f}ms")
            
            # Test performance
            stats = fs.get_performance_stats()
            print(f"Performance: {stats['queries_per_second']:.1f} queries/second")
            
            return result.base_moves
    
    except Exception as e:
        print(f"Error testing Fairy-Stockfish: {e}")
        return []


if __name__ == "__main__":
    test_fairy_interface()
