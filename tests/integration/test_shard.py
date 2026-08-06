"""Integration tests for sharding with real feature files.

These tests run behave as a subprocess with --shard and verify that:
- Each shard passes independently.
- All shards combined cover every feature (no gaps, no overlap).
- Sharding + --parallel works.
- Invalid shard values produce clear errors.
- Sharding + @serial works.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_SIMPLE = Path(__file__).parent.parent / "fixtures" / "simple"
FIXTURES_SERIAL = Path(__file__).parent.parent / "fixtures" / "serial"
PROJECT_ROOT = Path(__file__).parent.parent.parent

ALL_FEATURE_NAMES = ["login", "checkout", "search", "profile"]


def _run_behave(
    fixture_dir: Path,
    shard: str | None = None,
    parallel: int | None = None,
    tags: list[str] | None = None,
) -> tuple[int, str, str]:
    """Run behave with optional shard and parallel flags.

    Uses a wrapper script that imports ``behave_pool.config`` before
    calling behave's main, ensuring custom CLI options (``--shard``,
    ``--parallel-scheme``, etc.) are registered before argument parsing.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    features_dir = fixture_dir / "features"
    args = [
        "--runner",
        "behave_pool:ParallelRunner",
        str(features_dir),
    ]
    if parallel is not None:
        args.extend(["--parallel", str(parallel)])
    if shard is not None:
        args.extend(["--shard", shard])
    if tags:
        for tag in tags:
            args.extend(["--tags", tag])

    # Build a small inline script that imports behave_pool.config
    # (which registers --shard and other options in behave's OPTIONS list)
    # before calling behave's main().
    wrapper = (
        "import sys, behave_pool.config; "
        "from behave.__main__ import main; "
        f"sys.exit(main({args!r}))"
    )

    cmd = [sys.executable, "-c", wrapper]

    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(fixture_dir),
        timeout=120,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def _extract_features_from_output(stdout: str) -> set[str]:
    """Extract feature names that appear in behave output.

    Looks for lines like 'Feature: Login' in the output.
    """
    features = set()
    for match in re.finditer(r"Feature:\s+(\w+)", stdout):
        features.add(match.group(1).lower())
    return features


def _extract_features_from_report(fixture_dir: Path) -> set[str]:
    """Extract feature names from the JSON report file.

    Used in parallel mode where stdout doesn't contain feature names.
    """
    import json

    report_path = fixture_dir / "behave-pool-report.json"
    if not report_path.exists():
        return set()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    features = set()
    for feature in data.get("features", []):
        name = feature.get("name", "")
        if name:
            features.add(name.lower())
    return features


def _cleanup_fixture(fixture_dir: Path) -> None:
    """Clean up timing and report files after a test."""
    for filename in [".behave-pool-timing.json", "behave-pool-report.json"]:
        path = fixture_dir / filename
        if path.exists():
            path.unlink()


@pytest.mark.integration
class TestShardSequential:
    """Sharding with --parallel 1 (sequential within shard)."""

    def teardown_method(self) -> None:
        _cleanup_fixture(FIXTURES_SIMPLE)

    def test_shard_1_of_4_sequential_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="1/4", parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_2_of_4_sequential_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="2/4", parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_3_of_4_sequential_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="3/4", parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_4_of_4_sequential_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="4/4", parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_all_shards_cover_all_features(self) -> None:
        """Running all 4 shards (1/4 to 4/4) should cover all 4 features."""
        all_features: set[str] = set()
        for i in range(1, 5):
            rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard=f"{i}/4", parallel=1)
            assert rc == 0, f"Shard {i}/4 failed\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            all_features |= _extract_features_from_output(stdout)
        assert all_features == set(ALL_FEATURE_NAMES), (
            f"Expected {set(ALL_FEATURE_NAMES)}, got {all_features}"
        )

    def test_shards_no_overlap(self) -> None:
        """Each feature should appear in exactly one shard."""
        shard_features: dict[int, set[str]] = {}
        for i in range(1, 5):
            rc, stdout, _ = _run_behave(FIXTURES_SIMPLE, shard=f"{i}/4", parallel=1)
            assert rc == 0
            shard_features[i] = _extract_features_from_output(stdout)

        # Check no overlap
        for i in range(1, 5):
            for j in range(i + 1, 5):
                overlap = shard_features[i] & shard_features[j]
                assert not overlap, (
                    f"Shards {i} and {j} overlap on features: {overlap}"
                )


