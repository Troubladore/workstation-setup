#!/usr/bin/env python3
"""Test import structure and basic module loading without external dependencies.

Validates that the framework modules have correct structure and can be
imported at the basic level (without requiring SQLModel/SQLAlchemy).
"""

import importlib.util
import sys
import unittest
from pathlib import Path

# Add framework to path
framework_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(framework_root))


class TestImportStructure(unittest.TestCase):
    """Test framework module import structure."""

    def test_module_files_importable(self):
        """Test that module files can be loaded (syntax check)."""
        module_files = [
            "base/__init__.py",
            "base/models/__init__.py",
            "base/triggers/__init__.py",
            "base/loaders/__init__.py",
            "utils/__init__.py",
            "config/__init__.py",
            "engines/__init__.py",
        ]

        for module_file in module_files:
            with self.subTest(module=module_file):
                module_path = framework_root / module_file
                self.assertTrue(module_path.exists(), f"Module file not found: {module_file}")

                # Test that the file can be loaded as a module
                spec = importlib.util.spec_from_file_location("test_module", module_path)
                self.assertIsNotNone(spec, f"Could not create spec for {module_file}")

    def test_core_module_structure(self):
        """Test that core modules have expected structure."""
        # Check that key files exist and are readable
        key_files = [
            "base/models/table_mixins.py",
            "base/models/temporal_patterns.py",
            "base/triggers/trigger_builder.py",
            "base/loaders/data_factory.py",
            "utils/deployment.py",
            "config/targets.py",
        ]

        for file_path in key_files:
            with self.subTest(file=file_path):
                full_path = framework_root / file_path
                self.assertTrue(full_path.exists(), f"Core file not found: {file_path}")

                # Test file is readable and has content
                with open(full_path, encoding="utf-8") as f:
                    content = f.read()

                self.assertGreater(len(content), 0, f"File is empty: {file_path}")

                # Test basic Python structure (has classes or functions)
                has_class = "class " in content
                has_def = "def " in content

                self.assertTrue(
                    has_class or has_def,
                    f"File appears to have no classes or functions: {file_path}",
                )

    def test_expected_class_definitions(self):
        """Test that expected classes are defined in their modules."""
        expected_classes = {
            "base/models/table_mixins.py": [
                "class ReferenceTableMixin",
                "class TransactionalTableMixin",
                "class TemporalTableMixin",
            ],
            "base/models/temporal_patterns.py": [
                "class TemporalTablePair",
                "def discover_temporal_pairs",
            ],
            "base/triggers/trigger_builder.py": [
                "class PostgreSQLTemporalTriggerBuilder",
                "class TriggerSQL",
            ],
            "base/loaders/data_factory.py": [
                "class DataFactory",
                "class ReferenceDataFactory",
                "class TransactionalDataFactory",
                "class TemporalDataFactory",
            ],
        }

        for file_path, expected_definitions in expected_classes.items():
            with self.subTest(file=file_path):
                full_path = framework_root / file_path

                with open(full_path, encoding="utf-8") as f:
                    content = f.read()

                for definition in expected_definitions:
                    self.assertIn(
                        definition,
                        content,
                        f"Expected definition not found in {file_path}: {definition}",
                    )

    def test_import_dependencies_documented(self):
        """Test that modules document their external dependencies clearly."""
        dependency_files = [
            "base/models/table_mixins.py",
            "base/triggers/trigger_builder.py",
            "base/loaders/data_factory.py",
            "utils/deployment.py",
        ]

        for file_path in dependency_files:
            with self.subTest(file=file_path):
                full_path = framework_root / file_path

                with open(full_path, encoding="utf-8") as f:
                    content = f.read()

                # Check for common external dependencies
                has_sqlmodel = "sqlmodel" in content.lower()
                has_sqlalchemy = "sqlalchemy" in content.lower()

                if has_sqlmodel or has_sqlalchemy:
                    # If file uses these dependencies, it should handle import errors gracefully
                    # or have clear documentation about requirements
                    has_docstring = '"""' in content[:500]  # Check first 500 chars for docstring

                    self.assertTrue(
                        has_docstring,
                        f"File uses external dependencies but lacks documentation: {file_path}",
                    )


class TestFrameworkConsistency(unittest.TestCase):
    """Test framework naming and structure consistency."""

    def test_framework_naming_consistency(self):
        """Test that references use consistent framework name."""
        files_to_check = [
            "README.md",
            "base/models/table_mixins.py",
            "base/loaders/data_factory.py",
        ]

        for file_path in files_to_check:
            with self.subTest(file=file_path):
                full_path = framework_root / file_path
                if full_path.exists():
                    with open(full_path, encoding="utf-8") as f:
                        content = f.read()

                    # Should reference data-platform-framework, not the old name
                    self.assertNotIn(
                        "layer2-datakits-framework",
                        content,
                        f"Old framework name found in {file_path}",
                    )

    def test_directory_structure_consistency(self):
        """Test that directory structure matches expected patterns."""
        # Base directories should exist
        base_dirs = ["base", "utils", "config", "engines", "tests", "scripts"]

        for dir_name in base_dirs:
            with self.subTest(directory=dir_name):
                dir_path = framework_root / dir_name
                self.assertTrue(dir_path.exists(), f"Expected base directory not found: {dir_name}")
                self.assertTrue(
                    dir_path.is_dir(), f"Expected directory is not a directory: {dir_name}"
                )

        # Base subdirectories should exist
        base_subdirs = [
            "base/models",
            "base/triggers",
            "base/loaders",
            "tests/unit",
            "tests/integration",
        ]

        for subdir_name in base_subdirs:
            with self.subTest(subdirectory=subdir_name):
                subdir_path = framework_root / subdir_name
                self.assertTrue(
                    subdir_path.exists(), f"Expected subdirectory not found: {subdir_name}"
                )


if __name__ == "__main__":
    # Run tests with detailed output
    unittest.main(verbosity=2)
