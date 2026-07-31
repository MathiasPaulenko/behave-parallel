# behave-pool

[![CI](https://github.com/MathiasPaulenko/behave-pool/actions/workflows/ci.yml/badge.svg)](https://github.com/MathiasPaulenko/behave-pool/actions/workflows/ci.yml)
[![Documentation](https://github.com/MathiasPaulenko/behave-pool/actions/workflows/docs.yml/badge.svg)](https://mathiaspaulenko.github.io/behave-pool/)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/behave-pool.svg)](https://pypi.org/project/behave-pool/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Parallel test execution for [Behave](https://github.com/behave/behave) BDD via native `ITestRunner`.

## Features

- **Native ITestRunner** — Registered via `--runner=` or `behave.ini`. Zero monkey-patching.
- **Dynamic dispatch** — `multiprocessing.Process` + `Queue`. Workers consume work units as they finish.
- **@serial tag** — Non-parallelizable scenarios run sequentially after the parallel phase.
- **LPT load balancing** — Historical durations for optimal work distribution.
- **Timing persistence** — `.behave-pool-timing.json` stores durations between runs.
- **Ecosystem integration** — Optional `behave-priority`, `behave-modern-json-report`.
- **Zero heavy dependencies** — Only stdlib `multiprocessing` + `behave>=1.3.0`.

## Installation

```bash
pip install behave-pool
```

## Quick start

1. Register the runner in your `behave.ini`:

```ini
[behave.runners]
parallel = behave_pool:ParallelRunner
```

1. Run Behave with parallel workers:

```bash
behave --runner=parallel --parallel 4 --parallel-scheme feature features/
```

## CLI options

| Option | Default | Description |
| --- | --- | --- |
| `--parallel N` | `1` | Number of worker processes. `1` = sequential passthrough. |
| `--parallel-scheme` | `feature` | Parallelization unit: `feature` (scenario planned for future). |
| `--parallel-balance` | `lpt` | Work ordering: `lpt` (longest first) or `fifo` (insertion order). |
| `--parallel-timing-file` | `.behave-pool-timing.json` | Path to timing file for LPT balancing. |

## Usage

### Feature-level parallelization

Each feature file runs in its own worker process. Workers are dispatched dynamically and consume work units from a shared queue.

```bash
# 4 worker processes, LPT balancing
behave --runner=parallel --parallel 4 features/
```

### Serial scenarios

Tag scenarios with `@serial` to run them sequentially after all parallel work units complete:

```gherkin
@serial
Scenario: Database migration
  Given the database is empty
  When I run the migration
  Then all tables should exist
```

### LPT load balancing

By default, `behave-pool` uses Longest Processing Time (LPT) scheduling. It stores historical durations in `.behave-pool-timing.json` and dispatches the slowest features first, minimizing total wall-clock time.

```bash
# Use FIFO ordering instead of LPT
behave --runner=parallel --parallel 4 --parallel-balance fifo features/
```

### behave.ini configuration

All CLI options can also be set in `behave.ini`:

```ini
[behave]
parallel = 4
parallel-scheme = feature
parallel-balance = lpt
parallel-timing-file = .behave-pool-timing.json
```

## Requirements

- Python >=3.11
- behave >=1.3.0

## Documentation

Full documentation is available at
<https://mathiaspaulenko.github.io/behave-pool/>.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup
instructions and guidelines.

Please review our [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for notable changes.

## License

[MIT](LICENSE) — Copyright (c) 2026 Mathias Paulenko

## Acknowledgements

- [Behave](https://github.com/behave/behave) — the BDD framework this library extends.
- [Contributor Covenant](https://www.contributor-covenant.org/) — Code of Conduct.
- [Keep a Changelog](https://keepachangelog.com/) — Changelog format.
