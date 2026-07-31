"""Step definitions for timing integration tests."""

from __future__ import annotations

import time

from behave import given, then, when


@given("a step that runs quickly")
def step_given_quick(context) -> None:
    pass


@when("I wait for {seconds} seconds")
def step_when_wait(context, seconds: str) -> None:
    time.sleep(float(seconds))


@then("the wait should complete")
def step_then_wait_complete(context) -> None:
    assert True
