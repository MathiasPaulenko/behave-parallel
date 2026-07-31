# Ecosystem

`behave-pool` is designed to integrate with other packages in the Behave
ecosystem. This page covers the optional integrations available.

## behave-priority

[**behave-priority**](https://pypi.org/project/behave-priority/) provides
priority-based scenario ordering. Scenarios tagged with `@priority.high`,
`@priority.medium`, or `@priority.low` are executed in priority order.

### Installation

```bash
pip install "behave-pool[ecosystem]"
```

Or separately:

```bash
pip install behave-priority
```

### Usage with behave-pool

`behave-priority` works as a Behave runner that wraps `ParallelRunner`.
Register both in `behave.ini`:

```ini
[behave.runners]
parallel = behave_pool:ParallelRunner
priority = behave_priority:PriorityRunner
```

Run with priority ordering and parallel execution:

```bash
behave --runner=priority --parallel 4 features/
```

### Example feature with priorities

```gherkin
Feature: User management

  @priority.high
  Scenario: Admin can create users
    Given I am an admin
    When I create a new user
    Then the user should exist

  @priority.medium
  Scenario: User can update profile
    Given I am a registered user
    When I update my profile
    Then my profile should be updated

  @priority.low
  Scenario: User can delete account
    Given I am a registered user
    When I delete my account
    Then my account should be removed
```

## behave-modern-json-report

[**behave-modern-json-report**](https://pypi.org/project/behave-modern-json-report/)
provides a modern JSON report format for Behave test results, with richer
output than Behave's built-in JSON formatter.

### Installation

```bash
pip install "behave-pool[ecosystem]"
```

Or separately:

```bash
pip install behave-modern-json-report
```

### Usage with behave-pool

Register the formatter in `behave.ini`:

```ini
[behave]
format = modern-json

[behave.formatters]
modern-json = behave_modern_json_report:ModernJSONFormatter

[behave.runners]
parallel = behave_pool:ParallelRunner
```

Run with JSON output:

```bash
behave --runner=parallel --parallel 4 --format=modern-json --outfile=report.json features/
```

### Output format

The modern JSON report includes:

- Feature, scenario, and step-level results
- Durations for each level
- Error messages and tracebacks
- Tags and metadata

```json
{
  "features": [
    {
      "name": "Login functionality",
      "filename": "features/login.feature",
      "status": "passed",
      "duration": 1.23,
      "scenarios": [
        {
          "name": "User logs in with valid credentials",
          "status": "passed",
          "duration": 0.45,
          "steps": [...]
        }
      ]
    }
  ],
  "summary": {
    "total_features": 1,
    "total_scenarios": 1,
    "passed": 1,
    "failed": 0,
    "duration": 1.23
  }
}
```

## Using all ecosystem packages together

```bash
pip install "behave-pool[ecosystem]"
```

```ini
[behave]
parallel = 4
parallel-balance = lpt
format = modern-json

[behave.runners]
parallel = behave_pool:ParallelRunner

[behave.formatters]
modern-json = behave_modern_json_report:ModernJSONFormatter
```

```bash
behave --format=modern-json --outfile=report.json features/
```

This gives you:

- **Parallel execution** with 4 worker processes
- **LPT load balancing** for optimal wall-clock time
- **Modern JSON output** for CI integration and reporting

## Compatibility

| Package | Status | Notes |
| --- | --- | --- |
| `behave-priority` | Compatible | Works as a wrapping runner |
| `behave-modern-json-report` | Compatible | Works as a formatter |
| `behave` | Required (`>=1.3.0`) | Base framework |
| `pytest` | Compatible | For running `behave-pool`'s own test suite |

## Custom integrations

`behave-pool` exposes a stable public API for custom integrations:

```python
from behave_pool import ParallelRunner
from behave_pool.config import ConfigSnapshot, snapshot_config
from behave_pool.work_unit import WorkUnit
from behave_pool.result import WorkerResult
from behave_pool.timing import TimingStore
```

See the [API reference](api-reference.md) for full documentation of these
classes.
