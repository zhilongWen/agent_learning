"""RAG (检索增强生成) 系统模块"""

from mem.embedding import EmbeddingModel, LocalTransformerEmbedding, TFIDFEmbedding, create_embedding_model, \
    create_embedding_model_with_fallback
from mem.rag.document import Document, DocumentProcessor
from mem.rag.pipeline import load_and_chunk_texts, build_graph_from_chunks, index_chunks, embed_query, search_vectors, \
    rank, rerank_with_cross_encoder, merge_snippets, compute_graph_signals_from_pool, expand_neighbors_from_pool, \
    merge_snippets_grouped, search_vectors_expanded, tldr_summarize, compress_ranked_items

__all__ = [
    "EmbeddingModel",
    "LocalTransformerEmbedding",
    "TFIDFEmbedding",
    "create_embedding_model",
    "create_embedding_model_with_fallback",
    "Document",
    "DocumentProcessor",
    "load_and_chunk_texts",
    "build_graph_from_chunks",
    "index_chunks",
    "embed_query",
    "search_vectors",
    "rank",
    "merge_snippets",
    "rerank_with_cross_encoder",
    "expand_neighbors_from_pool",
    "compute_graph_signals_from_pool",
    "merge_snippets_grouped",
    "search_vectors_expanded",
    "compress_ranked_items",
    "tldr_summarize",
]
