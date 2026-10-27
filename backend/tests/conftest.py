import os
import secrets
import pytest

# Generate dynamic unpredictable token per test run
TEST_OFFICER_TOKEN = secrets.token_hex(32)

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Ensure OFFICER_AUTH_TOKEN is dynamically configured with an unpredictable secret in test environment.
    Prevents tests from failing closed due to unconfigured secret.
    """
    monkeypatch.setenv("OFFICER_AUTH_TOKEN", TEST_OFFICER_TOKEN)
