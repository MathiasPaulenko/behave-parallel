"""Tests for WorkUnit dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from behave_parallel.work_unit import WorkUnit


@pytest.fixture
def mock_config() -> MagicMock:
    return MagicMock()


class TestWorkUnitConstruction:
    def test_minimal_construction(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(id="feature:login.feature", config=mock_config)
        assert unit.id == "feature:login.feature"
        assert unit.config is mock_config
        assert unit.feature_path is None
        assert unit.scenario_line is None
        assert unit.tags == []

    def test_full_construction(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(
            id="scenario:login.feature:12",
            config=mock_config,
            feature_path="features/login.feature",
            scenario_line=12,
            tags=["smoke", "serial"],
        )
        assert unit.id == "scenario:login.feature:12"
        assert unit.feature_path == "features/login.feature"
        assert unit.scenario_line == 12
        assert unit.tags == ["smoke", "serial"]


class TestIsSerial:
    def test_with_serial_tag(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(id="feature:x.feature", config=mock_config, tags=["serial"])
        assert unit.is_serial is True

    def test_without_serial_tag(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(id="feature:x.feature", config=mock_config, tags=["smoke"])
        assert unit.is_serial is False

    def test_with_multiple_tags_including_serial(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(
            id="feature:x.feature",
            config=mock_config,
            tags=["smoke", "serial", "wip"],
        )
        assert unit.is_serial is True

    def test_empty_tags(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(id="feature:x.feature", config=mock_config)
        assert unit.is_serial is False


class TestFrozenImmutability:
    def test_cannot_set_field(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(id="feature:x.feature", config=mock_config)
        with pytest.raises(FrozenInstanceError):
            unit.id = "feature:y.feature"  # type: ignore[misc]

    def test_cannot_set_tags(self, mock_config: MagicMock) -> None:
        unit = WorkUnit(id="feature:x.feature", config=mock_config)
        with pytest.raises(FrozenInstanceError):
            unit.tags = ["serial"]  # type: ignore[misc]


class TestWorkUnitPicklable:
    """WorkUnit is sent through multiprocessing.JoinableQueue and must be picklable.

    The config field must be a ConfigSnapshot (not a full Configuration) for
    this to work, since behave's Configuration contains non-picklable objects.
    """

    def test_work_unit_with_config_snapshot_picklable(self) -> None:
        import pickle

        from behave_parallel.config import ConfigSnapshot

        snap = ConfigSnapshot(
            base_dir="features",
            steps_dir="steps",
            environment_file="environment.py",
            lang="en",
            stop=False,
        )
        unit = WorkUnit(
            id="feature:login.feature",
            config=snap,
            feature_path="features/login.feature",
            tags=["smoke", "serial"],
        )
        restored = pickle.loads(pickle.dumps(unit))
        assert restored.id == "feature:login.feature"
        assert restored.feature_path == "features/login.feature"
        assert restored.tags == ["smoke", "serial"]
        assert restored.scenario_line is None
        assert isinstance(restored.config, ConfigSnapshot)
        assert restored.config.base_dir == "features"

    def test_work_unit_minimal_picklable(self) -> None:
        import pickle

        from behave_parallel.config import ConfigSnapshot

        snap = ConfigSnapshot(
            base_dir="features",
            steps_dir="steps",
            environment_file="environment.py",
            lang=None,
            stop=False,
        )
        unit = WorkUnit(id="feature:x.feature", config=snap)
        restored = pickle.loads(pickle.dumps(unit))
        assert restored.id == "feature:x.feature"
        assert restored.tags == []
