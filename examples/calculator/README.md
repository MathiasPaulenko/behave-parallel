# behave-pool calculator example

This example demonstrates how to use `behave-pool` to run Behave features
in parallel.

## Structure

```text
examples/calculator/
  features/
    calculator.feature      # Feature with parallel and @serial scenarios
    steps/
      calculator_steps.py   # Step definitions
```

## Running

From the `examples/calculator` directory:

```bash
# Install behave-pool (if not already installed)
pip install behave-pool

# Run with 4 parallel workers
behave --runner=parallel --parallel 4

# Run with FIFO ordering instead of LPT
behave --runner=parallel --parallel 4 --parallel-balance fifo
```

## What to expect

- The first two scenarios run in parallel across worker processes.
- The `@serial` tagged scenario runs sequentially after all parallel work
  units complete.
- A `.behave-pool-timing.json` file is created to store durations for
  LPT scheduling on subsequent runs.
