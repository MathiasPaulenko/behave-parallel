"""WorkerResult: the outcome of executing a WorkUnit in a worker process."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkerResult:
    """Result of a worker executing a single WorkUnit.

    Produced by WorkerRunner.run_work_unit() and sent back to the
    coordinator via the result queue for aggregation.

    Attributes:
        worker_id: Identifier of the worker process that produced this result.
        work_unit_id: ID of the WorkUnit that was executed.
        failed: True if any scenario or step in the work unit failed.
        duration: Wall-clock execution time in seconds.
        report_path: Path to the temporary JSON report file, or None if
            no report was written.
        undefined_steps: List of undefined step text patterns encountered.
        error: Error message if the worker process crashed, None otherwise.
    """

    worker_id: int
    work_unit_id: str
    failed: bool
    duration: float
    report_path: str | None = None
    undefined_steps: list[str] = field(default_factory=list)
    error: str | None = None
