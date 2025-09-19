"""Data Platform Framework

Comprehensive framework library for data platform infrastructure.
Supports Layer 2 component testing and Layer 3 pipeline orchestration.

Built with latest stable versions:
- SQLModel 0.0.25 (Sep 2025)
- psycopg2-binary 2.9.10 (Oct 2024)
- PyMySQL 1.1.1
"""

__version__ = "1.0.0"
__author__ = "Data Platform Team"

# Framework component exports
from . import base, config, engines, utils

# Version information for dependency verification
REQUIRED_VERSIONS = {"sqlmodel": "0.0.25", "psycopg2-binary": "2.9.10", "PyMySQL": "1.1.1"}
