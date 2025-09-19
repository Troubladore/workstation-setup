"""Data Platform Framework - Data Factory for Test Data Generation

Creates realistic test data for Layer 2 component testing and validation.
Supports reference data loading, transactional data generation, and temporal
data scenarios for comprehensive datakit testing.

Extracted and adapted from medallion-demo data merge patterns.

Features:
- Reference data loading with soft delete patterns
- Transactional data generation with audit trails
- Temporal data scenarios with history tracking
- Bulk loading utilities for performance
- Configurable data volumes for different test scenarios
"""

import random
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any, Generic, TypeVar

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

T = TypeVar("T", bound=SQLModel)


class DataFactory(ABC, Generic[T]):
    """Abstract base class for data factories"""

    @abstractmethod
    def create_sample_data(self, count: int = 10) -> list[T]:
        """Create sample data records for testing"""
        pass

    @abstractmethod
    def get_model_class(self) -> type[T]:
        """Return the model class this factory creates"""
        pass


class ReferenceDataFactory(DataFactory[T]):
    """Factory for reference/lookup data with soft delete patterns.

    Creates reference data suitable for Layer 2 testing with realistic
    inactivation patterns and proper audit trails.
    """

    def __init__(self, model_class: type[T], data_generator: callable):
        self.model_class = model_class
        self.data_generator = data_generator

    def get_model_class(self) -> type[T]:
        return self.model_class

    def create_sample_data(self, count: int = 10) -> list[T]:
        """Create sample reference data with some inactive records"""
        records = []

        for i in range(count):
            # Generate base data using provided generator
            record_data = self.data_generator(i)

            # Create instance
            record = self.model_class(**record_data)

            # Randomly inactivate some records (20% chance)
            if random.random() < 0.2:
                record.inactivate()

            records.append(record)

        return records

    def create_country_data(self, count: int = 20) -> list[T]:
        """Create sample country reference data"""
        countries = [
            "United States",
            "Canada",
            "United Kingdom",
            "Germany",
            "France",
            "Japan",
            "Australia",
            "Brazil",
            "India",
            "China",
            "Mexico",
            "Italy",
            "Spain",
            "Netherlands",
            "Sweden",
            "Norway",
            "Switzerland",
            "Austria",
            "Belgium",
            "Denmark",
        ]

        def country_generator(i: int) -> dict[str, Any]:
            return {
                "name": countries[i % len(countries)],
                "code": countries[i % len(countries)][:2].upper(),
                "active": True,
            }

        original_generator = self.data_generator
        self.data_generator = country_generator
        result = self.create_sample_data(min(count, len(countries)))
        self.data_generator = original_generator
        return result


class TransactionalDataFactory(DataFactory[T]):
    """Factory for transactional/business entity data.

    Creates transactional data with proper audit trails and realistic
    business patterns for comprehensive Layer 2 testing.
    """

    def __init__(self, model_class: type[T], data_generator: callable):
        self.model_class = model_class
        self.data_generator = data_generator

    def get_model_class(self) -> type[T]:
        return self.model_class

    def create_sample_data(self, count: int = 10) -> list[T]:
        """Create sample transactional data with varied timestamps"""
        records = []
        base_time = datetime.now(UTC) - timedelta(days=30)

        for i in range(count):
            # Generate base data using provided generator
            record_data = self.data_generator(i)

            # Create instance
            record = self.model_class(**record_data)

            # Vary creation timestamps over the last 30 days
            creation_time = base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            record.created_at = creation_time
            record.systime = creation_time

            # Some records have been updated since creation
            if random.random() < 0.3:  # 30% chance of update
                update_time = creation_time + timedelta(
                    days=random.randint(1, 5), hours=random.randint(0, 23)
                )
                record.updated_at = update_time
                record.systime = update_time

            records.append(record)

        return records

    def create_trade_data(self, count: int = 50) -> list[T]:
        """Create sample trading data"""
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX"]

        def trade_generator(i: int) -> dict[str, Any]:
            return {
                "symbol": random.choice(symbols),
                "quantity": random.randint(1, 1000),
                "price": round(random.uniform(50.0, 500.0), 2),
                "side": random.choice(["BUY", "SELL"]),
            }

        original_generator = self.data_generator
        self.data_generator = trade_generator
        result = self.create_sample_data(count)
        self.data_generator = original_generator
        return result


