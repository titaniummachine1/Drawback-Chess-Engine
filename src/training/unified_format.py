"""
Unified Training Data Format for Drawback Chess Engine

Creates the unified JSONL format that works for both AI vs AI (perfect info)
and AI vs Human (hidden info) training scenarios.
"""

import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from ..reconstruction.retroactive_reconstructor import ReconstructedGame, ReconstructedPosition


@dataclass
class UnifiedTrainingSample:
    """Single training sample in unified format."""
    ply: int
    fen: str
    player: str
    move_played: str
    base_moves: List[str]
    legality_mask: List[int]  # TARGET 1: Physics Engine (0=Illegal, 1=Legal)
    active_drawback_id: Optional[int]  # TARGET 2: Detective (drawback ID)
    game_result: str  # For value head training
    is_reconstructed: bool  # Track data source


@dataclass
class UnifiedGame:
    """Complete game in unified training format."""
    game_id: str
    meta: Dict[str, Any]
    training_samples: List[UnifiedTrainingSample]


class DrawbackRegistry:
    """Registry for mapping drawback names to IDs and back."""
    
    def __init__(self):
        # Predefined drawback types
        self.drawback_types = {
            "none": 0,
            "No_Castling": 1,
            "Knight_Immobility": 2,
            "Queen_Capture_Ban": 3,
            "Pawn_Immunity": 4,
            "Bishop_Movement_Limit": 5,
            "Rook_Restriction": 6,
            "King_Mobility_Limit": 7,
            "En_Passant_Forbidden": 8,
            "Promotion_Blocked": 9
        }
        
        # Reverse mapping
        self.id_to_drawback = {v: k for k, v in self.drawback_types.items()}
    
    def get_id(self, drawback_name: Optional[str]) -> Optional[int]:
        """Get drawback ID from name."""
        if drawback_name is None:
            return 0  # "none"
        return self.drawback_types.get(drawback_name, 0)
    
    def get_name(self, drawback_id: int) -> str:
        """Get drawback name from ID."""
        return self.id_to_drawback.get(drawback_id, "none")
    
    def register_drawback(self, drawback_name: str) -> int:
        """Register a new drawback type."""
        if drawback_name not in self.drawback_types:
            new_id = max(self.drawback_types.values()) + 1
            self.drawback_types[drawback_name] = new_id
            self.id_to_drawback[new_id] = drawback_name
            return new_id
        return self.drawback_types[drawback_name]
    
    def get_all_drawbacks(self) -> Dict[str, int]:
        """Get all drawback mappings."""
        return self.drawback_types.copy()


