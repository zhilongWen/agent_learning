import os

from dotenv import load_dotenv

from agents import ReflectionAgent
from core import HelloAgentsLLM

load_dotenv(verbose=True)

# 创建LLM
llm = HelloAgentsLLM(
    model=os.getenv("MODEL_ID"),
    app_id=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    provider="openai"
)

# # 创建ReflectionAgent（使用默认提示词）
# agent = ReflectionAgent(
#     name="反思助手",
#     llm=llm,
#     max_iterations=2
# )

# 代码生成专家的自定义提示词
sys_prompts = {
    "initial": """
你是一位资深的程序员。请根据以下要求编写代码：

要求: {task}

请提供完整的代码实现，包含必要的注释和文档。
""",
    "reflect": """
你是一位严格的代码评审专家。请审查以下代码：

# 原始任务: {task}
# 待审查的代码: {content}

请分析代码的质量，包括算法效率、可读性、错误处理等。
如果代码质量良好，请回答"无需改进"。
""",
    "refine": """
请根据代码评审意见优化你的代码：

# 原始任务: {task}
# 上一轮代码: {last_attempt}
# 评审意见: {feedback}

请提供优化后的代码。
"""
}

# 创建代码生成专家
code_agent = ReflectionAgent(
    name="代码专家",
    llm=llm,
    custom_prompts=sys_prompts,
    max_iterations=2
)

if __name__ == '__main__':
    # # 通用任务
    # response = agent.run("解释什么是机器学习")
    # print(response)

    # 代码生成与优化
    response = code_agent.run("编写一个Python函数来计算斐波那契数列")
    print(response)
