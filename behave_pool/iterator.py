"""Strategy pattern for iterating work units from Behave features."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import TYPE_CHECKING

from behave_pool.config import snapshot_config
from behave_pool.work_unit import WorkUnit

if TYPE_CHECKING:
    from behave.configuration import Configuration
    from behave.model import Feature


class WorkUnitIterator(ABC):
    """Abstract strategy for generating WorkUnits from parsed features."""

    @abstractmethod
    def iterate(self) -> Iterator[WorkUnit]:
        """Yield WorkUnit instances one at a time."""
        ...

    @staticmethod
    def for_scheme(
        scheme: str,
        features: list[Feature],
        config: Configuration,
    ) -> WorkUnitIterator:
        """Factory: return the iterator for the given parallel scheme.

        Args:
            scheme: "feature" or "scenario".
            features: Parsed Behave Feature objects.
            config: Coordinator's Configuration (will be deep-copied per unit).

        Returns:
            A WorkUnitIterator instance for the requested scheme.

        Raises:
            ValueError: If scheme is not recognised.
            NotImplementedError: If scheme is "scenario" (not yet implemented).
        """
        if scheme == "feature":
            return FeatureIterator(features, config)
        if scheme == "scenario":
            raise NotImplementedError("ScenarioIterator is not yet implemented")
        msg = f"Unknown parallel scheme: {scheme!r}. Use 'feature' or 'scenario'."
        raise ValueError(msg)


class FeatureIterator(WorkUnitIterator):
    """Generate one WorkUnit per feature file.

    Each WorkUnit contains an isolated deep copy of the Configuration
    so that workers can execute independently without shared mutable state.
    """

    def __init__(self, features: list[Feature], config: Configuration) -> None:
        self._features = features
        self._config = config

    def iterate(self) -> Iterator[WorkUnit]:
        """Yield one WorkUnit per feature.

        Tags are collected from both the feature and its scenarios.
        If any scenario has the ``serial`` tag, the work unit is
        marked serial so it runs in the serial phase.
        """
        for feature in self._features:
            tags = set(str(t) for t in (getattr(feature, "tags", None) or []))
            for scenario in getattr(feature, "scenarios", None) or []:
                tags.update(str(t) for t in (getattr(scenario, "tags", None) or []))
            yield WorkUnit(
                id=f"feature:{feature.filename}",
                config=snapshot_config(self._config),
                feature_path=feature.filename,
                scenario_line=None,
                tags=list(tags),
            )
