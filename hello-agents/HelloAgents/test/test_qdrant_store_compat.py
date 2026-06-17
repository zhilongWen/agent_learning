import unittest
from types import SimpleNamespace

from mem.storage.qdrant_store import QdrantVectorStore
from qdrant_client.http.models import Distance


class QueryPointsOnlyClient:
    def __init__(self):
        self.query_args = None

    def query_points(self, **kwargs):
        self.query_args = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(id="point-a", score=0.98, payload={"memory_id": "a"}),
                SimpleNamespace(id="point-b", score=0.12, payload={"memory_id": "b"}),
            ]
        )

    def get_collection(self, collection_name):
        return SimpleNamespace(
            points_count=2,
            indexed_vectors_count=2,
            segments_count=1,
        )


class QdrantStoreCompatTest(unittest.TestCase):
    def make_store(self):
        store = QdrantVectorStore.__new__(QdrantVectorStore)
        store.client = QueryPointsOnlyClient()
        store.collection_name = "compat_test"
        store.vector_size = 3
        store.distance = Distance.COSINE
        store.search_ef = 128
        store.search_exact = False
        return store

    def test_search_similar_uses_query_points_when_search_is_unavailable(self):
        store = self.make_store()

        results = store.search_similar([1.0, 0.0, 0.0], limit=2, where={"kind": "test"})

        self.assertEqual([r["metadata"]["memory_id"] for r in results], ["a", "b"])
        self.assertEqual(store.client.query_args["collection_name"], "compat_test")
        self.assertEqual(store.client.query_args["query"], [1.0, 0.0, 0.0])
        self.assertEqual(store.client.query_args["limit"], 2)

    def test_collection_info_treats_points_count_as_vectors_count_fallback(self):
        store = self.make_store()

        info = store.get_collection_info()

        self.assertEqual(info["points_count"], 2)
        self.assertEqual(info["vectors_count"], 2)
        self.assertEqual(info["indexed_vectors_count"], 2)


if __name__ == "__main__":
    unittest.main()
