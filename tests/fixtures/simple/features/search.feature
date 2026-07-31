Feature: Search
  Scenario: Search by keyword
    Given a product catalog
    When the user searches for "laptop"
    Then results should be displayed

  Scenario: Search with no results
    Given a product catalog
    When the user searches for "nonexistent"
    Then no results should be displayed
