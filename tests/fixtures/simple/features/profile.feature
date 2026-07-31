Feature: Profile
  Scenario: View profile
    Given a logged in user
    When the user views their profile
    Then the profile details should be shown

  Scenario: Update profile
    Given a logged in user
    When the user updates their name
    Then the profile should be updated
