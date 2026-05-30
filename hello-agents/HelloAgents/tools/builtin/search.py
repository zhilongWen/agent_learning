"""搜索工具 - HelloAgents原生搜索实现"""

import os
from typing import Optional, Dict, Any, List

from tools import Tool, ToolParameter
from tavily.tavily import TavilyClient
from serpapi.serp_api_client import SerpApiClient


class SearchTool(Tool):
    """
    智能混合搜索工具

    支持多种搜索引擎后端，智能选择最佳搜索源：
    1. 混合模式 (hybrid) - 智能选择TAVILY或SERPAPI
    2. Tavily API (tavily) - 专业AI搜索
    3. SerpApi (serpapi) - 传统Google搜索
    4. 模拟搜索 (mock) - 开发测试
    """

    def __init__(self, backend: str = "hybrid", tavily_key: Optional[str] = None, serpapi_key: Optional[str] = None):
        super().__init__(
            name="search",
            description="一个智能网页搜索引擎。支持混合搜索模式，自动选择最佳搜索源。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
        )
        self.backend = backend
        self.tavily_key = tavily_key or os.getenv("TAVILY_API_KEY")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_API_KEY")
        self.available_backends = []
        self._setup_backends()

    def _setup_backends(self):
        """设置搜索后端"""
        # 检查Tavily可用性
        if self.tavily_key:
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=self.tavily_key)
                self.available_backends.append("tavily")
                print("✅ Tavily搜索引擎已初始化")
            except ImportError:
                print("⚠️ Tavily未安装，无法使用Tavily搜索")
        else:
            print("⚠️ TAVILY_API_KEY未设置")

        # 检查SerpApi可用性
        if self.serpapi_key:
            try:
                import serpapi
                self.available_backends.append("serpapi")
                print("✅ SerpApi搜索引擎已初始化")
            except ImportError:
                print("⚠️ SerpApi未安装，无法使用SerpApi搜索")
        else:
            print("⚠️ SERPAPI_API_KEY未设置")

        # 确定最终使用的后端
        if self.backend == "hybrid":
            if self.available_backends:
                print(f"🔧 混合搜索模式已启用，可用后端: {', '.join(self.available_backends)}")
            else:
                print("⚠️ 没有可用的搜索后端，切换到模拟搜索模式")
                self.backend = "mock"
        elif self.backend == "tavily" and "tavily" not in self.available_backends:
            print("⚠️ Tavily不可用，切换到模拟搜索模式")
            self.backend = "mock"
        elif self.backend == "serpapi" and "serpapi" not in self.available_backends:
            print("⚠️ SerpApi不可用，切换到模拟搜索模式")
            self.backend = "mock"
        elif self.backend not in ["tavily", "serpapi", "hybrid", "mock"]:
            print("🔧 使用模拟搜索模式")
            self.backend = "mock"

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行搜索

        Args:
            parameters: 包含input参数的字典

        Returns:
            搜索结果
        """
        query = parameters.get("input", "").strip()
        if not query:
            return "错误：搜索查询不能为空"

        print(f"🔍 正在执行搜索: {query}")

        try:
            if self.backend == "hybrid":
                return self._search_hybrid(query)
            elif self.backend == "tavily":
                return self._search_tavily(query)
            elif self.backend == "serpapi":
                return self._search_serpapi(query)
            else:
                return self._search_mock(query)
        except Exception as e:
            return f"搜索时发生错误: {str(e)}"

    def _search_hybrid(self, query: str) -> str:
        """混合搜索 - 智能选择最佳搜索源"""
        # 优先使用Tavily（AI优化的搜索）
        if "tavily" in self.available_backends:
            try:
                print("🎯 使用Tavily进行AI优化搜索")
                return self._search_tavily(query)
            except Exception as e:
                print(f"⚠️ Tavily搜索失败: {e}")
                # 如果Tavily失败，尝试SerpApi
                if "serpapi" in self.available_backends:
                    print("🔄 切换到SerpApi搜索")
                    return self._search_serpapi(query)

        # 如果Tavily不可用，使用SerpApi
        elif "serpapi" in self.available_backends:
            try:
                print("🎯 使用SerpApi进行Google搜索")
                return self._search_serpapi(query)
            except Exception as e:
                print(f"⚠️ SerpApi搜索失败: {e}")

        # 如果都不可用，使用模拟搜索
        print("⚠️ 所有搜索后端都不可用，使用模拟搜索")
        return self._search_mock(query)

    def _search_tavily(self, query: str) -> str:
        """使用Tavily搜索"""
        response = self.tavily_client.search(
            query=query,
            search_depth="basic",
            include_answer=True,
            max_results=3
        )

        result = f"🎯 Tavily AI搜索结果：{response.get('answer', '未找到直接答案')}\n\n"

        for i, item in enumerate(response.get('results', [])[:3], 1):
            result += f"[{i}] {item.get('title', '')}\n"
            result += f"    {item.get('content', '')[:200]}...\n"
            result += f"    来源: {item.get('url', '')}\n\n"

        return result

    def _search_serpapi(self, query: str) -> str:
        """使用SerpApi搜索"""
        try:
            from serpapi import SerpApiClient
        except ImportError:
            return "错误：SerpApi未安装，请运行 pip install serpapi"

        params = {
            "engine": "google",
            "q": query,
            "api_key": self.serpapi_key,
            "gl": "cn",
            "hl": "zh-cn",
        }

        client = SerpApiClient(params)
        results = client.get_dict()

        result_text = "🔍 SerpApi Google搜索结果：\n\n"

        # 智能解析：优先寻找最直接的答案
        if "answer_box" in results and "answer" in results["answer_box"]:
            result_text += f"💡 直接答案：{results['answer_box']['answer']}\n\n"

        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            result_text += f"📖 知识图谱：{results['knowledge_graph']['description']}\n\n"

        if "organic_results" in results and results["organic_results"]:
            result_text += "🔗 相关结果：\n"
            for i, res in enumerate(results["organic_results"][:3], 1):
                result_text += f"[{i}] {res.get('title', '')}\n"
                result_text += f"    {res.get('snippet', '')}\n"
                result_text += f"    来源: {res.get('link', '')}\n\n"
            return result_text

        return f"对不起，没有找到关于 '{query}' 的信息。"

    def _search_mock(self, query: str) -> str:
        """模拟搜索（用于开发测试）"""
        return f"""🔧 模拟搜索结果，查询词：{query}

