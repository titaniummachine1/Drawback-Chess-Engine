"""
Variant Configuration Loader for Drawback Chess Engine

Loads and parses variant configuration files for Fairy-Stockfish.
"""

import configparser
from pathlib import Path
from typing import Dict, Any, Optional


class VariantConfig:
    """Configuration for a chess variant."""
    
    def __init__(self, config_file: str):
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        self.loaded = False
        
        if self.config_file.exists():
            self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        try:
            self.config.read(self.config_file)
            self.loaded = True
            print(f"Loaded variant config: {self.config_file}")
        except Exception as e:
            print(f"Failed to load variant config: {e}")
            self.loaded = False
    
    def get_variant_name(self) -> str:
        """Get variant name."""
        if self.loaded:
            # Check for [drawback:chess] section first
            if 'drawback:chess' in self.config:
                return 'drawback'
            # Fallback to [variant] section
            elif 'variant' in self.config:
                return self.config['variant'].get('name', 'chess')
        return 'chess'
    
    def get_victory_condition(self) -> str:
        """Get victory condition."""
        if self.loaded:
            if 'drawback:chess' in self.config:
                return self.config['drawback:chess'].get('victoryState', 'checkmate')
            elif 'variant' in self.config:
                return self.config['variant'].get('victoryState', 'checkmate')
        return 'checkmate'
    
    def is_illegal_checks(self) -> bool:
        """Check if checks are illegal."""
        if self.loaded:
            if 'drawback:chess' in self.config:
                return self.config['drawback:chess'].getboolean('illegalChecks', False)
            elif 'variant' in self.config:
                return self.config['variant'].getboolean('illegalChecks', False)
        return False
    
    def get_stalemate_value(self) -> str:
        """Get stalemate value."""
        if self.loaded:
            if 'drawback:chess' in self.config:
                return self.config['drawback:chess'].get('stalemateValue', 'draw')
            elif 'variant' in self.config:
                return self.config['variant'].get('stalemateValue', 'draw')
        return 'draw'
    
    def can_castle_out_of_check(self) -> bool:
        """Check if castling out of check is allowed."""
        if self.loaded:
            if 'drawback:chess' in self.config:
                return self.config['drawback:chess'].getboolean('castlingOutofCheck', False)
            elif 'variant' in self.config:
                return self.config['variant'].getboolean('castlingOutofCheck', False)
        return False
    
    def can_castle_through_check(self) -> bool:
        """Check if castling through check is allowed."""
        if self.loaded:
            if 'drawback:chess' in self.config:
                return self.config['drawback:chess'].getboolean('castlingThroughCheck', False)
            elif 'variant' in self.config:
                return self.config['variant'].getboolean('castlingThroughCheck', False)
        return False
    
    def get_start_fen(self) -> str:
        """Get starting FEN (use Fairy-Stockfish built-in default)."""
        # Let Fairy-Stockfish handle the default starting position
        # Return None to indicate use of built-in default
        if self.loaded and 'variant' in self.config:
            fen = self.config['variant'].get('start_fen')
            if fen and fen.strip():
                return fen.strip()
        
        # Return None to use Fairy-Stockfish built-in default
        return None
    
    def is_drawback_chess(self) -> bool:
        """Check if this is a Drawback Chess variant."""
        return self.get_variant_name().lower() == 'drawback'
    
    def apply_variant_rules(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply variant-specific rules to game state."""
        if not self.is_drawback_chess():
            return game_state
        
        # Apply Drawback Chess specific modifications
        modified_state = game_state.copy()
        
        # Override victory condition
        modified_state['victory_condition'] = self.get_victory_condition()
        
        # Override check rules
        modified_state['illegal_checks'] = self.is_illegal_checks()
        # Note: illegalChecks=false automatically ignores check threats and pins
        
        # Override castling rules
        modified_state['castling_out_of_check'] = self.can_castle_out_of_check()
        modified_state['castling_through_check'] = self.can_castle_through_check()
        
        # Override stalemate
        modified_state['stalemate_value'] = self.get_stalemate_value()
        
        # Note: King capture en passant must be handled by Python bridge logic
        modified_state['king_capture_en_passant'] = 'python_bridge_required'
        
        return modified_state
    
    def print_config(self):
        """Print current configuration."""
        if not self.loaded:
            print("No configuration loaded")
            return
        
        print(f"=== {self.get_variant_name()} Variant Configuration ===")
        print(f"Victory Condition: {self.get_victory_condition()}")
        print(f"Illegal Checks: {self.is_illegal_checks()}")
        print(f"Stalemate Value: {self.get_stalemate_value()}")
        print(f"Castle Out of Check: {self.can_castle_out_of_check()}")
        print(f"Castle Through Check: {self.can_castle_through_check()}")
        
        start_fen = self.get_start_fen()
        if start_fen:
            print(f"Start FEN: {start_fen}")
        else:
            print("Start FEN: Fairy-Stockfish built-in default")
        
        print("\nNote: King capture en passant must be handled in Python bridge")
        print("Note: illegalChecks=false automatically ignores check threats and pins")


def load_drawback_config() -> Optional[VariantConfig]:
    """Load the Drawback Chess configuration."""
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "engines" / "drawback.ini"
    
    if config_path.exists():
        return VariantConfig(config_path)
    else:
        print(f"Drawback config not found at: {config_path}")
        return None


def test_variant_config():
    """Test the variant configuration."""
    config = load_drawback_config()
    
    if config:
        config.print_config()
        
        # Test applying rules
        test_state = {
            'victory_condition': 'checkmate',
            'illegal_checks': True,
            'stalemate_value': 'draw'
        }
        
        modified = config.apply_variant_rules(test_state)
        print(f"\n=== Modified Game State ===")
        for key, value in modified.items():
            print(f"{key}: {value}")
    else:
        print("No configuration to test")


if __name__ == "__main__":
    test_variant_config()
