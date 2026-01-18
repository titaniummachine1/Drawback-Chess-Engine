"""
Chess Encoding Utilities for Drawback Chess Engine

Handles conversion between chess formats (FEN, UCI) and neural network tensors.
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional


# Constants for piece encoding
PIECE_TO_INDEX = {
    'P': 0, 'N': 1, 'B': 2, 'R': 3, 'Q': 4, 'K': 5,  # White
    'p': 6, 'n': 7, 'b': 8, 'r': 9, 'q': 10, 'k': 11  # Black
}

# Square to index mapping (a1=0, h8=63)
SQUARES = [
    f"{f}{r}" for r in "12345678" for f in "abcdefgh"
]
SQUARE_TO_INDEX = {square: i for i, square in enumerate(SQUARES)}


def fen_to_tensor(fen: str) -> torch.Tensor:
    """
    Convert FEN string to a [12, 8, 8] bitboard representation.
    
    Channels:
    0-5: White P, N, B, R, Q, K
    6-11: Black p, n, b, r, q, k
    """
    tensor = torch.zeros(12, 8, 8)
    
    parts = fen.split()
    placement = parts[0]
    
    rows = placement.split('/')
    for r, row_str in enumerate(rows):
        # FEN starts from rank 8, tensor starts from rank 8 (row 0)
        c = 0
        for char in row_str:
            if char.isdigit():
                c += int(char)
            else:
                piece_idx = PIECE_TO_INDEX[char]
                # Invert row so rank 1 is row 7, rank 8 is row 0
                tensor[piece_idx, r, c] = 1.0
                c += 1
                
    return tensor


def move_to_index(move_uci: str) -> int:
    """
    Convert a UCI move string to a unique index.
    This is a simplified mapping for a fixed-size policy head.
    
    Standard approach for policy head is [FromSquare * 64 + ToSquare].
    """
    if len(move_uci) < 4:
        return 0
        
    from_sq = move_uci[0:2]
    to_sq = move_uci[2:4]
    
    if from_sq not in SQUARE_TO_INDEX or to_sq not in SQUARE_TO_INDEX:
        return 0
        
    from_idx = SQUARE_TO_INDEX[from_sq]
    to_idx = SQUARE_TO_INDEX[to_sq]
    
    # Base index for move without promotion
    idx = from_idx * 64 + to_idx
    
    # Handle promotion (optional, adds offset)
    if len(move_uci) == 5:
        promo = move_uci[4]
        promo_offset = {'n': 1, 'b': 2, 'r': 3, 'q': 4}.get(promo, 0)
        # We reserve high indices for promotions
        idx += 4096 + (promo_offset * 64) 
        
    return idx


def create_legality_mask(legal_moves: List[str], max_moves: int = 4096 + (5 * 64)) -> torch.Tensor:
    """Create a binary mask for legal moves."""
    mask = torch.zeros(max_moves)
    for move in legal_moves:
        idx = move_to_index(move)
        if idx < max_moves:
            mask[idx] = 1.0
    return mask


def encode_move_history(moves: List[str], max_len: int = 10) -> torch.Tensor:
    """Encode move history as a fixed-size sequence of move indices."""
    history = torch.zeros(max_len, dtype=torch.long)
    # Take the last N moves
    recent_moves = moves[-max_len:]
    for i, move in enumerate(recent_moves):
        history[i] = move_to_index(move)
    return history
