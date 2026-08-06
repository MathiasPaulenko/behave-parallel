# Configuration

`behave-pool` adds several CLI options and `behave.ini` settings to control
parallel execution. This page documents every option with examples.

## CLI options

### `--parallel N`

| | |
|---|---|
| **Default** | `1` |
| **Type** | integer |
| **Description** | Number of worker processes. `1` = sequential passthrough (standard Behave). |

```bash
# 4 worker processes
behave --runner=parallel --parallel 4 features/

# Sequential (same as standard behave)
behave --runner=parallel --parallel 1 features/

# Auto-detect from --jobs (behave's built-in option)
behave --runner=parallel --jobs 4 features/
```

!!! note "`--parallel` vs `--jobs`"
    `behave-pool` maps Behave's built-in `--jobs` option to `--parallel`.
    You can use either. If both are specified, `--jobs` takes precedence.

---

### `--parallel-scheme`

| | |
|---|---|
| **Default** | `feature` |
| **Choices** | `feature` |
| **Description** | Parallelization unit: one work unit per feature file. |

```bash
# Feature-level parallelization (default)
behave --runner=parallel --parallel 4 --parallel-scheme feature features/
```

!!! warning "Scenario scheme"
    `--parallel-scheme scenario` is recognized but not yet implemented.
    It will raise `NotImplementedError`. Scenario-level parallelization
    is planned for a future release.

---

### `--parallel-balance`

| | |
|---|---|
| **Default** | `lpt` |
| **Choices** | `lpt`, `fifo` |
| **Description** | Work unit ordering strategy. |

=== "LPT (default)"

    Longest Processing Time first. Features are sorted descending by their
    historical duration so the slowest features start first, minimizing
    total wall-clock time.

    ```bash
    behave --runner=parallel --parallel 4 --parallel-balance lpt features/
    ```

    Requires a timing file (see `--parallel-timing-file`). On the first run,
    when no timing data exists, all durations default to `0.0` and LPT
    ordering has no effect.

=== "FIFO"

    First In, First Out. Work units are dispatched in the order features are
    discovered (alphabetical by filename).

    ```bash
    behave --runner=parallel --parallel 4 --parallel-balance fifo features/
    ```

---

### `--parallel-timing-file`

| | |
|---|---|
| **Default** | `.behave-pool-timing.json` |
| **Type** | string (file path) |
| **Description** | Path to the JSON file storing historical durations for LPT balancing. |

```bash
# Custom timing file location
behave --runner=parallel --parallel 4 \
    --parallel-timing-file .my-timings.json \
    features/
```

The timing file is a simple JSON object mapping work unit IDs to durations
in seconds:

```json
{
  "feature:features/login.feature": 1.23,
  "feature:features/checkout.feature": 0.45,
  "feature:features/search.feature": 2.10
}
```

!!! tip "Gitignore"
    Add `.behave-pool-timing.json` to your `.gitignore` — it's a local
    optimization artifact, not something you should commit.

---

### `--parallel-report`

| | |
|---|---|
| **Default** | `behave-pool-report.json` |
| **Type** | string (file path) |
| **Description** | Path to the unified JSON report file. After all workers finish, their individual reports are merged into a single Behave-compatible JSON array. |

```bash
# Default report path
behave --runner=parallel --parallel 4 features/
# → writes behave-pool-report.json

# Custom report path
behave --runner=parallel --parallel 4 \
    --parallel-report reports/run-2024-01-15.json \
    features/
```

The report follows the **behave-modern-json-report** `ExecutionReport` schema
(v1.1.0), a rich structured format with execution metadata, statistics,
environment info, and full feature/scenario/step details:

