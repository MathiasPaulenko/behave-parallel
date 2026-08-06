"""Sharding support for CI parallelism across multiple machines.

Sharding divides the total scenario list into ``total_shards`` contiguous
groups.  Each CI runner executes only its assigned shard (``shard_index``).

The algorithm:

1. Parse all scenarios from the features directory using behave-model.
2. Sort deterministically by ``feature.name`` → ``scenario.name``.
3. Split the sorted list into ``total_shards`` groups.  The first
   ``len % total_shards`` shards receive one extra scenario.
4. Execute only the ``shard_index``-th group (1-based).

Sharding composes with ``--parallel`` (local parallelism within a shard)
and ``@serial`` (serial scenarios within a shard run sequentially).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from behave.exception import ConfigError
from behave.runner import parse_features

if TYPE_CHECKING:
    from behave.model import Feature, Scenario

    from behave_pool.work_unit import WorkUnit

T = TypeVar("T")


class ShardError(ValueError, ConfigError):  # type: ignore[misc]
    """Raised when shard configuration or parsing is invalid.

    Also inherits from :class:`behave.exception.ConfigError` so that
    behave's ``main()`` catches it and prints a clean error message
    instead of a raw traceback.
    """


_SHARD_RE = re.compile(r"^(?P<index>\d+)/(?P<total>\d+)$")


@dataclass(frozen=True)
class ShardConfig:
    """Configuration for sharding.

    Attributes:
        shard_index: 1-based index of the shard to execute.
        total_shards: Total number of shards the suite is divided into.
        features_dir: Path to the features directory to scan.
        parallel: Number of local worker processes (0 or 1 = sequential).
    """

    shard_index: int
    total_shards: int
    features_dir: str = "features/"
    parallel: int = 1

    def __post_init__(self) -> None:
        validate_shard(self.shard_index, self.total_shards)


def parse_shard_string(value: str) -> ShardConfig:
    """Parse a ``INDEX/TOTAL`` shard string into a :class:`ShardConfig`.

    Args:
        value: String like ``"1/3"``.

    Returns:
        A :class:`ShardConfig` with ``shard_index`` and ``total_shards`` set.

    Raises:
        ShardError: If the string is malformed or values are out of range.
    """
    match = _SHARD_RE.match(value.strip())
    if not match:
        msg = (
            f"Invalid shard format {value!r}. "
            "Expected 'INDEX/TOTAL' (e.g. '1/3')."
        )
        raise ShardError(msg)

    shard_index = int(match.group("index"))
    total_shards = int(match.group("total"))
    validate_shard(shard_index, total_shards)
    return ShardConfig(shard_index=shard_index, total_shards=total_shards)


def validate_shard(shard_index: int, total_shards: int) -> None:
    """Validate shard parameters.

    Args:
        shard_index: 1-based shard index.
        total_shards: Total number of shards.

    Raises:
        ShardError: If ``total_shards`` < 1 or ``shard_index`` is out of range.
    """
    if total_shards < 1:
        msg = f"total_shards must be >= 1, got {total_shards}"
        raise ShardError(msg)
    if shard_index < 1:
        msg = f"shard_index must be >= 1, got {shard_index}"
        raise ShardError(msg)
    if shard_index > total_shards:
        msg = (
            f"shard_index ({shard_index}) must be <= total_shards ({total_shards})"
        )
        raise ShardError(msg)


def collect_scenarios(features_dir: str) -> list[tuple[Feature, Scenario]]:
    """Parse all scenarios from a features directory.

    Args:
        features_dir: Path to the directory containing ``.feature`` files.

    Returns:
        A list of ``(feature, scenario)`` tuples in parse order.
    """
    from pathlib import Path

    base = Path(features_dir)
    feature_files = sorted(base.rglob("*.feature"))
    features = parse_features(
        [str(f) for f in feature_files],
    )
    result: list[tuple[Feature, Scenario]] = []
    for feature in features:
        for scenario in getattr(feature, "scenarios", None) or []:
            result.append((feature, scenario))
    return result


def sort_scenarios(
    pairs: list[tuple[Feature, Scenario]],
) -> list[tuple[Feature, Scenario]]:
    """Sort scenario pairs deterministically by feature name then scenario name.

    Args:
        pairs: List of ``(feature, scenario)`` tuples.

    Returns:
        Sorted list.
    """
    return sorted(
        pairs,
        key=lambda pair: (
            getattr(pair[0], "name", None) or "",
            getattr(pair[1], "name", None) or "",
        ),
    )


def split_shards(
    items: list[T],
    shard_index: int,
    total_shards: int,
) -> list[T]:
    """Split a list into ``total_shards`` contiguous groups and return group ``shard_index``.

    The first ``len(items) % total_shards`` shards receive one extra item.

    Args:
        items: Sorted list of items to split.
        shard_index: 1-based shard index.
        total_shards: Total number of shards.

    Returns:
        The slice of items belonging to the requested shard.
    """
    validate_shard(shard_index, total_shards)
    n = len(items)
    base_size = n // total_shards
    remainder = n % total_shards

    start = (shard_index - 1) * base_size + min(shard_index - 1, remainder)
    count = base_size + (1 if shard_index <= remainder else 0)
    return items[start : start + count]


def select_shard_work_units(
    work_units: list[WorkUnit],
    shard_index: int,
    total_shards: int,
) -> list[WorkUnit]:
    """Select the work units belonging to a shard.

    Work units are sorted by their ``id`` (which encodes the feature path)
    to ensure deterministic, reproducible sharding across machines.

    Args:
        work_units: All work units from the planning phase.
        shard_index: 1-based shard index.
        total_shards: Total number of shards.

    Returns:
        Work units assigned to the requested shard.
    """
    sorted_units = sorted(work_units, key=lambda u: u.id)
    return split_shards(sorted_units, shard_index, total_shards)


def run_with_shard(config: ShardConfig) -> bool:
    """Run a single shard of the test suite.

    Parses all scenarios, sorts them, selects the shard, and executes it.
    When ``config.parallel > 1``, scenarios within the shard are distributed
    among local workers using the existing LPT dispatch.

    Args:
        config: Shard configuration.

    Returns:
        ``True`` if any test failed (Behave convention).
    """
    from behave.configuration import Configuration

    from behave_pool.runner import ParallelRunner

    behave_config = Configuration(
        command_args=[config.features_dir],
        load_config=False,
        jobs=config.parallel,
    )
    behave_config.shard_index = config.shard_index
    behave_config.total_shards = config.total_shards

    runner = ParallelRunner(behave_config)
    return runner.run()
