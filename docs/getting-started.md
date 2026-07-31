# Getting started

This guide walks you through installing `behave-pool`, registering the runner,
and running your first parallel test suite.

## Installation

### From PyPI

```bash
pip install behave-pool
```

### With ecosystem extras

```bash
pip install "behave-pool[ecosystem]"
```

This installs optional packages:

- `behave-priority` — Priority-based scenario ordering
- `behave-modern-json-report` — Modern JSON report format

### From source

```bash
git clone https://github.com/MathiasPaulenko/behave-pool.git
cd behave-pool
pip install -e ".[dev]"
```

## Register the runner

`behave-pool` implements Behave's `ITestRunner` interface. You need to register
it so Behave knows how to load it.

### Option A: `behave.ini`

Create or edit `behave.ini` in your project root:

```ini
[behave.runners]
parallel = behave_pool:ParallelRunner
```

### Option B: `setup.cfg` / `pyproject.toml` (entry point)

If you distribute your test suite as a package, add the entry point in your
`pyproject.toml`:

```toml
[project.entry-points."behave.runners"]
parallel = "behave_pool:ParallelRunner"
```

### Option C: Command-line `--runner`

You can skip registration entirely and pass the runner inline:

```bash
behave --runner=behave_pool:ParallelRunner --parallel 4 features/
```

## Your first parallel run

Make sure you have a `features/` directory with at least two `.feature` files.

=== "bash"

    ```bash
    behave --runner=parallel --parallel 4 features/
    ```

=== "behave.ini"

    ```ini
    [behave]
    parallel = 4

    [behave.runners]
    parallel = behave_pool:ParallelRunner
    ```

    Then simply run:

    ```bash
    behave features/
    ```

### What happens?

1. `ParallelRunner` parses all `.feature` files in `features/`.
2. It creates one `WorkUnit` per feature file.
3. It launches 4 worker processes (using `spawn` start method).
4. Each worker consumes work units from a shared queue.
5. Results are collected and aggregated.
6. A `.behave-pool-timing.json` file is created with observed durations.

### Output example

```
Feature: Login functionality
  Scenario: User logs in with valid credentials ... passed
  Scenario: User logs in with invalid credentials ... passed

Feature: Checkout flow
  Scenario: Add item to cart ... passed
  Scenario: Complete purchase ... passed

2 features passed, 0 failed, 0 skipped
4 scenarios passed, 0 failed, 0 skipped
```

## Choosing the number of workers

A good starting point is the number of CPU cores:

```bash
# Check available cores
python -c "import os; print(os.cpu_count())"

# Use that many workers
behave --runner=parallel --parallel 8 features/
```

!!! tip "Rule of thumb"
    Start with `--parallel N` where N = number of CPU cores. If features are
    very fast (< 1s), fewer workers may be better due to spawn overhead. If
    features are slow (I/O bound), more workers than cores can improve
    throughput.

## Verifying installation

```bash
python -c "from behave_pool import ParallelRunner; print(ParallelRunner)"
```

Expected output:

```
<class 'behave_pool.runner.ParallelRunner'>
```

## Next steps

- [Configuration](configuration.md) — Learn about all CLI options and `behave.ini` settings
- [Serial scenarios](serial-scenarios.md) — Handle non-parallelizable scenarios with `@serial`
- [LPT balancing](lpt-balancing.md) — Optimize wall-clock time with LPT scheduling
- [Examples](examples.md) — See complete worked examples