@pytest.mark.integration
class TestShardParallel:
    """Sharding with --parallel > 1 (local parallelism within shard)."""

    def teardown_method(self) -> None:
        _cleanup_fixture(FIXTURES_SIMPLE)

    def test_shard_1_of_2_parallel_2_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="1/2", parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_2_of_2_parallel_2_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="2/2", parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_1_of_3_parallel_4_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="1/3", parallel=4)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_2_of_3_parallel_4_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="2/3", parallel=4)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_3_of_3_parallel_4_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="3/3", parallel=4)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_all_shards_parallel_cover_all_features(self) -> None:
        """Running all 2 shards with parallel=2 should cover all features."""
        all_features: set[str] = set()
        for i in range(1, 3):
            rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard=f"{i}/2", parallel=2)
            assert rc == 0, f"Shard {i}/2 failed\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            all_features |= _extract_features_from_report(FIXTURES_SIMPLE)
        assert all_features == set(ALL_FEATURE_NAMES), (
            f"Expected {set(ALL_FEATURE_NAMES)}, got {all_features}"
        )


@pytest.mark.integration
class TestShardSingle:
    """Single shard (1/1) should run everything."""

    def teardown_method(self) -> None:
        _cleanup_fixture(FIXTURES_SIMPLE)

    def test_shard_1_of_1_runs_all_features(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="1/1", parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        features = _extract_features_from_output(stdout)
        assert features == set(ALL_FEATURE_NAMES), (
            f"Expected all features, got {features}"
        )

    def test_shard_1_of_1_parallel_4_runs_all_features(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="1/1", parallel=4)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        features = _extract_features_from_report(FIXTURES_SIMPLE)
        assert features == set(ALL_FEATURE_NAMES), (
            f"Expected all features, got {features}"
        )


@pytest.mark.integration
class TestShardValidation:
    """Invalid shard values should produce clear errors."""

    def test_shard_index_zero_fails(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="0/3", parallel=1)
        assert rc != 0
        assert "shard_index must be >= 1" in stderr or "shard_index must be >= 1" in stdout

    def test_shard_index_exceeds_total_fails(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="5/3", parallel=1)
        assert rc != 0
        assert "must be <= total_shards" in stderr or "must be <= total_shards" in stdout

    def test_shard_total_zero_fails(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="1/0", parallel=1)
        assert rc != 0
        assert "total_shards must be >= 1" in stderr or "total_shards must be >= 1" in stdout

    def test_shard_invalid_format_fails(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="invalid", parallel=1)
        assert rc != 0
        assert "Invalid shard format" in stderr or "Invalid shard format" in stdout

    def test_shard_missing_slash_fails(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="13", parallel=1)
        assert rc != 0
        assert "Invalid shard format" in stderr or "Invalid shard format" in stdout


@pytest.mark.integration
class TestShardWithSerial:
    """Sharding with @serial tagged scenarios."""

    def teardown_method(self) -> None:
        _cleanup_fixture(FIXTURES_SERIAL)

    def test_shard_1_of_2_serial_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SERIAL, shard="1/2", parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_2_of_2_serial_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SERIAL, shard="2/2", parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_1_of_1_serial_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SERIAL, shard="1/1", parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"


@pytest.mark.integration
class TestShardMoreShardsThanFeatures:
    """When there are more shards than features, some shards should be empty but still pass."""

    def teardown_method(self) -> None:
        _cleanup_fixture(FIXTURES_SIMPLE)

    def test_shard_5_of_8_passes(self) -> None:
        """Shard 5 of 8 may get no features — should still pass (exit 0)."""
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="5/8", parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_shard_8_of_8_passes(self) -> None:
        rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard="8/8", parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_all_8_shards_cover_all_features(self) -> None:
        """Even with 8 shards (more than 4 features), all features should be covered."""
        all_features: set[str] = set()
        for i in range(1, 9):
            rc, stdout, stderr = _run_behave(FIXTURES_SIMPLE, shard=f"{i}/8", parallel=1)
            assert rc == 0, f"Shard {i}/8 failed\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            all_features |= _extract_features_from_output(stdout)
        assert all_features == set(ALL_FEATURE_NAMES), (
            f"Expected {set(ALL_FEATURE_NAMES)}, got {all_features}"
        )
