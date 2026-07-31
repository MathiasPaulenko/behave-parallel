"""Test that behave_parallel public API is importable."""

from __future__ import annotations

import behave_parallel


def test_parallel_runner_importable() -> None:
    """ParallelRunner must be importable from behave_parallel."""
    from behave_parallel import ParallelRunner

    assert ParallelRunner is not None


def test_version_attribute() -> None:
    """behave_parallel must expose __version__."""
    assert hasattr(behave_parallel, "__version__")
    assert isinstance(behave_parallel.__version__, str)
    assert behave_parallel.__version__ == "0.1.0"


def test_all_exports() -> None:
    """__all__ must list ParallelRunner and __version__."""
    assert "ParallelRunner" in behave_parallel.__all__
    assert "__version__" in behave_parallel.__all__
