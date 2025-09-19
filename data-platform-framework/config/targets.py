"""Layer 2 Datakits Framework - Test Target Configurations

Defines standard test database targets for unit testing data objects.
Supports multiple database types and connection configurations.
"""

from typing import Any

# Default test target configurations
DEFAULT_TARGETS = {
    "sqlite_memory": {
        "type": "sqlite",
        "database": "test_datakit",
        "in_memory": True,
        "echo": False,
        "description": "Fast in-memory SQLite for unit tests",
    },
    "sqlite_file": {
        "type": "sqlite",
        "database": "test_datakit",
        "in_memory": False,
        "temp_dir": "/tmp/datakits_test",
        "echo": False,
        "description": "File-based SQLite for persistent tests",
    },
    "postgres_container": {
        "type": "postgres",
        "database": "test_datakit",
        "host": "localhost",
        "port": 5433,  # Non-standard port for test container
        "user": "postgres",
        "password": "postgres",
        "conn_method": "password",
        "echo": False,
        "description": "PostgreSQL container for integration tests",
    },
    "postgres_local": {
        "type": "postgres",
        "database": "test_datakit",
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "conn_method": "socket",
        "echo": False,
        "description": "Local PostgreSQL via unix socket",
    },
    "mysql_container": {
        "type": "mysql",
        "database": "test_datakit",
        "host": "localhost",
        "port": 3307,  # Non-standard port for test container
        "user": "root",
        "password": "test_pass",
        "echo": False,
        "description": "MySQL container for cross-database tests",
    },
}


def get_target_config(target_name: str) -> dict[str, Any]:
    """Get configuration for a named test target.

    Args:
        target_name: Name of the test target configuration

    Returns:
        Target configuration dictionary

    Raises:
        KeyError: If target_name is not found
    """
    if target_name not in DEFAULT_TARGETS:
        available = list(DEFAULT_TARGETS.keys())
        raise KeyError(f"Unknown target '{target_name}'. Available: {available}")

    return DEFAULT_TARGETS[target_name].copy()


def list_available_targets() -> dict[str, str]:
    """List all available test targets with descriptions.

    Returns:
        Dictionary mapping target names to descriptions
    """
    return {name: config["description"] for name, config in DEFAULT_TARGETS.items()}


def create_custom_target(target_type: str, database: str, **kwargs) -> dict[str, Any]:
    """Create a custom test target configuration.

    Args:
        target_type: Database type (postgres, mysql, sqlite)
        database: Database name
        **kwargs: Additional configuration parameters

    Returns:
        Custom target configuration
    """
    config = {"type": target_type, "database": database, "echo": kwargs.get("echo", False)}

    # Add type-specific defaults
    if target_type == "postgres":
        config.update(
            {
                "host": kwargs.get("host", "localhost"),
                "port": kwargs.get("port", 5432),
                "user": kwargs.get("user", "postgres"),
                "conn_method": kwargs.get("conn_method", "tcp"),
            }
        )
        if "password" in kwargs:
            config["password"] = kwargs["password"]

    elif target_type == "mysql":
        config.update(
            {
                "host": kwargs.get("host", "localhost"),
                "port": kwargs.get("port", 3306),
                "user": kwargs.get("user", "root"),
                "password": kwargs.get("password", "test_pass"),
            }
        )

    elif target_type == "sqlite":
        config.update({"in_memory": kwargs.get("in_memory", True)})
        if "temp_dir" in kwargs:
            config["temp_dir"] = kwargs["temp_dir"]

    else:
        raise ValueError(f"Unsupported target type: {target_type}")

    return config


# Environment-specific overrides
def get_ci_target() -> dict[str, Any]:
    """Get target configuration optimized for CI/CD environments."""
    return get_target_config("sqlite_memory")


def get_development_target() -> dict[str, Any]:
    """Get target configuration for local development."""
    return get_target_config("postgres_local")


def get_integration_target() -> dict[str, Any]:
    """Get target configuration for integration testing."""
    return get_target_config("postgres_container")
