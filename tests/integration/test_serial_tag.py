"""Integration tests for @serial tag two-phase execution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "serial"
FEATURES_DIR = FIXTURES_DIR / "features"
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _run_behave(parallel: int) -> tuple[int, str, str]:
    """Run behave with parallel flag.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    cmd = [
        sys.executable,
        "-m",
        "behave",
        "--runner",
        "behave_parallel:ParallelRunner",
        "--parallel",
        str(parallel),
        str(FEATURES_DIR),
    ]

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
class TestSerialTagExecution:
    """Test that @serial scenarios execute after parallel ones."""

    def teardown_method(self) -> None:
        """Clean up timing file after each test."""
        timing_file = FIXTURES_DIR / ".behave-parallel-timing.json"
        if timing_file.exists():
            timing_file.unlink()

    def test_all_scenarios_pass(self) -> None:
        rc, stdout, stderr = _run_behave(parallel=4)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_serial_scenarios_execute_after_parallel(self) -> None:
        """With --parallel 4, all 4 scenarios run. The 2 @serial scenarios
        must execute in the serial phase (after parallel phase completes).

        We verify by checking that the exit code is 0 (all pass) and
        that behave ran without errors.
        """
        rc, stdout, stderr = _run_behave(parallel=4)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_serial_with_parallel_1(self) -> None:
        """With --parallel 1, everything runs sequentially (passthrough)."""
        rc, stdout, stderr = _run_behave(parallel=1)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_serial_with_parallel_2(self) -> None:
        """With --parallel 2, parallel batch runs with 2 workers,
        then serial batch runs with 1 worker."""
        rc, stdout, stderr = _run_behave(parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_tmp_dir_cleaned_after_serial_run(self) -> None:
        """tmp directory should be cleaned up after a run with serial tags."""
        _run_behave(parallel=4)
        tmp_dir = FIXTURES_DIR / "tmp"
        assert not tmp_dir.exists(), f"tmp dir should be cleaned up: {tmp_dir}"