class UnifiedFormatConverter:
    """Converts reconstructed games to unified training format."""
    
    def __init__(self):
        self.drawback_registry = DrawbackRegistry()
    
    def convert_game(self, reconstructed_game: ReconstructedGame) -> UnifiedGame:
        """Convert a reconstructed game to unified format."""
        training_samples = []
        
        for sample in reconstructed_game.training_samples:
            unified_sample = self._convert_position(sample, reconstructed_game.meta)
            training_samples.append(unified_sample)
        
        return UnifiedGame(
            game_id=reconstructed_game.game_id,
            meta=reconstructed_game.meta,
            training_samples=training_samples
        )
    
    def _convert_position(self, position: ReconstructedPosition, 
                          game_meta: Dict[str, Any]) -> UnifiedTrainingSample:
        """Convert a single position to unified format."""
        # Convert drawback name to ID
        drawback_id = self.drawback_registry.get_id(position.active_drawback)
        
        return UnifiedTrainingSample(
            ply=position.ply,
            fen=position.fen,
            player=position.player,
            move_played=position.move_played,
            base_moves=position.base_moves,
            legality_mask=position.legality_mask,
            active_drawback_id=drawback_id,
            game_result=game_meta.get('result', 'unknown'),
            is_reconstructed=position.is_reconstructed
        )
    
    def convert_batch(self, reconstructed_games: List[ReconstructedGame]) -> List[UnifiedGame]:
        """Convert a batch of reconstructed games."""
        return [self.convert_game(game) for game in reconstructed_games]
    
    def save_jsonl(self, unified_games: List[UnifiedGame], output_file: str):
        """Save unified games to JSONL format (one game per line)."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            for game in unified_games:
                # Convert to dict and handle non-serializable objects
                game_dict = asdict(game)
                json.dump(game_dict, f, separators=(',', ':'))
                f.write('\n')
        
        print(f"Saved {len(unified_games)} games to {output_path}")
    
    def load_jsonl(self, input_file: str) -> List[UnifiedGame]:
        """Load unified games from JSONL format."""
        games = []
        
        with open(input_file, 'r') as f:
            for line in f:
                if line.strip():
                    game_dict = json.loads(line)
                    game = UnifiedGame(**game_dict)
                    games.append(game)
        
        return games
    
    def create_training_splits(self, unified_games: List[UnifiedGame], 
                              output_dir: str, train_ratio: float = 0.8,
                              val_ratio: float = 0.1, test_ratio: float = 0.1):
        """Create train/val/test splits for training."""
        import random
        
        random.shuffle(unified_games)
        
        total_games = len(unified_games)
        train_size = int(total_games * train_ratio)
        val_size = int(total_games * val_ratio)
        test_size = total_games - train_size - val_size
        
        train_games = unified_games[:train_size]
        val_games = unified_games[train_size:train_size + val_size]
        test_games = unified_games[train_size + val_size:]
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save splits
        self.save_jsonl(train_games, output_path / "train.jsonl")
        self.save_jsonl(val_games, output_path / "val.jsonl")
        self.save_jsonl(test_games, output_path / "test.jsonl")
        
        # Save metadata
        metadata = {
            "total_games": total_games,
            "train_games": len(train_games),
            "val_games": len(val_games),
            "test_games": len(test_games),
            "drawback_types": self.drawback_registry.get_all_drawbacks(),
            "created_at": time.time()
        }
        
        with open(output_path / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Created training splits:")
        print(f"  Train: {len(train_games)} games")
        print(f"  Val: {len(val_games)} games")
        print(f"  Test: {len(test_games)} games")
        
        return train_games, val_games, test_games


class TrainingDataAnalyzer:
    """Analyzes unified training data for insights."""
    
    def __init__(self):
        self.drawback_registry = DrawbackRegistry()
    
    def analyze_dataset(self, unified_games: List[UnifiedGame]) -> Dict[str, Any]:
        """Analyze the training dataset."""
        total_samples = sum(len(game.training_samples) for game in unified_games)
        
        # Drawback distribution
        drawback_counts = {}
        game_result_counts = {}
        reconstructed_counts = {"reconstructed": 0, "known": 0}
        
        for game in unified_games:
            game_result_counts[game.meta.get('result', 'unknown')] = \
                game_result_counts.get(game.meta.get('result', 'unknown'), 0) + 1
            
            for sample in game.training_samples:
                drawback_name = self.drawback_registry.get_name(sample.active_drawback_id)
                drawback_counts[drawback_name] = drawback_counts.get(drawback_name, 0) + 1
                
                if sample.is_reconstructed:
                    reconstructed_counts["reconstructed"] += 1
                else:
                    reconstructed_counts["known"] += 1
        
        # Calculate statistics
        analysis = {
            "total_games": len(unified_games),
            "total_samples": total_samples,
            "avg_samples_per_game": total_samples / len(unified_games) if unified_games else 0,
            "game_results": game_result_counts,
            "drawback_distribution": drawback_counts,
            "data_sources": reconstructed_counts,
            "drawback_types": self.drawback_registry.get_all_drawbacks()
        }
        
        return analysis
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """Print analysis results."""
        print("\n=== Training Dataset Analysis ===")
        print(f"Total Games: {analysis['total_games']}")
        print(f"Total Samples: {analysis['total_samples']}")
        print(f"Avg Samples/Game: {analysis['avg_samples_per_game']:.1f}")
        
        print("\nGame Results:")
        for result, count in analysis['game_results'].items():
            print(f"  {result}: {count}")
        
        print("\nDrawback Distribution:")
        for drawback, count in sorted(analysis['drawback_distribution'].items()):
            print(f"  {drawback}: {count}")
        
        print("\nData Sources:")
        for source, count in analysis['data_sources'].items():
            print(f"  {source}: {count}")


# Convenience functions
def create_unified_dataset(reconstructed_games: List[ReconstructedGame], 
                          output_dir: str = "data/unified") -> str:
    """Create unified training dataset from reconstructed games."""
    converter = UnifiedFormatConverter()
    
    # Convert to unified format
    unified_games = converter.convert_batch(reconstructed_games)
    
    # Create training splits
    train_games, val_games, test_games = converter.create_training_splits(
        unified_games, output_dir
    )
    
    # Analyze dataset
    analyzer = TrainingDataAnalyzer()
    analysis = analyzer.analyze_dataset(unified_games)
    analyzer.print_analysis(analysis)
    
    return output_dir


def load_unified_dataset(data_dir: str) -> tuple:
    """Load unified training dataset."""
    converter = UnifiedFormatConverter()
    
    train_games = converter.load_jsonl(f"{data_dir}/train.jsonl")
    val_games = converter.load_jsonl(f"{data_dir}/val.jsonl")
    test_games = converter.load_jsonl(f"{data_dir}/test.jsonl")
    
    return train_games, val_games, test_games
