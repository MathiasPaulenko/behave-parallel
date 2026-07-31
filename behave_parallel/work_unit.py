"""WorkUnit: a single unit of test work to be dispatched to a worker."""

from __future__ import annotations

from dataclasses import dataclass, field

from behave_parallel.config import ConfigSnapshot


@dataclass(frozen=True)
class WorkUnit:
    """A single unit of test work for parallel dispatch.

    A WorkUnit represents either a whole feature file or a single scenario
    (identified by line number) within a feature file. It carries a
    picklable ConfigSnapshot so that workers can execute independently
    after being spawned via multiprocessing.

    Attributes:
        id: Unique identifier, e.g. "feature:login.feature" or
            "scenario:login.feature:12".
        config: Picklable ConfigSnapshot with essential configuration.
        feature_path: Path to the .feature file.
        scenario_line: Line number of the scenario within the feature file.
            None when the work unit represents an entire feature.
        tags: Tags associated with the scenario or feature.
    """

    id: str
    config: ConfigSnapshot
    feature_path: str | None = None
    scenario_line: int | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def is_serial(self) -> bool:
        """True if this work unit is tagged with @serial.

        Serial work units are executed sequentially after all parallel
        work units have completed.
        """
        return "serial" in self.tags
