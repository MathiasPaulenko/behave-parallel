"""Parallel configuration options for behave-parallel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from behave.configuration import Configuration


def _register_parallel_options() -> None:
    """Register --parallel-scheme and --parallel-balance in behave's OPTIONS list (once)."""
    from behave.configuration import OPTIONS

    existing: set[str] = set()
    for fixed, _ in OPTIONS:
        if fixed:
            existing.add(fixed[0])

    if "--parallel-scheme" not in existing:
        OPTIONS.append(
            (
                ("--parallel-scheme",),
                {
                    "dest": "parallel_scheme",
                    "default": "feature",
                    "help": "Parallelization scheme: feature (default: %(default)s).",
                },
            ),
        )

    if "--parallel-balance" not in existing:
        OPTIONS.append(
            (
                ("--parallel-balance",),
                {
                    "dest": "parallel_balance",
                    "default": "lpt",
                    "choices": ["lpt", "fifo"],
                    "help": (
                        "Work unit ordering: lpt (longest first) or fifo (default: %(default)s)."
                    ),
                },
            ),
        )

    if "--parallel-timing-file" not in existing:
        OPTIONS.append(
            (
                ("--parallel-timing-file",),
                {
                    "dest": "parallel_timing_file",
                    "default": ".behave-parallel-timing.json",
                    "help": "Path to timing file for LPT balancing (default: %(default)s).",
                },
            ),
        )


_register_parallel_options()


@dataclass(frozen=True)
class ConfigSnapshot:
    """Picklable snapshot of essential Configuration fields for worker processes.

    The full behave Configuration contains non-picklable objects (file
    handles, reporters).  This snapshot captures only the fields needed
    by WorkerRunner to execute features.
    """

    base_dir: str
    steps_dir: str
    environment_file: str
    lang: str | None
    stop: bool
    paths: list[str] = field(default_factory=list)
    parallel: int = 1
    parallel_scheme: str = "feature"
    parallel_balance: str = "lpt"
    parallel_timing_file: str = ".behave-parallel-timing.json"
    dry_run: bool = False
    use_nested_step_modules: bool = False


def snapshot_config(config: Configuration) -> ConfigSnapshot:
    """Create a picklable snapshot from a Configuration instance."""
    return ConfigSnapshot(
        base_dir=str(getattr(config, "base_dir", None) or "features"),
        steps_dir=str(getattr(config, "steps_dir", None) or "steps"),
        environment_file=str(getattr(config, "environment_file", None) or "environment.py"),
        lang=config.lang,
        stop=config.stop,
        paths=[str(p) for p in config.paths] if config.paths else [],
        parallel=getattr(config, "parallel", None) or getattr(config, "jobs", None) or 1,
        parallel_scheme=getattr(config, "parallel_scheme", "feature"),
        parallel_balance=getattr(config, "parallel_balance", "lpt"),
        parallel_timing_file=str(
            getattr(config, "parallel_timing_file", None) or ".behave-parallel-timing.json"
        ),
        dry_run=config.dry_run,
        use_nested_step_modules=getattr(config, "use_nested_step_modules", False),
    )


def add_parallel_options(config: Configuration) -> None:
    """Add parallel-related attributes to a Configuration instance.

    Maps behave's ``config.jobs`` (from ``--parallel``/``--jobs``) to
    ``config.parallel`` and ensures ``config.parallel_scheme`` exists.

    Args:
        config: Behave Configuration instance to augment.
    """
    jobs = getattr(config, "jobs", 1)
    if jobs is None:
        jobs = 1
    config.parallel = jobs

    if not hasattr(config, "parallel_scheme") or config.parallel_scheme is None:
        config.parallel_scheme = "feature"

    if not hasattr(config, "parallel_balance") or config.parallel_balance is None:
        config.parallel_balance = "lpt"

    if not hasattr(config, "parallel_timing_file") or config.parallel_timing_file is None:
        config.parallel_timing_file = ".behave-parallel-timing.json"

    if not hasattr(config, "use_nested_step_modules"):
        config.use_nested_step_modules = False
