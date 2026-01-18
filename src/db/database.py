"""
Database Management for Drawback Chess Engine

Handles database connection, initialization, and session management.
"""

import logging
from pathlib import Path
from typing import Optional, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to data/ directory in project root
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "chess_games.db"
        
        self.db_path = Path(db_path)
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection and create tables."""
        # Create SQLite engine with optimizations for chess data
        engine_url = f"sqlite:///{self.db_path}"
        
        self.engine = create_engine(
            engine_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
                "isolation_level": None,
            },
            echo=False,
        )
        
        # Enable foreign key constraints and WAL mode
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create all tables from the minimal models
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def vacuum_database(self):
        """Optimize database size and performance."""
        with self.get_session() as session:
            session.execute("VACUUM")
            session.execute("ANALYZE")
            logger.info("Database vacuumed and analyzed")


# Global database instance
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(db_path: Optional[str] = None) -> DatabaseManager:
    """Initialize the global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    return _db_manager
