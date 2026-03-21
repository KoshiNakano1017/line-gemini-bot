"""Integration tests for FirestoreConfigStore.

Requires Firestore emulator. Run:
  gcloud emulators firestore start --host-port=localhost:8080
  FIRESTORE_EMULATOR_HOST=localhost:8080 pytest tests/test_firestore_config_store.py -v
"""

import uuid

import pytest

from app.storage.firestore_config_store import (
    BotConfig,
    FirestoreConfigStore,
    _DEFAULT_BOT_ROLE,
)
from tests.conftest import FIRESTORE_TEST_PROJECT, skip_if_no_emulator


@skip_if_no_emulator
class TestFirestoreConfigStore:
    """Integration tests for FirestoreConfigStore."""

    @pytest.fixture
    def store(self) -> FirestoreConfigStore:
        return FirestoreConfigStore(
            project_id=FIRESTORE_TEST_PROJECT,
            document_id=f"bot_role_test_{uuid.uuid4().hex[:8]}",
        )

    def test_get_default(self, store: FirestoreConfigStore) -> None:
        cfg = store.get()
        assert isinstance(cfg, BotConfig)
        assert cfg.bot_role == _DEFAULT_BOT_ROLE
        assert cfg.updated_at

    def test_set_and_get_role(self, store: FirestoreConfigStore) -> None:
        new_role = "あなたはテスト用アシスタントです。"
        updated = store.set_role(new_role)
        assert updated.bot_role == new_role
        assert updated.updated_at

        cfg = store.get()
        assert cfg.bot_role == new_role

    def test_set_empty_falls_back_to_default(self, store: FirestoreConfigStore) -> None:
        store.set_role("  ")
        cfg = store.get()
        assert cfg.bot_role == _DEFAULT_BOT_ROLE
