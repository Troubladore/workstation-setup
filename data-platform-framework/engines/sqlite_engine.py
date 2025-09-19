"""SQLite Engine Factory for Layer 2 Datakits Framework

Provides lightweight SQLite database connections for fast unit testing.
Ideal for CI/CD environments and rapid data object validation.
"""

import os
import tempfile

from sqlalchemy.engine import Engine
from sqlmodel import create_engine


def get_sqlite_file_path(db_name: str, temp_dir: str | None = None) -> str:
    """Get SQLite file path for test database.

    Args:
        db_name: Database name (will become sqlite_<name>.db)
        temp_dir: Optional temporary directory (uses system temp if not provided)

    Returns:
        Full path to SQLite database file
    """
    sqlite_filename = f"sqlite_{db_name}.db"

    if temp_dir:
        # Use provided temporary directory
        os.makedirs(temp_dir, exist_ok=True)
        return os.path.join(temp_dir, sqlite_filename)
    else:
        # Use system temporary directory for truly disposable tests
        return os.path.join(tempfile.gettempdir(), "datakits_test", sqlite_filename)


def get_connection_url(db_name: str, in_memory: bool = False, temp_dir: str | None = None) -> str:
    """Build SQLite connection URL.

    Args:
        db_name: Database name
        in_memory: If True, create in-memory database (fastest)
        temp_dir: Optional temporary directory for file-based databases

    Returns:
        SQLite connection URL string
    """
    if in_memory:
        return "sqlite://"  # In-memory database
    else:
        sqlite_file_path = get_sqlite_file_path(db_name, temp_dir)
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(sqlite_file_path), exist_ok=True)
        return f"sqlite:///{sqlite_file_path}"


def create_engine_for_test_target(
    database_name: str, engine_config: dict, echo: bool = False
) -> Engine:
    """Create SQLAlchemy engine for a SQLite test database target.

    Args:
        database_name: Name of the test database
        engine_config: Configuration dict with connection details
        echo: Whether to echo SQL statements (useful for debugging)

    Returns:
        SQLAlchemy engine instance

    Example engine_config:
    {
        "type": "sqlite",
        "in_memory": true,        # For fastest tests
        "temp_dir": "/tmp/tests"  # Optional: specific temp location
    }
    """
    in_memory = engine_config.get("in_memory", False)
    temp_dir = engine_config.get("temp_dir")

    connection_url = get_connection_url(database_name, in_memory, temp_dir)
    engine = create_engine(connection_url, echo=echo)
    return engine


# Convenience function for direct usage
def get_engine(
    echo_msgs: bool = True,
    db_name: str = "test",
    in_memory: bool = False,
) -> Engine:
    """Create SQLite engine with direct parameters.

    Args:
        echo_msgs: Whether to echo SQL statements
        db_name: Database name
        in_memory: If True, create in-memory database (fastest for tests)

    Returns:
        SQLAlchemy engine instance
    """
    engine_config = {"in_memory": in_memory}

    return create_engine_for_test_target(db_name, engine_config, echo_msgs)


def cleanup_test_databases(temp_dir: str | None = None):
    """Clean up SQLite test database files.

    Args:
        temp_dir: Optional temp directory to clean (cleans default if not provided)
    """
    if temp_dir:
        cleanup_dir = temp_dir
    else:
        cleanup_dir = os.path.join(tempfile.gettempdir(), "datakits_test")

    if os.path.exists(cleanup_dir):
        import shutil

        shutil.rmtree(cleanup_dir)
        print(f"Cleaned up SQLite test databases in {cleanup_dir}")
