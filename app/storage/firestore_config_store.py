"""Firestore-based ConfigStore.

Reference: https://cloud.google.com/firestore/docs/create-database-server-client-library
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from google.cloud import firestore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_DEFAULT_BOT_ROLE = (
    "あなたは親切で簡潔なアシスタントです。"
    "与えられたナレッジ以外は推測せず、分からない場合は「分かりかねます」と答えてください。"
)

_COLLECTION = "config"
_DOCUMENT_ID = "bot_role"


@dataclass(frozen=True)
class BotConfig:
    bot_role: str
    updated_at: str


class FirestoreConfigStore:
    """ConfigStore implementation using Cloud Firestore."""

    def __init__(
        self,
        project_id: str,
        database: str | None = None,
        document_id: str | None = None,
    ):
        """Initialize Firestore client.

        Args:
            project_id: GCP project ID.
            database: Firestore database name. Default is "(default)".
            document_id: Document ID for config. Default is "bot_role".
                        Use a unique ID in tests to avoid collisions.
        """
        self._client = firestore.Client(project=project_id, database=database or "(default)")
        doc_id = document_id or _DOCUMENT_ID
        self._doc_ref = self._client.collection(_COLLECTION).document(doc_id)
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Create default config if document does not exist."""
        doc = self._doc_ref.get()
        if not doc.exists:
            self._doc_ref.set({
                "bot_role": _DEFAULT_BOT_ROLE,
                "updated_at": _utc_now_iso(),
            })

    def get(self) -> BotConfig:
        """Get current bot config."""
        doc = self._doc_ref.get()
        if not doc.exists:
            return BotConfig(bot_role=_DEFAULT_BOT_ROLE, updated_at=_utc_now_iso())
        data = doc.to_dict() or {}
        return BotConfig(
            bot_role=data.get("bot_role") or _DEFAULT_BOT_ROLE,
            updated_at=data.get("updated_at") or _utc_now_iso(),
        )

    def set_role(self, bot_role: str) -> BotConfig:
        """Update bot role and return new config."""
        bot_role = (bot_role or "").strip()
        if not bot_role:
            bot_role = _DEFAULT_BOT_ROLE

        updated_at = _utc_now_iso()
        self._doc_ref.set({
            "bot_role": bot_role,
            "updated_at": updated_at,
        })
        return BotConfig(bot_role=bot_role, updated_at=updated_at)
