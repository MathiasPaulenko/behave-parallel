"""Step definitions for serial tag integration tests."""

from behave import given, then, when


@given("a step that runs quickly")
def step_given_quick(context) -> None:
    pass


@when("I do task {n}")
def step_when_task(context, n: str) -> None:
    pass


@when("I do serial task {n}")
def step_when_serial_task(context, n: str) -> None:
    pass


@then("task {n} should succeed")
def step_then_task_succeeds(context, n: str) -> None:
    assert True


@then("serial task {n} should succeed")
def step_then_serial_succeeds(context, n: str) -> None:
    assert True
