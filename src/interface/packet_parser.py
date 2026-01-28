"""
Packet Parser for Drawback Chess WebSocket Traffic

Translates raw site packets into structured data for the AI and Storage.
"""

import json
from typing import Optional, Dict, List, Any


class PacketParser:
    """Parses Network traffic and JSON responses from drawbackchess.com."""

    @staticmethod
    def parse_game_state(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract board, legal moves, and drawbacks from the game state JSON."""
        game_data = data.get("game", {})

        # 1. Extract Handicaps (Rules)
        handicaps = game_data.get("handicaps", {})
        white_rule = handicaps.get("white")
        black_rule = handicaps.get("black")

        # 2. Extract Legal Moves and convert to UCI (e.g., {"E2": [{"stop": "E4"}]} -> ["e2e4"])
        turn = game_data.get("turn")
        legal_premoves = game_data.get("legal_premoves", {})
        raw_moves = legal_premoves.get(turn, {}) if turn else {}
        uci_moves = []
        for start_sq, destinations in raw_moves.items():
            for move_obj in destinations:
                stop_sq = move_obj.get("stop")
                if start_sq and stop_sq:
                    uci_moves.append(f"{start_sq}{stop_sq}".lower())

        # 3. Game Context
        revealed = game_data.get("revealedHandicaps", {})

        return {
            "type": "game_state",
            "game_id": game_data.get("id"),
            "white_drawback": white_rule,
            "black_drawback": black_rule,
            "revealed_drawbacks": revealed,  # Added this field
            "legal_moves": uci_moves,
            "board": game_data.get("board"),
            "turn": game_data.get("turn"),
            "ply": game_data.get("ply")
        }

    @staticmethod
    def parse_move_request(payload: str) -> Optional[Dict[str, Any]]:
        """Parse an outgoing move request (What the player actually played)."""
        try:
            data = json.loads(payload)
            if "start" in data and "stop" in data:
                return {
                    "type": "local_move",
                    "uci": (data["start"] + data["stop"]).lower(),
                    "game_id": data.get("id"),
                    "color": data.get("color")
                }
        except:
            return None
        return None

    @staticmethod
    def parse_game_result(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract game result when a game ends."""
        if "winner" in data or "result" in data:
            return {
                "type": "game_over",
                "game_id": data.get("id"),
                "result": data.get("result"),  # e.g., 'white_win', 'draw'
                "winner": data.get("winner")
            }
        return None

    @staticmethod
    def board_to_fen(board: Dict[str, Any], turn: str) -> str:
        """
        Convert the site's board dictionary into a FEN-like string.
        Format: {"A1": {"color": "white", "piece": "rook"}, ...}
        """
        rows = []
        for rank in range(8, 0, -1):
            row = ""
            empty = 0
            for file_char in "ABCDEFGH":
                sq = f"{file_char}{rank}"
                item = board.get(sq)
                if item:
                    if empty > 0:
                        row += str(empty)
                        empty = 0

                    p = item["piece"]
                    char = 'p' if p == 'pawn' else p[0]
                    if p == 'knight':
                        char = 'n'

                    char = char.upper(
                    ) if item["color"] == "white" else char.lower()
                    row += char
                else:
                    empty += 1
            if empty > 0:
                row += str(empty)
            rows.append(row)

        fen_base = "/".join(rows)
        return f"{fen_base} {turn[0]} - - 0 1"
