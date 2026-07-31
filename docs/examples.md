# Examples

Complete worked examples showing how to use `behave-pool` in real projects.

## Example 1: Calculator API

A simple test suite with 3 feature files running in parallel.

### Project structure

```
my-project/
├── behave.ini
├── features/
│   ├── environment.py
│   ├── steps/
│   │   └── calculator_steps.py
│   ├── addition.feature
│   ├── subtraction.feature
│   └── multiplication.feature
```

### `behave.ini`

```ini
[behave]
parallel = 4

[behave.runners]
parallel = behave_pool:ParallelRunner
```

### `features/addition.feature`

```gherkin
Feature: Addition

  Scenario: Add two positive numbers
    Given I have a calculator
    When I add 2 and 3
    Then the result should be 5

  Scenario: Add negative numbers
    Given I have a calculator
    When I add -1 and -2
    Then the result should be -3
```

### `features/subtraction.feature`

```gherkin
Feature: Subtraction

  Scenario: Subtract two numbers
    Given I have a calculator
    When I subtract 5 from 10
    Then the result should be 5

  Scenario: Subtract to get negative
    Given I have a calculator
    When I subtract 10 from 3
    Then the result should be -7
```

### `features/multiplication.feature`

```gherkin
@serial
Feature: Multiplication

  Scenario: Multiply two numbers
    Given I have a calculator
    When I multiply 3 by 4
    Then the result should be 12
```

### `features/steps/calculator_steps.py`

```python
from behave import given, when, then

_calculator = {}
_result = None


@given("I have a calculator")
def step_have_calculator(context):
    _calculator["ready"] = True


@when("I add {a:d} and {b:d}")
def step_add(context, a, b):
    _result = a + b


@when("I subtract {b:d} from {a:d}")
def step_subtract(context, a, b):
    _result = a - b


@when("I multiply {a:d} by {b:d}")
def step_multiply(context, a, b):
    _result = a * b


@then("the result should be {expected:d}")
def step_result(context, expected):
    assert _result == expected, f"Expected {expected}, got {_result}"
```

### Running

```bash
behave features/
```

**Output:**

```
Feature: Addition
  Scenario: Add two positive numbers ... passed
  Scenario: Add negative numbers ... passed

Feature: Subtraction
  Scenario: Subtract two numbers ... passed
  Scenario: Subtract to get negative ... passed

Feature: Multiplication
  Scenario: Multiply two numbers ... passed

5 scenarios passed, 0 failed, 0 skipped
```

**What happened:**

1. `addition.feature` and `subtraction.feature` ran in parallel (2 workers).
2. `multiplication.feature` was tagged `@serial`, so it ran after the parallel
   phase in a single worker.
3. `.behave-pool-timing.json` was created with durations.

## Example 2: Web API test suite

A larger suite with mixed parallel and serial scenarios.

### Project structure

```
api-tests/
├── behave.ini
├── features/
│   ├── environment.py
│   ├── steps/
│   │   ├── auth_steps.py
│   │   ├── user_steps.py
│   │   └── order_steps.py
│   ├── auth.feature
│   ├── users.feature
│   ├── orders.feature
│   └── cleanup.feature
```

### `behave.ini`

```ini
[behave]
parallel = 4
parallel-balance = lpt
parallel-timing-file = .api-test-timings.json

[behave.runners]
parallel = behave_pool:ParallelRunner
```

### `features/auth.feature`

```gherkin
Feature: Authentication

  Scenario: Login with valid credentials
    Given the API is running
    When I login as "admin" with password "secret"
    Then I should receive a valid token

  Scenario: Login with invalid credentials
    Given the API is running
    When I login as "admin" with password "wrong"
    Then I should receive a 401 error
```

### `features/users.feature`

```gherkin
Feature: User management

  Scenario: List all users
    Given I am authenticated as admin
    When I request the user list
    Then I should receive a list of users

  Scenario: Create a new user
    Given I am authenticated as admin
    When I create a user with email "test@example.com"
    Then the user should exist in the database
```

