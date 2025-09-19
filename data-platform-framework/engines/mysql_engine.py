"""MySQL Engine Factory for Layer 2 Datakits Framework

Provides disposable MySQL database connections for unit testing data objects.
Supports containerized MySQL environments for multi-database testing.
"""

from sqlalchemy.engine import Engine
from sqlmodel import create_engine


def get_connection_url(
    database_name: str,
    user_name: str,
    password: str | None = None,
    host: str = "localhost",
    port: int = 3306,
) -> str:
    """Build MySQL connection URL.

    Args:
        database_name: Name of the database to connect to
        user_name: Database username
        password: Database password
        host: Database host (default: localhost)
        port: Database port (default: 3306)

    Returns:
        MySQL connection URL string
    """
    if password is None:
        password = "test_pass"  # Default for test containers

    # MySQL connection URL format
    return f"mysql+pymysql://{user_name}:{password}@{host}:{port}/{database_name}"


def create_engine_for_test_target(
    database_name: str, engine_config: dict, echo: bool = False
) -> Engine:
    """Create SQLAlchemy engine for a MySQL test database target.

    Args:
        database_name: Name of the test database
        engine_config: Configuration dict with connection details
        echo: Whether to echo SQL statements (useful for debugging)

    Returns:
        SQLAlchemy engine instance

    Example engine_config:
    {
        "type": "mysql",
        "host": "localhost",
        "port": 3306,  # Test container port
        "user": "test_user",
        "password": "test_pass"
    }
    """
    user_name = engine_config.get("user", "root")
    host = engine_config.get("host", "localhost")
    port = engine_config.get("port", 3306)
    password = engine_config.get("password", "test_pass")

    connection_url = get_connection_url(database_name, user_name, password, host, port)
    engine = create_engine(connection_url, echo=echo)
    return engine


# Convenience function for direct usage
def get_engine(
    echo_msgs: bool = True,
    database_name: str = "test",
    user_name: str | None = None,
    password: str | None = None,
    host: str = "localhost",
    port: int = 3306,
) -> Engine:
    """Create MySQL engine with direct parameters.

    For Layer 2, prefer using create_engine_for_test_target() with explicit config.
    """
    if user_name is None:
        user_name = "root"

    if password is None:
        password = "test_pass"

    engine_config = {"host": host, "port": port, "user": user_name, "password": password}

    return create_engine_for_test_target(database_name, engine_config, echo_msgs)
