import json
import os

import requests
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

load_dotenv(override=True)

API_KEY = os.environ.get("API_KEY")
BASE_URL = os.environ.get("BASE_URL")
MODEL_ID = os.environ.get("MODEL_ID")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

SYSTEM = "你是一个智能旅行助手。使用提供的工具一步步分析并解决用户的请求，收集到足够信息后直接给出最终答案。"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def get_weather(city: str) -> str:
    """
    通过调用 wttr.in API 查询真实的天气信息。
    """
    # API端点，我们请求JSON格式的数据
    url = f"https://wttr.in/{city}?format=j1"

    try:
        # 发起网络请求
        response = requests.get(url)
        # 检查响应状态码是否为200 (成功)
        response.raise_for_status()
        # 解析返回的JSON数据
        data = response.json()

        # 提取当前天气状况
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        # 格式化成自然语言返回
        return f"{city}当前天气：{weather_desc}，气温{temp_c}摄氏度"

    except requests.exceptions.RequestException as e:
        # 处理网络错误
        return f"错误：查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        # 处理数据解析错误
        return f"错误：解析天气数据失败，可能是城市名称无效 - {e}"


def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气，使用Tavily Search API搜索并返回优化后的景点推荐。
    """

    # 从环境变量或主程序配置中获取API密钥
    api_key = TAVILY_API_KEY  # 推荐方式
    # 或者，我们可以在主循环中传入，如此处代码所示

    if not api_key:
        return "错误：未配置TAVILY_API_KEY。"

    # 2. 初始化Tavily客户端
    tavily = TavilyClient(api_key=api_key)

    # 3. 构造一个精确的查询
    query = f"'{city}' 在'{weather}'天气下最值得去的旅游景点推荐及理由"

    try:
        # 4. 调用API，include_answer=True会返回一个综合性的回答
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        # 5. Tavily返回的结果已经非常干净，可以直接使用
        # response['answer'] 是一个基于所有搜索结果的总结性回答
        if response.get("answer"):
            return response["answer"]

        # 如果没有综合性回答，则格式化原始结果
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"

        return "根据搜索，为您找到以下信息：\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"错误：执行Tavily搜索时出现问题 - {e}"


TOOL_HANDLERS = {
    "get_weather": lambda **kw: get_weather(kw["city"]),
    "get_attraction": lambda **kw: get_attraction(kw["city"], kw["weather"]),
}

TOOLS = [
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "查询指定城市的实时天气。",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名称"}},
            "required": ["city"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_attraction",
        "description": "根据城市和天气搜索推荐的旅游景点。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"},
                "weather": {"type": "string", "description": "天气描述"},
            },
            "required": ["city", "weather"],
        },
    }},
]


def agent_loop(messages: list):
    while True:
        print("input model messages:", messages)
        response = client.chat.completions.create(
            model=MODEL_ID, messages=messages, tools=TOOLS,
        )
        print("model response:", response)
        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if response.choices[0].finish_reason != "tool_calls" or not msg.tool_calls:
            return
        for tc in msg.tool_calls:
            handler = TOOL_HANDLERS.get(tc.function.name)
            args = json.loads(tc.function.arguments or "{}")
            print("handler:", tc.function.name)
            print("args:", args)
            output = handler(**args) if handler else f"Unknown tool: {tc.function.name}"
            print(f"> {tc.function.name}:")
            print(output[:200])
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})


if __name__ == '__main__':
    user_prompt = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
    print(f"用户输入: {user_prompt}\n" + "=" * 40)
    history = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    agent_loop(history)
    final_content = history[-1].get("content") if isinstance(history[-1], dict) else None
    if final_content:
        print("\n最终答案:")
        print(final_content)
