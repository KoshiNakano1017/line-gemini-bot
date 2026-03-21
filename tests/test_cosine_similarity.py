"""Unit tests for cosine similarity (no Firestore required)."""

import pytest

from app.rag.firestore_knowledge_store import _cosine_similarity


class TestCosineSimilarity:
    """Tests for _cosine_similarity function."""

    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        b = [-1.0, 0.0, 0.0]
        # Cosine similarity of opposite vectors is -1, we clamp to [0, 1]
        assert _cosine_similarity(a, b) == 0.0

    def test_similar_vectors(self) -> None:
        a = [1.0, 1.0, 0.0]
        b = [1.0, 0.9, 0.1]
        sim = _cosine_similarity(a, b)
        assert 0.9 < sim <= 1.0

    def test_empty_vectors(self) -> None:
        assert _cosine_similarity([], []) == 0.0
        assert _cosine_similarity([1.0], []) == 0.0
        assert _cosine_similarity([], [1.0]) == 0.0

    def test_length_mismatch(self) -> None:
        assert _cosine_similarity([1.0, 2.0], [1.0]) == 0.0
