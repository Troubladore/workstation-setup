"""Unit tests for PostgreSQL temporal trigger builder.

Tests the critical trigger generation logic that ensures temporal table integrity:
- SQL generation for INSERT/UPDATE/DELETE triggers
- Proper field exclusion handling
- Trigger function creation with correct parameters
- SQL syntax validation and optimization
"""

import pytest
from data_platform_framework.base.models.temporal_patterns import TriggerConfig
from data_platform_framework.base.triggers.trigger_builder import (
    PostgreSQLTemporalTriggerBuilder,
    TriggerSQL,
    build_temporal_triggers_for_table,
)


class TestPostgreSQLTemporalTriggerBuilder:
    """Test PostgreSQL temporal trigger builder functionality"""

    def test_trigger_builder_initialization(self):
        """Test trigger builder initializes correctly"""
        builder = PostgreSQLTemporalTriggerBuilder()
        assert builder.generated_functions == set()

    @pytest.fixture
    def sample_trigger_config(self):
        """Sample trigger configuration for testing"""
        return TriggerConfig(
            primary_table="trades",
            history_table="trades__history",
            primary_schema="trading",
            history_schema="trading",
            trackable_fields=["trade_id", "symbol", "quantity", "price"],
            primary_key_field="trade_id",
        )

    def test_build_insert_trigger(self, sample_trigger_config):
        """Test INSERT trigger generation"""
        builder = PostgreSQLTemporalTriggerBuilder()
        trigger_sql = builder.build_insert_trigger(sample_trigger_config)

        assert isinstance(trigger_sql, TriggerSQL)

        # Check trigger naming
        assert trigger_sql.trigger_name == "tr_trades_insert_history"
        assert trigger_sql.function_name == "fn_trades_insert_history"

        # Check function SQL contains expected elements
        function_sql = trigger_sql.function_sql
        assert "CREATE OR REPLACE FUNCTION trading.fn_trades_insert_history()" in function_sql
        assert "INSERT INTO trading.trades__history" in function_sql
        assert "trade_id, symbol, quantity, price" in function_sql
        assert "NEW.trade_id, NEW.symbol, NEW.quantity, NEW.price" in function_sql
        assert "operation_type" in function_sql
        assert "'INSERT'" in function_sql
        assert "RETURN NEW" in function_sql

        # Check trigger SQL
        trigger_sql_content = trigger_sql.trigger_sql
        assert "CREATE TRIGGER tr_trades_insert_history" in trigger_sql_content
        assert "AFTER INSERT ON trading.trades" in trigger_sql_content
        assert "FOR EACH ROW" in trigger_sql_content
        assert "EXECUTE FUNCTION trading.fn_trades_insert_history();" in trigger_sql_content

    def test_build_update_trigger(self, sample_trigger_config):
        """Test UPDATE trigger generation"""
        builder = PostgreSQLTemporalTriggerBuilder()
        trigger_sql = builder.build_update_trigger(sample_trigger_config)

        assert isinstance(trigger_sql, TriggerSQL)

        # Check trigger naming
        assert trigger_sql.trigger_name == "tr_trades_update_history"
        assert trigger_sql.function_name == "fn_trades_update_history"

        # Check function SQL contains change detection
        function_sql = trigger_sql.function_sql
        assert "CREATE OR REPLACE FUNCTION trading.fn_trades_update_history()" in function_sql
        assert "IS DISTINCT FROM" in function_sql  # Change detection logic
        assert "OLD.trade_id IS DISTINCT FROM NEW.trade_id" in function_sql
        assert "'UPDATE'" in function_sql
        assert "RETURN NEW" in function_sql

        # Check all trackable fields have change detection
        for field in sample_trigger_config.trackable_fields:
            assert f"OLD.{field} IS DISTINCT FROM NEW.{field}" in function_sql

        # Check trigger SQL
        trigger_sql_content = trigger_sql.trigger_sql
        assert "CREATE TRIGGER tr_trades_update_history" in trigger_sql_content
        assert "AFTER UPDATE ON trading.trades" in trigger_sql_content

    def test_build_delete_trigger(self, sample_trigger_config):
        """Test DELETE trigger generation"""
        builder = PostgreSQLTemporalTriggerBuilder()
        trigger_sql = builder.build_delete_trigger(sample_trigger_config)

        assert isinstance(trigger_sql, TriggerSQL)

        # Check trigger naming
        assert trigger_sql.trigger_name == "tr_trades_delete_history"
        assert trigger_sql.function_name == "fn_trades_delete_history"

        # Check function SQL uses OLD values for deleted records
        function_sql = trigger_sql.function_sql
        assert "CREATE OR REPLACE FUNCTION trading.fn_trades_delete_history()" in function_sql
        assert "OLD.trade_id, OLD.symbol, OLD.quantity, OLD.price" in function_sql
        assert "'DELETE'" in function_sql
        assert "RETURN OLD" in function_sql  # DELETE triggers return OLD

        # Check trigger SQL
        trigger_sql_content = trigger_sql.trigger_sql
        assert "CREATE TRIGGER tr_trades_delete_history" in trigger_sql_content
        assert "AFTER DELETE ON trading.trades" in trigger_sql_content

    def test_build_all_triggers(self, sample_trigger_config):
        """Test building all triggers for a table"""
        builder = PostgreSQLTemporalTriggerBuilder()
        all_triggers = builder.build_all_triggers(sample_trigger_config)

        assert len(all_triggers) == 3  # INSERT, UPDATE, DELETE

        # Check we have all three trigger types
        trigger_names = {trigger.trigger_name for trigger in all_triggers}
        assert "tr_trades_insert_history" in trigger_names
        assert "tr_trades_update_history" in trigger_names
        assert "tr_trades_delete_history" in trigger_names

        # Check all are TriggerSQL objects
        for trigger in all_triggers:
            assert isinstance(trigger, TriggerSQL)
            assert trigger.function_sql is not None
            assert trigger.trigger_sql is not None

    def test_build_history_table_sql(self, sample_trigger_config):
        """Test history table SQL generation"""
        builder = PostgreSQLTemporalTriggerBuilder()
        history_sql = builder.build_history_table_sql(sample_trigger_config)

        assert "CREATE TABLE IF NOT EXISTS trading.trades__history" in history_sql

        # Check trackable fields are included (as placeholders)
        for field in sample_trigger_config.trackable_fields:
            assert field in history_sql

        # Check temporal fields are included
        assert "history_id UUID PRIMARY KEY" in history_sql
        assert "effective_time TIMESTAMP WITH TIME ZONE" in history_sql
        assert "systime TIMESTAMP WITH TIME ZONE" in history_sql
        assert "operation_type VARCHAR(10)" in history_sql

        # Check operation_type constraint
        assert "CHECK (operation_type IN ('INSERT', 'UPDATE', 'DELETE'))" in history_sql

        # Check indexes are created
        assert "CREATE INDEX IF NOT EXISTS idx_trades__history_effective_time" in history_sql
        assert "CREATE INDEX IF NOT EXISTS idx_trades__history_systime" in history_sql
        assert "CREATE INDEX IF NOT EXISTS idx_trades__history_primary_key" in history_sql

    def test_trigger_config_naming_methods(self):
        """Test TriggerConfig naming methods"""
        config = TriggerConfig(
            primary_table="customers",
            history_table="customers__history",
            primary_schema="sales",
            history_schema="sales",
            trackable_fields=["id", "name"],
            primary_key_field="id",
        )

        assert config.get_insert_trigger_name() == "tr_customers_insert_history"
        assert config.get_update_trigger_name() == "tr_customers_update_history"
        assert config.get_delete_trigger_name() == "tr_customers_delete_history"

    def test_field_exclusion_handling(self):
        """Test that excluded fields are properly omitted from triggers"""
        config = TriggerConfig(
            primary_table="documents",
            history_table="documents__history",
            primary_schema="content",
            history_schema="content",
            trackable_fields=["doc_id", "title", "author"],  # content_blob excluded
            primary_key_field="doc_id",
        )

        builder = PostgreSQLTemporalTriggerBuilder()
        insert_trigger = builder.build_insert_trigger(config)

        # Should include trackable fields
        assert "doc_id, title, author" in insert_trigger.function_sql
        assert "NEW.doc_id, NEW.title, NEW.author" in insert_trigger.function_sql

        # Should NOT include excluded fields (content_blob not in trackable_fields)
        assert "content_blob" not in insert_trigger.function_sql

    def test_empty_trackable_fields_handling(self):
        """Test handling of config with no trackable fields"""
        config = TriggerConfig(
            primary_table="empty_table",
            history_table="empty_table__history",
            primary_schema="test",
            history_schema="test",
            trackable_fields=[],  # No trackable fields
            primary_key_field="id",
        )

        builder = PostgreSQLTemporalTriggerBuilder()
        insert_trigger = builder.build_insert_trigger(config)

        # Should handle empty field list gracefully
        assert "CREATE OR REPLACE FUNCTION" in insert_trigger.function_sql
        assert "INSERT INTO test.empty_table__history" in insert_trigger.function_sql
        # Should have empty field lists but still include temporal fields
        assert "history_id," in insert_trigger.function_sql
        assert "effective_time," in insert_trigger.function_sql


