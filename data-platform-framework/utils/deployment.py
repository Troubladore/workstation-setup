"""Layer 2 Datakits Framework - Data Object Deployment Utilities

Core utilities for deploying data objects to disposable test databases.
Supports dynamic discovery, multi-database targeting, and validation.
"""

import importlib
import importlib.util
import logging
import os
import sys
from types import ModuleType
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel

from engines.mysql_engine import create_engine_for_test_target as create_mysql_engine
from engines.postgres_engine import create_engine_for_test_target as create_postgres_engine
from engines.sqlite_engine import create_engine_for_test_target as create_sqlite_engine

logger = logging.getLogger(__name__)


def configure_logging(log_level: str = "INFO"):
    """Configure logging for the deployment framework.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    if hasattr(configure_logging, "has_run"):
        return

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Clear existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure logging with UTF-8 support
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # Configure encoding for cross-platform compatibility
    if hasattr(handler.stream, "reconfigure"):
        try:
            handler.stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
        handlers=[handler],
    )

    configure_logging.has_run = True
    logger.info(f"Logging configured at level: {log_level}")


def create_engine_for_target(target_config: dict[str, Any]) -> Engine:
    """Create database engine for specified target configuration.

    This is the main factory for Layer 2 data object testing.
    Supports multiple database types for unit test configurations.

    Args:
        target_config: Database target configuration

    Returns:
        SQLAlchemy engine instance

    Example target_config:
    {
        "type": "postgres",
        "database": "test_datakit_bronze",
        "host": "localhost",
        "port": 5433,
        "user": "test_user",
        "password": "test_pass",
        "conn_method": "password"
    }
    """
    db_type = target_config.get("type", "sqlite")
    database_name = target_config.get("database", "test")
    echo = target_config.get("echo", False)

    if db_type == "postgres":
        return create_postgres_engine(database_name, target_config, echo)
    elif db_type == "mysql":
        return create_mysql_engine(database_name, target_config, echo)
    elif db_type == "sqlite":
        return create_sqlite_engine(database_name, target_config, echo)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def discover_datakit_modules(datakit_path: str) -> list[ModuleType]:
    """Discover Python modules in a datakit directory.

    Args:
        datakit_path: Path to datakit directory

    Returns:
        List of imported Python modules
    """
    modules = []

    if not os.path.exists(datakit_path):
        logger.warning(f"Datakit path not found: {datakit_path}")
        return modules

    # Add datakit path to Python path for imports
    if datakit_path not in sys.path:
        sys.path.insert(0, datakit_path)

    logger.debug(f"Discovering modules in {datakit_path}")

    for root, _, files in os.walk(datakit_path):
        for filename in files:
            if filename.endswith(".py") and filename != "__init__.py":
                # Calculate relative path for module name
                rel_path = os.path.relpath(root, datakit_path)
                if rel_path == ".":
                    module_name = filename[:-3]
                else:
                    module_name = f"{rel_path.replace(os.sep, '.')}.{filename[:-3]}"

                try:
                    module = importlib.import_module(module_name)
                    modules.append(module)
                    logger.debug(f"Imported module: {module_name}")
                except ImportError as e:
                    logger.warning(f"Could not import {module_name}: {e}")

    return modules


def discover_sqlmodel_classes(modules: list[ModuleType]) -> list[type[SQLModel]]:
    """Discover SQLModel table classes from imported modules.

    Args:
        modules: List of Python modules to examine

    Returns:
        List of SQLModel table classes
    """
    table_classes = []

    logger.info(f"Examining {len(modules)} modules for SQLModel classes")

    for i, module in enumerate(modules):
        module_name = getattr(module, "__name__", f"unknown_module_{i}")
        logger.debug(f"Module {i+1}/{len(modules)}: {module_name}")

        for name, obj in module.__dict__.items():
            if _is_table_class(obj):
                table_classes.append(obj)
                logger.info(f"Found table class: {name} -> {obj.__tablename__}")

    logger.info(f"Discovered {len(table_classes)} SQLModel table classes")
    return table_classes


def _is_table_class(obj) -> bool:
    """Check if object is a SQLModel table class.

    Args:
        obj: Object to check

    Returns:
        True if object is a table class
    """
    return (
        isinstance(obj, type)
        and issubclass(obj, SQLModel)
        and hasattr(obj, "__tablename__")
        and not obj.__dict__.get("__abstract__", False)
    )


def deploy_data_objects(
    table_classes: list[type[SQLModel]], target_config: dict[str, Any], create_database: bool = True
) -> dict[str, Any]:
    """Deploy data objects (tables) to target database.

    This is the core deployment function for Layer 2 unit testing.
    Creates tables in disposable database targets.

    Args:
        table_classes: List of SQLModel table classes to deploy
        target_config: Database target configuration
        create_database: Whether to create database/schema first

    Returns:
        Deployment result dictionary
    """
    logger.info(f"Deploying {len(table_classes)} data objects to {target_config['type']} target")

    try:
        # Create engine for target
        engine = create_engine_for_target(target_config)

        # Test connection
        with engine.connect():
            logger.info(f"Successfully connected to {target_config['type']} target")

        # Create database objects
        if create_database:
            # Create all table metadata
            SQLModel.metadata.create_all(engine, tables=[cls.__table__ for cls in table_classes])

        logger.info(f"Successfully deployed {len(table_classes)} tables")

        return {
            "success": True,
            "tables_deployed": len(table_classes),
            "target_type": target_config["type"],
            "database": target_config.get("database", "unknown"),
        }

    except Exception as e:
        logger.error(f"Failed to deploy data objects: {e}")
        return {
            "success": False,
            "error": str(e),
            "target_type": target_config.get("type", "unknown"),
        }


def validate_deployment(
    table_classes: list[type[SQLModel]], target_config: dict[str, Any]
) -> dict[str, Any]:
    """Validate that data objects were deployed successfully.

    Args:
        table_classes: List of table classes that should exist
        target_config: Database target configuration

    Returns:
        Validation result dictionary
    """
    logger.info(f"Validating deployment of {len(table_classes)} tables")

    try:
        engine = create_engine_for_target(target_config)

        with engine.connect() as conn:
            # Check that each table exists
            missing_tables = []
            existing_tables = []

            for table_class in table_classes:
                table_name = table_class.__tablename__

                # Use SQLAlchemy reflection to check table existence
                try:
                    conn.execute(f"SELECT 1 FROM {table_name} LIMIT 0")
                    existing_tables.append(table_name)
                    logger.debug(f"Table exists: {table_name}")
                except Exception:
                    missing_tables.append(table_name)
                    logger.warning(f"Table missing: {table_name}")

            success = len(missing_tables) == 0

            return {
                "success": success,
                "existing_tables": existing_tables,
                "missing_tables": missing_tables,
                "total_expected": len(table_classes),
            }

    except Exception as e:
        logger.error(f"Failed to validate deployment: {e}")
        return {"success": False, "error": str(e)}


def cleanup_test_target(target_config: dict[str, Any]) -> dict[str, Any]:
    """Clean up disposable test database target.

    Args:
        target_config: Database target configuration

    Returns:
        Cleanup result dictionary
    """
    logger.info(f"Cleaning up {target_config['type']} test target")

    try:
        if target_config["type"] == "sqlite":
            from engines.sqlite_engine import cleanup_test_databases

            cleanup_test_databases(target_config.get("temp_dir"))
        else:
            # For containerized databases, typically handled by container lifecycle
            logger.info(f"Cleanup for {target_config['type']} handled by container lifecycle")

        return {"success": True, "message": "Test target cleaned up"}

    except Exception as e:
        logger.error(f"Failed to cleanup test target: {e}")
        return {"success": False, "error": str(e)}
