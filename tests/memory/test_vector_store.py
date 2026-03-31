from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from u_core.memory import InMemoryVectorStore


class TestInMemoryVectorStore(unittest.TestCase):
    def test_query_ranks_by_highest_cosine_similarity(self) -> None:
        store = InMemoryVectorStore()
        store.upsert("best", [1.0, 0.0], {"kind": "best"})
        store.upsert("middle", [0.6, 0.8], {"kind": "middle"})
        store.upsert("worst", [-1.0, 0.0], {"kind": "worst"})

        results = store.query([1.0, 0.0], top_k=3)

        self.assertEqual(["best", "middle", "worst"], [key for key, _, _ in results])
        self.assertAlmostEqual(1.0, results[0][1], places=6)
        self.assertGreater(results[1][1], results[2][1])

    def test_query_respects_top_k_and_returns_all_when_top_k_is_large(self) -> None:
        store = InMemoryVectorStore()
        store.upsert("a", [1.0, 0.0])
        store.upsert("b", [0.0, 1.0])
        store.upsert("c", [0.7, 0.7])

        top_two = store.query([1.0, 0.0], top_k=2)
        self.assertEqual(2, len(top_two))

        top_ten = store.query([1.0, 0.0], top_k=10)
        self.assertEqual(3, len(top_ten))

    def test_dimension_mismatch_and_zero_vectors_score_as_zero(self) -> None:
        store = InMemoryVectorStore()
        store.upsert("dimension-mismatch", [1.0, 2.0, 3.0])
        store.upsert("stored-zero", [0.0, 0.0])
        store.upsert("valid", [1.0, 0.0])

        mismatch_results = store.query([1.0, 0.0], top_k=3)
        scores = {key: score for key, score, _ in mismatch_results}
        self.assertEqual(0.0, scores["dimension-mismatch"])
        self.assertEqual(0.0, scores["stored-zero"])
        self.assertEqual(1.0, scores["valid"])

        zero_query_results = store.query([0.0, 0.0], top_k=3)
        zero_query_scores = {key: score for key, score, _ in zero_query_results}
        self.assertEqual(0.0, zero_query_scores["dimension-mismatch"])
        self.assertEqual(0.0, zero_query_scores["stored-zero"])
        self.assertEqual(0.0, zero_query_scores["valid"])


if __name__ == "__main__":
    unittest.main()