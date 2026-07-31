Feature: Mixed serial and parallel scenarios

  Scenario: Parallel task 1
    Given a step that runs quickly
    When I do task 1
    Then task 1 should succeed

  Scenario: Parallel task 2
    Given a step that runs quickly
    When I do task 2
    Then task 2 should succeed

  @serial
  Scenario: Serial task 1
    Given a step that runs quickly
    When I do serial task 1
    Then serial task 1 should succeed

  @serial
  Scenario: Serial task 2
    Given a step that runs quickly
    When I do serial task 2
    Then serial task 2 should succeed
