"""Integration tests for LPT balancing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "timing"
FEATURES_DIR = FIXTURES_DIR / "features"
PROJECT_ROOT = Path(__file__).parent.parent.parent
TIMING_FILE_NAME = ".behave-parallel-timing.json"


def _run_behave(parallel: int) -> tuple[int, str, str]:
    """Run behave with parallel flag.

    Uses default balance (lpt) and default timing file path
    (relative to CWD which is FIXTURES_DIR).

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
class TestLPTBalancing:
    """Test LPT balancing with TimingStore."""

    def teardown_method(self) -> None:
        """Clean up timing file after each test."""
        timing_file = FIXTURES_DIR / TIMING_FILE_NAME
        if timing_file.exists():
            timing_file.unlink()

    def test_lpt_passes(self) -> None:
        rc, stdout, stderr = _run_behave(parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_timing_file_created_post_execution(self) -> None:
        timing_file = FIXTURES_DIR / TIMING_FILE_NAME
        if timing_file.exists():
            timing_file.unlink()

        rc, stdout, stderr = _run_behave(parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

        assert timing_file.exists(), "Timing file should be created after execution"
        data = json.loads(timing_file.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert len(data) > 0, "Timing file should have at least one entry"

    def test_lpt_with_pre_populated_timings(self) -> None:
        """Pre-populate timing file and verify run succeeds with LPT ordering."""
        timing_file = FIXTURES_DIR / TIMING_FILE_NAME
        timing_file.write_text(
            json.dumps(
                {
                    "feature:slow.feature": 1.0,
                    "feature:slow.feature:11": 0.1,
                    "feature:slow.feature:16": 0.5,
                    "feature:slow.feature:21": 1.0,
                }
            ),
            encoding="utf-8",
        )

        rc, stdout, stderr = _run_behave(parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

    def test_timing_file_updated_with_new_durations(self) -> None:
        """Verify timing file is updated with actual durations after run."""
        timing_file = FIXTURES_DIR / TIMING_FILE_NAME
        timing_file.write_text(
            json.dumps({"feature:slow.feature": 99.0}),
            encoding="utf-8",
        )

        rc, stdout, stderr = _run_behave(parallel=2)
        assert rc == 0, f"Exit code {rc}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"

        data = json.loads(timing_file.read_text(encoding="utf-8"))
        # The actual work unit ID includes the full path prefix
        actual_key = "feature:features/slow.feature"
        assert actual_key in data, f"Expected key {actual_key} in {data}"
        assert data[actual_key] != 99.0

    def test_tmp_dir_cleaned_after_lpt_run(self) -> None:
        _run_behave(parallel=2)
        tmp_dir = FIXTURES_DIR / "tmp"
        assert not tmp_dir.exists(), f"tmp dir should be cleaned up: {tmp_dir}"