```json
{
  "schemaVersion": "1.1.0",
  "execution": {
    "executionId": "exec-a1b2c3...",
    "status": "passed",
    "duration": 12.345,
    "startTime": "2024-01-15T10:30:00.123Z",
    "endTime": "2024-01-15T10:30:12.468Z"
  },
  "statistics": {
    "features": 3,
    "scenarios": 15,
    "steps": 42,
    "passed": 40,
    "failed": 0,
    "skipped": 2,
    "passRate": 1.0,
    "duration": 12.345,
    "byTag": {
      "@smoke": { "count": 5, "duration": 3.2, "passed": 5 }
    }
  },
  "environment": {
    "pythonVersion": "3.12.1",
    "behaveVersion": "1.2.6",
    "platform": "linux",
    "os": "Linux",
    "ciProvider": "github-actions",
    "gitBranch": "main",
    "gitCommit": "a1b2c3d"
  },
  "features": [
    {
      "id": "feature-abc123",
      "name": "Login",
      "description": "User authentication flows",
      "filename": "features/login.feature",
      "line": 1,
      "tags": ["@smoke"],
      "status": "passed",
      "duration": 1.23,
      "scenarios": [
        {
          "id": "scenario-def456",
          "name": "Successful login",
          "featureId": "feature-abc123",
          "status": "passed",
          "duration": 0.8,
          "steps": [
            {
              "id": "step-ghi789",
              "keyword": "Given ",
              "text": "I am on the login page",
              "status": "passed",
              "duration": 0.2,
              "error": null,
              "attachments": [],
              "logs": []
            }
          ]
        }
      ]
    }
  ],
  "metadata": {}
}
```

!!! note "Downstream tools"
    The report uses the same schema as `behave-modern-json-report`, so any
    tool built for that ecosystem (HTML formatters, dashboards, AI analyzers)
    can consume the parallel report directly — no conversion needed.

### `--shard`

| | |
|---|---|
| **Default** | _(disabled)_ |
| **Type** | string (`INDEX/TOTAL`) |
| **Description** | Split the suite into `TOTAL` shards and run shard `INDEX` (1-based). |

```bash
# Run shard 1 of 3 with 4 local workers
behave --runner=parallel --parallel 4 --shard 1/3 features/

# Run shard 2 of 3
behave --runner=parallel --parallel 4 --shard 2/3 features/
```

Sharding divides work units into `TOTAL` contiguous groups. The first
`len % TOTAL` shards receive one extra work unit. Work units are sorted
deterministically by ID before splitting, ensuring reproducible shard
assignment across machines.

!!! note "Compatibility"
    Sharding composes with all other features:
    
    - **`--parallel`**: local parallelism within each shard.
    - **`@serial`**: serial scenarios run sequentially within the shard.
    - **`--tags`**: tag filtering applies before sharding.

!!! warning "Validation"
    Invalid shard values raise `ShardError`:
    
    - `shard_index` must be in `[1, total_shards]`.
    - `total_shards` must be `>= 1`.
    - Format must be `INDEX/TOTAL` (e.g. `1/3`, not `1-3` or `1of3`).

Output includes shard metadata for CI visibility:

```
Shard 1/3 — 4 scenarios selected (of 10 total)
```

---

## behave.ini configuration

All options can be set permanently in `behave.ini`:

```ini
[behave]
parallel = 4
parallel-scheme = feature
parallel-balance = lpt
parallel-timing-file = .behave-pool-timing.json
parallel-report = behave-pool-report.json
shard = 1/3

[behave.runners]
parallel = behave_pool:ParallelRunner
```

With this configuration, running `behave features/` will automatically use
4 worker processes with LPT balancing.

### Example: CI vs local development

You can use different `behave.ini` files for CI and local development:

=== "CI (fast feedback)"

    ```ini
    [behave]
    parallel = 8
    parallel-balance = lpt

    [behave.runners]
    parallel = behave_pool:ParallelRunner
    ```

=== "Local (debugging)"

    ```ini
    [behave]
    parallel = 1

    [behave.runners]
    parallel = behave_pool:ParallelRunner
    ```

## Environment variables

`behave-pool` does not introduce any environment variables. All configuration
is done through CLI options or `behave.ini`.

## Default values summary

| Option | Default | Choices |
| --- | --- | --- |
| `--parallel` | `1` | any positive integer |
| `--parallel-scheme` | `feature` | `feature` |
| `--parallel-balance` | `lpt` | `lpt`, `fifo` |
| `--parallel-timing-file` | `.behave-pool-timing.json` | any file path |
| `--shard` | _(disabled)_ | `INDEX/TOTAL` (e.g. `1/3`) |
