"""WorkerRunner and WorkerProcess for parallel test execution."""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import queue
import time
from pathlib import Path
from typing import TYPE_CHECKING

from behave.runner import (
    Context,
    ModelRunner,
    exec_file,
    load_step_modules,
    parse_features,
    select_subdirectories,
)

from behave_parallel.result import WorkerResult

if TYPE_CHECKING:
    from multiprocessing import Queue as QueueType
    from typing import Any

    from behave.configuration import Configuration

    from behave_parallel.config import ConfigSnapshot
    from behave_parallel.work_unit import WorkUnit

logger = logging.getLogger(__name__)


class WorkerRunner(ModelRunner):  # type: ignore[misc]
    """Runner that executes work units in an isolated worker process.

    Lifecycle:
        1. setup() — once at worker start (load hooks, steps, before_all).
        2. run_work_unit(unit) — called per work unit.
        3. teardown() — once at worker end (after_all, close formatters).
    """

    def __init__(
        self,
        config: Configuration,
        worker_id: int,
        result_queue: QueueType[WorkerResult],
        stop_event: Any,
    ) -> None:
        super().__init__(config)
        self.worker_id = worker_id
        self.result_queue = result_queue
        self.stop_event = stop_event
        self._last_result: WorkerResult | None = None
        self._setup_done = False
        self.base_dir = config.base_dir if getattr(config, "base_dir", None) else "features"

    def load_hooks(self, filename: str | None = None) -> None:
        """Load environment hooks from the environment file."""
        env_filename = (
            filename or getattr(self.config, "environment_file", None) or "environment.py"
        )
        hooks_path = os.path.join(self.base_dir, env_filename)
        if os.path.exists(hooks_path):
            exec_file(hooks_path, self.hooks)

        if "before_all" not in self.hooks:
            self.hooks["before_all"] = _noop_hook

    def load_step_definitions(self, extra_step_paths: list[str] | None = None) -> None:
        """Load step definitions from the steps directory."""
        if extra_step_paths is None:
            extra_step_paths = []
        steps_dir = os.path.join(self.base_dir, getattr(self.config, "steps_dir", None) or "steps")
        step_paths = [steps_dir]
        if self.config.use_nested_step_modules:
            step_subdirectories = select_subdirectories(steps_dir)
            step_paths.extend(step_subdirectories)
        step_paths = list(step_paths) + list(extra_step_paths)
        load_step_modules(step_paths)
        from behave.step_registry import registry as global_registry

        self.step_registry = global_registry

    def setup(self) -> None:
        """Load hooks, step definitions, create Context, run before_all."""
        self.load_hooks()
        self.load_step_definitions()
        self.context = Context(self)
        self.run_hook("before_all")
        self._setup_done = True
        logger.debug("WorkerRunner %d setup complete", self.worker_id)

    def run_work_unit(self, unit: WorkUnit) -> WorkerResult:
        """Execute a single work unit and return the result.

        Args:
            unit: The WorkUnit to execute.

        Returns:
            WorkerResult with timing, failure status, and report path.
        """
        start = time.perf_counter()
        try:
            if not unit.feature_path:
                raise ValueError(f"Work unit {unit.id} has no feature_path")
            self.features = parse_features(
                [unit.feature_path],
                language=self.config.lang,
            )
            self.undefined_steps.clear()
            self.hook_failures = 0
            if self.context is not None:
                self.aborted = False
            failed = self._run_features()
            duration = time.perf_counter() - start
            undefined = list(self.undefined_steps)
            report_path = self._write_report(unit)
            result = WorkerResult(
                worker_id=self.worker_id,
                work_unit_id=unit.id,
                failed=failed,
                duration=duration,
                report_path=report_path,
                undefined_steps=undefined,
            )
        except Exception as exc:
            duration = time.perf_counter() - start
            logger.exception("WorkerRunner %d error in work unit %s", self.worker_id, unit.id)
            result = WorkerResult(
                worker_id=self.worker_id,
                work_unit_id=unit.id,
                failed=True,
                duration=duration,
                error=str(exc),
            )
        self._last_result = result
        return result

    def teardown(self) -> None:
        """Run after_all hooks and close formatters.

        Safe to call even if setup() did not complete: skips hooks
        and formatters that were never initialised.
        """
        if self._setup_done:
            self.run_hook("after_all")
        for formatter in getattr(self, "formatters", []):
            formatter.close()
        logger.debug("WorkerRunner %d teardown complete", self.worker_id)

    def collect_result(self) -> WorkerResult | None:
        """Return the last WorkerResult produced, or None."""
        return self._last_result

    def _run_features(self) -> bool:
        """Run self.features without before_all/after_all hooks.

        Returns:
            True if any feature failed.
        """
        run_feature = not self.aborted
        failed_count = 0
        undefined_steps_initial_size = len(self.undefined_steps)
        for feature in self.features:
            if run_feature:
                try:
                    self.feature = feature
                    for formatter in self.formatters:
                        formatter.uri(feature.filename)
                    failed = feature.run(self)
                    if failed:
                        failed_count += 1
                        if self.config.stop or self.aborted:
                            run_feature = False
                except KeyboardInterrupt:
                    self.abort(reason="KeyboardInterrupt")
                    failed_count += 1
                    run_feature = False
            for reporter in self.config.reporters:
                reporter.feature(feature)
        return (
            failed_count > 0
            or self.aborted
            or self.hook_failures > 0
            or len(self.undefined_steps) > undefined_steps_initial_size
        )

    def _write_report(self, unit: WorkUnit) -> str | None:
        """Write a minimal JSON report for the work unit.

        Returns:
            Path to the report file, or None if writing failed.
        """
        tmp_dir = Path("tmp")
        safe_id = unit.id.replace(":", "_").replace("/", "_").replace("\\", "_")
        report_path = tmp_dir / f"worker_{self.worker_id}_{safe_id}.json"
        try:
            tmp_dir.mkdir(exist_ok=True)
            failed = any(getattr(f, "status", "passed") == "failed" for f in self.features)
            report_data = {
                "worker_id": self.worker_id,
                "work_unit_id": unit.id,
                "features": [
                    {
                        "name": f.name,
                        "filename": f.filename,
                        "status": (
                            "failed" if getattr(f, "status", "passed") == "failed" else "passed"
                        ),
                    }
                    for f in self.features
                ],
                "failed": failed,
            }
            report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
            return str(report_path)
        except Exception:
            logger.warning("Failed to write report to %s", report_path)
            return None


