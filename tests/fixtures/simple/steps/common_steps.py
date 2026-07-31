"""Common step definitions for simple test fixtures."""

from behave import given, then, when


@given("a user exists")
def step_user_exists(context):
    context.user = {"name": "testuser", "password": "pass123"}


@given("a cart with items")
def step_cart_with_items(context):
    context.cart = ["item1", "item2"]


@given("an empty cart")
def step_empty_cart(context):
    context.cart = []


@given("a product catalog")
def step_product_catalog(context):
    context.catalog = ["laptop", "mouse", "keyboard"]


@given("a logged in user")
def step_logged_in_user(context):
    context.user = {"name": "testuser"}


@when('the user logs in with valid credentials')
def step_login_valid(context):
    context.authenticated = True


@when('the user logs in with invalid credentials')
def step_login_invalid(context):
    context.authenticated = False


@when("the user proceeds to checkout")
def step_checkout(context):
    context.checkout_success = len(context.cart) > 0


@when('the user searches for "laptop"')
def step_search_laptop(context):
    context.search_results = [p for p in context.catalog if "laptop" in p]


@when('the user searches for "nonexistent"')
def step_search_nonexistent(context):
    context.search_results = []


@when("the user views their profile")
def step_view_profile(context):
    context.profile_shown = True


@when("the user updates their name")
def step_update_name(context):
    context.profile_updated = True


@then("the user should be authenticated")
def step_assert_authenticated(context):
    assert context.authenticated is True


@then("the user should not be authenticated")
def step_assert_not_authenticated(context):
    assert context.authenticated is False


@then("the order should be confirmed")
def step_assert_order_confirmed(context):
    assert context.checkout_success is True


@then("the checkout should fail")
def step_assert_checkout_fail(context):
    assert context.checkout_success is False


@then("results should be displayed")
def step_assert_results_displayed(context):
    assert len(context.search_results) > 0


@then("no results should be displayed")
def step_assert_no_results(context):
    assert len(context.search_results) == 0


@then("the profile details should be shown")
def step_assert_profile_shown(context):
    assert context.profile_shown is True


@then("the profile should be updated")
def step_assert_profile_updated(context):
    assert context.profile_updated is True
