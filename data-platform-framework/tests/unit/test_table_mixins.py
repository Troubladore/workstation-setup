"""Unit tests for table mixins and base classes.

Tests the fundamental building blocks of our data platform:
- ReferenceTableMixin behavior and soft deletes
- TransactionalTableMixin audit trails
- TemporalTableMixin effective time management
- Base table classes with proper ID patterns
"""

from datetime import UTC, datetime
from unittest.mock import patch

from data_platform_framework.base.models.table_mixins import (
    ReferenceTable,
    ReferenceTableMixin,
    TemporalTable,
    TemporalTableMixin,
    TransactionalTable,
    TransactionalTableMixin,
)


class TestReferenceTableMixin:
    """Test reference table mixin functionality"""

    def test_reference_mixin_defaults(self):
        """Test that reference mixin has correct default values"""

        class TestRefTable(ReferenceTableMixin):
            pass

        instance = TestRefTable()

        # Should start as active (inactivated_date is None)
        assert instance.inactivated_date is None
        assert instance.is_active() is True

        # Should have systime set
        assert instance.systime is not None
        assert isinstance(instance.systime, datetime)

    def test_inactivate_functionality(self):
        """Test soft delete functionality via inactivate()"""

        class TestRefTable(ReferenceTableMixin):
            pass

        instance = TestRefTable()
        original_systime = instance.systime

        # Initially active
        assert instance.is_active() is True

        # Inactivate the record
        with patch("data_platform_framework.base.models.table_mixins.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.UTC = UTC

            instance.inactivate()

        # Should now be inactive
        assert instance.is_active() is False
        assert instance.inactivated_date == mock_now
        assert instance.systime == mock_now
        assert instance.systime != original_systime

    def test_reference_table_base_class(self):
        """Test ReferenceTable base class with SMALLINT ID"""
        # Can't instantiate abstract SQLModel directly, but we can test the mixin
        # In real usage, this would be: class Country(ReferenceTable, table=True): ...

        assert hasattr(ReferenceTable, "id")
        assert hasattr(ReferenceTable, "inactivated_date")
        assert hasattr(ReferenceTable, "systime")


class TestTransactionalTableMixin:
    """Test transactional table mixin functionality"""

    def test_transactional_mixin_defaults(self):
        """Test that transactional mixin has correct default values"""

        class TestTxnTable(TransactionalTableMixin):
            pass

        instance = TestTxnTable()

        # Should have all audit timestamps
        assert instance.systime is not None
        assert instance.created_at is not None
        assert instance.updated_at is not None

        # All should be datetime objects
        assert isinstance(instance.systime, datetime)
        assert isinstance(instance.created_at, datetime)
        assert isinstance(instance.updated_at, datetime)

    def test_touch_functionality(self):
        """Test touch() method updates timestamps"""

        class TestTxnTable(TransactionalTableMixin):
            pass

        instance = TestTxnTable()
        original_systime = instance.systime
        original_updated_at = instance.updated_at
        original_created_at = instance.created_at

        # Touch should update systime and updated_at, but not created_at
        with patch("data_platform_framework.base.models.table_mixins.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.UTC = UTC

            instance.touch()

        # Should have updated modification timestamps
        assert instance.systime == mock_now
        assert instance.updated_at == mock_now

        # Should NOT have updated creation timestamp
        assert instance.created_at == original_created_at

        # Timestamps should have changed
        assert instance.systime != original_systime
        assert instance.updated_at != original_updated_at

    def test_transactional_table_base_class(self):
        """Test TransactionalTable base class with UUID ID"""
        assert hasattr(TransactionalTable, "id")
        assert hasattr(TransactionalTable, "systime")
        assert hasattr(TransactionalTable, "created_at")
        assert hasattr(TransactionalTable, "updated_at")


class TestTemporalTableMixin:
    """Test temporal table mixin functionality"""

    def test_temporal_mixin_defaults(self):
        """Test that temporal mixin has correct default values"""

        class TestTemporalTable(TemporalTableMixin):
            pass

        instance = TestTemporalTable()

        # Should have temporal timestamps
        assert instance.effective_time is not None
        assert instance.systime is not None

        # Should be datetime objects
        assert isinstance(instance.effective_time, datetime)
        assert isinstance(instance.systime, datetime)

    def test_set_effective_time(self):
        """Test set_effective_time() method"""

        class TestTemporalTable(TemporalTableMixin):
            pass

        instance = TestTemporalTable()
        original_systime = instance.systime

        # Set custom effective time
        custom_effective_time = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)

        with patch("data_platform_framework.base.models.table_mixins.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.UTC = UTC

            instance.set_effective_time(custom_effective_time)

        # Should have set custom effective time and updated systime
        assert instance.effective_time == custom_effective_time
        assert instance.systime == mock_now
        assert instance.systime != original_systime

    def test_temporal_table_base_class(self):
        """Test TemporalTable base class with UUID ID"""
        assert hasattr(TemporalTable, "id")
        assert hasattr(TemporalTable, "effective_time")
        assert hasattr(TemporalTable, "systime")


class TestMixinInteractions:
    """Test interactions between different mixins"""

    def test_multiple_mixin_inheritance(self):
        """Test class inheriting multiple mixins"""

        class ComplexTable(ReferenceTableMixin, TransactionalTableMixin):
            pass

        instance = ComplexTable()

        # Should have fields from both mixins
        assert hasattr(instance, "inactivated_date")  # From reference
        assert hasattr(instance, "created_at")  # From transactional

        # Methods from both mixins should work
        assert instance.is_active() is True

        instance.touch()  # Should update transactional timestamps
        instance.inactivate()  # Should inactivate reference

        assert instance.is_active() is False

    def test_field_name_conflicts_handled(self):
        """Test that systime field doesn't conflict between mixins"""

        class ConflictTable(ReferenceTableMixin, TransactionalTableMixin, TemporalTableMixin):
            pass

        instance = ConflictTable()

        # Should have systime (all mixins define it, but should resolve consistently)
        assert hasattr(instance, "systime")
        assert isinstance(instance.systime, datetime)

        # All mixin methods should work
        instance.touch()
        instance.inactivate()
        instance.set_effective_time(datetime.now(UTC))

        # Should still be functional
        assert instance.is_active() is False


# Integration tests with actual database would go in tests/integration/
# These unit tests focus on the mixin logic and method behavior
