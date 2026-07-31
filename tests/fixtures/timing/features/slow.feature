Feature: Scenarios with varied durations for LPT testing

  Scenario: Fast scenario
    Given a step that runs quickly
    When I wait for 0.1 seconds
    Then the wait should complete

  Scenario: Medium scenario
    Given a step that runs quickly
    When I wait for 0.5 seconds
    Then the wait should complete

  Scenario: Slow scenario
    Given a step that runs quickly
    When I wait for 1.0 seconds
    Then the wait should complete
