"""Conftest for contract tests - no database required."""

import os

# Prevent the root conftest from running migrations
# Contract tests are pure unit tests that only verify parsing logic
os.environ["PYTEST_SKIP_DB_SETUP"] = "1"


def pytest_configure(config):  # type: ignore
    """Skip database setup for contract tests."""
    # This intentionally does nothing to prevent the root conftest
    # from running database migrations
    pass


def pytest_runtest_setup(item):  # type: ignore
    """Ensure contract tests don't require database fixtures."""
    # Contract tests should not use db_session or async_client fixtures
    pass
