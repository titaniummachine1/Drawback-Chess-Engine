"""
Simple script to check the contents of the local database.
"""
from src.db.database import get_database
from src.db.models import Game, Position
from sqlalchemy import func


def check_stats():
    db = get_database()
    with db.get_session() as session:
        game_count = session.query(Game).count()
        pos_count = session.query(Position).count()

        print(f"--- Database Stats ---")
        print(f"Total Games: {game_count}")
        print(f"Total Positions: {pos_count}")

        if game_count > 0:
            print(f"\nLast 5 Games:")
            games = session.query(Game).order_by(
                Game.created_at.desc()).limit(5).all()
            for g in games:
                print(
                    f"- {g.uuid}: White='{g.white_drawback}', Black='{g.black_drawback}'")

        if pos_count > 0:
            print(f"\nLast 5 Positions:")
            positions = session.query(Position).order_by(
                Position.created_at.desc()).limit(5).all()
            for p in positions:
                move = p.move_uci or "N/A"
                print(f"- Game {p.game_id}, Ply {p.move_number}, Move: {move}")
                print(f"  Moves: {len(p.get_legal_moves())} available")


if __name__ == "__main__":
    check_stats()
