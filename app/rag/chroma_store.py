from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

import chromadb


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


class ChromaKnowledgeStore:
    def __init__(self, persist_dir: str, collection_name: str = "knowledge"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, *, question: str, answer: str, embedding: list[float], metadata: dict[str, Any] | None = None) -> KnowledgeItem:
        q = (question or "").strip()
        a = (answer or "").strip()
        doc = f"Q: {q}\nA: {a}".strip()
        item_id = str(uuid.uuid4())

        meta = dict(metadata or {})
        meta.update({"question": q, "answer": a})

        self._collection.upsert(
            ids=[item_id],
            documents=[doc],
            embeddings=[embedding],
            metadatas=[meta],
        )
        return KnowledgeItem(id=item_id, document=doc, metadata=meta)

    def delete(self, item_id: str) -> None:
        self._collection.delete(ids=[item_id])

    def list_all(self, limit: int = 1000) -> list[KnowledgeItem]:
        res = self._collection.get(
            include=["documents", "metadatas"],
            limit=limit,
        )
        ids = res.get("ids") or []
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        out: list[KnowledgeItem] = []
        for i, item_id in enumerate(ids):
            out.append(
                KnowledgeItem(
                    id=item_id,
                    document=(docs[i] if i < len(docs) else "") or "",
                    metadata=(metas[i] if i < len(metas) else {}) or {},
                )
            )
        return out

    def count(self) -> int:
        return int(self._collection.count())

    def search(self, *, query_embedding: list[float], top_k: int = 3, min_similarity: float = 0.0) -> list[RetrievedItem]:
        if top_k <= 0:
            return []
        res = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        ids = (res.get("ids") or [[]])[0] or []
        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        dists = (res.get("distances") or [[]])[0] or []

        out: list[RetrievedItem] = []
        for i, item_id in enumerate(ids):
            dist = float(dists[i]) if i < len(dists) and dists[i] is not None else 1.0
            # For cosine space in Chroma, distance is typically (1 - cosine_similarity).
            sim = max(0.0, min(1.0, 1.0 - dist))
            if sim < min_similarity:
                continue
            out.append(
                RetrievedItem(
                    id=item_id,
                    document=(docs[i] if i < len(docs) else "") or "",
                    metadata=(metas[i] if i < len(metas) else {}) or {},
                    similarity=sim,
                )
            )
        return out

    def reembed_all(self, embeddings: list[list[float]]) -> int:
        items = self.list_all(limit=2000)
        if not items:
            return 0
        if len(embeddings) != len(items):
            raise ValueError("embeddings length mismatch")
        for it, emb in zip(items, embeddings):
            self._collection.upsert(
                ids=[it.id],
                documents=[it.document],
                embeddings=[emb],
                metadatas=[it.metadata],
            )
        return len(items)
