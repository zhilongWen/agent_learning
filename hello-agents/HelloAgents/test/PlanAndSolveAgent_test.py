import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    llm=llm,
    max_steps=2
)

if __name__ == '__main__':
    # 通用问题分解
    response = agent.run("用两步说明如何开始学习Python编程。")
    print(response)
