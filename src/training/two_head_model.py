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

from ..utils.chess_utils import fen_to_tensor, move_to_index, encode_move_history


class ResBlock(nn.Module):
    """Classic Residual Block for Chess Board processing."""
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        return F.relu(out)


class ChessBoardEncoder(nn.Module):
    """Subtractive Backbone: ResNet-10 for 'Toaster' hardware."""
    
    def __init__(self, boards: int = 14, filters: int = 128):
        super().__init__()
        # Initial projection
        self.conv_in = nn.Conv2d(boards, filters, kernel_size=3, padding=1)
        self.bn_in = nn.BatchNorm2d(filters)
        
        # 5 ResBlocks (each has 2 convs = total 10 layers)
        self.blocks = nn.Sequential(*[ResBlock(filters) for _ in range(5)])
        
        # Compression for heads
        self.pool = nn.AdaptiveAvgPool2d((1, 1)) # Global average pooling
        self.flatten = nn.Flatten()
        self.repr_layer = nn.Linear(filters, 512)
    
    def forward(self, fen: str) -> torch.Tensor:
        # 1. Convert FEN to Bitplanes [14, 8, 8]
        # (Using the real converter from utils)
        board_tensor = fen_to_tensor(fen).unsqueeze(0) # [1, 14, 8, 8]
        
        # 2. Pass through ResNet
        x = F.relu(self.bn_in(self.conv_in(board_tensor)))
        x = self.blocks(x)
        
        # 3. Global feature vector
        x = self.pool(x)
        x = self.flatten(x)
        return F.relu(self.repr_layer(x))


class PhysicsEngineHead(nn.Module):
    """
    Head A: The Masker
    Predicts legality % for 4096 moves from [Board + DrawbackVector + RandomState].
    """
    
    def __init__(self, board_repr_size: int = 512, text_vec_size: int = 384):
        super().__init__()
        # Input: Board Repr (512) + Text Vector (384) + Random State (16)
        # Random State is for non-deterministic drawbacks like "Color pick"
        self.physics_fc = nn.Sequential(
            nn.Linear(board_repr_size + text_vec_size + 16, 512),
            nn.ReLU(),
            nn.Linear(512, 1024),
            nn.ReLU(),
            nn.Linear(1024, 4096) # Policy-style output matching 4096 move indices
        )
        
    def forward(self, board_repr: torch.Tensor, text_vec: torch.Tensor, 
                random_state: Optional[torch.Tensor] = None) -> torch.Tensor:
        if random_state is None:
            random_state = torch.zeros(board_repr.size(0), 16, device=board_repr.device)
            
        # Concatenate all inputs
        x = torch.cat([board_repr, text_vec, random_state], dim=1)
        
        # Sigmoid for % probability (0 = Illegal, 1 = Legal)
        return torch.sigmoid(self.physics_fc(x))


class DetectiveHead(nn.Module):
    """
    Head B: The Guesser
    Guesses the 'Drawback Latent Vector' from move history.
    """
    
    def __init__(self, board_repr_size: int = 512, latent_dim: int = 384):
        super().__init__()
        # Simplified: LSTM/GRU over encoded move history
        self.history_gru = nn.GRU(64, 256, batch_first=True)
        self.fc = nn.Sequential(
            nn.Linear(256 + board_repr_size, 512),
            nn.ReLU(),
            nn.Linear(512, latent_dim) # Predict the 384D embedding
        )
        
    def encode_move_history(self, move_history: List[str]) -> torch.Tensor:
        """Encode move history using UCI indices."""
        # Use only the last move for the embedding head (simplified)
        # In a real model, this would be an LSTM/Transformer over the history tensor
        if not move_history:
            return torch.zeros(64)
            
        last_move_idx = move_to_index(move_history[-1])
        move_tensor = torch.tensor([last_move_idx % (self.max_history * 2)], dtype=torch.long)
        
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

    def predict_legality_from_history(self, fen: str, move_history: List[str], 
                                     random_state: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Subtractive Head Inference (Unkown Opponent Drawback):
        1. Board Encoder processes FEN.
        2. Detective Head analyzes history to guess the Latent Drawback Vector (384D).
        3. Physics Head uses that Vector to predict illegal moves in a single pass.
        """
        board_repr = self.board_encoder(fen)
        
        # 1. Guess the drawback vector
        latent_drawback_vec = self.detective_head(board_repr, move_history)
        
        # 2. Apply physics mask using the guessed vector
        legality_mask = self.physics_head(board_repr, latent_drawback_vec, random_state)
        
        return legality_mask

    def predict_legality_known_drawback(self, fen: str, drawback_text_vec: torch.Tensor,
                                       random_state: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Prediction for when the drawback is known (e.g., our own turn)."""
        board_repr = self.board_encoder(fen)
        return self.physics_head(board_repr, drawback_text_vec, random_state)


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