### `features/orders.feature`

```gherkin
Feature: Order processing

  Scenario: Create an order
    Given I am authenticated as a customer
    When I create an order for product "widget"
    Then the order should be created

  @serial
  Scenario: Process pending orders
    Given there are pending orders
    When I trigger order processing
    Then all orders should be processed
```

### `features/cleanup.feature`

```gherkin
@serial
Feature: Cleanup

  Scenario: Remove test data
    Given test data exists
    When I run the cleanup script
    Then no test data should remain
```

### `features/environment.py`

```python
import requests

BASE_URL = "http://localhost:8000"
_token = None


def before_all(context):
    context.base_url = BASE_URL
    context.session = requests.Session()


def before_scenario(context, scenario):
    if "authenticated" in scenario.effective_tags:
        if "admin" in scenario.effective_tags:
            resp = context.session.post(
                f"{context.base_url}/auth/login",
                json={"username": "admin", "password": "secret"},
            )
            context.token = resp.json()["token"]
            context.session.headers["Authorization"] = f"Bearer {context.token}"
        elif "customer" in scenario.effective_tags:
            resp = context.session.post(
                f"{context.base_url}/auth/login",
                json={"username": "customer", "password": "pass"},
            )
            context.token = resp.json()["token"]
            context.session.headers["Authorization"] = f"Bearer {context.token}"


def after_all(context):
    context.session.close()
```

### Running

```bash
# First run — no timing data, features run alphabetically
behave features/

# Second run — LPT uses stored durations
behave features/
```

**Execution order (second run with LPT):**

1. **Parallel phase**: `auth.feature`, `users.feature`, `orders.feature` (without
   the `@serial` scenario) run across 4 workers.
2. **Serial phase**: The `@serial` scenario from `orders.feature` and all
   scenarios from `cleanup.feature` run one at a time.

## Example 3: CI/CD pipeline

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: behave --runner=parallel --parallel 4 features/
```

### GitLab CI

```yaml
test:
  image: python:3.12
  script:
    - pip install behave-pool
    - behave --runner=parallel --parallel 4 features/
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'pip install behave-pool'
                sh 'behave --runner=parallel --parallel 4 features/'
            }
        }
    }
}
```

## Example 4: Custom timing file per environment

```ini
# behave.ci.ini — for CI
[behave]
parallel = 8
parallel-balance = lpt
parallel-timing-file = .ci-timings.json

[behave.runners]
parallel = behave_pool:ParallelRunner
```

```ini
# behave.ini — for local development
[behave]
parallel = 2
parallel-balance = fifo

[behave.runners]
parallel = behave_pool:ParallelRunner
```

```bash
# CI
BEHAVE_CONFIG=behave.ci.ini behave features/

# Local
behave features/
```

## Example 5: Programmatic usage

You can use `behave-pool` programmatically without the `behave` CLI:

```python
from behave.configuration import Configuration
from behave_pool import ParallelRunner

# Create configuration
config = Configuration(["--parallel", "4", "features/"])

# Create and run the parallel runner
runner = ParallelRunner(config)
failed = runner.run()

if failed:
    print("Tests failed!")
    exit(1)
else:
    print("All tests passed!")
```

### Using TimingStore directly

```python
from pathlib import Path
from behave_pool.timing import TimingStore

# Load existing timings
store = TimingStore(path=Path(".behave-pool-timing.json"))
durations = store.load()
print(durations)
# {"feature:features/login.feature": 1.23, ...}

# Get duration for a specific feature
duration = store.get_duration("feature:features/login.feature")
print(f"Login feature took {duration}s last time")

# Update with new duration
store.update("feature:features/login.feature", 1.45)

# Save (only if changed)
saved = store.save_if_changed()
print(f"Saved: {saved}")
```
