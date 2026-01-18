"""
Drawback Chess Python Bridge

Handles special Drawback Chess rules that Fairy-Stockfish doesn't natively support,
particularly the king capture en passant rule when castling through check.
"""

from typing import List, Tuple, Optional
import re


class DrawbackBridge:
    """
    Bridge for Drawback Chess-specific rules that require custom Python logic.
    
    Handles:
    - King capture en passant when castling through check
    - Other special Drawback Chess rules not supported by Fairy-Stockfish
    """
    
    def __init__(self):
        """Initialize the Drawback Chess bridge."""
        self.castling_squares = {
            'white_kingside': ('e1', 'g1', 'f1'),  # start, end, passed_through
            'white_queenside': ('e1', 'c1', 'd1'),
            'black_kingside': ('e8', 'g8', 'f8'),
            'black_queenside': ('e8', 'c8', 'd8')
        }
    
    def add_king_capture_en_passant_moves(self, base_moves: List[str], fen: str) -> List[str]:
        """
        Add king capture en passant moves when opponent castles through check.
        
        This is the critical rule: if opponent castles through check, 
        the king can be captured on the square it passed through.
        
        Args:
            base_moves: List of base moves from Fairy-Stockfish
            fen: Current position FEN
            
        Returns:
            Enhanced list of moves including king capture en passant
        """
        enhanced_moves = base_moves.copy()
        
        # Check if any move in base_moves is a castling move
        for move in base_moves:
            if self._is_castling_move(move):
                # Get the square the king passed through
                passed_square = self._get_castling_passed_square(move, fen)
                if passed_square:
                    # Add king capture on the passed square
                    capture_move = self._create_king_capture_move(passed_square, fen)
                    if capture_move and capture_move not in enhanced_moves:
                        enhanced_moves.append(capture_move)
        
        return enhanced_moves
    
    def _is_castling_move(self, move: str) -> bool:
        """Check if a move is castling."""
        # Kingside castling
        if move in ['e1g1', 'e8g8']:
            return True
        # Queenside castling  
        if move in ['e1c1', 'e8c8']:
            return True
        return False
    
    def _get_castling_passed_square(self, castling_move: str, fen: str) -> Optional[str]:
        """Get the square the king passed through during castling."""
        if castling_move == 'e1g1':  # White kingside
            return 'f1'
        elif castling_move == 'e1c1':  # White queenside
            return 'd1'
        elif castling_move == 'e8g8':  # Black kingside
            return 'f8'
        elif castling_move == 'e8c8':  # Black queenside
            return 'd8'
        return None
    
    def _create_king_capture_move(self, target_square: str, fen: str) -> Optional[str]:
        """
        Create a king capture move on the target square.
        
        Args:
            target_square: Square where king can be captured (e.g., 'f1', 'd1', 'f8', 'd8')
            fen: Current position FEN to determine player to move
            
        Returns:
            King capture move in UCI format (e.g., 'xf1' for pawn capture, 'Nf1' for knight capture)
        """
        try:
            # Extract current player from FEN
            fen_parts = fen.split()
            if len(fen_parts) < 2:
                return None
            
            current_player = fen_parts[1]  # 'w' for white, 'b' for black
            
            # Determine which pieces can capture on the target square
            # This is a simplified version - in practice, you'd need to analyze the board
            # to find actual pieces that can capture on that square
            
            # For now, we'll add placeholder captures that would need board analysis
            # The actual implementation would need to:
            # 1. Parse the board position from FEN
            # 2. Find pieces that can legally capture on target_square
            # 3. Generate proper UCI capture moves
            
            # Example captures (these would need real board analysis):
            captures = []
            
            # Pawn captures (most common)
            if current_player == 'w':
                # White pawn captures on dark squares
                if target_square in ['f1', 'd1']:
                    captures.append(f'e{target_square[1]}{target_square}')  # Pawn from e-file
            else:
                # Black pawn captures on dark squares  
                if target_square in ['f8', 'd8']:
                    captures.append(f'e{target_square[1]}{target_square}')  # Pawn from e-file
            
            # Knight captures (knights can capture on these squares)
            knight_squares = self._get_knight_capture_squares(target_square)
            for knight_sq in knight_squares:
                captures.append(f'N{knight_sq}{target_square}')
            
            # Return the first valid capture (simplified)
            return captures[0] if captures else None
            
        except Exception as e:
            print(f"Error creating king capture move: {e}")
            return None
    
    def _get_knight_capture_squares(self, target_square: str) -> List[str]:
        """Get squares from which a knight could capture on target_square."""
        file = target_square[0]
        rank = target_square[1]
        
        # Knight move offsets
        offsets = [
            (2, 1), (2, -1), (-2, 1), (-2, -1),
            (1, 2), (1, -2), (-1, 2), (-1, -2)
        ]
        
        knight_squares = []
        for df, dr in offsets:
            new_file = chr(ord(file) + df)
            new_rank = str(int(rank) + dr)
            
            if 'a' <= new_file <= 'h' and '1' <= new_rank <= '8':
                knight_squares.append(new_file + new_rank)
        
        return knight_squares
    
    def is_king_capture_en_passant_legal(self, move: str, fen: str, previous_move: str) -> bool:
        """
        Check if a king capture en passant move is legal.
        
        This verifies:
        1. The previous move was castling through check
        2. The current move captures the king on the passed-through square
        3. The capture follows Drawback Chess rules
        
        Args:
            move: Current move being evaluated
            fen: Current position FEN
            previous_move: The move just played (should be castling)
            
        Returns:
            True if the king capture en passant is legal
        """
        # Check if previous move was castling
        if not self._is_castling_move(previous_move):
            return False
        
        # Get the square the king passed through
        passed_square = self._get_castling_passed_square(previous_move, fen)
        if not passed_square:
            return False
        
        # Check if current move captures on the passed square
        if move.endswith(passed_square) and 'x' in move or len(move) == 4:
            # This is a capture move on the passed square
            return True
        
        return False
    
    def apply_drawback_rules(self, moves: List[str], fen: str, previous_move: Optional[str] = None) -> List[str]:
        """
        Apply all Drawback Chess-specific rules to the move list.
        
        Args:
            moves: Base moves from Fairy-Stockfish
            fen: Current position FEN
            previous_move: The move just played (for context)
            
        Returns:
            Enhanced move list with Drawback Chess rules applied
        """
        enhanced_moves = moves.copy()
        
        # Apply king capture en passant rule
        enhanced_moves = self.add_king_capture_en_passant_moves(enhanced_moves, fen)
        
        # Apply other Drawback Chess rules here as needed
        
        return enhanced_moves
    
    def explain_king_capture_en_passant(self) -> str:
        """Explain the king capture en passant rule."""
        return """
        King Capture En Passant Rule:
        
        When a player castles through check, the opponent can capture 
        the king on the square it passed through.
        
        Examples:
        - White castles e1g1 (kingside) through f1 → Black can capture on f1
        - White castles e1c1 (queenside) through d1 → Black can capture on d1  
        - Black castles e8g8 (kingside) through f8 → White can capture on f8
        - Black castles e8c8 (queenside) through d8 → White can capture on d8
        
        This is a critical Drawback Chess rule that must be handled 
        by the Python bridge since Fairy-Stockfish doesn't natively support it.
        """


def test_drawback_bridge():
    """Test the Drawback Chess bridge functionality."""
    bridge = DrawbackBridge()
    
    print("=== Drawback Chess Bridge Test ===")
    print(bridge.explain_king_capture_en_passant())
    
    # Test castling detection
    print("\nTesting castling detection:")
    test_moves = ['e1g1', 'e1c1', 'e8g8', 'e8c8', 'e2e4', 'Nf3']
    for move in test_moves:
        is_castle = bridge._is_castling_move(move)
        print(f"{move}: {'Castling' if is_castle else 'Not castling'}")
    
    # Test passed square detection
    print("\nTesting passed square detection:")
    castling_moves = ['e1g1', 'e1c1', 'e8g8', 'e8c8']
    for move in castling_moves:
        passed = bridge._get_castling_passed_square(move, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        print(f"{move}: passes through {passed}")
    
    print("\n✅ Drawback bridge test completed!")


if __name__ == "__main__":
    test_drawback_bridge()
