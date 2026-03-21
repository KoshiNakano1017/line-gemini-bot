"""Factory for ConfigStore and KnowledgeStore based on settings."""

from __future__ import annotations

from app.config import Settings
from app.rag.chroma_store import ChromaKnowledgeStore
from app.rag.firestore_knowledge_store import FirestoreKnowledgeStore
from app.storage.config_store import ConfigStore
from app.storage.firestore_config_store import FirestoreConfigStore


def get_config_store(settings: Settings) -> ConfigStore | FirestoreConfigStore:
    """Return ConfigStore implementation based on settings."""
    if settings.firestore_project_id:
        return FirestoreConfigStore(
            project_id=settings.firestore_project_id,
            database=settings.firestore_database,
        )
    return ConfigStore(settings.sqlite_path)


def get_knowledge_store(settings: Settings) -> ChromaKnowledgeStore | FirestoreKnowledgeStore:
    """Return KnowledgeStore implementation based on settings."""
    if settings.firestore_project_id:
        return FirestoreKnowledgeStore(
            project_id=settings.firestore_project_id,
            database=settings.firestore_database,
        )
    return ChromaKnowledgeStore(settings.chroma_dir)