class TemporalDataFactory(DataFactory[T]):
    """Factory for temporal data with history tracking.

    Creates temporal data suitable for testing temporal table patterns,
    including scenarios that will trigger history record creation.
    """

    def __init__(self, model_class: type[T], data_generator: callable):
        self.model_class = model_class
        self.data_generator = data_generator

    def get_model_class(self) -> type[T]:
        return self.model_class

    def create_sample_data(self, count: int = 10) -> list[T]:
        """Create sample temporal data with varied effective times"""
        records = []
        base_time = datetime.now(UTC) - timedelta(days=60)

        for i in range(count):
            # Generate base data using provided generator
            record_data = self.data_generator(i)

            # Create instance
            record = self.model_class(**record_data)

            # Set varied effective times over the last 60 days
            effective_time = base_time + timedelta(
                days=random.randint(0, 60),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            record.set_effective_time(effective_time)

            records.append(record)

        return records

    def create_temporal_scenario_data(
        self, entity_count: int = 10, versions_per_entity: int = 3
    ) -> list[T]:
        """Create temporal data with multiple versions per entity.

        This creates data designed to test temporal table triggers by
        having the same logical entity with different effective times.
        """
        records = []
        base_time = datetime.now(UTC) - timedelta(days=30)

        for entity_id in range(entity_count):
            for version in range(versions_per_entity):
                # Generate base data
                record_data = self.data_generator(entity_id)

                # Modify some fields for different versions
                if "version" in record_data:
                    record_data["version"] = version + 1

                record = self.model_class(**record_data)

                # Set effective time for this version
                effective_time = base_time + timedelta(
                    days=version * 5,  # Versions spaced 5 days apart
                    hours=random.randint(9, 17),  # Business hours
                )

                record.set_effective_time(effective_time)
                records.append(record)

        return records


class BulkDataLoader:
    """Utility for efficiently loading large amounts of test data.

    Provides bulk loading capabilities for Layer 2 performance testing
    and realistic data volume scenarios.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def bulk_load_data(self, data_records: list[SQLModel], batch_size: int = 1000) -> int:
        """Bulk load data records efficiently.

        Args:
            data_records: List of SQLModel instances to load
            batch_size: Number of records to process per batch

        Returns:
            Number of records successfully loaded
        """
        loaded_count = 0

        with Session(self.engine) as session:
            try:
                # Process in batches for memory efficiency
                for i in range(0, len(data_records), batch_size):
                    batch = data_records[i : i + batch_size]

                    # Add batch to session
                    for record in batch:
                        session.add(record)

                    # Commit batch
                    session.commit()
                    loaded_count += len(batch)

                    print(f"Loaded batch: {loaded_count}/{len(data_records)} records")

            except Exception as e:
                session.rollback()
                raise RuntimeError(f"Bulk loading failed at record {loaded_count}: {e}")

        return loaded_count

    def load_reference_data_set(self, factories: dict[str, ReferenceDataFactory]) -> dict[str, int]:
        """Load a complete set of reference data from multiple factories.

        Args:
            factories: Dictionary of {table_name: factory} mappings

        Returns:
            Dictionary of {table_name: record_count} results
        """
        results = {}

        for table_name, factory in factories.items():
            print(f"Loading reference data for {table_name}...")

            # Generate data
            data_records = factory.create_sample_data()

            # Load data
            count = self.bulk_load_data(data_records)
            results[table_name] = count

            print(f"✅ Loaded {count} records for {table_name}")

        return results


# Convenience functions for common test scenarios


def create_test_data_scenario(engine: Engine, scenario_name: str = "basic") -> dict[str, Any]:
    """Create a complete test data scenario for Layer 2 testing.

    Args:
        engine: Database engine to load data into
        scenario_name: Type of scenario ('basic', 'temporal', 'large_volume')

    Returns:
        Dictionary with scenario details and loaded record counts
    """
    loader = BulkDataLoader(engine)
    results = {"scenario": scenario_name, "tables": {}}

    if scenario_name == "basic":
        # Basic scenario: Small amounts of reference and transactional data
        results["description"] = "Basic test scenario with minimal data"
        # Implementation would use specific factories for the scenario

    elif scenario_name == "temporal":
        # Temporal scenario: Focus on temporal table patterns
        results["description"] = "Temporal testing scenario with history patterns"
        # Implementation would use temporal factories

    elif scenario_name == "large_volume":
        # Large volume scenario: Performance testing
        results["description"] = "Large volume scenario for performance testing"
        # Implementation would generate larger datasets

    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    return results


def cleanup_test_data(engine: Engine, table_names: list[str]) -> None:
    """Clean up test data from specified tables.

    Args:
        engine: Database engine
        table_names: List of table names to clean
    """
    with Session(engine) as session:
        for table_name in table_names:
            try:
                session.execute(f"DELETE FROM {table_name}")
                session.commit()
                print(f"✅ Cleaned data from {table_name}")
            except Exception as e:
                session.rollback()
                print(f"⚠️  Error cleaning {table_name}: {e}")


# Factory registry for easy access to common data generators

COMMON_FACTORIES = {
    "countries": lambda: ReferenceDataFactory,
    "currencies": lambda: ReferenceDataFactory,
    "trades": lambda: TransactionalDataFactory,
    "orders": lambda: TransactionalDataFactory,
    "positions": lambda: TemporalDataFactory,
    "accounts": lambda: TemporalDataFactory,
}
