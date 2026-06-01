"""RAG工具

为HelloAgents框架提供检索增强生成(RAG)能力的工具实现。
可以作为工具添加到任何Agent中，让Agent具备知识库检索功能。
"""

from typing import Dict, Any, List
import os

from mem import ChromaVectorStore
from mem.rag import create_embedding_model_with_fallback, TFIDFEmbedding, DocumentProcessor, VectorRetriever, \
    HybridRetriever, Document
from tools import Tool, ToolParameter


# from ..base import Tool, ToolParameter
# from ...memory.rag import (
#     SentenceTransformerEmbedding, TFIDFEmbedding, HuggingFaceEmbedding,
#     DocumentProcessor, Document,
#     VectorRetriever, HybridRetriever,
#     create_embedding_model_with_fallback
# )
# from ...memory.storage import ChromaVectorStore


class RAGTool(Tool):
    """RAG工具
    
    为Agent提供知识库检索功能：
    - 添加文档到知识库
    - 检索相关文档
    - 管理知识库
    - 支持多种检索策略
    """

    def __init__(
            self,
            knowledge_base_path: str = "./knowledge_base",
            embedding_model: str = "sentence-transformers",
            retrieval_strategy: str = "vector"
    ):
        super().__init__(
            name="rag",
            description="RAG工具 - 可以从知识库中检索相关信息来增强回答"
        )

        self.knowledge_base_path = knowledge_base_path
        self.embedding_model_name = embedding_model
        self.retrieval_strategy = retrieval_strategy

        # 确保知识库目录存在
        os.makedirs(knowledge_base_path, exist_ok=True)

        # 初始化组件
        self._init_components()

    def _init_components(self):
        """初始化RAG组件"""
        try:
            # 初始化嵌入模型 - 使用智能fallback
            if self.embedding_model_name == "sentence-transformers":
                self.embedding_model = create_embedding_model_with_fallback("sentence_transformer")
            elif self.embedding_model_name == "huggingface":
                self.embedding_model = create_embedding_model_with_fallback("huggingface")
            elif self.embedding_model_name == "tfidf":
                self.embedding_model = TFIDFEmbedding()
            else:
                # 默认使用智能fallback
                self.embedding_model = create_embedding_model_with_fallback("sentence_transformer")

            # 初始化文档处理器
            self.document_processor = DocumentProcessor()

            # 初始化向量存储
            self.vector_store = ChromaVectorStore(
                collection_name="rag_knowledge_base",
                persist_directory=os.path.join(self.knowledge_base_path, "chroma_db")
            )

            # 初始化检索器
            if self.retrieval_strategy == "vector":
                self.retriever = VectorRetriever(
                    embedding_model=self.embedding_model,
                    vector_store=self.vector_store
                )
            else:
                self.retriever = HybridRetriever(
                    vector_retriever=VectorRetriever(
                        embedding_model=self.embedding_model,
                        vector_store=self.vector_store
                    ),
                    keyword_retriever=None  # 可以后续添加
                )

            self.initialized = True

        except Exception as e:
            self.initialized = False
            self.init_error = str(e)

    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具 - Tool基类要求的接口

        Args:
            parameters: 工具参数字典，必须包含action参数

        Returns:
            执行结果字符串
        """
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败：缺少必需的参数"

        action = parameters.get("action")
        # 移除action参数，传递其余参数给execute方法
        kwargs = {k: v for k, v in parameters.items() if k != "action"}

        return self.execute(action, **kwargs)

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义 - Tool基类要求的接口"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description="要执行的操作：add_document(添加文档), add_text(添加文本), search(搜索), list_documents(列出文档), stats(获取统计), clear(清空知识库)",
                required=True
            ),
            ToolParameter(
                name="file_path",
                type="string",
                description="文档文件路径（add_document操作时必需）",
                required=False
            ),
            ToolParameter(
                name="text",
                type="string",
                description="要添加的文本内容（add_text操作时必需）",
                required=False
            ),
            ToolParameter(
                name="document_id",
                type="string",
                description="文档ID（可选，用于标识文档）",
                required=False
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询（search操作时必需）",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="搜索结果数量限制（默认：5）",
                required=False,
                default=5
            ),
            ToolParameter(
                name="min_score",
                type="number",
                description="最小相似度分数（默认：0.1）",
                required=False,
                default=0.1
            )
        ]

    def execute(self, action: str, **kwargs) -> str:
        """执行RAG操作
        
        支持的操作：
        - add_document: 添加文档到知识库
        - add_text: 添加文本到知识库
        - search: 搜索知识库
        - list_documents: 列出所有文档
        - stats: 获取知识库统计
        """

        if not self.initialized:
            return f"❌ RAG工具初始化失败: {getattr(self, 'init_error', '未知错误')}"

        if action == "add_document":
            return self._add_document(**kwargs)
        elif action == "add_text":
            return self._add_text(**kwargs)
        elif action == "search":
            return self._search(**kwargs)
        elif action == "list_documents":
            return self._list_documents()
        elif action == "stats":
            return self._get_stats()
        elif action == "clear":
            return self.clear_knowledge_base()
        else:
            return f"不支持的操作: {action}。支持的操作: add_document, add_text, search, list_documents, stats, clear"

    def _add_document(self, file_path: str, document_id: str = None) -> str:
        """添加文档到知识库"""
        try:
            if not os.path.exists(file_path):
                return f"❌ 文件不存在: {file_path}"

            # 读取文档内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 处理文档
            document_id = document_id or os.path.basename(file_path)
            document = Document(content=content, metadata={"source": file_path}, doc_id=document_id)
            chunks = self.document_processor.process_document(document)

            # 添加到知识库
            chunk_ids = self.retriever.add_documents(chunks)
            added_count = len(chunk_ids)

            return f"✅ 文档已添加到知识库: {document_id} ({added_count} 个片段)"

        except Exception as e:
            return f"❌ 添加文档失败: {str(e)}"

    def _add_text(self, text: str, document_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """添加文本到知识库"""
        try:
            # 处理文本
            document_id = document_id or f"text_{hash(text) % 10000}"
            document = Document(content=text, metadata=metadata or {}, doc_id=document_id)
            chunks = self.document_processor.process_document(document)

            # 添加到知识库
            chunk_ids = self.retriever.add_documents(chunks)
            added_count = len(chunk_ids)

            return f"✅ 文本已添加到知识库: {document_id} ({added_count} 个片段)"

        except Exception as e:
            return f"❌ 添加文本失败: {str(e)}"

    def _search(self, query: str, limit: int = 5, min_score: float = 0.1) -> str:
        """搜索知识库"""
        try:
            results = self.retriever.retrieve(query, top_k=limit)

            if not results:
                return f"🔍 未找到与 '{query}' 相关的内容"

            # 过滤低分结果
            filtered_results = [r for r in results if r.metadata.get('similarity_score', 0) >= min_score]

            if not filtered_results:
                return f"🔍 未找到足够相关的内容 (最低分数要求: {min_score})"

            # 格式化结果
            formatted_results = []
            formatted_results.append(f"🔍 找到 {len(filtered_results)} 条相关内容:")

            for i, doc_chunk in enumerate(filtered_results, 1):
                score = doc_chunk.metadata.get('similarity_score', 0)

                content_preview = doc_chunk.content[:100] + "..." if len(doc_chunk.content) > 100 else doc_chunk.content
                source_info = f"来源: {doc_chunk.doc_id}" if doc_chunk.doc_id else ""

                formatted_results.append(
                    f"{i}. {content_preview} (相关性: {score:.2f}) {source_info}"
                )

            return "\n".join(formatted_results)

        except Exception as e:
            return f"❌ 搜索失败: {str(e)}"

    def _list_documents(self) -> str:
        """列出知识库的文档片段数量（基于向量存储统计）"""
        try:
            vector_stats = self.vector_store.get_collection_stats()
            # 兼容不同后端的字段命名
            total = (
                    vector_stats.get("total_documents")
                    or vector_stats.get("total_entities")
                    or vector_stats.get("count")
                    or 0
            )
            store_type = vector_stats.get("store_type", "unknown")
            return f"📚 知识库（{store_type}）包含 {int(total)} 个文档片段"
        except Exception as e:
            return f"❌ 获取文档列表失败: {str(e)}"

    def _get_stats(self) -> str:
        """获取知识库统计"""
        try:
            stats_info = [
                f"📊 知识库统计",
                f"存储根路径: {self.knowledge_base_path}",
                f"嵌入模型: {self.embedding_model_name}",
                f"检索策略: {self.retrieval_strategy}"
            ]

            # 获取向量存储统计（兼容不同实现）
            try:
                vector_stats = self.vector_store.get_collection_stats()
                store_type = vector_stats.get("store_type", "unknown")
                total = (
                        vector_stats.get("total_documents")
                        or vector_stats.get("total_entities")
                        or vector_stats.get("count")
                        or 0
                )
                stats_info.append(f"存储后端: {store_type}")
                stats_info.append(f"文档片段数: {int(total)}")

                # 其他常见字段（按存在性追加）
                for k in [
                    "vector_dimension", "dimension",
                    "collection_name", "persist_directory",
                    "index_type", "persist_path"
                ]:
                    if k in vector_stats:
                        stats_info.append(f"{k}: {vector_stats[k]}")
            except Exception:
                stats_info.append("存储统计读取失败，可能未初始化或无可用后端")

            return "\n".join(stats_info)

        except Exception as e:
            return f"❌ 获取统计信息失败: {str(e)}"

    def get_relevant_context(self, query: str, limit: int = 3) -> str:
        """为查询获取相关上下文
        
        这个方法可以被Agent调用来获取相关的知识库上下文
        """
        try:
            results = self.retriever.retrieve(query, top_k=limit)

            if not results:
                return ""

            context_parts = ["相关知识:"]
            for result in results:
                doc = result['document']
                context_parts.append(f"- {doc.content}")

            return "\n".join(context_parts)

        except Exception as e:
            return f"获取上下文失败: {str(e)}"

    def batch_add_texts(self, texts: List[str], document_ids: List[str] = None) -> str:
        """批量添加文本"""
        try:
            if document_ids and len(document_ids) != len(texts):
                return "❌ 文本数量和文档ID数量不匹配"

            total_chunks = 0
            for i, text in enumerate(texts):
                doc_id = document_ids[i] if document_ids else f"batch_text_{i}"
                document = Document(content=text, metadata={}, doc_id=doc_id)
                chunks = self.document_processor.process_document(document)

                chunk_ids = self.retriever.add_documents(chunks)
                total_chunks += len(chunk_ids)

            return f"✅ 批量添加完成: {len(texts)} 个文本, {total_chunks} 个片段"

        except Exception as e:
            return f"❌ 批量添加失败: {str(e)}"

    def clear_knowledge_base(self) -> str:
        """清空知识库（删除持久化数据并重建）"""
        import shutil
        try:
            # 尝试删除向量存储的持久化目录
            persist_dir = getattr(self.vector_store, "persist_directory", None) or getattr(self.vector_store,
                                                                                           "persist_path", None)
            if persist_dir and os.path.exists(persist_dir):
                shutil.rmtree(persist_dir, ignore_errors=True)
            # 重新初始化组件
            self._init_components()
            return "✅ 知识库已清空"
        except Exception as e:
            return f"❌ 清空知识库失败: {str(e)}"
