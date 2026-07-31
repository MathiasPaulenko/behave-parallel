Feature: Checkout
  Scenario: Successful checkout
    Given a cart with items
    When the user proceeds to checkout
    Then the order should be confirmed

  Scenario: Empty cart checkout
    Given an empty cart
    When the user proceeds to checkout
    Then the checkout should fail
