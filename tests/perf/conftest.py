"""Performance test configuration."""

import pytest


@pytest.fixture
def perf_threshold_ms() -> int:
    """Default performance threshold in milliseconds."""
    return 200
