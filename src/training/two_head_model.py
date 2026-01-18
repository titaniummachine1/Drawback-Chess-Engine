"""
Two-Head Neural Network Architecture for Drawback Chess Engine

Implements the Physics Engine Head (Mask) and Detective Head (Guesser)
that use the same unified training data.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional


class ChessBoardEncoder(nn.Module):
    """Encodes chess board state into tensor representation."""
    
    def __init__(self, board_size: int = 8, piece_types: int = 12):
        super().__init__()
        self.board_size = board_size
        self.piece_types = piece_types
        
        # Convolutional layers for board pattern recognition
        self.conv1 = nn.Conv2d(piece_types, 64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        
        # Additional features (castling rights, en passant, etc.)
        self.additional_features = nn.Linear(10, 32)  # 10 additional features
        
        # Final board representation
        self.board_repr = nn.Linear(256 * board_size * board_size + 32, 512)
    
    def encode_fen(self, fen: str) -> torch.Tensor:
        """Encode FEN to board tensor (simplified implementation)."""
        # This is a placeholder - proper implementation would parse FEN
        # and create proper piece placement tensors
        
        # For now, create a random tensor based on FEN hash
        board_tensor = torch.zeros(self.piece_types, self.board_size, self.board_size)
        
        # Simple hash-based encoding (replace with proper FEN parsing)
        fen_hash = hash(fen) % (self.piece_types * self.board_size * self.board_size)
        piece_type = fen_hash // (self.board_size * self.board_size)
        square = fen_hash % (self.board_size * self.board_size)
        row = square // self.board_size
        col = square % self.board_size
        
        board_tensor[piece_type, row, col] = 1.0
        
        return board_tensor
    
    def extract_additional_features(self, fen: str) -> torch.Tensor:
        """Extract additional features from FEN."""
        # Parse FEN for castling rights, en passant, etc.
        features = torch.zeros(10)
        
        try:
            fen_parts = fen.split()
            if len(fen_parts) >= 3:
                # Castling rights
                castling = fen_parts[2]
                features[0] = 1.0 if 'K' in castling else 0.0  # White king-side
                features[1] = 1.0 if 'Q' in castling else 0.0  # White queen-side
                features[2] = 1.0 if 'k' in castling else 0.0  # Black king-side
                features[3] = 1.0 if 'q' in castling else 0.0  # Black queen-side
                
                # En passant
                if len(fen_parts) >= 4 and fen_parts[3] != '-':
                    features[4] = 1.0
                
                # Side to move
                if len(fen_parts) >= 1:
                    features[5] = 1.0 if fen_parts[1] == 'w' else 0.0
                
                # Move counters (normalized)
                if len(fen_parts) >= 6:
                    halfmove = int(fen_parts[4]) / 100.0  # Normalize
                    fullmove = int(fen_parts[5]) / 100.0  # Normalize
                    features[6] = min(halfmove, 1.0)
                    features[7] = min(fullmove / 100.0, 1.0)
        except (ValueError, IndexError):
            pass  # Use default zeros if parsing fails
        
        return features
    
    def forward(self, fen: str) -> torch.Tensor:
        """Encode FEN to board representation."""
        # Encode board
        board_tensor = self.encode_fen(fen)
        board_tensor = board_tensor.unsqueeze(0)  # Add batch dimension
        
        # Convolutional layers
        x = F.relu(self.conv1(board_tensor))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        
        # Flatten
        x = x.view(x.size(0), -1)
        
        # Additional features
        additional = self.extract_additional_features(fen)
        additional = self.additional_features(additional)
        
        # Concatenate and final representation
        x = torch.cat([x, additional], dim=1)
        board_repr = F.relu(self.board_repr(x))
        
        return board_repr


class PhysicsEngineHead(nn.Module):
    """Head A: Physics Engine - learns which moves are illegal given a drawback."""
    
    def __init__(self, board_repr_size: int = 512, max_moves: int = 218):
        super().__init__()
        self.max_moves = max_moves
        
        # Process board representation + drawback
        self.drawback_embedding = nn.Embedding(20, 32)  # 20 drawback types
        self.physics_fc1 = nn.Linear(board_repr_size + 32, 256)
        self.physics_fc2 = nn.Linear(256, 128)
        self.physics_output = nn.Linear(128, max_moves)  # Legality probabilities
        
    def forward(self, board_repr: torch.Tensor, drawback_ids: torch.Tensor) -> torch.Tensor:
        """Predict legality mask for moves."""
        # Embed drawback
        drawback_emb = self.drawback_embedding(drawback_ids)
        
        # Combine board representation with drawback
        x = torch.cat([board_repr, drawback_emb], dim=1)
        
        # Process through network
        x = F.relu(self.physics_fc1(x))
        x = F.relu(self.physics_fc2(x))
        
        # Output legality probabilities
        legality_logits = self.physics_output(x)
        legality_probs = torch.sigmoid(legality_logits)
        
        return legality_probs


class DetectiveHead(nn.Module):
    """Head B: Detective - guesses opponent's drawback from move history."""
    
    def __init__(self, board_repr_size: int = 512, max_history: int = 10, drawback_types: int = 10):
        super().__init__()
        self.max_history = max_history
        self.drawback_types = drawback_types
        
        # Process board representation
        self.detective_fc1 = nn.Linear(board_repr_size, 256)
        
        # Process move history (simplified - would use proper move encoding)
        self.move_embedding = nn.Embedding(max_history * 2, 64)  # Move encoding
        
        # Combine board + history for drawback prediction
        self.combined_fc1 = nn.Linear(256 + 64, 128)
        self.combined_fc2 = nn.Linear(128, 64)
        self.drawback_output = nn.Linear(64, drawback_types)  # Drawback probabilities
        
    def encode_move_history(self, move_history: List[str]) -> torch.Tensor:
        """Encode move history (simplified)."""
        # This is a placeholder - proper implementation would use
        # sophisticated move encoding with piece types, squares, etc.
        
        if not move_history:
            return torch.zeros(64)
        
        # Simple hash-based encoding for demonstration
        move_hash = hash(str(move_history)) % (self.max_history * 2)
        move_tensor = torch.tensor([move_hash], dtype=torch.long)
        
        return self.move_embedding(move_tensor).squeeze(0)
    
    def forward(self, board_repr: torch.Tensor, move_history: List[str]) -> torch.Tensor:
        """Predict drawback probabilities."""
        # Process board representation
        x = F.relu(self.detective_fc1(board_repr))
        
        # Process move history
        history_emb = self.encode_move_history(move_history)
        
        # Combine
        combined = torch.cat([x, history_emb.unsqueeze(0)], dim=1)
        combined = F.relu(self.combined_fc1(combined))
        combined = F.relu(self.combined_fc2(combined))
        
        # Output drawback probabilities
        drawback_logits = self.drawback_output(combined)
        drawback_probs = F.softmax(drawback_logits, dim=1)
        
        return drawback_probs


