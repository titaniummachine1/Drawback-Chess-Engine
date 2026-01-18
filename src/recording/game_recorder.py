"""
Game Recorder for Drawback Chess Engine

Captures raw game data + final drawback reveal for retroactive reconstruction.
Works for both AI vs AI (perfect info) and AI vs Human (hidden info) games.
"""

import json
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class GameMove:
    """Single move in the game."""
    ply: int  # Move number (0, 1, 2, ...)
    player: str  # 'white' or 'black'
    move_uci: str  # UCI notation
    move_san: Optional[str] = None  # Standard notation if available
    timestamp: Optional[float] = None  # When move was made
    time_spent: Optional[float] = None  # Time taken for move


@dataclass
class GameRecord:
    """Complete raw game record before reconstruction."""
    game_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    game_type: str  # 'ai_vs_ai' or 'ai_vs_human'
    opponent_type: str  # 'engine' or 'human'
    engine_version: str
    time_control: str
    
    # Game state
    moves: List[GameMove]
    final_fen: Optional[str] = None
    result: Optional[str] = None  # 'white_win', 'black_win', 'draw', 'aborted'
    
    # Drawback information (may be None during game)
    white_drawback: Optional[str] = None  # May be revealed at end
    black_drawback: Optional[str] = None  # May be revealed at end
    
    # Raw packet data (for debugging)
    reveal_packet: Optional[Dict[str, Any]] = None
    
    # Metadata
    server_info: Optional[Dict[str, Any]] = None
    client_info: Optional[Dict[str, Any]] = None


