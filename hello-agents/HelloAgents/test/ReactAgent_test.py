import os

from dotenv import load_dotenv

from agents import SimpleAgent, ReActAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin.calculator import calculate

load_dotenv(verbose=True)

# 创建LLM
llm = HelloAgentsLLM(
    model=os.getenv("MODEL_ID"),
    app_id=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    provider="openai"
)

# 创建工具注册表
registry = ToolRegistry()
registry.register_function("calculate", "数学计算工具", calculate)

# # 创建ReActAgent（使用默认提示词）
# agent = ReActAgent(
#     name="工具助手",
#     llm=llm,
#     tool_registry=registry,
#     max_steps=3
# )

# 自定义ReAct提示词模板
custom_prompt = """
你是一个专业的数学解题专家。

可用工具：{tools}

解题格式：
Thought: 分析数学问题的类型和解题策略
Action: 使用工具计算或给出最终答案

问题：{question}
历史：{history}
"""

# 创建自定义ReActAgent
custom_agent = ReActAgent(
    name="数学专家",
    llm=llm,
    tool_registry=registry,
    custom_prompt=custom_prompt,
    max_steps=10
)

if __name__ == '__main__':
    # # 使用工具解决问题
    # response = agent.run("计算 123 * 456 + 789 的结果")
    # print(response)

    # 使用自定义Agent
    # response = custom_agent.run("如果一个正方形的面积是64，那么它的周长是多少？")
    response = custom_agent.run("求正弦函数一个周期在坐标轴上围成的面积")
    print(response)
