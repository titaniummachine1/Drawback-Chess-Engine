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
    def get_sensors(fen: str, history_uci: List[str] = None) -> Dict[str, Any]:
        """
        Calculate Drawback-optimized sensors for a position.

        Rules:
        - Side with NO moves loses (zugzwang).
        - Kings can be captured.
        - Check/Pin doesn't restrict movement in this variant.
        """
        board = chess.Board(fen)
        turn = "white" if board.turn == chess.WHITE else "black"

        # Mobility: Crucial for detecting drawbacks like "Knights cannot move"
        legal_moves_count = len(list(board.legal_moves))

        sensors = {
            "mobility": legal_moves_count,
            "is_check": board.is_check(),
            "is_terminal": False,
            "terminal_type": None,
            "turn": turn,
            "halfmove_clock": board.halfmove_clock,
            "fullmove_number": board.fullmove_number,
        }

        # 1. Terminal Deduction (Drawback Rules)
        # Check if king is missing (captured)
        white_king = board.king(chess.WHITE)
        black_king = board.king(chess.BLACK)

        if white_king is None:
            sensors["is_terminal"] = True
            sensors["terminal_type"] = "white_king_captured"
        elif black_king is None:
            sensors["is_terminal"] = True
            sensors["terminal_type"] = "black_king_captured"
        elif legal_moves_count == 0:
            sensors["is_terminal"] = True
            sensors["terminal_type"] = f"{turn}_no_legal_moves"

        # Standard draw conditions still exist (repetition, 50-move)
        if not sensors["is_terminal"]:
            if board.is_repetition(3):
                sensors["is_terminal"] = True
                sensors["terminal_type"] = "repetition"
            elif board.is_fifty_moves():
                sensors["is_terminal"] = True
                sensors["terminal_type"] = "fifty_moves"

        # 2. General Position Sensors (Help AI 'see' patterns)

        # Center Control
        center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        sensors["center_control_own"] = sum(
            1 for sq in center_squares if board.is_attacked_by(board.turn, sq))
        sensors["center_control_opp"] = sum(
            1 for sq in center_squares if board.is_attacked_by(not board.turn, sq))

        # King Safety / Position
        if white_king and black_king:
            sensors["white_king_dist_center"] = abs(chess.square_file(
                white_king) - 3.5) + abs(chess.square_rank(white_king) - 3.5)
            sensors["black_king_dist_center"] = abs(chess.square_file(
                black_king) - 3.5) + abs(chess.square_rank(black_king) - 3.5)

        # 3. History-based sensors
        if history_uci and len(history_uci) > 0:
            # Same piece moved streak
            last_move = chess.Move.from_uci(history_uci[-1])
            # Current square because move is applied
            piece_type = board.piece_type_at(last_move.to_square)

            streak = 1
            for i in range(len(history_uci)-2, -1, -2):  # Look at same side's previous moves
                m = chess.Move.from_uci(history_uci[i])
                # We can't easily know history piece types without complex playback,
                # but we can track if the SQUARE moved from was the same.
                if m.to_square == last_move.from_square:
                    streak += 1
                else:
                    break
            sensors["piece_move_streak"] = streak
        else:
            sensors["piece_move_streak"] = 0

        # 4. Advanced "Smart" Sensors for AI

        # Threat Counts (How many pieces are currently under attack)
        own_pieces = board.piece_map()
        sensors["own_attacked_count"] = sum(1 for (sq, p) in own_pieces.items(
        ) if p.color == board.turn and board.is_attacked_by(not board.turn, sq))
        sensors["opp_attacked_count"] = sum(1 for (sq, p) in own_pieces.items(
        ) if p.color != board.turn and board.is_attacked_by(board.turn, sq))

        # Material Imbalance
        white_val = sum(PIECE_VALUES.get(p.piece_type, 0)
                        for p in board.piece_map().values() if p.color == chess.WHITE)
        black_val = sum(PIECE_VALUES.get(p.piece_type, 0)
                        for p in board.piece_map().values() if p.color == chess.BLACK)
        sensors["material_delta"] = white_val - \
            black_val if board.turn == chess.WHITE else black_val - white_val

        # Piece Diversity (Count of unique piece types left)
        sensors["unique_piece_types"] = len(
            set(p.piece_type for p in board.piece_map().values() if p.color == board.turn))

        # King Neighborhood (Threats near king)
        king_sq = white_king if board.turn == chess.WHITE else black_king
        if king_sq:
            nhood = chess.SquareSet(chess.BB_KING_ATTACKS[king_sq])
            sensors["king_neighbors_attacked"] = sum(
                1 for sq in nhood if board.is_attacked_by(not board.turn, sq))
            sensors["pawn_shield_count"] = sum(1 for sq in nhood if board.piece_type_at(
                sq) == chess.PAWN and board.color_at(sq) == board.turn)
        else:
            sensors["king_neighbors_attacked"] = 0
            sensors["pawn_shield_count"] = 0

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
