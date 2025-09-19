#!/usr/bin/env python3
"""Data Platform Framework Test Runner

Comprehensive test execution with detailed reporting.
Handles unit tests, integration tests, and framework validation.
"""

import sys
import unittest
from pathlib import Path

# Add the framework to the Python path
framework_root = Path(__file__).parent.parent
sys.path.insert(0, str(framework_root))


def discover_and_run_tests(test_dir: str = "unit", verbose: bool = True) -> bool:
    """Discover and run all tests in the specified directory.

    Args:
        test_dir: Directory to search for tests ("unit" or "integration")
        verbose: Whether to show verbose output

    Returns:
        True if all tests passed, False otherwise
    """
    print(f"\n🧪 Running {test_dir} tests...\n")

    # Set up test discovery
    test_path = framework_root / "tests" / test_dir
    if not test_path.exists():
        print(f"❌ Test directory not found: {test_path}")
        return False

    # Discover tests
    loader = unittest.TestLoader()
    start_dir = str(test_path)
    pattern = "test_*.py"

    try:
        suite = loader.discover(start_dir, pattern=pattern, top_level_dir=str(framework_root))
    except Exception as e:
        print(f"❌ Error discovering tests: {e}")
        return False

    # Run tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # Report results
    if result.wasSuccessful():
        print(f"✅ All {test_dir} tests passed!")
        return True
    else:
        print(f"❌ {test_dir} tests failed:")
        print(f"  - Failures: {len(result.failures)}")
        print(f"  - Errors: {len(result.errors)}")
        return False


def check_framework_dependencies() -> dict[str, bool]:
    """Check if required dependencies are available."""
    dependencies = {"sqlmodel": False, "sqlalchemy": False, "psycopg2": False, "pymysql": False}

    for dep in dependencies:
        try:
            __import__(dep)
            dependencies[dep] = True
        except ImportError:
            dependencies[dep] = False

    return dependencies


def main():
    """Main test execution."""
    print("🏗️  Data Platform Framework Test Suite")
    print("=" * 50)

    # Check dependencies
    deps = check_framework_dependencies()
    print("\n📦 Dependencies Status:")
    for dep, available in deps.items():
        status = "✅" if available else "❌"
        print(f"  {status} {dep}")

    # Warn about missing dependencies
    missing_deps = [dep for dep, available in deps.items() if not available]
    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("   Some tests may be skipped or fail.")
        if "sqlalchemy" in missing_deps or "sqlmodel" in missing_deps:
            print("   Core dependencies missing - tests will likely fail.")
            return False

    # Run unit tests
    unit_success = discover_and_run_tests("unit")

    # Run integration tests if dependencies are available
    integration_success = True
    if all(deps[dep] for dep in ["sqlalchemy", "sqlmodel"]):
        integration_success = discover_and_run_tests("integration")
    else:
        print("\n⚠️  Skipping integration tests - missing database dependencies")

    # Final report
    print("\n" + "=" * 50)
    if unit_success and integration_success:
        print("🎉 All framework tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
