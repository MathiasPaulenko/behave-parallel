# Contributing to behave-pool

Thanks for your interest in contributing! Please read our
[Code of Conduct](CODE_OF_CONDUCT.md) before participating.

## Setup

```bash
git clone https://github.com/MathiasPaulenko/behave-pool.git
cd behave-pool
make dev
pre-commit install
```

## Development commands

| Command             | Description                                  |
| ------------------- | -------------------------------------------- |
| `make help`         | Show all available targets.                  |
| `make dev`          | Install with dev extras.                     |
| `make lint`         | Run `ruff check` + `mypy --strict`.          |
| `make lint-fix`     | Auto-fix lint issues.                        |
| `make format`       | Format the code with `ruff format`.          |
| `make format-check` | Verify formatting without changes.           |
| `make test`         | Run the test suite.                          |
| `make test-cov`     | Run tests with coverage (fail under 90%).    |
| `make check`        | Full pre-commit check (lint + format + test).|
| `make build`        | Build sdist + wheel into `dist/`.            |
| `make docs-serve`   | Serve documentation locally.                 |
| `make clean`        | Remove build artifacts and caches.           |

## Pre-PR checklist

- [ ] `make check` passes
- [ ] `make test-cov` passes with >= 90% coverage
- [ ] New behavior is covered by tests
- [ ] `CHANGELOG.md` updated under `[Unreleased]`

## Release process

Automated via `release.yml` GitHub Actions workflow:

1. Bump version in `pyproject.toml`.
2. Move `[Unreleased]` in `CHANGELOG.md` to the new version.
3. Commit and push to `main`.
4. Workflow detects bump → builds → publishes to PyPI (Trusted Publishing) → creates GitHub Release.

## Code style

- Python >=3.11, `from __future__ import annotations` in every module.
- `ruff` for linting and formatting (line length 100).
- `mypy --strict` with no errors.
- Public API documented with docstrings (Google style).