[1] 相关信息标题
    这里是关于 {query} 的模拟搜索内容。在实际使用中，这里会显示真实的搜索结果。
    来源: https://example.com

[2] 另一个相关结果
    更多关于 {query} 的信息内容。
    来源: https://example2.com

💡 提示：这是模拟结果，请配置TAVILY_API_KEY或SERPAPI_API_KEY以获取实际搜索结果。
   - TAVILY_API_KEY: AI优化的搜索结果
   - SERPAPI_API_KEY: 传统Google搜索结果"""

    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="input",
                type="string",
                description="搜索查询关键词",
                required=True
            )
        ]


# 便捷函数
def search(query: str, backend: str = "hybrid") -> str:
    """
    便捷的搜索函数

    Args:
        query: 搜索查询关键词
        backend: 搜索后端 ("hybrid", "tavily", "serpapi", "mock")

    Returns:
        搜索结果
    """
    tool = SearchTool(backend=backend)
    return tool.run({"input": query})


# 专用搜索函数
def search_tavily(query: str) -> str:
    """使用Tavily进行AI优化搜索"""
    tool = SearchTool(backend="tavily")
    return tool.run({"input": query})


def search_serpapi(query: str) -> str:
    """使用SerpApi进行Google搜索"""
    tool = SearchTool(backend="serpapi")
    return tool.run({"input": query})


def search_hybrid(query: str) -> str:
    """智能混合搜索，自动选择最佳搜索源"""
    tool = SearchTool(backend="hybrid")
    return tool.run({"input": query})