class TwoHeadChessModel(nn.Module):
    """Complete two-head model for Drawback Chess Engine."""
    
    def __init__(self, board_size: int = 8, piece_types: int = 12, 
                 max_moves: int = 218, drawback_types: int = 10):
        super().__init__()
        
        # Shared encoder
        self.board_encoder = ChessBoardEncoder(board_size, piece_types)
        
        # Two heads
        self.physics_head = PhysicsEngineHead(
            board_repr_size=512, 
            max_moves=max_moves
        )
        
        self.detective_head = DetectiveHead(
            board_repr_size=512,
            max_history=10,
            drawback_types=drawback_types
        )
        
        self.max_moves = max_moves
        self.drawback_types = drawback_types
    
    def forward(self, fen: str, drawback_id: Optional[int] = None, 
                move_history: Optional[List[str]] = None) -> Dict[str, torch.Tensor]:
        """Forward pass through both heads."""
        # Encode board
        board_repr = self.board_encoder(fen)
        
        outputs = {}
        
        # Physics head (if drawback is known)
        if drawback_id is not None:
            drawback_tensor = torch.tensor([drawback_id], dtype=torch.long)
            legality_mask = self.physics_head(board_repr, drawback_tensor)
            outputs['legality_mask'] = legality_mask
        
        # Detective head (if move history is available)
        if move_history is not None:
            drawback_probs = self.detective_head(board_repr, move_history)
            outputs['drawback_probs'] = drawback_probs
        
        return outputs
    
    def predict_legality(self, fen: str, drawback_id: int) -> torch.Tensor:
        """Predict move legality for a known drawback."""
        board_repr = self.board_encoder(fen)
        drawback_tensor = torch.tensor([drawback_id], dtype=torch.long)
        return self.physics_head(board_repr, drawback_tensor)
    
    def predict_drawback(self, fen: str, move_history: List[str]) -> torch.Tensor:
        """Predict opponent's drawback from move history."""
        board_repr = self.board_encoder(fen)
        return self.detective_head(board_repr, move_history)


