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

## behave.ini configuration

All options can be set permanently in `behave.ini`:

```ini
[behave]
parallel = 4
parallel-scheme = feature
parallel-balance = lpt
parallel-timing-file = .behave-pool-timing.json

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
