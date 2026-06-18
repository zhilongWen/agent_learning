import unittest
from types import SimpleNamespace

from mem.storage.qdrant_store import QdrantVectorStore
from qdrant_client.http.models import Distance


class QueryPointsOnlyClient:
    def __init__(self):
        self.query_args = None
        self.collections = {
            "compat_test": SimpleNamespace(size=3),
            "rag_knowledge_base": SimpleNamespace(size=1024),
        }
        self.created_collections = []

    def query_points(self, **kwargs):
        self.query_args = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(id="point-a", score=0.98, payload={"memory_id": "a"}),
                SimpleNamespace(id="point-b", score=0.12, payload={"memory_id": "b"}),
            ]
        )

    def get_collection(self, collection_name):
        vectors = self.collections.get(collection_name)
        return SimpleNamespace(
            points_count=2,
            indexed_vectors_count=2,
            segments_count=1,
            config=SimpleNamespace(
                params=SimpleNamespace(vectors=vectors)
            ),
        )

    def get_collections(self):
        collections = [SimpleNamespace(name=name) for name in self.collections]
        return SimpleNamespace(collections=collections)

    def create_collection(self, collection_name, vectors_config, hnsw_config=None):
        self.collections[collection_name] = vectors_config
        self.created_collections.append(collection_name)

    def update_collection(self, **kwargs):
        return None

    def create_payload_index(self, **kwargs):
        return None


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
        self.assertEqual(info["config"]["vector_size"], 3)

    def test_existing_collection_with_different_dimension_gets_dimension_suffix(self):
        store = self.make_store()
        store.collection_name = "rag_knowledge_base"
        store.vector_size = 384

        store._ensure_collection()

        self.assertEqual(store.collection_name, "rag_knowledge_base_dim384")
        self.assertIn("rag_knowledge_base_dim384", store.client.created_collections)


if __name__ == "__main__":
    unittest.main()
