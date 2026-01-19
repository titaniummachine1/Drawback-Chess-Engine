"""
Game Interpreter for Drawback Chess.
Provides smart sensors and game state deduction tools for AI training.
"""

import chess
from typing import List, Dict, Any, Optional

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}


class GameInterpreter:
    """Derives complex features (sensors) from raw chess data."""

    @staticmethod
    def get_sensors(fen: str, last_move_uci: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate features for a single position.
        If last_move_uci is provided, it calculates features relative to the move that led to this position.
        """
        board = chess.Board(fen)

        sensors = {
            "is_check": board.is_check(),
            "is_terminal": board.is_checkmate() or board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition(3),
            "terminal_type": None,
            "halfmove_clock": board.halfmove_clock,
            "fullmove_number": board.fullmove_number,
        }

        if sensors["is_terminal"]:
            if board.is_checkmate():
                sensors["terminal_type"] = "checkmate"
            elif board.is_insufficient_material():
                sensors["terminal_type"] = "insufficient_material"
            elif board.is_repetition(3):
                sensors["terminal_type"] = "repetition"
            elif board.is_fifty_moves():
                sensors["terminal_type"] = "fifty_moves"

        return sensors

    @staticmethod
    def analyze_move(prev_fen: str, move_uci: str) -> Dict[str, Any]:
        """
        Analyze a specific move from a previous state.
        Determines captures, checks, and material changes.
        """
        board = chess.Board(prev_fen)
        move = chess.Move.from_uci(move_uci)

        is_capture = board.is_capture(move)
        captured_piece_type = None
        captured_value = 0

        if is_capture:
            # Handle En Passant separately or check destination square piece
            if board.is_en_passant(move):
                captured_piece_type = chess.PAWN
            else:
                dest_piece = board.piece_at(move.to_square)
                if dest_piece:
                    captured_piece_type = dest_piece.piece_type

            captured_value = PIECE_VALUES.get(captured_piece_type, 0)

        # Execute move to see results
        board.push(move)

        return {
            "move": move_uci,
            "is_capture": is_capture,
            "captured_type": captured_piece_type,
            "captured_value": captured_value,
            "is_check": board.is_check(),
            "new_fen": board.fen()
        }

    @staticmethod
    def get_captured_counts(fen: str) -> Dict[str, Dict[str, int]]:
        """
        Calculate total pieces captured by both sides by comparing current board to initial.
        Returns: {'white': {'q': 1, 'n': 0, ...}, 'black': {...}}
        'white' means pieces WHITE HAS CAPTURED (i.e. black pieces missing).
        """
        board = chess.Board(fen)
        # Starting counts
        counts = {
            'P': 8, 'N': 2, 'B': 2, 'R': 2, 'Q': 1,
            'p': 8, 'n': 2, 'b': 2, 'r': 2, 'q': 1
        }

        # Subtract pieces present on board
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if p:
                symbol = p.symbol()
                if symbol != 'K' and symbol != 'k':
                    counts[symbol] -= 1

        # White captures black pieces (lowercase), Black captures white pieces (uppercase)
        return {
            "white": {
                "p": max(0, counts['p']),
                "n": max(0, counts['n']),
                "b": max(0, counts['b']),
                "r": max(0, counts['r']),
                "q": max(0, counts['q']),
            },
            "black": {
                "p": max(0, counts['P']),
                "n": max(0, counts['N']),
                "b": max(0, counts['B']),
                "r": max(0, counts['R']),
                "q": max(0, counts['Q']),
            }
        }
