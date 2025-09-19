"""Data Platform Framework - Temporal Trigger Builder

Generates PostgreSQL triggers for temporal table pairs (current + history).
Creates INSERT, UPDATE, DELETE triggers that automatically maintain history tables.

Key Features:
- Automatic history record creation on primary table changes
- Field exclusion support (respects temporal_exclude annotations)
- Comprehensive audit trail with operation_type tracking
- Optimized SQL generation for performance
- Support for custom effective_time handling

Generated Triggers:
1. INSERT: Creates history record when new primary record inserted
2. UPDATE: Creates history record when primary record modified
3. DELETE: Creates history record when primary record deleted

History Table Structure:
- All trackable fields from primary table
- history_id: UUID primary key for history records
- effective_time: Business effective time (from primary or current timestamp)
- systime: System timestamp when history record created
- operation_type: 'INSERT', 'UPDATE', or 'DELETE'
"""

from dataclasses import dataclass

from ..models.temporal_patterns import TriggerConfig


@dataclass
class TriggerSQL:
    """Container for generated trigger SQL"""

    function_sql: str
    trigger_sql: str
    trigger_name: str
    function_name: str


class PostgreSQLTemporalTriggerBuilder:
    """Builder for PostgreSQL temporal table triggers.

    Generates optimized trigger functions and triggers that automatically
    maintain history tables for temporal data patterns.
    """

    def __init__(self):
        self.generated_functions = set()  # Track generated functions to avoid duplicates

    def build_insert_trigger(self, config: TriggerConfig) -> TriggerSQL:
        """Build INSERT trigger for temporal table.

        Creates history record when new record inserted into primary table.
        """
        function_name = f"fn_{config.primary_table}_insert_history"
        trigger_name = config.get_insert_trigger_name()

        # Build field lists for INSERT
        trackable_field_list = ", ".join(config.trackable_fields)
        new_field_list = ", ".join([f"NEW.{field}" for field in config.trackable_fields])

        function_sql = f"""
-- Temporal INSERT trigger function for {config.primary_schema}.{config.primary_table}
CREATE OR REPLACE FUNCTION {config.history_schema}.{function_name}()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert history record for new primary record
    INSERT INTO {config.history_schema}.{config.history_table} (
        {trackable_field_list},
        history_id,
        effective_time,
        systime,
        operation_type
    ) VALUES (
        {new_field_list},
        gen_random_uuid(),
        COALESCE(NEW.effective_time, CURRENT_TIMESTAMP),
        CURRENT_TIMESTAMP,
        'INSERT'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
        """.strip()

        trigger_sql = f"""
-- Temporal INSERT trigger for {config.primary_schema}.{config.primary_table}
CREATE TRIGGER {trigger_name}
    AFTER INSERT ON {config.primary_schema}.{config.primary_table}
    FOR EACH ROW
    EXECUTE FUNCTION {config.history_schema}.{function_name}();
        """.strip()

        return TriggerSQL(
            function_sql=function_sql,
            trigger_sql=trigger_sql,
            trigger_name=trigger_name,
            function_name=function_name,
        )

    def build_update_trigger(self, config: TriggerConfig) -> TriggerSQL:
        """Build UPDATE trigger for temporal table.

        Creates history record when existing record updated in primary table.
        Only fires if trackable fields actually changed.
        """
        function_name = f"fn_{config.primary_table}_update_history"
        trigger_name = config.get_update_trigger_name()

        # Build field lists for UPDATE
        trackable_field_list = ", ".join(config.trackable_fields)
        new_field_list = ", ".join([f"NEW.{field}" for field in config.trackable_fields])

        # Build change detection conditions
        change_conditions = " OR ".join(
            [f"OLD.{field} IS DISTINCT FROM NEW.{field}" for field in config.trackable_fields]
        )

        function_sql = f"""
-- Temporal UPDATE trigger function for {config.primary_schema}.{config.primary_table}
CREATE OR REPLACE FUNCTION {config.history_schema}.{function_name}()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create history record if trackable fields actually changed
    IF {change_conditions} THEN
        INSERT INTO {config.history_schema}.{config.history_table} (
            {trackable_field_list},
            history_id,
            effective_time,
            systime,
            operation_type
        ) VALUES (
            {new_field_list},
            gen_random_uuid(),
            COALESCE(NEW.effective_time, CURRENT_TIMESTAMP),
            CURRENT_TIMESTAMP,
            'UPDATE'
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
        """.strip()

        trigger_sql = f"""
-- Temporal UPDATE trigger for {config.primary_schema}.{config.primary_table}
CREATE TRIGGER {trigger_name}
    AFTER UPDATE ON {config.primary_schema}.{config.primary_table}
    FOR EACH ROW
    EXECUTE FUNCTION {config.history_schema}.{function_name}();
        """.strip()

        return TriggerSQL(
            function_sql=function_sql,
            trigger_sql=trigger_sql,
            trigger_name=trigger_name,
            function_name=function_name,
        )

    def build_delete_trigger(self, config: TriggerConfig) -> TriggerSQL:
        """Build DELETE trigger for temporal table.

        Creates history record when record deleted from primary table.
        Uses OLD values since record is being deleted.
        """
        function_name = f"fn_{config.primary_table}_delete_history"
        trigger_name = config.get_delete_trigger_name()

        # Build field lists for DELETE (use OLD values)
        trackable_field_list = ", ".join(config.trackable_fields)
        old_field_list = ", ".join([f"OLD.{field}" for field in config.trackable_fields])

        function_sql = f"""
-- Temporal DELETE trigger function for {config.primary_schema}.{config.primary_table}
CREATE OR REPLACE FUNCTION {config.history_schema}.{function_name}()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert history record for deleted primary record
    INSERT INTO {config.history_schema}.{config.history_table} (
        {trackable_field_list},
        history_id,
        effective_time,
        systime,
        operation_type
    ) VALUES (
        {old_field_list},
        gen_random_uuid(),
        COALESCE(OLD.effective_time, CURRENT_TIMESTAMP),
        CURRENT_TIMESTAMP,
        'DELETE'
    );

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;
        """.strip()

        trigger_sql = f"""
-- Temporal DELETE trigger for {config.primary_schema}.{config.primary_table}
CREATE TRIGGER {trigger_name}
    AFTER DELETE ON {config.primary_schema}.{config.primary_table}
    FOR EACH ROW
    EXECUTE FUNCTION {config.history_schema}.{function_name}();
        """.strip()

        return TriggerSQL(
            function_sql=function_sql,
            trigger_sql=trigger_sql,
            trigger_name=trigger_name,
            function_name=function_name,
        )

    def build_all_triggers(self, config: TriggerConfig) -> list[TriggerSQL]:
        """Build all temporal triggers (INSERT, UPDATE, DELETE) for a table pair.

        Args:
            config: Trigger configuration for the temporal table pair

        Returns:
            List of TriggerSQL objects for all three operations
        """
        triggers = []

        triggers.append(self.build_insert_trigger(config))
        triggers.append(self.build_update_trigger(config))
        triggers.append(self.build_delete_trigger(config))

        return triggers

    def build_history_table_sql(self, config: TriggerConfig) -> str:
        """Build CREATE TABLE SQL for history table.

        Generates the history table structure with all trackable fields
        plus required temporal fields.
        """
        # This is a simplified version - in practice, we'd need column type information
        # from the primary table to generate accurate CREATE TABLE statements

        trackable_fields_placeholder = "\n    ".join(
            [f"{field} <TYPE_FROM_PRIMARY>," for field in config.trackable_fields]
        )

        return f"""
-- History table for {config.primary_schema}.{config.primary_table}
CREATE TABLE IF NOT EXISTS {config.history_schema}.{config.history_table} (
    -- Trackable fields from primary table
    {trackable_fields_placeholder}

    -- Required temporal fields
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    effective_time TIMESTAMP WITH TIME ZONE NOT NULL,
    systime TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    operation_type VARCHAR(10) NOT NULL CHECK (operation_type IN ('INSERT', 'UPDATE', 'DELETE'))
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_{config.history_table}_effective_time
    ON {config.history_schema}.{config.history_table} (effective_time);

CREATE INDEX IF NOT EXISTS idx_{config.history_table}_systime
    ON {config.history_schema}.{config.history_table} (systime);

CREATE INDEX IF NOT EXISTS idx_{config.history_table}_primary_key
    ON {config.history_schema}.{config.history_table} ({config.primary_key_field});
        """.strip()


def build_temporal_triggers_for_table(config: TriggerConfig) -> list[str]:
    """Convenience function to build all SQL statements for a temporal table.

    Args:
        config: Trigger configuration

    Returns:
        List of SQL statements to execute (functions + triggers)
    """
    builder = PostgreSQLTemporalTriggerBuilder()
    triggers = builder.build_all_triggers(config)

    sql_statements = []

    # Add all trigger functions
    for trigger in triggers:
        sql_statements.append(trigger.function_sql)

    # Add all trigger creations
    for trigger in triggers:
        sql_statements.append(trigger.trigger_sql)

    return sql_statements
