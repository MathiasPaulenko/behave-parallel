"""ParallelRunner: coordinator that orchestrates parallel feature execution."""

from __future__ import annotations

import logging
import multiprocessing
import os
import queue
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from behave.runner import Runner, make_formatters, parse_features

from behave_pool.config import add_parallel_options, snapshot_config
from behave_pool.iterator import WorkUnitIterator
from behave_pool.result import WorkerResult
from behave_pool.timing import TimingStore
from behave_pool.worker import WorkerProcess

if TYPE_CHECKING:
    from behave.configuration import Configuration

    from behave_pool.work_unit import WorkUnit

logger = logging.getLogger(__name__)


class ParallelRunner(Runner):  # type: ignore[misc]
    """Coordinator that dispatches work units to worker processes.

    When ``config.parallel <= 1`` it falls back to the standard Behave
    sequential runner.  Otherwise it plans, dispatches, and collects
    results from N worker processes.
    """

    def __init__(self, config: Configuration) -> None:
        super().__init__(config)
        add_parallel_options(config)

    def run(self) -> bool:
        """Run the test suite — parallel or sequential depending on config."""
        with self.path_manager:
            self.setup_paths()
            return self.run_with_paths()

    def run_with_paths(self) -> bool:
        """Run tests with configured paths.

        If ``config.parallel <= 1`` delegates to the standard sequential
        runner.  Otherwise enters the parallel pipeline.
        """
        if self.config.parallel <= 1:
            return self._run_sequential()

        return self._run_parallel()

    def _run_sequential(self) -> bool:
        """Standard Behave sequential execution."""
        from behave.runner import Context

        self.context = Context(self)
        self.load_hooks()
        self.load_step_definitions()

        feature_locations = [
            filename for filename in self.feature_locations() if not self.config.exclude(filename)
        ]
        features = parse_features(feature_locations, language=self.config.lang)
        self.features.extend(features)

        stream_openers = self.config.outputs
        self.formatters = make_formatters(self.config, stream_openers)
        failed: bool = self.run_model()
        return failed

    def _run_parallel(self) -> bool:
        """Execute the parallel pipeline: plan -> split -> dispatch -> collect."""
        ctx = multiprocessing.get_context("spawn")
        task_queue: Any = ctx.JoinableQueue()
        result_queue: Any = ctx.Queue()
        stop_event: Any = ctx.Event()

        try:
            work_units = self._plan()
            parallel_batch, serial_batch = self._split_by_serial_tag(work_units)
            dispatched = self._dispatch(
                task_queue, result_queue, stop_event, parallel_batch, serial_batch
            )
            return self._collect(result_queue, dispatched)
        finally:
            stop_event.set()
            task_queue.close()
            result_queue.close()

    def _plan(self) -> list[WorkUnit]:
        """Parse features and create work units.

        Returns:
            List of work units to execute.
        """
        from behave.runner import Context

        self.context = Context(self)
        self.load_hooks()

        feature_locations = [
            filename for filename in self.feature_locations() if not self.config.exclude(filename)
        ]
        features = parse_features(feature_locations, language=self.config.lang)
        self.features.extend(features)

        iterator = WorkUnitIterator.for_scheme(
            scheme=self.config.parallel_scheme,
            features=features,
            config=self.config,
        )
        work_units = list(iterator.iterate())
        work_units = self._sort_by_duration(work_units)

        return work_units

    def _sort_by_duration(self, units: list[WorkUnit]) -> list[WorkUnit]:
        """Sort work units by historical duration (LPT) or keep FIFO order.

        When ``config.parallel_balance`` is ``"lpt"``, units are sorted
        descending by their stored duration in the TimingStore so that
        the longest jobs start first, improving overall wall-clock time.

        When ``config.parallel_balance`` is ``"fifo"``, the original
        order is preserved.

        Args:
            units: Work units to sort.

        Returns:
            Sorted list of work units.
        """
        balance = getattr(self.config, "parallel_balance", "lpt")
        if balance == "fifo":
            return units

        timing_file = (
            getattr(self.config, "parallel_timing_file", None) or ".behave-pool-timing.json"
        )
        store = TimingStore(path=Path(timing_file))
        store.load()
        return sorted(units, key=lambda u: store.get_duration(u.id), reverse=True)

    @staticmethod
    def _split_by_serial_tag(
        units: list[WorkUnit],
    ) -> tuple[list[WorkUnit], list[WorkUnit]]:
        """Split work units into parallel and serial batches.

        Args:
            units: All work units to split.

        Returns:
            Tuple of (parallel_batch, serial_batch).
        """
        parallel_batch = [u for u in units if not u.is_serial]
        serial_batch = [u for u in units if u.is_serial]
        return parallel_batch, serial_batch

    def _dispatch(
        self,
        task_queue: Any,
        result_queue: Any,
        stop_event: Any,
        parallel_batch: list[WorkUnit],
        serial_batch: list[WorkUnit],
    ) -> list[WorkUnit]:
        """Two-phase dispatch: parallel first, then serial.

        Phase 1: enqueue parallel_batch, launch N workers, wait for completion.
        Phase 2: enqueue serial_batch one at a time, launch 1 worker, wait.

        Returns:
            List of work units that were actually enqueued (dispatched).
        """
        n_workers = self.config.parallel
        config_snapshot = snapshot_config(self.config)
        dispatched: list[WorkUnit] = []
        ctx = multiprocessing.get_context("spawn")

        # -- Phase 1: parallel batch with N workers.
        if parallel_batch:
            for unit in parallel_batch:
                task_queue.put(unit)
            for _ in range(n_workers):
                task_queue.put(None)
            dispatched.extend(parallel_batch)

            workers: list[WorkerProcess] = []
            for worker_id in range(n_workers):
                worker = WorkerProcess(
                    worker_id=worker_id,
                    task_queue=task_queue,
                    result_queue=result_queue,
                    stop_event=stop_event,
                    config_snapshot=config_snapshot,
                    ctx=ctx,
                )
                worker.start()
                workers.append(worker)

            for worker in workers:
                worker.join(timeout=300)
                if worker.is_alive():
                    logger.warning(
                        "Worker %d did not terminate within 300s; "
                        "setting stop event and terminating.",
                        worker.worker_id,
                    )
                    stop_event.set()
                    worker.terminate()

            # Drain any unconsumed items so the queue is empty for Phase 2.
            while not task_queue.empty():
                try:
                    task_queue.get_nowait()
                    task_queue.task_done()
                except queue.Empty:
                    break

        # -- Phase 2: serial batch with 1 worker.
        if serial_batch and not stop_event.is_set():
            for unit in serial_batch:
                task_queue.put(unit)
            task_queue.put(None)
            dispatched.extend(serial_batch)

            serial_worker = WorkerProcess(
                worker_id=0,
                task_queue=task_queue,
                result_queue=result_queue,
                stop_event=stop_event,
                config_snapshot=config_snapshot,
                ctx=ctx,
            )
            serial_worker.start()
            serial_worker.join(timeout=300)
            if serial_worker.is_alive():
                logger.warning(
                    "Serial worker did not terminate within 300s; "
                    "setting stop event and terminating."
                )
                stop_event.set()
                serial_worker.terminate()

            # Drain any unconsumed items.
            while not task_queue.empty():
                try:
                    task_queue.get_nowait()
                    task_queue.task_done()
                except queue.Empty:
                    break

        return dispatched

    def _collect(
        self,
        result_queue: Any,
        work_units: list[WorkUnit],
        deadline_seconds: float = 30,
    ) -> bool:
        """Drain result queue, merge results, and compute exit code.

        Returns:
            True if any test failed (Behave convention).
        """
        expected = len(work_units)
        results: list[WorkerResult] = []
        received_ids: set[str] = set()

        # Drain all available results, waiting up to deadline_seconds for late arrivals.
        deadline = time.monotonic() + deadline_seconds
        while len(results) < expected and time.monotonic() < deadline:
            try:
                result = result_queue.get(timeout=1)
            except queue.Empty:
                continue
            except (EOFError, OSError):
                break
            results.append(result)
            received_ids.add(result.work_unit_id)

        # Detect missing results from crashed or timed-out workers.
        missing = [u.id for u in work_units if u.id not in received_ids]
        if missing:
            logger.warning(
                "Missing %d result(s) from worker(s): %s",
                len(missing),
                ", ".join(missing),
            )

        any_failed = any(r.failed for r in results)

        # Missing results indicate worker crashes — treat as failures.
        if missing:
            any_failed = True

        self._update_timings(results)

        self._merge_reports(results)

        logger.info(
            "Parallel run complete: %d work units, %d results, failed=%s",
            len(work_units),
            len(results),
            any_failed,
        )

        return any_failed

    def _update_timings(self, results: list[WorkerResult]) -> None:
        """Update the TimingStore with observed durations from results.

        Timing persistence is best-effort: any failure is logged and
        does not affect the test run outcome.

        Args:
            results: Worker results containing durations to persist.
        """
        timing_file = (
            getattr(self.config, "parallel_timing_file", None) or ".behave-pool-timing.json"
        )
        try:
            store = TimingStore(path=Path(timing_file))
            store.load()
            for result in results:
                store.update(result.work_unit_id, result.duration)
            store.save_if_changed()
        except Exception:
            logger.warning(
                "Failed to update timing file %s; timings will not persist.", timing_file
            )

    def _merge_reports(self, results: list[WorkerResult]) -> None:
        """Merge per-worker JSON reports into a unified Behave-compatible JSON.

        Reads each worker's report file (pointed to by WorkerResult.report_path),
        collects all feature dicts, computes aggregate statistics, detects the
        runtime environment, and writes a full behave-modern-json-report
        ExecutionReport JSON to the path specified by ``--parallel-report``.

        After merging, the temporary ``tmp/`` directory is cleaned up.

        Args:
            results: Worker results with report paths to merge.
        """
        import json

        all_features: list[dict[str, Any]] = []

        for result in results:
            if not result.report_path:
                continue
            try:
                report_file = Path(result.report_path)
                if report_file.exists():
                    data = json.loads(report_file.read_text(encoding="utf-8"))
                    all_features.extend(data.get("features", []))
            except Exception:
                logger.warning(
                    "Failed to read worker report %s; skipping.", result.report_path
                )

        statistics = self._compute_statistics(all_features)
        environment = self._detect_environment()
        execution = self._build_execution(results)

        report = {
            "schemaVersion": "1.1.0",
            "execution": execution,
            "statistics": statistics,
            "environment": environment,
            "features": all_features,
            "metadata": {},
        }

        report_path = Path(
            getattr(self.config, "parallel_report", None) or "behave-pool-report.json"
        )
        try:
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("Unified report written to %s", report_path)
        except Exception:
            logger.warning("Failed to write unified report to %s", report_path)

        tmp_dir = Path("tmp")
        if tmp_dir.is_dir():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _compute_statistics(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute aggregate statistics from merged feature dicts."""
        _status_fields = {
            "passed": "passed",
            "failed": "failed",
            "skipped": "skipped",
            "undefined": "undefined",
            "pending": "pending",
        }
        _failed_statuses = frozenset({"failed", "error", "hook_error", "cleanup_error"})

        feature_count = 0
        scenario_count = 0
        step_count = 0
        counts: dict[str, int] = dict.fromkeys(_status_fields.values(), 0)
        total_duration = 0.0
        error_count = 0
        slowest_step_duration = 0.0
        all_durations: list[float] = []
        exception_counts: dict[str, int] = {}
        by_tag: dict[str, dict[str, Any]] = {}

        for feature in features:
            feature_count += 1
            feature_duration = 0.0

            for scenario in feature.get("scenarios", []) or []:
                scenario_count += 1
                scenario_duration = 0.0

                for step in scenario.get("steps", []) or []:
                    step_count += 1
                    status = step.get("status", "untested")
                    field_name = _status_fields.get(status)
                    if field_name is not None:
                        counts[field_name] += 1
                    step_duration = step.get("duration", 0.0) or 0.0
                    scenario_duration += step_duration
                    if status in _failed_statuses:
                        error_count += 1
                    slowest_step_duration = max(slowest_step_duration, step_duration)
                    error = step.get("error")
                    if error and error.get("type"):
                        etype = error["type"]
                        exception_counts[etype] = exception_counts.get(etype, 0) + 1

                scenario_duration = scenario.get("duration", 0.0) or scenario_duration
                all_durations.append(scenario_duration)
                feature_duration += scenario_duration

                scenario_tags = set(scenario.get("tags", []) or [])
                feature_tags = set(feature.get("tags", []) or [])
                for tag in scenario_tags | feature_tags:
                    tag_data = by_tag.setdefault(
                        tag,
                        {
                            "count": 0,
                            "duration": 0.0,
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "undefined": 0,
                            "pending": 0,
                            "untested": 0,
                            "error": 0,
                            "hook_error": 0,
                            "cleanup_error": 0,
                            "xfailed": 0,
                            "xpassed": 0,
                        },
                    )
                    tag_data["count"] += 1
                    tag_data["duration"] += scenario_duration
                    s = scenario.get("status", "passed")
                    if s in tag_data:
                        tag_data[s] += 1

            total_duration += feature.get("duration", 0.0) or feature_duration

        total_terminal = counts["passed"] + counts["failed"]
        pass_rate = (counts["passed"] / total_terminal) if total_terminal else 0.0
        avg_scenario_duration = (
            sum(all_durations) / len(all_durations) if all_durations else 0.0
        )
        common_exception_type = (
            max(exception_counts, key=lambda k: exception_counts.get(k, 0))
            if exception_counts
            else None
        )

        stats: dict[str, Any] = {
            "features": feature_count,
            "scenarios": scenario_count,
            "steps": step_count,
            "passed": counts["passed"],
            "failed": counts["failed"],
            "skipped": counts["skipped"],
            "undefined": counts["undefined"],
            "pending": counts["pending"],
            "passRate": round(pass_rate, 6),
            "duration": round(total_duration, 6),
            "errorCount": error_count,
            "totalAttachments": 0,
            "totalLogs": 0,
            "slowestStepDuration": round(slowest_step_duration, 6),
            "avgScenarioDuration": round(avg_scenario_duration, 6),
            "byTag": by_tag,
        }
        if common_exception_type is not None:
            stats["commonExceptionType"] = common_exception_type
        return stats

    def _detect_environment(self) -> dict[str, Any]:
        """Detect runtime environment for the report."""
        import os
        import platform as _platform
        import socket
        import subprocess
        import sys

        env: dict[str, Any] = {}

        env["pythonVersion"] = sys.version.split(" ", 1)[0]
        env["platform"] = sys.platform
        env["os"] = _platform.system() or "Unknown"
        env["osVersion"] = _platform.release() or "Unknown"

        try:
            env["hostname"] = socket.gethostname() or "unknown"
        except Exception:
            env["hostname"] = "unknown"

        ci_env = os.environ
        if ci_env.get("GITHUB_ACTIONS") == "true":
            env["ciProvider"] = "github-actions"
        elif ci_env.get("GITLAB_CI"):
            env["ciProvider"] = "gitlab-ci"
        elif ci_env.get("JENKINS_URL"):
            env["ciProvider"] = "jenkins"
        elif ci_env.get("CI"):
            env["ciProvider"] = "ci"

        cwd = os.getcwd()
        if cwd:
            env["cwd"] = cwd

        cmd = " ".join(sys.argv)
        if cmd:
            env["command"] = cmd

        try:
            import getpass

            env["user"] = getpass.getuser()
        except Exception:
            pass

        cpu = os.cpu_count()
        if cpu:
            env["cpuCount"] = cpu

        try:
            import behave

            bv = str(getattr(behave, "__version__", "") or "")
            if bv:
                env["behaveVersion"] = bv
        except Exception:
            pass

        git_info: dict[str, str] = {}
        try:
            for key, cmd in [
                ("branch", ["git", "rev-parse", "--abbrev-ref", "HEAD"]),
                ("commit", ["git", "rev-parse", "--short", "HEAD"]),
                ("remote", ["git", "remote", "get-url", "origin"]),
            ]:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=2, check=False
                )
                if result.returncode == 0:
                    git_info[key] = result.stdout.strip()
        except Exception:
            pass

        if git_info.get("branch"):
            env["gitBranch"] = git_info["branch"]
        if git_info.get("commit"):
            env["gitCommit"] = git_info["commit"]
        if git_info.get("remote"):
            env["gitRemote"] = git_info["remote"]

        return env

    def _build_execution(self, results: list[WorkerResult]) -> dict[str, Any]:
        """Build the execution metadata block."""
        import uuid
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        total_duration = sum(r.duration for r in results)
        any_failed = any(r.failed for r in results)

        execution: dict[str, Any] = {
            "executionId": f"exec-{uuid.uuid4().hex}",
            "status": "failed" if any_failed else "passed",
            "duration": round(total_duration, 6),
            "startTime": now,
            "endTime": now,
        }
        return execution
