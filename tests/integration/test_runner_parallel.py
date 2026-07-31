"""Integration tests for ParallelRunner."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "simple"
FEATURES_DIR = FIXTURES_DIR / "features"
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _run_behave(parallel: int | None = None) -> tuple[int, str, str]:
    """Run behave with optional parallel flags.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    cmd = [
        sys.executable,
        "-m",
        "behave",
        "--runner",
        "behave_parallel:ParallelRunner",
        str(FEATURES_DIR),
    ]
    if parallel is not None:
        cmd.extend(["--parallel", str(parallel)])

    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(FIXTURES_DIR),
        timeout=60,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.mark.integration
class TestParallelRunnerSequential:
    """Test that --parallel 1 is passthrough (same as vanilla behave)."""

    def teardown_method(self) -> None:
        """Clean up timing file after each test."""
        timing_file = FIXTURES_DIR / ".behave-parallel-timing.json"
        if timing_file.exists():
            timing_file.unlink()

    def test_parallel_1_passes(self) -> None:
        rc, stdout, stderr = _run_behave(parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_parallel_1_runs_all_features(self) -> None:
        rc, stdout, _ = _run_behave(parallel=1)
        assert rc == 0
        for feature_name in ["login", "checkout", "search", "profile"]:
            assert feature_name in stdout, f"Feature '{feature_name}' not found in output"


@pytest.mark.integration
class TestParallelRunnerParallel:
    """Test parallel execution with --parallel 4."""

    def teardown_method(self) -> None:
        """Clean up timing file after each test."""
        timing_file = FIXTURES_DIR / ".behave-parallel-timing.json"
        if timing_file.exists():
            timing_file.unlink()

    def test_parallel_4_passes(self) -> None:
        rc, stdout, stderr = _run_behave(parallel=4)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_parallel_2_passes(self) -> None:
        rc, stdout, stderr = _run_behave(parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_parallel_4_cleans_tmp(self) -> None:
        """After parallel run, tmp/ directory should be cleaned up."""
        _run_behave(parallel=4)
        tmp_dir = FIXTURES_DIR / "tmp"
        assert not tmp_dir.exists(), "tmp/ directory was not cleaned up"


@pytest.mark.integration
class TestParallelRunnerNoParallel:
    """Test default (no --parallel flag) is passthrough."""

    def teardown_method(self) -> None:
        """Clean up timing file after each test."""
        timing_file = FIXTURES_DIR / ".behave-parallel-timing.json"
        if timing_file.exists():
            timing_file.unlink()

    def test_default_passes(self) -> None:
        rc, stdout, stderr = _run_behave()
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