class TestTriggerSQLDataclass:
    """Test TriggerSQL dataclass"""

    def test_trigger_sql_creation(self):
        """Test TriggerSQL dataclass creation"""
        trigger_sql = TriggerSQL(
            function_sql="CREATE FUNCTION...",
            trigger_sql="CREATE TRIGGER...",
            trigger_name="tr_test",
            function_name="fn_test",
        )

        assert trigger_sql.function_sql == "CREATE FUNCTION..."
        assert trigger_sql.trigger_sql == "CREATE TRIGGER..."
        assert trigger_sql.trigger_name == "tr_test"
        assert trigger_sql.function_name == "fn_test"


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_build_temporal_triggers_for_table(self):
        """Test convenience function for building all triggers"""
        config = TriggerConfig(
            primary_table="orders",
            history_table="orders__history",
            primary_schema="sales",
            history_schema="sales",
            trackable_fields=["order_id", "customer_id", "amount"],
            primary_key_field="order_id",
        )

        sql_statements = build_temporal_triggers_for_table(config)

        # Should return list of SQL statements
        assert isinstance(sql_statements, list)
        assert len(sql_statements) == 6  # 3 functions + 3 triggers

        # Check that we have both functions and triggers
        function_statements = [
            stmt for stmt in sql_statements if "CREATE OR REPLACE FUNCTION" in stmt
        ]
        trigger_statements = [stmt for stmt in sql_statements if "CREATE TRIGGER" in stmt]

        assert len(function_statements) == 3  # INSERT, UPDATE, DELETE functions
        assert len(trigger_statements) == 3  # INSERT, UPDATE, DELETE triggers

        # Check ordering (functions should come before triggers)
        for i, stmt in enumerate(sql_statements[:3]):
            assert "CREATE OR REPLACE FUNCTION" in stmt

        for i, stmt in enumerate(sql_statements[3:]):
            assert "CREATE TRIGGER" in stmt


# Performance and SQL validation tests would be in integration tests
# These unit tests focus on the logic and structure of generated SQL
