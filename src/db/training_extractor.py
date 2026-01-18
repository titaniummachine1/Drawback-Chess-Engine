"""
Training Data Extractor for Minimal Storage

Generates complex training data from minimal stored data on-demand.
"""

import json
import numpy as np
from typing import List, Dict, Any, Iterator, Tuple
from dataclasses import dataclass

from .minimal_storage import get_minimal_storage
from ..engine.chess_engine import GameState


@dataclass
class TrainingSample:
    """Complete training sample generated from minimal data."""
    fen: str
    legal_moves: List[str]
    game_result: str  # 'white_win', 'black_win', 'draw'
    has_drawback: bool
    drawback_type: Optional[str]
    drawback_severity: float
    position_value: float  # Calculated from game result
    move_probabilities: Dict[str, float]  # Calculated from game outcome
    legal_moves_mask: Dict[str, bool]


class TrainingExtractor:
    """Extracts training data from minimal storage."""
    
    def __init__(self):
        self.storage = get_minimal_storage()
    
    def extract_training_samples(self, limit: int = 10000, 
                               with_drawbacks_only: bool = False) -> Iterator[TrainingSample]:
        """
        Extract training samples from minimal storage.
        
        Args:
            limit: Maximum number of samples to extract
            with_drawbacks_only: Only extract samples with drawbacks
            
        Yields:
            TrainingSample objects
        """
        for fen, legal_moves, drawback_info, result in self.storage.get_training_positions(
            limit=limit, with_drawbacks_only=with_drawbacks_only
        ):
            # Calculate position value from game result
            position_value = self._calculate_position_value(fen, result)
            
            # Generate move probabilities
            move_probabilities = self._generate_move_probabilities(
                legal_moves, position_value, drawback_info
            )
            
            # Create legal moves mask
            legal_moves_mask = {move: True for move in legal_moves}
            
            # Extract drawback info
            has_drawback = drawback_info is not None
            drawback_type = drawback_info.get("type") if drawback_info else None
            drawback_severity = drawback_info.get("severity", 0.0) if drawback_info else 0.0
            
            yield TrainingSample(
                fen=fen,
                legal_moves=legal_moves,
                game_result=result or "unknown",
                has_drawback=has_drawback,
                drawback_type=drawback_type,
                drawback_severity=drawback_severity,
                position_value=position_value,
                move_probabilities=move_probabilities,
                legal_moves_mask=legal_moves_mask
            )
    
    def extract_drawback_samples(self, min_severity: float = 0.5) -> List[TrainingSample]:
        """Extract samples specifically for drawback training."""
        drawback_data = self.storage.get_drawback_training_data(min_severity)
        samples = []
        
        for data in drawback_data:
            fen = data["fen"]
            legal_moves = data["legal_moves"]
            drawback_type = data["drawback_type"]
            severity = data["severity"]
            response_data = data["response_data"]
            
            # Calculate position value (drawbacks are usually negative)
            position_value = -severity * 0.5  # Scale drawback severity to position value
            
            # Generate move probabilities based on drawback response
            move_probabilities = self._generate_drawback_move_probabilities(
                legal_moves, response_data
            )
            
            legal_moves_mask = {move: True for move in legal_moves}
            
            samples.append(TrainingSample(
                fen=fen,
                legal_moves=legal_moves,
                game_result="drawback_analysis",  # Special marker for drawback training
                has_drawback=True,
                drawback_type=drawback_type,
                drawback_severity=severity,
                position_value=position_value,
                move_probabilities=move_probabilities,
                legal_moves_mask=legal_moves_mask
            ))
        
        return samples
    
    def _calculate_position_value(self, fen: str, game_result: str) -> float:
        """Calculate position value from game result and FEN."""
        # Base values
        result_values = {
            'white_win': 1.0,
            'black_win': -1.0,
            'draw': 0.0,
            'unknown': 0.0
        }
        
        base_value = result_values.get(game_result, 0.0)
        
        # Adjust based on position in game (from FEN move counters)
        try:
            fen_parts = fen.split()
            if len(fen_parts) >= 6:
                fullmove_number = int(fen_parts[5])
                halfmove_clock = int(fen_parts[4])
                
                # Early game positions are less certain about final result
                if fullmove_number <= 10:
                    uncertainty_factor = 0.3
                elif fullmove_number <= 20:
                    uncertainty_factor = 0.6
                else:
                    uncertainty_factor = 0.9
                
                base_value *= uncertainty_factor
        except (ValueError, IndexError):
            pass  # Use base value if FEN parsing fails
        
        return base_value
    
    def _generate_move_probabilities(self, legal_moves: List[str], 
                                    position_value: float,
                                    drawback_info: Dict[str, Any]) -> Dict[str, float]:
        """Generate move probability distribution."""
        if not legal_moves:
            return {}
        
        # Base uniform distribution
        base_prob = 1.0 / len(legal_moves)
        probabilities = {move: base_prob for move in legal_moves}
        
        # Adjust based on drawback information
        if drawback_info:
            response_data = drawback_info.get("response_data", {})
            legal_moves_response = response_data.get("legal_moves", [])
            
            # Boost probability of moves that address the drawback
            for move in legal_moves_response:
                if move in probabilities:
                    probabilities[move] *= 2.0  # Double the probability
        
        # Normalize probabilities
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {move: prob / total_prob for move, prob in probabilities.items()}
        
        return probabilities
    
    def _generate_drawback_move_probabilities(self, legal_moves: List[str],
                                            response_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate move probabilities specifically for drawback training."""
        if not legal_moves:
            return {}
        
        # Start with uniform distribution
        probabilities = {move: 1.0 for move in legal_moves}
        
        # Boost moves that are in the response data
        response_moves = response_data.get("legal_moves", [])
        for move in response_moves:
            if move in probabilities:
                probabilities[move] *= 3.0  # Triple boost for drawback-response moves
        
        # Additional boosts based on metadata
        affected_pieces = response_data.get("affected_pieces", [])
        threat_squares = response_data.get("threat_squares", [])
        
        for move in legal_moves:
            # Boost moves that protect affected pieces
            if self._move_protects_piece(move, affected_pieces):
                probabilities[move] *= 1.5
            
            # Boost moves that address threat squares
            if self._move_addresses_threat(move, threat_squares):
                probabilities[move] *= 1.5
        
        # Normalize
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {move: prob / total_prob for move, prob in probabilities.items()}
        
        return probabilities
    
    def _move_protects_piece(self, move: str, affected_pieces: List[str]) -> bool:
        """Check if a move protects an affected piece."""
        # Simple heuristic: if move is a defensive move
        # This is a placeholder - implement proper chess logic
        return len(move) >= 4 and move[2] in ['a', 'b', 'c', 'd']  # Simplified heuristic
    
    def _move_addresses_threat(self, move: str, threat_squares: List[str]) -> bool:
        """Check if a move addresses a threat square."""
        if len(move) < 4:
            return False
        
        to_square = move[2:4]
        return to_square in threat_squares
    
    def export_tensorflow_dataset(self, output_path: str, limit: int = 10000):
        """Export training data in TensorFlow-ready format."""
        samples = list(self.extract_training_samples(limit=limit))
        
        dataset = {
            "inputs": [],
            "target_values": [],
            "target_policies": [],
            "legal_moves_masks": [],
            "drawback_labels": []
        }
        
        for sample in samples:
            # Encode position (simplified - use proper chess encoding in production)
            position_encoding = self._encode_position(sample.fen)
            
            # Create policy vector (one-hot encoding of best move)
            best_move = max(sample.move_probabilities.items(), key=lambda x: x[1])[0]
            policy_vector = self._create_policy_vector(best_move, sample.legal_moves)
            
            # Create legal moves mask
            legal_mask = self._create_legal_mask(sample.legal_moves)
            
            dataset["inputs"].append(position_encoding)
            dataset["target_values"].append(sample.position_value)
            dataset["target_policies"].append(policy_vector)
            dataset["legal_moves_masks"].append(legal_mask)
            dataset["drawback_labels"].append(1.0 if sample.has_drawback else 0.0)
        
        # Save as numpy arrays
        np.savez_compressed(
            output_path,
            inputs=np.array(dataset["inputs"]),
            target_values=np.array(dataset["target_values"]),
            target_policies=np.array(dataset["target_policies"]),
            legal_moves_masks=np.array(dataset["legal_moves_masks"]),
            drawback_labels=np.array(dataset["drawback_labels"])
        )
    
    def _encode_position(self, fen: str) -> np.ndarray:
        """Encode FEN position into tensor (simplified version)."""
        # This is a placeholder - implement proper chess board encoding
        # Returns a simple fixed-size encoding for demonstration
        encoding = np.zeros(8 * 8 * 12)  # 8x8 board, 12 piece types
        
        # Simple hash-based encoding (replace with proper FEN parsing)
        fen_hash = hash(fen) % (8 * 8 * 12)
        encoding[fen_hash] = 1.0
        
        return encoding
    
    def _create_policy_vector(self, best_move: str, legal_moves: List[str]) -> np.ndarray:
        """Create policy vector for best move."""
        # Simplified - use move index as encoding
        policy = np.zeros(len(legal_moves))
        if best_move in legal_moves:
            move_index = legal_moves.index(best_move)
            policy[move_index] = 1.0
        return policy
    
    def _create_legal_mask(self, legal_moves: List[str]) -> np.ndarray:
        """Create legal moves mask."""
        return np.ones(len(legal_moves), dtype=bool)