class TwoHeadTrainer:
    """Trainer for the two-head model."""
    
    def __init__(self, model: TwoHeadChessModel):
        self.model = model
        self.physics_optimizer = torch.optim.Adam(
            list(model.board_encoder.parameters()) + 
            list(model.physics_head.parameters()),
            lr=0.001
        )
        self.detective_optimizer = torch.optim.Adam(
            list(model.board_encoder.parameters()) + 
            list(model.detective_head.parameters()),
            lr=0.001
        )
        
        self.physics_criterion = nn.BCELoss()
        self.detective_criterion = nn.CrossEntropyLoss()
    
    def train_physics_head(self, fen: str, drawback_id: int, 
                          target_mask: List[int]) -> float:
        """Train the physics head on a single sample."""
        self.physics_optimizer.zero_grad()
        
        # Forward pass
        predicted_mask = self.model.predict_legality(fen, drawback_id)
        
        # Prepare target
        target_tensor = torch.tensor(target_mask, dtype=torch.float32).unsqueeze(0)
        
        # Calculate loss
        loss = self.physics_criterion(predicted_mask, target_tensor)
        
        # Backward pass
        loss.backward()
        self.physics_optimizer.step()
        
        return loss.item()
    
    def train_detective_head(self, fen: str, move_history: List[str], 
                            target_drawback_id: int) -> float:
        """Train the detective head on a single sample."""
        self.detective_optimizer.zero_grad()
        
        # Forward pass
        predicted_probs = self.model.predict_drawback(fen, move_history)
        
        # Prepare target
        target_tensor = torch.tensor([target_drawback_id], dtype=torch.long)
        
        # Calculate loss
        loss = self.detective_criterion(predicted_probs, target_tensor)
        
        # Backward pass
        loss.backward()
        self.detective_optimizer.step()
        
        return loss.item()
    
    def train_epoch(self, training_samples: List[Dict]) -> Dict[str, float]:
        """Train one epoch on training samples."""
        physics_losses = []
        detective_losses = []
        
        for sample in training_samples:
            # Train physics head
            if sample.get('active_drawback_id') is not None:
                physics_loss = self.train_physics_head(
                    sample['fen'],
                    sample['active_drawback_id'],
                    sample['legality_mask']
                )
                physics_losses.append(physics_loss)
            
            # Train detective head
            if sample.get('move_history'):
                detective_loss = self.train_detective_head(
                    sample['fen'],
                    sample['move_history'],
                    sample['active_drawback_id'] or 0
                )
                detective_losses.append(detective_loss)
        
        return {
            'physics_loss': np.mean(physics_losses) if physics_losses else 0.0,
            'detective_loss': np.mean(detective_losses) if detective_losses else 0.0
        }


# Convenience functions
def create_two_head_model(max_moves: int = 218, drawback_types: int = 10) -> TwoHeadChessModel:
    """Create a new two-head model."""
    return TwoHeadChessModel(max_moves=max_moves, drawback_types=drawback_types)


def create_trainer(model: TwoHeadChessModel) -> TwoHeadTrainer:
    """Create a trainer for the two-head model."""
    return TwoHeadTrainer(model)


def demo_training():
    """Demonstrate training on sample data."""
    print("=== Two-Head Model Training Demo ===")
    
    # Create model and trainer
    model = create_two_head_model()
    trainer = create_trainer(model)
    
    # Sample training data
    sample_samples = [
        {
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
            'active_drawback_id': 1,  # No_Castling
            'legality_mask': [1, 1, 0, 0, 1] + [0] * 213,  # Example mask
            'move_history': []
        },
        {
            'fen': 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
            'active_drawback_id': 2,  # Knight_Immobility
            'legality_mask': [1, 0, 1, 0, 1] + [0] * 213,
            'move_history': ['e2e4', 'e7e5']
        }
    ]
    
    # Train for a few epochs
    for epoch in range(3):
        losses = trainer.train_epoch(sample_samples)
        print(f"Epoch {epoch + 1}: Physics Loss = {losses['physics_loss']:.4f}, "
              f"Detective Loss = {losses['detective_loss']:.4f}")
    
    print("Training demo complete!")
    
    # Test inference
    print("\n=== Inference Demo ===")
    
    # Physics head inference
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    drawback_id = 1  # No_Castling
    
    legality_probs = model.predict_legality(fen, drawback_id)
    print(f"Predicted legality for No_Castling: {legality_probs.squeeze()[:5]}")
    
    # Detective head inference
    move_history = ['e2e4', 'e7e5']
    drawback_probs = model.predict_drawback(fen, move_history)
    print(f"Predicted drawback probabilities: {drawback_probs.squeeze()}")


if __name__ == "__main__":
    demo_training()
