Feature: Calculator

  Scenario: Add two numbers
    Given I have a calculator
    When I add 2 and 3
    Then the result should be 5

  Scenario: Subtract two numbers
    Given I have a calculator
    When I subtract 5 from 8
    Then the result should be 3

  @serial
  Scenario: Shared resource operation
    Given I have a calculator
    When I multiply 4 by 6
    Then the result should be 24
