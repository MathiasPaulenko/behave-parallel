from behave import given, then, when


@given("I have a calculator")
def step_have_calculator(context):
    context.calculator = True


@when("I add {a:d} and {b:d}")
def step_add(context, a, b):
    context.result = a + b


@when("I subtract {a:d} from {b:d}")
def step_subtract(context, a, b):
    context.result = b - a


@when("I multiply {a:d} by {b:d}")
def step_multiply(context, a, b):
    context.result = a * b


@then("the result should be {expected:d}")
def step_result(context, expected):
    assert context.result == expected, f"Expected {expected}, got {context.result}"
