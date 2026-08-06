# Sharding

Sharding splits the test suite into independent groups so multiple CI runners
can execute different shards in parallel across separate machines.

## Overview

```
CI Runner 1: --shard 1/3    CI Runner 2: --shard 2/3    CI Runner 3: --shard 3/3
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  Shard 1 of 3    │        │  Shard 2 of 3    │        │  Shard 3 of 3    │
│  Features A, B   │        │  Features C, D   │        │  Features E, F   │
│  --parallel 4    │        │  --parallel 4    │        │  --parallel 4    │
│  4 local workers │        │  4 local workers │        │  4 local workers │
└──────────────────┘        └──────────────────┘        └──────────────────┘
```

Each CI runner executes only its assigned shard. Within each shard,
`--parallel` provides local parallelism as usual.

## Usage

### CLI

```bash
# 3 CI runners, each with 4 local workers
behave --runner=parallel --parallel 4 --shard 1/3 features/
behave --runner=parallel --parallel 4 --shard 2/3 features/
behave --runner=parallel --parallel 4 --shard 3/3 features/
```

### behave.ini

```ini
[behave]
parallel = 4
shard = 1/3
```

### Python API

```python
from behave_pool import ShardConfig, run_with_shard

config = ShardConfig(
    shard_index=1,
    total_shards=3,
    features_dir="features/",
    parallel=4,
)
failed = run_with_shard(config)
```

## Algorithm

1. **Parse** all features and create work units (same as normal planning).
2. **Sort** work units deterministically by ID (feature path).
3. **Split** the sorted list into `TOTAL` contiguous groups. The first
   `len % TOTAL` shards receive one extra work unit.
4. **Execute** only the `INDEX`-th group (1-based).

This ensures:

- **Deterministic** shard assignment — the same feature always lands in
  the same shard given the same `TOTAL`.
- **No overlap** — every work unit belongs to exactly one shard.
- **Even distribution** — shard sizes differ by at most one work unit.

## Compatibility

Sharding composes with all other `behave-pool` features:

| Feature | Behavior with sharding |
| --- | --- |
| `--parallel N` | Local parallelism within each shard. Shard filtering happens first, then work units are distributed among N workers. |
| `@serial` tag | Serial scenarios within the shard run sequentially after the parallel phase. |
| `--tags` | Tag filtering applies before sharding. Only matching scenarios are split into shards. |
| `--parallel-balance` | LPT/FIFO ordering applies within the shard. |
| `--parallel-report` | Each shard produces its own report file. |

### Execution order

```
1. Tag filtering (--tags)
       ↓
2. Sharding (--shard INDEX/TOTAL)
       ↓
3. Serial/parallel split (@serial)
       ↓
4. LPT ordering (--parallel-balance)
       ↓
5. Local dispatch (--parallel N)
```

## Validation

Invalid shard values raise `ShardError` with a clear message:

| Input | Error |
| --- | --- |
| `--shard 0/3` | `shard_index must be >= 1, got 0` |
| `--shard 4/3` | `shard_index (4) must be <= total_shards (3)` |
| `--shard 1/0` | `total_shards must be >= 1, got 0` |
| `--shard invalid` | `Invalid shard format 'invalid'. Expected 'INDEX/TOTAL' (e.g. '1/3').` |
| `--shard 13` | `Invalid shard format '13'. Expected 'INDEX/TOTAL' (e.g. '1/3').` |

## Output

When sharding is active, the runner logs shard metadata:

```
Shard 1/3 — 4 scenarios selected (of 10 total)
Running 4 scenarios with 4 workers...
```

## CI integration example

### GitHub Actions

```yaml
jobs:
  test:
    strategy:
      matrix:
        shard: [1/3, 2/3, 3/3]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install behave-pool
      - run: behave --runner=parallel --parallel 4 --shard ${{ matrix.shard }} features/
```

### GitLab CI

```yaml
test:
  parallel: 3
  script:
    - pip install behave-pool
    - behave --runner=parallel --parallel 4 --shard ${CI_NODE_INDEX}/${CI_NODE_TOTAL} features/
```