class GameRecorder:
    """Records games and captures drawback reveal packets."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize recorder with data directory."""
        if data_dir is None:
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data" / "raw_games"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_game: Optional[GameRecord] = None
        self.packet_monitor_active = False
    
    def start_new_game(self, game_type: str = 'ai_vs_human', 
                      opponent_type: str = 'human',
                      engine_version: str = '1.0.0',
                      time_control: str = '10+0') -> str:
        """
        Start recording a new game.
        
        Args:
            game_type: 'ai_vs_ai' or 'ai_vs_human'
            opponent_type: 'engine' or 'human'
            engine_version: Version of our engine
            time_control: Time control format
            
        Returns:
            Game ID for the new game
        """
        game_id = str(uuid.uuid4())
        
        self.current_game = GameRecord(
            game_id=game_id,
            started_at=datetime.utcnow(),
            ended_at=None,
            game_type=game_type,
            opponent_type=opponent_type,
            engine_version=engine_version,
            time_control=time_control,
            moves=[],
            white_drawback=None,
            black_drawback=None,
            reveal_packet=None
        )
        
        print(f"Started recording game {game_id} ({game_type})")
        return game_id
    
    def add_move(self, player: str, move_uci: str, move_san: Optional[str] = None,
                time_spent: Optional[float] = None):
        """Add a move to the current game."""
        if self.current_game is None:
            raise ValueError("No active game recording")
        
        ply = len(self.current_game.moves)
        timestamp = time.time()
        
        game_move = GameMove(
            ply=ply,
            player=player,
            move_uci=move_uci,
            move_san=move_san,
            timestamp=timestamp,
            time_spent=time_spent
        )
        
        self.current_game.moves.append(game_move)
        print(f"Ply {ply}: {player} plays {move_uci}")
    
    def set_initial_drawbacks(self, white_drawback: Optional[str] = None,
                            black_drawback: Optional[str] = None):
        """Set known drawbacks (for AI vs AI games)."""
        if self.current_game is None:
            raise ValueError("No active game recording")
        
        self.current_game.white_drawback = white_drawback
        self.current_game.black_drawback = black_drawback
        
        print(f"Set drawbacks - White: {white_drawback}, Black: {black_drawback}")
    
    def capture_reveal_packet(self, packet_data: Dict[str, Any]):
        """Capture the end-of-game drawback reveal packet."""
        if self.current_game is None:
            raise ValueError("No active game recording")
        
        self.current_game.reveal_packet = packet_data
        
        # Extract drawback information from packet
        # This will need to be adapted based on actual packet format
        drawbacks = self._extract_drawbacks_from_packet(packet_data)
        
        if 'white' in drawbacks:
            self.current_game.white_drawback = drawbacks['white']
        if 'black' in drawbacks:
            self.current_game.black_drawback = drawbacks['black']
        
        print(f"Captured reveal packet: {drawbacks}")
    
    def _extract_drawbacks_from_packet(self, packet: Dict[str, Any]) -> Dict[str, str]:
        """Extract drawback information from reveal packet."""
        drawbacks = {}
        
        # Try different possible packet formats
        if 'players' in packet:
            players = packet['players']
            if 'white' in players and 'drawback' in players['white']:
                drawbacks['white'] = players['white']['drawback']
            if 'black' in players and 'drawback' in players['black']:
                drawbacks['black'] = players['black']['drawback']
        
        elif 'white_drawback' in packet or 'black_drawback' in packet:
            if 'white_drawback' in packet:
                drawbacks['white'] = packet['white_drawback']
            if 'black_drawback' in packet:
                drawbacks['black'] = packet['black_drawback']
        
        elif 'drawbacks' in packet:
            drawback_data = packet['drawbacks']
            if isinstance(drawback_data, dict):
                drawbacks.update(drawback_data)
        
        return drawbacks
    
    def end_game(self, result: str, final_fen: Optional[str] = None):
        """End the current game and save the record."""
        if self.current_game is None:
            raise ValueError("No active game recording")
        
        self.current_game.ended_at = datetime.utcnow()
        self.current_game.result = result
        self.current_game.final_fen = final_fen
        
        # Save the game record
        self._save_game_record()
        
        print(f"Game ended: {result}")
        print(f"Drawbacks - White: {self.current_game.white_drawback}, Black: {self.current_game.black_drawback}")
        
        # Reset for next game
        game_id = self.current_game.game_id
        self.current_game = None
        
        return game_id
    
    def _save_game_record(self):
        """Save the current game record to file."""
        if self.current_game is None:
            return
        
        # Convert to JSON-serializable format
        record_dict = asdict(self.current_game)
        
        # Convert datetime objects to strings
        record_dict['started_at'] = self.current_game.started_at.isoformat()
        if self.current_game.ended_at:
            record_dict['ended_at'] = self.current_game.ended_at.isoformat()
        
        # Save to file
        filename = f"{self.current_game.game_id}.json"
        filepath = self.data_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(record_dict, f, indent=2)
        
        print(f"Saved game record to {filepath}")
    
    def load_game_record(self, game_id: str) -> Optional[GameRecord]:
        """Load a game record from file."""
        filepath = self.data_dir / f"{game_id}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r') as f:
            record_dict = json.load(f)
        
        # Convert back to GameRecord object
        record_dict['started_at'] = datetime.fromisoformat(record_dict['started_at'])
        if record_dict.get('ended_at'):
            record_dict['ended_at'] = datetime.fromisoformat(record_dict['ended_at'])
        
        # Convert moves back to GameMove objects
        moves_data = record_dict.pop('moves')
        game_record = GameRecord(**record_dict)
        game_record.moves = [GameMove(**move) for move in moves_data]
        
        return game_record
    
    def list_recorded_games(self) -> List[str]:
        """List all recorded game IDs."""
        game_files = list(self.data_dir.glob("*.json"))
        return [f.stem for f in game_files]
    
    def get_games_by_type(self, game_type: str) -> List[GameRecord]:
        """Get all games of a specific type."""
        games = []
        
        for game_id in self.list_recorded_games():
            record = self.load_game_record(game_id)
            if record and record.game_type == game_type:
                games.append(record)
        
        return games
    
    def get_games_with_revealed_drawbacks(self) -> List[GameRecord]:
        """Get games where drawbacks were revealed."""
        games = []
        
        for game_id in self.list_recorded_games():
            record = self.load_game_record(game_id)
            if record and (record.white_drawback or record.black_drawback):
                games.append(record)
        
        return games
    
    def export_for_reconstruction(self, output_file: str):
        """Export all games with revealed drawbacks for reconstruction."""
        games = self.get_games_with_revealed_drawbacks()
        
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_games": len(games),
            "games": []
        }
        
        for game in games:
            game_dict = asdict(game)
            game_dict['started_at'] = game.started_at.isoformat()
            if game.ended_at:
                game_dict['ended_at'] = game.ended_at.isoformat()
            
            export_data["games"].append(game_dict)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Exported {len(games)} games for reconstruction to {output_file}")


# Global recorder instance
_recorder: Optional[GameRecorder] = None


def get_recorder() -> GameRecorder:
    """Get the global game recorder instance."""
    global _recorder
    if _recorder is None:
        _recorder = GameRecorder()
    return _recorder


# Example usage functions
def start_ai_vs_human_game():
    """Start a new AI vs Human game recording."""
    recorder = get_recorder()
    return recorder.start_new_game(
        game_type='ai_vs_human',
        opponent_type='human'
    )


def start_ai_vs_ai_game(white_drawback: str, black_drawback: str):
    """Start a new AI vs AI game recording."""
    recorder = get_recorder()
    game_id = recorder.start_new_game(
        game_type='ai_vs_ai',
        opponent_type='engine'
    )
    recorder.set_initial_drawbacks(white_drawback, black_drawback)
    return game_id


def record_move(player: str, move_uci: str):
    """Record a move in the current game."""
    recorder = get_recorder()
    recorder.add_move(player, move_uci)


def capture_game_end_packet(packet_data: Dict[str, Any], result: str):
    """Capture the game end packet and finalize recording."""
    recorder = get_recorder()
    recorder.capture_reveal_packet(packet_data)
    return recorder.end_game(result)
