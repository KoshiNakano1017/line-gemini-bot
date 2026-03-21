"""Integration tests for FirestoreKnowledgeStore.

Requires Firestore emulator. Run:
  gcloud emulators firestore start --host-port=localhost:8080
  FIRESTORE_EMULATOR_HOST=localhost:8080 pytest tests/test_firestore_knowledge_store.py -v
"""

import pytest

from app.rag.firestore_knowledge_store import (
    FirestoreKnowledgeStore,
    KnowledgeItem,
    RetrievedItem,
)
from tests.conftest import FIRESTORE_TEST_PROJECT, skip_if_no_emulator


@skip_if_no_emulator
class TestFirestoreKnowledgeStore:
    """Integration tests for FirestoreKnowledgeStore."""

    @pytest.fixture
    def store(self) -> FirestoreKnowledgeStore:
        return FirestoreKnowledgeStore(
            project_id=FIRESTORE_TEST_PROJECT,
            collection_name="knowledge_test",
        )

    def test_upsert_and_list(self, store: FirestoreKnowledgeStore) -> None:
        emb = [0.1] * 768
        item = store.upsert(
            question="テスト質問",
            answer="テスト回答",
            embedding=emb,
            metadata={"category": "test"},
        )
        assert isinstance(item, KnowledgeItem)
        assert item.document == "Q: テスト質問\nA: テスト回答"
        assert item.metadata.get("question") == "テスト質問"
        assert item.metadata.get("category") == "test"

        items = store.list_all()
        assert len(items) >= 1
        ids = [i.id for i in items]
        assert item.id in ids

    def test_count(self, store: FirestoreKnowledgeStore) -> None:
        before = store.count()
        emb = [0.2] * 768
        store.upsert(question="c1", answer="a1", embedding=emb)
        assert store.count() == before + 1

    def test_search_by_similarity(self, store: FirestoreKnowledgeStore) -> None:
        emb1 = [1.0] + [0.0] * 767
        emb2 = [0.0] * 767 + [1.0]
        query_emb = [0.99] + [0.0] * 767

        store.upsert(question="q1", answer="a1", embedding=emb1)
        store.upsert(question="q2", answer="a2", embedding=emb2)

        results = store.search(query_embedding=query_emb, top_k=2, min_similarity=0.0)
        assert len(results) >= 1
        assert all(isinstance(r, RetrievedItem) for r in results)
        assert all(0 <= r.similarity <= 1 for r in results)
        # Query is similar to emb1, so first result should have high similarity
        if results:
            assert results[0].similarity > 0.9

    def test_delete(self, store: FirestoreKnowledgeStore) -> None:
        emb = [0.3] * 768
        item = store.upsert(question="del_q", answer="del_a", embedding=emb)
        store.delete(item.id)
        items = store.list_all()
        assert item.id not in [i.id for i in items]
