# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project setup: scaffold, CI/CD, pre-commit, MkDocs configuration.
- `ParallelRunner` stub that delegates to standard Behave `Runner` (passthrough mode).
- `TimingStore` for persisting historical work unit durations as JSON.
- LPT (Longest Processing Time) load balancing via `--parallel-balance lpt|fifo`.
- `--parallel-timing-file` CLI option for custom timing file path.
- `@serial` tag support: two-phase dispatch (parallel then serial).
- Behave runner entry point (`behave.runners`) for `--runner=` registration.

### Fixed

- `TimingStore.load()` now catches `TypeError` for non-numeric JSON values.
- `TimingStore.save()` now uses atomic writes (temp file + rename) to prevent corruption.
- `TimingStore.save()` narrowed `except Exception` to `except OSError`.
- `WorkerRunner._write_report()` now reflects actual feature pass/fail status.
- `WorkerRunner._write_report()` now catches all exceptions (not just `OSError`),
  preventing non-serializable feature data from causing `TypeError` to propagate
  and incorrectly marking a work unit as failed.
- `WorkerRunner.run_work_unit()` now resets `self.aborted` before each work unit,
  preventing silent feature skips in subsequent work units after a KeyboardInterrupt
  or other abort in a previous work unit.
- `WorkerRunner.teardown()` is now safe when `setup()` did not complete.
- `WorkerRunner.run_work_unit()` now parses feature files from `WorkUnit.feature_path`
  via `parse_features` before running, fixing zero-feature execution in workers.
- `WorkerRunner.load_step_definitions()` now sets `self.step_registry` from the global
  Behave step registry, fixing `feature.run()` crashes in worker processes.
- `WorkerRunner._worker_run_loop()` now catches `EOFError`/`OSError` on closed task
  queue and exits gracefully instead of crashing.
- `WorkerRunner._worker_run_loop()` uses `task_queue.get(timeout=5)` instead of
  blocking `get()` to allow periodic `stop_event` checks.
- `ParallelRunner._dispatch()` skips launching parallel workers when batch is empty.
- `ParallelRunner._dispatch()` sets `stop_event` for workers that exceed join timeout.
- `ParallelRunner._dispatch()` skips serial phase when `stop_event` is set during
  parallel phase, preventing infinite block.
- `ParallelRunner._dispatch()` replaces `task_queue.join()` with `worker.join(timeout=300)`
  and explicit queue drain, preventing deadlock when workers exit prematurely or hang indefinitely.
  Workers that don't terminate within the timeout are now forcibly terminated via
  `WorkerProcess.terminate()`.
- `ParallelRunner._collect()` detects missing results from crashed workers and treats
  them as failures.
- `ParallelRunner._collect()` narrows `except` clause to `queue.Empty`/`EOFError`/`OSError`.
- `ParallelRunner._dispatch()` now returns the list of actually dispatched work units.
  `_run_parallel()` passes only dispatched units to `_collect()`, preventing false
  "missing results" warnings and a 30-second wait for serial units that were never
  enqueued when `stop_event` was set during the parallel phase.
- `ParallelRunner._run_parallel()` cleans up queues in `finally` block.
- `ConfigSnapshot` now includes `parallel`, `parallel_scheme`, `parallel_balance`,
  `parallel_timing_file`, `dry_run`, and `use_nested_step_modules` fields.
- `_make_config()` now sets all parallel-related fields from `ConfigSnapshot`.
- Entry point group corrected from `behave.plugins` to `behave.runners` in
  `pyproject.toml`.
- `__init__.py` docstring corrected: feature-level parallelization, not scenario.
- `config.py` help text corrected: removed stale scenario reference.
- `iterator.py` error message corrected: removed stale F9 reference.
- `_worker_run_loop()` now sets `stop_event` when a worker aborts, ensuring other
  workers stop cooperatively and the coordinator skips the serial phase. Without
  this, the aborted worker's sentinel remained in the queue and another worker
  could consume it and exit early, leaving work units unprocessed.
- Removed dead `TYPE_CHECKING` block in `work_unit.py`.
- Added picklability regression tests for `WorkerResult` and `WorkUnit`, both
  of which are sent through `multiprocessing.Queue` / `JoinableQueue` and must
  survive pickle round-trips.
- `ParallelRunner._collect()` now accepts a `deadline_seconds` parameter
  (default 30s) so tests can exercise the missing-result path without waiting
  the full 30-second deadline.
- Added regression test verifying `WorkerRunner.run_work_unit()` catches
  `parse_features` exceptions and returns a failed `WorkerResult` instead of
  propagating.