def _noop_hook(context: object) -> None:
    """Default no-op hook used when before_all is not defined."""


def _make_config(snapshot: ConfigSnapshot) -> Configuration:
    """Reconstruct a behave Configuration from a picklable ConfigSnapshot."""
    from behave.configuration import Configuration

    cmd_args = list(snapshot.paths) if snapshot.paths else [snapshot.base_dir]
    config = Configuration(cmd_args, load_config=False)
    config.base_dir = snapshot.base_dir
    config.steps_dir = snapshot.steps_dir
    config.environment_file = snapshot.environment_file
    config.lang = snapshot.lang
    config.stop = snapshot.stop
    config.dry_run = snapshot.dry_run
    config.use_nested_step_modules = snapshot.use_nested_step_modules
    config.reporters = []
    config.parallel = snapshot.parallel
    config.parallel_scheme = snapshot.parallel_scheme
    config.parallel_balance = snapshot.parallel_balance
    config.parallel_timing_file = snapshot.parallel_timing_file
    return config


def _worker_run_loop(
    worker_id: int,
    task_queue: Any,
    result_queue: QueueType[WorkerResult],
    stop_event: Any,
    config_snapshot: ConfigSnapshot,
) -> None:
    """Top-level worker loop function (picklable for Windows spawn).

    Consumes WorkUnits from task_queue, executes them via WorkerRunner,
    and puts WorkerResults into result_queue. Stops when:
    - A None sentinel is received from the queue.
    - stop_event is set by the coordinator.
    """
    config = _make_config(config_snapshot)
    runner = WorkerRunner(config, worker_id, result_queue, stop_event)
    try:
        runner.setup()
        while True:
            if stop_event.is_set():
                break
            try:
                unit = task_queue.get(timeout=5)
            except queue.Empty:
                continue
            except (EOFError, OSError):
                logger.warning(
                    "Worker %d: task queue closed unexpectedly; exiting.",
                    worker_id,
                )
                break
            if unit is None:
                task_queue.task_done()
                break
            if stop_event.is_set():
                task_queue.task_done()
                continue
            result = runner.run_work_unit(unit)
            result_queue.put(result)
            task_queue.task_done()
            if runner.aborted:
                stop_event.set()
                logger.warning(
                    "Worker %d: aborted after work unit %s; stopping all workers.",
                    worker_id,
                    unit.id,
                )
                break
    finally:
        runner.teardown()


class WorkerProcess:
    """Wrapper around multiprocessing.Process for consuming WorkUnits.

    Each WorkerProcess runs _worker_run_loop in a separate process,
    consuming WorkUnits from a JoinableQueue and producing WorkerResults
    in a result Queue.
    """

    def __init__(
        self,
        worker_id: int,
        task_queue: Any,
        result_queue: QueueType[WorkerResult],
        stop_event: Any,
        config_snapshot: ConfigSnapshot,
    ) -> None:
        self.worker_id = worker_id
        self._task_queue = task_queue
        self._result_queue = result_queue
        self._stop_event = stop_event
        self._config_snapshot = config_snapshot
        self._process: multiprocessing.Process | None = None

    def start(self) -> None:
        """Launch the worker process."""
        self._process = multiprocessing.Process(
            target=_worker_run_loop,
            args=(
                self.worker_id,
                self._task_queue,
                self._result_queue,
                self._stop_event,
                self._config_snapshot,
            ),
            daemon=True,
        )
        self._process.start()

    def join(self, timeout: float | None = None) -> None:
        """Wait for the worker process to terminate."""
        if self._process is not None:
            self._process.join(timeout)

    def is_alive(self) -> bool:
        """Return True if the worker process is still running."""
        if self._process is None:
            return False
        return self._process.is_alive()

    def terminate(self) -> None:
        """Forcefully terminate the worker process.

        Should only be called after ``join(timeout=...)`` returns and
        ``is_alive()`` is still True, as a last resort to avoid
        indefinite hangs from stuck workers.
        """
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            logger.warning("Worker %d forcibly terminated.", self.worker_id)
