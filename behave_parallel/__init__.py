"""behave-parallel: parallel test execution for Behave BDD via native ITestRunner.

Public API:

    from behave_parallel import ParallelRunner

    # Register in behave.ini:
    # [behave.runners]
    # parallel = behave_parallel:ParallelRunner

    # Then run:
    # behave --runner=parallel --parallel 4 --parallel-scheme feature features/
"""

from __future__ import annotations

__version__ = "0.1.0"

from behave_parallel.runner import ParallelRunner

__all__ = ["ParallelRunner", "__version__"]
