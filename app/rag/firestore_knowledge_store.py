"""Firestore-based KnowledgeStore with in-app cosine similarity search.

Reference: https://cloud.google.com/firestore/docs/create-database-server-client-library
Firestore stores documents; we fetch all and compute similarity in Python for small datasets.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Any

from google.cloud import firestore


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    document: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievedItem:
    id: str
    document: str
    metadata: dict[str, Any]
    similarity: float


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class FirestoreKnowledgeStore:
    """KnowledgeStore implementation using Cloud Firestore."""

    def __init__(self, project_id: str, collection_name: str = "knowledge", database: str | None = None):
        """Initialize Firestore client.

        Args:
            project_id: GCP project ID.
            collection_name: Firestore collection for knowledge items.
            database: Firestore database name. Default is "(default)".
        """
        self._client = firestore.Client(project=project_id, database=database or "(default)")
        self._collection = self._client.collection(collection_name)

    def upsert(
        self,
        *,
        question: str,
        answer: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeItem:
        """Insert or update a knowledge item."""
        q = (question or "").strip()
        a = (answer or "").strip()
        doc = f"Q: {q}\nA: {a}".strip()
        item_id = str(uuid.uuid4())

        meta = dict(metadata or {})
        meta.update({"question": q, "answer": a})

        self._collection.document(item_id).set({
            "document": doc,
            "embedding": embedding,
            "metadata": meta,
        })
        return KnowledgeItem(id=item_id, document=doc, metadata=meta)

    def delete(self, item_id: str) -> None:
        """Delete a knowledge item by ID."""
        self._collection.document(item_id).delete()

    def list_all(self, limit: int = 1000) -> list[KnowledgeItem]:
        """List all knowledge items."""
        query = self._collection.limit(limit)
        docs = query.stream()
        out: list[KnowledgeItem] = []
        for doc in docs:
            data = doc.to_dict() or {}
            out.append(
                KnowledgeItem(
                    id=doc.id,
                    document=data.get("document") or "",
                    metadata=data.get("metadata") or {},
                )
            )
        return out

    def count(self) -> int:
        """Count knowledge items."""
        return len(self.list_all(limit=10000))

    def search(
        self,
        *,
        query_embedding: list[float],
        top_k: int = 3,
        min_similarity: float = 0.0,
    ) -> list[RetrievedItem]:
        """Search by cosine similarity. Fetches all items and computes in-app."""
        if top_k <= 0:
            return []

        all_docs = self._collection.stream()
        candidates: list[tuple[RetrievedItem, float]] = []

        for doc in all_docs:
            data = doc.to_dict() or {}
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                continue
            emb = [float(x) for x in embedding]
            sim = _cosine_similarity(query_embedding, emb)
            if sim < min_similarity:
                continue
            item = RetrievedItem(
                id=doc.id,
                document=data.get("document") or "",
                metadata=data.get("metadata") or {},
                similarity=sim,
            )
            candidates.append((item, sim))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in candidates[:top_k]]

    def reembed_all(self, embeddings: list[list[float]]) -> int:
        """Re-embed all items with new embeddings."""
        items = self.list_all(limit=2000)
        if not items:
            return 0
        if len(embeddings) != len(items):
            raise ValueError("embeddings length mismatch")

        for it, emb in zip(items, embeddings):
            self._collection.document(it.id).update({"embedding": emb})
        return len(items)
