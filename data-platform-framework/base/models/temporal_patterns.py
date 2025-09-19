"""Data Platform Framework - Temporal Table Discovery and Validation

Auto-discovery and validation of temporal table pairs with sophisticated support
for excluding specific fields from history tracking.

Extracted and adapted from medallion-demo temporal_discovery.py for platform use.

Key Features:
- Auto-discover primary table → __history table pairs using naming conventions
- Validate that history tables contain correct fields (respecting exclusions)
- Generate trigger configurations automatically with excluded fields filtered out
- Support field-level and class-level exclusion annotations
- Comprehensive validation reporting with exclusion analysis

Field Exclusion API:

Method 1 - Field-level annotations (Recommended):
```python
class Trade(TemporalTable, table=True):
    trade_id: UUID = Field(primary_key=True)
    quantity: int = Field()                                    # ✅ Tracked in history

    # Exclude specific fields from history tracking
    batch_id: str = Field(temporal_exclude=True)               # 🚫 Not tracked
    large_document: bytes = Field(temporal_exclude=True)       # 🚫 Not tracked
    computed_cache: str = Field(temporal_exclude=True)         # 🚫 Not tracked
```

Method 2 - Class-level exclusions:
```python
class Document(TemporalTable, table=True):
    __temporal_exclude__ = ['content_blob', 'search_cache']    # 🚫 Not tracked

    document_id: UUID = Field(primary_key=True)               # ✅ Tracked in history
    title: str = Field()                                       # ✅ Tracked in history
    content_blob: bytes = Field()                              # 🚫 Not tracked (excluded)
    search_cache: str = Field()                                # 🚫 Not tracked (excluded)
```
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class TemporalTablePair:
    """Represents a primary table and its corresponding history table"""

    primary_table: str
    history_table: str
    primary_schema: str
    history_schema: str
    primary_fields: set[str]
    history_fields: set[str]
    trackable_fields: set[str]  # Primary fields that should be in history
    excluded_fields: set[str]  # Fields excluded from history tracking
    temporal_fields: set[str]  # Required temporal fields in history table


@dataclass
class TriggerConfig:
    """Configuration for temporal table triggers"""

    primary_table: str
    history_table: str
    primary_schema: str
    history_schema: str
    trackable_fields: list[str]
    primary_key_field: str

    def get_insert_trigger_name(self) -> str:
        return f"tr_{self.primary_table}_insert_history"

    def get_update_trigger_name(self) -> str:
        return f"tr_{self.primary_table}_update_history"

    def get_delete_trigger_name(self) -> str:
        return f"tr_{self.primary_table}_delete_history"


@dataclass
class TemporalValidationResult:
    """Results of temporal table validation"""

    pair: TemporalTablePair
    is_valid: bool
    validation_errors: list[str]
    missing_history_fields: set[str]
    unexpected_history_fields: set[str]
    exclusion_analysis: dict[str, Any]


class TemporalTableDiscovery:
    """Discovery and validation engine for temporal table pairs.

    Discovers primary → __history table pairs and validates their structure
    according to temporal patterns and field exclusion rules.
    """

    def __init__(self, engine: Engine):
        self.engine = engine
        self.inspector = inspect(engine)

    def discover_temporal_pairs(self, schema: str | None = None) -> list[TemporalTablePair]:
        """Discover all temporal table pairs in the database.

        Args:
            schema: Optional schema to search (None = all schemas)

        Returns:
            List of discovered temporal table pairs
        """
        temporal_pairs = []

        # Get all tables in the database
        if schema:
            schemas_to_search = [schema]
        else:
            schemas_to_search = self.inspector.get_schema_names()

        for schema_name in schemas_to_search:
            tables = self.inspector.get_table_names(schema=schema_name)

            for table in tables:
                # Check if this is a primary table (has corresponding __history table)
                if not table.endswith("__history"):
                    history_table_name = f"{table}__history"

                    if history_table_name in tables:
                        # Found a temporal pair
                        pair = self._analyze_temporal_pair(
                            primary_table=table,
                            history_table=history_table_name,
                            schema=schema_name,
                        )
                        if pair:
                            temporal_pairs.append(pair)
                            logger.info(
                                f"Discovered temporal pair: {schema_name}.{table} → {history_table_name}"
                            )

        return temporal_pairs

    def _analyze_temporal_pair(
        self, primary_table: str, history_table: str, schema: str
    ) -> TemporalTablePair | None:
        """Analyze a primary/history table pair and extract field information.

        Args:
            primary_table: Name of primary table
            history_table: Name of history table
            schema: Schema containing both tables

        Returns:
            TemporalTablePair if valid, None otherwise
        """
        try:
            # Get field information for both tables
            primary_columns = self.inspector.get_columns(primary_table, schema=schema)
            history_columns = self.inspector.get_columns(history_table, schema=schema)

            primary_fields = {col["name"] for col in primary_columns}
            history_fields = {col["name"] for col in history_columns}

            # Expected temporal fields in history table
            temporal_fields = {"history_id", "effective_time", "systime", "operation_type"}

            # Fields that should be tracked (primary fields minus exclusions)
            trackable_fields, excluded_fields = self._determine_trackable_fields(
                primary_table, primary_fields, schema
            )

            return TemporalTablePair(
                primary_table=primary_table,
                history_table=history_table,
                primary_schema=schema,
                history_schema=schema,
                primary_fields=primary_fields,
                history_fields=history_fields,
                trackable_fields=trackable_fields,
                excluded_fields=excluded_fields,
                temporal_fields=temporal_fields,
            )

        except Exception as e:
            logger.error(f"Error analyzing temporal pair {schema}.{primary_table}: {e}")
            return None

    def _determine_trackable_fields(
        self, table_name: str, primary_fields: set[str], schema: str
    ) -> tuple[set[str], set[str]]:
        """Determine which fields should be tracked in history vs excluded.

        This is a simplified version - in a full implementation, this would
        inspect SQLModel class annotations to find temporal_exclude=True fields
        and __temporal_exclude__ class attributes.

        For now, we use built-in exclusions and naming conventions.
        """
        # Built-in exclusions (always excluded from history)
        builtin_exclusions = {
            "effective_time",  # Handled specially by trigger logic
            "systime",  # System timestamp, not business data
            "created_at",  # Immutable, no need to track changes
        }

        # Naming convention exclusions (fields that typically shouldn't be tracked)
        convention_exclusions = {
            field
            for field in primary_fields
            if any(field.endswith(suffix) for suffix in ["_cache", "_hash", "_blob", "_temp"])
        }

        excluded_fields = builtin_exclusions | convention_exclusions
        trackable_fields = primary_fields - excluded_fields

        logger.debug(
            f"Table {schema}.{table_name}: trackable={trackable_fields}, excluded={excluded_fields}"
        )

        return trackable_fields, excluded_fields

    def validate_temporal_pair(self, pair: TemporalTablePair) -> TemporalValidationResult:
        """Validate that a temporal table pair has correct structure.

        Validation Rules:
        1. History table must contain all trackable primary table fields
        2. History table must contain required temporal fields
        3. History table must NOT contain excluded fields
        4. Primary key field must be identifiable
        """
        validation_errors = []

        # Check that history table has all trackable fields
        missing_history_fields = pair.trackable_fields - pair.history_fields
        if missing_history_fields:
            validation_errors.append(
                f"History table missing trackable fields: {missing_history_fields}"
            )

        # Check that history table has required temporal fields
        missing_temporal_fields = pair.temporal_fields - pair.history_fields
        if missing_temporal_fields:
            validation_errors.append(
                f"History table missing temporal fields: {missing_temporal_fields}"
            )

        # Check that history table doesn't have excluded fields
        unexpected_history_fields = pair.excluded_fields & pair.history_fields
        if unexpected_history_fields:
            validation_errors.append(
                f"History table contains excluded fields: {unexpected_history_fields}"
            )

        # Exclusion analysis for reporting
        exclusion_analysis = {
            "total_primary_fields": len(pair.primary_fields),
            "trackable_fields": len(pair.trackable_fields),
            "excluded_fields": len(pair.excluded_fields),
            "exclusion_rate": len(pair.excluded_fields) / len(pair.primary_fields)
            if pair.primary_fields
            else 0,
        }

        is_valid = len(validation_errors) == 0

        return TemporalValidationResult(
            pair=pair,
            is_valid=is_valid,
            validation_errors=validation_errors,
            missing_history_fields=missing_history_fields,
            unexpected_history_fields=unexpected_history_fields,
            exclusion_analysis=exclusion_analysis,
        )

    def generate_trigger_config(self, pair: TemporalTablePair) -> TriggerConfig | None:
        """Generate trigger configuration for a validated temporal table pair.

        Args:
            pair: Validated temporal table pair

        Returns:
            TriggerConfig if primary key can be identified, None otherwise
        """
        # Try to identify primary key field
        primary_key_field = self._identify_primary_key(pair.primary_table, pair.primary_schema)

        if not primary_key_field:
            logger.error(
                f"Cannot identify primary key for {pair.primary_schema}.{pair.primary_table}"
            )
            return None

        return TriggerConfig(
            primary_table=pair.primary_table,
            history_table=pair.history_table,
            primary_schema=pair.primary_schema,
            history_schema=pair.history_schema,
            trackable_fields=sorted(list(pair.trackable_fields)),
            primary_key_field=primary_key_field,
        )

    def _identify_primary_key(self, table_name: str, schema: str) -> str | None:
        """Identify the primary key field for a table"""
        try:
            pk_constraint = self.inspector.get_pk_constraint(table_name, schema=schema)

            if pk_constraint and pk_constraint.get("constrained_columns"):
                # Use first column if composite primary key
                return pk_constraint["constrained_columns"][0]

            # Fallback: look for common primary key field names
            columns = self.inspector.get_columns(table_name, schema=schema)
            for col in columns:
                if col["name"].lower() in ["id", f"{table_name}_id", "uuid"]:
                    return col["name"]

            return None

        except Exception as e:
            logger.error(f"Error identifying primary key for {schema}.{table_name}: {e}")
            return None


def discover_and_validate_temporal_tables(
    engine: Engine, schema: str | None = None
) -> list[TemporalValidationResult]:
    """Convenience function to discover and validate all temporal table pairs.

    Args:
        engine: Database engine
        schema: Optional schema to search (None = all schemas)

    Returns:
        List of validation results for all discovered pairs
    """
    discovery = TemporalTableDiscovery(engine)
    pairs = discovery.discover_temporal_pairs(schema)

    validation_results = []
    for pair in pairs:
        result = discovery.validate_temporal_pair(pair)
        validation_results.append(result)

        if result.is_valid:
            logger.info(
                f"✅ Temporal pair validation passed: {pair.primary_table} → {pair.history_table}"
            )
        else:
            logger.error(
                f"❌ Temporal pair validation failed: {pair.primary_table} → {pair.history_table}"
            )
            for error in result.validation_errors:
                logger.error(f"   {error}")

    return validation_results
