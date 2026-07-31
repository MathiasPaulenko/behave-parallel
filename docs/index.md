# behave-pool

Parallel test execution for [Behave](https://github.com/behave/behave) BDD via native `ITestRunner`.

## Quick start

```bash
pip install behave-pool
```

Register the runner in `behave.ini`:

```ini
[behave.runners]
parallel = behave_pool:ParallelRunner
```

Run Behave with parallel workers:

```bash
behave --runner=parallel --parallel 4 --parallel-scheme feature features/
```

## How it works

`behave-pool` implements Behave's `ITestRunner` interface via `ParallelRunner`.
When `--parallel` is greater than 1, the runner:

1. **Plans** — Parses feature files and creates `WorkUnit` objects (one per feature).
2. **Splits** — Separates work units tagged `@serial` from the parallel batch.
3. **Dispatches** — Enqueues parallel work units and launches N worker processes.
   Each worker consumes units from a shared `JoinableQueue`.
4. **Collects** — Drains `WorkerResult` objects from the result queue and aggregates
   pass/fail status.
5. **Serial phase** — Runs `@serial` work units one at a time after all parallel
   workers complete.
6. **Updates timings** — Persists observed durations to `.behave-pool-timing.json`
   for LPT scheduling on subsequent runs.

When `--parallel` is 1, the runner falls back to standard sequential Behave execution.

## CLI options

| Option | Default | Description |
| --- | --- | --- |
| `--parallel N` | `1` | Number of worker processes. `1` = sequential passthrough. |
| `--parallel-scheme` | `feature` | Parallelization unit: `feature` (scenario planned for future). |
| `--parallel-balance` | `lpt` | Work ordering: `lpt` (longest first) or `fifo` (insertion order). |
| `--parallel-timing-file` | `.behave-pool-timing.json` | Path to timing file for LPT balancing. |

## Serial scenarios

Tag scenarios with `@serial` to run them sequentially after all parallel work
units complete:

```gherkin
@serial
Scenario: Database migration
  Given the database is empty
  When I run the migration
  Then all tables should exist
```

## LPT load balancing

By default, `behave-pool` uses Longest Processing Time (LPT) scheduling.
It stores historical durations and dispatches the slowest features first,
minimizing total wall-clock time.

Use `--parallel-balance fifo` to preserve insertion order instead.

## Requirements

- Python >=3.11
- behave >=1.3.0

## API reference

- [ParallelRunner](api-reference.md#behave_pool.runner.ParallelRunner)
- [ConfigSnapshot](api-reference.md#behave_pool.config.ConfigSnapshot)
- [WorkUnit](api-reference.md#behave_pool.work_unit.WorkUnit)
- [WorkerResult](api-reference.md#behave_pool.result.WorkerResult)
- [TimingStore](api-reference.md#behave_pool.timing.TimingStore)
