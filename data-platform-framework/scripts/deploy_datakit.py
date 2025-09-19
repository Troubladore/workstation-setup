#!/usr/bin/env python3
"""Layer 2 Datakits Framework - Deploy Datakit to Test Target

CLI tool for deploying datakit data objects to disposable test databases.
Supports multiple database targets for unit test configurations.

Usage:
    python deploy_datakit.py <datakit_path> [options]

Examples:
    # Deploy to fast in-memory SQLite
    python deploy_datakit.py /path/to/bronze-pagila --target sqlite_memory

    # Deploy to PostgreSQL container
    python deploy_datakit.py /path/to/bronze-pagila --target postgres_container

    # Deploy with custom configuration
    python deploy_datakit.py /path/to/bronze-pagila --target-type postgres \\
           --database test_bronze --port 5433
"""

import argparse
import sys
from pathlib import Path

# Add framework to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.targets import (
    create_custom_target,
    get_development_target,
    get_target_config,
    list_available_targets,
)
from utils.deployment import (
    cleanup_test_target,
    configure_logging,
    deploy_data_objects,
    discover_datakit_modules,
    discover_sqlmodel_classes,
    validate_deployment,
)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy datakit data objects to test database targets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Deploy bronze-pagila to in-memory SQLite (fastest):
    %(prog)s /path/to/layer2-datakits/bronze-pagila --target sqlite_memory

  Deploy to PostgreSQL test container:
    %(prog)s /path/to/layer2-datakits/bronze-pagila --target postgres_container

  Custom PostgreSQL configuration:
    %(prog)s /path/to/layer2-datakits/bronze-pagila --target-type postgres \\
             --database test_bronze --host localhost --port 5433

  List available targets:
    %(prog)s --list-targets
        """,
    )

    # Required arguments
    parser.add_argument("datakit_path", nargs="?", help="Path to datakit directory")

    # Target selection (mutually exclusive)
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", help="Use predefined target configuration")
    target_group.add_argument("--target-type", help="Custom target type (postgres, mysql, sqlite)")

    # Custom target options
    parser.add_argument("--database", help="Database name")
    parser.add_argument("--host", help="Database host")
    parser.add_argument("--port", type=int, help="Database port")
    parser.add_argument("--user", help="Database username")
    parser.add_argument("--password", help="Database password")

    # Behavior options
    parser.add_argument(
        "--validate", action="store_true", help="Validate deployment after creation"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up test target after deployment"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    # Information commands
    parser.add_argument(
        "--list-targets", action="store_true", help="List available target configurations"
    )

    args = parser.parse_args()

    # Configure logging
    configure_logging(args.log_level)

    # Handle information commands
    if args.list_targets:
        print("Available test targets:")
        for name, description in list_available_targets().items():
            print(f"  {name:18} - {description}")
        return 0

    # Validate required arguments
    if not args.datakit_path:
        parser.error("datakit_path is required (or use --list-targets)")

    datakit_path = Path(args.datakit_path)
    if not datakit_path.exists():
        print(f"Error: Datakit path does not exist: {datakit_path}")
        return 1

    # Determine target configuration
    try:
        if args.target:
            target_config = get_target_config(args.target)
            print(f"Using predefined target: {args.target}")
        elif args.target_type:
            target_config = create_custom_target(
                args.target_type,
                args.database or "test_datakit",
                host=args.host,
                port=args.port,
                user=args.user,
                password=args.password,
            )
            print(f"Using custom {args.target_type} target")
        else:
            # Default to development target
            target_config = get_development_target()
            print("Using default development target (postgres_local)")

    except (KeyError, ValueError) as e:
        print(f"Error: {e}")
        return 1

    print(f"Target: {target_config['type']} database '{target_config['database']}'")

    # Deploy datakit
    try:
        print(f"Discovering data objects in {datakit_path}")
        modules = discover_datakit_modules(str(datakit_path))

        if not modules:
            print("Warning: No Python modules found in datakit")
            return 0

        table_classes = discover_sqlmodel_classes(modules)

        if not table_classes:
            print("Warning: No SQLModel table classes found")
            return 0

        print(f"Found {len(table_classes)} data objects to deploy")

        # Deploy to target
        print("Deploying data objects...")
        result = deploy_data_objects(table_classes, target_config)

        if result["success"]:
            print(f"✅ Successfully deployed {result['tables_deployed']} tables")
        else:
            print(f"❌ Deployment failed: {result['error']}")
            return 1

        # Optional validation
        if args.validate:
            print("Validating deployment...")
            validation_result = validate_deployment(table_classes, target_config)

            if validation_result["success"]:
                print(f"✅ All {validation_result['total_expected']} tables validated")
            else:
                print(f"❌ Validation failed: {validation_result.get('error', 'Unknown error')}")
                if validation_result.get("missing_tables"):
                    print(f"Missing tables: {validation_result['missing_tables']}")
                return 1

        # Optional cleanup
        if args.cleanup:
            print("Cleaning up test target...")
            cleanup_result = cleanup_test_target(target_config)
            if cleanup_result["success"]:
                print("✅ Test target cleaned up")
            else:
                print(f"⚠️  Cleanup warning: {cleanup_result.get('error', 'Unknown error')}")

        print("🎉 Datakit deployment completed successfully!")
        return 0

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
