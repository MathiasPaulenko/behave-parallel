"""Tests for WorkerResult dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from behave_parallel.result import WorkerResult


class TestWorkerResultConstruction:
    def test_minimal_construction(self) -> None:
        result = WorkerResult(
            worker_id=0,
            work_unit_id="feature:login.feature",
            failed=False,
            duration=1.5,
        )
        assert result.worker_id == 0
        assert result.work_unit_id == "feature:login.feature"
        assert result.failed is False
        assert result.duration == 1.5
        assert result.report_path is None
        assert result.undefined_steps == []
        assert result.error is None

    def test_full_construction(self) -> None:
        result = WorkerResult(
            worker_id=1,
            work_unit_id="scenario:checkout.feature:8",
            failed=True,
            duration=3.2,
            report_path="tmp/worker_1_scenario_checkout_feature_8.json",
            undefined_steps=["Given a logged in user", "Then the cart is empty"],
            error="AssertionError: expected 0 items",
        )
        assert result.worker_id == 1
        assert result.work_unit_id == "scenario:checkout.feature:8"
        assert result.failed is True
        assert result.duration == 3.2
        assert result.report_path == "tmp/worker_1_scenario_checkout_feature_8.json"
        assert result.undefined_steps == ["Given a logged in user", "Then the cart is empty"]
        assert result.error == "AssertionError: expected 0 items"

    def test_error_only_construction(self) -> None:
        result = WorkerResult(
            worker_id=2,
            work_unit_id="feature:crash.feature",
            failed=True,
            duration=0.1,
            error="Worker crashed with exit code 1",
        )
        assert result.error == "Worker crashed with exit code 1"
        assert result.report_path is None


class TestFrozenImmutability:
    def test_cannot_set_field(self) -> None:
        result = WorkerResult(
            worker_id=0,
            work_unit_id="feature:x.feature",
            failed=False,
            duration=1.0,
        )
        with pytest.raises(FrozenInstanceError):
            result.failed = True  # type: ignore[misc]

    def test_cannot_set_worker_id(self) -> None:
        result = WorkerResult(
            worker_id=0,
            work_unit_id="feature:x.feature",
            failed=False,
            duration=1.0,
        )
        with pytest.raises(FrozenInstanceError):
            result.worker_id = 5  # type: ignore[misc]


class TestWorkerResultPicklable:
    """WorkerResult is sent through multiprocessing.Queue and must be picklable."""

    def test_minimal_result_picklable(self) -> None:
        import pickle

        result = WorkerResult(
            worker_id=0,
            work_unit_id="feature:login.feature",
            failed=False,
            duration=1.5,
        )
        restored = pickle.loads(pickle.dumps(result))
        assert restored.worker_id == 0
        assert restored.work_unit_id == "feature:login.feature"
        assert restored.failed is False
        assert restored.duration == 1.5
        assert restored.report_path is None
        assert restored.undefined_steps == []
        assert restored.error is None

    def test_full_result_picklable(self) -> None:
        import pickle

        result = WorkerResult(
            worker_id=1,
            work_unit_id="scenario:checkout.feature:8",
            failed=True,
            duration=3.2,
            report_path="tmp/worker_1_report.json",
            undefined_steps=["Given a logged in user"],
            error="AssertionError: expected 0 items",
        )
        restored = pickle.loads(pickle.dumps(result))
        assert restored.worker_id == 1
        assert restored.work_unit_id == "scenario:checkout.feature:8"
        assert restored.failed is True
        assert restored.duration == 3.2
        assert restored.report_path == "tmp/worker_1_report.json"
        assert restored.undefined_steps == ["Given a logged in user"]
        assert restored.error == "AssertionError: expected 0 items"
