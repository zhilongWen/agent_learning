import os

from dotenv import load_dotenv

from agents import ReflectionAgent, PlanAndSolveAgent
from core import HelloAgentsLLM

load_dotenv(verbose=True)

# 创建LLM
llm = HelloAgentsLLM(
    model=os.getenv("MODEL_ID"),
    app_id=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    provider="openai"
)

# 创建PlanAndSolveAgent（使用默认提示词）
agent = PlanAndSolveAgent(
    name="规划助手",
    llm=llm
)

if __name__ == '__main__':
    # 通用问题分解
    response = agent.run("如何学习Python编程？")
    print(response)
