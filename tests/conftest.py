"""Pytest configuration.

Firestore tests require the emulator. Start it with:
  gcloud emulators firestore start --host-port=localhost:8080

Then run tests with:
  FIRESTORE_EMULATOR_HOST=localhost:8080 pytest tests/ -v
"""

import os

import pytest

# Project ID for emulator (any string works)
FIRESTORE_TEST_PROJECT = os.environ.get("FIRESTORE_TEST_PROJECT", "test-project")


def firestore_emulator_available() -> bool:
    """Check if Firestore emulator is configured."""
    return bool(os.environ.get("FIRESTORE_EMULATOR_HOST"))


skip_if_no_emulator = pytest.mark.skipif(
    not firestore_emulator_available(),
    reason="FIRESTORE_EMULATOR_HOST not set. Run: gcloud emulators firestore start",
)
