"""behave-pool: parallel test execution for Behave BDD via native ITestRunner.

Public API:

    from behave_pool import ParallelRunner

    # Register in behave.ini:
    # [behave.runners]
    # parallel = behave_pool:ParallelRunner

    # Then run:
    # behave --runner=parallel --parallel 4 --parallel-scheme feature features/
"""

from __future__ import annotations

__version__ = "1.1.0"

from behave_pool.runner import ParallelRunner

__all__ = ["ParallelRunner", "__version__"]
