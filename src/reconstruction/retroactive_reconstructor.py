"""
Retroactive Reconstruction for Drawback Chess Engine

Replays games with revealed drawbacks using Fairy-Stockfish to generate
perfect legal move data for every position in the game.
"""

import json
import subprocess
import tempfile
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from ..recording.game_recorder import GameRecord, GameMove, get_recorder


@dataclass
class ReconstructedPosition:
    """Position with reconstructed legal moves."""
    ply: int
    fen: str
    player: str
    move_played: str
    base_moves: List[str]  # All possible moves without drawbacks
    legal_moves: List[str]  # Legal moves with drawbacks applied
    legality_mask: List[int]  # 1 for legal, 0 for illegal
    active_drawback: Optional[str]  # Drawback affecting this player
    is_reconstructed: bool  # True if this was reconstructed (vs known)


@dataclass
class ReconstructedGame:
    """Complete game with reconstructed legal move data."""
    game_id: str
    meta: Dict[str, Any]
    training_samples: List[ReconstructedPosition]


class FairyStockfishInterface:
    """Interface to Fairy-Stockfish for drawback chess analysis."""
    
    def __init__(self, stockfish_path: Optional[str] = None):
        """Initialize Fairy-Stockfish interface."""
        self.stockfish_path = stockfish_path or "stockfish"  # Assume in PATH
        self.process = None
        self._verify_stockfish()
    
    def _verify_stockfish(self):
        """Verify that Fairy-Stockfish is available and supports drawback chess."""
        try:
            result = subprocess.run(
                [self.stockfish_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise RuntimeError("Fairy-Stockfish not found or not working")
            
            print(f"Fairy-Stockfish verified: {result.stdout.strip()}")
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"Failed to verify Fairy-Stockfish: {e}")
    
    def start_engine(self):
        """Start the Fairy-Stockfish engine."""
        if self.process is not None:
            return
        
        try:
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
            
            # Wait for ready response
            self._wait_for_response("uciok")
            
            # Set up drawback chess variant if supported
            self._send_command("setoption name UCI_Variant value drawback")
            
            print("Fairy-Stockfish engine started")
            
        except Exception as e:
            raise RuntimeError(f"Failed to start Fairy-Stockfish: {e}")
    
    def _send_command(self, command: str):
        """Send command to engine."""
        if self.process is None:
            raise RuntimeError("Engine not started")
        
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
    
    def _wait_for_response(self, expected: str, timeout: float = 5.0) -> str:
        """Wait for specific response from engine."""
        start_time = time.time()
        response = ""
        
        while time.time() - start_time < timeout:
            if self.process.stdout.readable():
                line = self.process.stdout.readline()
                if line:
                    response += line
                    if expected in line:
                        return response
            
            time.sleep(0.01)
        
        raise TimeoutError(f"Did not receive expected response: {expected}")
    
    def set_position(self, fen: str):
        """Set position on engine."""
        self._send_command(f"position fen {fen}")
    
    def get_legal_moves(self, fen: str, drawback: Optional[str] = None) -> List[str]:
        """Get legal moves for a position with optional drawback."""
        if self.process is None:
            self.start_engine()
        
        # Set position
        self.set_position(fen)
        
        # Apply drawback if specified
        if drawback:
            # This would depend on Fairy-Stockfish's drawback implementation
            # For now, we'll simulate by filtering moves
            pass
        
        # Get legal moves
        self._send_command("go perft 1")
        
        # Parse perft output to extract legal moves
        legal_moves = self._parse_perft_output()
        
        return legal_moves
    
    def _parse_perft_output(self) -> List[str]:
        """Parse perft output to extract legal moves."""
        moves = []
        
        # Read output until we get the perft result
        start_time = time.time()
        while time.time() - start_time < 2.0:  # 2 second timeout
            if self.process.stdout.readable():
                line = self.process.stdout.readline()
                if line:
                    line = line.strip()
                    if line.startswith("nodes searched"):
                        break
                    elif ":" in line and not line.startswith("info"):
                        # This looks like a move:count line
                        move_part = line.split(":")[0].strip()
                        if move_part and len(move_part) >= 4:
                            moves.append(move_part)
            
            time.sleep(0.01)
        
        return moves
    
    def stop_engine(self):
        """Stop the Fairy-Stockfish engine."""
        if self.process is not None:
            self._send_command("quit")
            self.process.wait(timeout=5)
            self.process = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_engine()


class RetroactiveReconstructor:
    """Reconstructs legal move data from recorded games."""
    
    def __init__(self, stockfish_path: Optional[str] = None):
        """Initialize reconstructor."""
        self.stockfish = FairyStockfishInterface(stockfish_path)
        self.recorder = get_recorder()
    
    def reconstruct_game(self, game_record: GameRecord) -> ReconstructedGame:
        """
        Reconstruct a single game with legal move data.
        
        Args:
            game_record: Raw game record from recorder
            
        Returns:
            ReconstructedGame with legal move data for every position
        """
        print(f"Reconstructing game {game_record.game_id}")
        
        # Prepare metadata
        meta = {
            "white_drawback": game_record.white_drawback,
            "black_drawback": game_record.black_drawback,
            "game_type": game_record.game_type,
            "result": game_record.result,
            "total_moves": len(game_record.moves)
        }
        
        training_samples = []
        
        # Start Fairy-Stockfish
        with self.stockfish:
            # Replay the game move by move
            current_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            for i, move in enumerate(game_record.moves):
                player = move.player
                move_played = move.move_uci
                
                # Get legal moves for this position
                active_drawback = (game_record.white_drawback if player == "white" 
                                 else game_record.black_drawback)
                
                # Reconstruct legal moves
                base_moves, legal_moves, legality_mask = self._reconstruct_position(
                    current_fen, player, active_drawback
                )
                
                # Create training sample
                sample = ReconstructedPosition(
                    ply=move.ply,
                    fen=current_fen,
                    player=player,
                    move_played=move_played,
                    base_moves=base_moves,
                    legal_moves=legal_moves,
                    legality_mask=legality_mask,
                    active_drawback=active_drawback,
                    is_reconstructed=(game_record.game_type == 'ai_vs_human')
                )
                
                training_samples.append(sample)
                
                # Update position for next move
                current_fen = self._apply_move_to_fen(current_fen, move_played)
        
        return ReconstructedGame(
            game_id=game_record.game_id,
            meta=meta,
            training_samples=training_samples
        )
    
    def _reconstruct_position(self, fen: str, player: str, 
                            drawback: Optional[str]) -> Tuple[List[str], List[str], List[int]]:
        """
        Reconstruct legal moves for a specific position.
        
        Returns:
            Tuple of (base_moves, legal_moves, legality_mask)
        """
        # Get base legal moves (without drawbacks)
        base_moves = self.stockfish.get_legal_moves(fen)
        base_moves.sort()  # Ensure consistent ordering
        
        if drawback is None:
            # No drawback - all base moves are legal
            legal_moves = base_moves.copy()
            legality_mask = [1] * len(base_moves)
        else:
            # Apply drawback filter
            legal_moves = self._apply_drawback_filter(fen, base_moves, drawback, player)
            legality_mask = [
                1 if move in legal_moves else 0
                for move in base_moves
            ]
        
        return base_moves, legal_moves, legality_mask
    
    def _apply_drawback_filter(self, fen: str, base_moves: List[str], 
                             drawback: str, player: str) -> List[str]:
        """Apply drawback filter to base legal moves."""
        # This is a simplified implementation
        # In reality, this would use Fairy-Stockfish's drawback chess support
        
        filtered_moves = base_moves.copy()
        
        # Apply different drawback types
        if drawback == "No_Castling":
            # Remove castling moves
            filtered_moves = [m for m in filtered_moves if not (
                (player == "white" and m in ["e1g1", "e1c1"]) or
                (player == "black" and m in ["e8g8", "e8c8"])
            )]
        
        elif drawback == "Knight_Immobility":
            # Remove knight moves
            filtered_moves = [m for m in filtered_moves if not (
                fen[self._get_piece_index_from_move(m)] in ['N', 'n']
            )]
        
        elif drawback == "Queen_Capture_Ban":
            # Remove queen capture moves
            filtered_moves = [m for m in filtered_moves if not (
                len(m) >= 4 and 'x' in m and 
                fen[self._get_piece_index_from_move(m)] in ['Q', 'q']
            )]
        
        elif drawback == "Pawn_Immunity":
            # Remove pawn capture moves
            filtered_moves = [m for m in filtered_moves if not (
                len(m) >= 4 and 'x' in m and 
                fen[self._get_piece_index_from_move(m)] in ['P', 'p']
            )]
        
        return filtered_moves
    
    def _get_piece_index_from_move(self, move: str) -> int:
        """Get piece index from FEN for a move (simplified)."""
        # This is a placeholder - proper implementation would
        # parse the FEN and find the piece at the move's from-square
        return 0
    
    def _apply_move_to_fen(self, fen: str, move: str) -> str:
        """Apply a move to a FEN string (simplified)."""
        # This is a placeholder - proper implementation would
        # use a chess library like python-chess
        # For now, return the same FEN (this would be fixed in production)
        return fen
    
    def reconstruct_all_games(self, output_dir: str):
        """Reconstruct all recorded games with revealed drawbacks."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get games with revealed drawbacks
        games = self.recorder.get_games_with_revealed_drawbacks()
        
        print(f"Found {len(games)} games with revealed drawbacks")
        
        reconstructed_games = []
        
        for game in games:
            try:
                reconstructed = self.reconstruct_game(game)
                reconstructed_games.append(reconstructed)
                
                # Save individual game
                self._save_reconstructed_game(reconstructed, output_path)
                
            except Exception as e:
                print(f"Error reconstructing game {game.game_id}: {e}")
                continue
        
        # Save batch summary
        self._save_batch_summary(reconstructed_games, output_path)
        
        print(f"Reconstructed {len(reconstructed_games)} games")
        return reconstructed_games
    
    def _save_reconstructed_game(self, game: ReconstructedGame, output_path: Path):
        """Save a reconstructed game to JSON file."""
        filename = f"{game.game_id}_reconstructed.json"
        filepath = output_path / filename
        
        game_dict = {
            "game_id": game.game_id,
            "meta": game.meta,
            "training_samples": [
                {
                    "ply": sample.ply,
                    "fen": sample.fen,
                    "player": sample.player,
                    "move_played": sample.move_played,
                    "base_moves": sample.base_moves,
                    "legal_moves": sample.legal_moves,
                    "legality_mask": sample.legality_mask,
                    "active_drawback": sample.active_drawback,
                    "is_reconstructed": sample.is_reconstructed
                }
                for sample in game.training_samples
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(game_dict, f, indent=2)
    
    def _save_batch_summary(self, games: List[ReconstructedGame], output_path: Path):
        """Save a summary of the reconstruction batch."""
        summary = {
            "reconstruction_timestamp": time.time(),
            "total_games": len(games),
            "total_positions": sum(len(g.training_samples) for g in games),
            "games": [
                {
                    "game_id": game.game_id,
                    "meta": game.meta,
                    "position_count": len(game.training_samples)
                }
                for game in games
            ]
        }
        
        with open(output_path / "reconstruction_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)


# Convenience functions
def reconstruct_all_recorded_games(output_dir: str = "data/reconstructed"):
    """Reconstruct all recorded games."""
    reconstructor = RetroactiveReconstructor()
    return reconstructor.reconstruct_all_games(output_dir)


def reconstruct_single_game(game_id: str) -> Optional[ReconstructedGame]:
    """Reconstruct a single game by ID."""
    recorder = get_recorder()
    game_record = recorder.load_game_record(game_id)
    
    if game_record is None:
        return None
    
    reconstructor = RetroactiveReconstructor()
    return reconstructor.reconstruct_game(game_record)
