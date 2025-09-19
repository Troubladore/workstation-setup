"""PostgreSQL Engine Factory for Layer 2 Datakits Framework

Provides disposable PostgreSQL database connections for unit testing data objects.
Supports multiple connection methods and containerized environments.
"""

import getpass
import os
import platform
import subprocess

from sqlalchemy.engine import Engine
from sqlmodel import create_engine


def get_connection_url(
    database_name: str,
    conn_method: str,
    user_name: str,
    password: str | None = None,
    host: str = "localhost",
    port: int = 5432,
) -> str:
    """Build PostgreSQL connection URL for different authentication methods.

    Args:
        database_name: Name of the database to connect to
        conn_method: Connection method ('password', 'tcp', 'socket')
        user_name: Database username
        password: Database password (for 'password' method)
        host: Database host (default: localhost)
        port: Database port (default: 5432)

    Returns:
        PostgreSQL connection URL string
    """
    if conn_method == "password":
        if password is None:
            password = "password"  # Default for test containers
        return f"postgresql://{user_name}:{password}@{host}:{port}/{database_name}"

    elif conn_method == "tcp":
        # Trusted TCP connections (for containerized tests)
        return f"postgresql://{user_name}@{host}:{port}/{database_name}?gssencmode=disable"

    elif conn_method == "socket":
        # Unix domain socket connections (fastest for local testing)
        return f"postgresql://{user_name}@/{database_name}?host=/var/run/postgresql"

    else:
        raise ValueError(f"Invalid connection method: {conn_method}")


def find_postgres_socket_dir(port: int = 5432) -> str | None:
    """Find PostgreSQL unix socket directory.

    Args:
        port: PostgreSQL port number

    Returns:
        Socket directory path or None if not found
    """
    # Skip socket detection on Windows
    if platform.system() == "Windows":
        return None

    # Try default socket locations
    default_dirs = ["/var/run/postgresql", "/tmp"]
    for dir_path in default_dirs:
        socket_path = os.path.join(dir_path, f".s.PGSQL.{port}")
        if os.path.exists(socket_path):
            return dir_path

    # Try using ss command to find active sockets
    try:
        result = subprocess.run(
            ["ss", "-x", "state", "listening"],
            capture_output=True,
            text=True,
            check=True,
        )

        for line in result.stdout.splitlines():
            if f"s.PGSQL.{port}" in line:
                socket_path = line.split()[-1]
                return os.path.dirname(socket_path)

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # ss not available or failed

    return None


def create_engine_for_test_target(
    database_name: str, engine_config: dict, echo: bool = False
) -> Engine:
    """Create SQLAlchemy engine for a test database target.

    This is the main factory function for Layer 2 unit testing.
    Creates disposable database connections for testing data objects.

    Args:
        database_name: Name of the test database
        engine_config: Configuration dict with connection details
        echo: Whether to echo SQL statements (useful for debugging)

    Returns:
        SQLAlchemy engine instance

    Example engine_config:
    {
        "type": "postgres",
        "host": "localhost",
        "port": 5433,  # Test container port
        "user": "test_user",
        "password": "test_pass",
        "conn_method": "password"
    }
    """
    user_name = engine_config.get("user", getpass.getuser())
    host = engine_config.get("host", "localhost")
    port = engine_config.get("port", 5432)
    conn_method = engine_config.get("conn_method", "tcp")  # Default to TCP for containers
    password = engine_config.get("password")

    if conn_method == "socket":
        socket_path = find_postgres_socket_dir(port)
        if socket_path is None:
            # Fallback to TCP connection
            print(f"Socket path not found for port {port}, falling back to TCP")
            connection_url = get_connection_url(
                database_name, "tcp", user_name, password, host, port
            )
        else:
            connection_url = (
                f"postgresql+psycopg2://{user_name}@localhost/{database_name}?host={socket_path}"
            )
    else:
        connection_url = get_connection_url(
            database_name, conn_method, user_name, password, host, port
        )

    engine = create_engine(connection_url, echo=echo)
    return engine


# Convenience function matching medallion-demo pattern
def get_engine(
    echo_msgs: bool = True,
    database_name: str = "postgres",
    conn_method: str = "socket",
    user_name: str | None = None,
    host: str = "localhost",
    port: int = 5432,
) -> Engine:
    """Legacy interface matching medallion-demo pattern.

    For Layer 2, prefer using create_engine_for_test_target() with explicit config.
    """
    if user_name is None:
        user_name = getpass.getuser()

    engine_config = {"host": host, "port": port, "user": user_name, "conn_method": conn_method}

    return create_engine_for_test_target(database_name, engine_config, echo_msgs)
