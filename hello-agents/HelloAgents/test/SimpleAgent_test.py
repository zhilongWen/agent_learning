import os

from dotenv import load_dotenv

from agents import SimpleAgent
from core import HelloAgentsLLM

load_dotenv(verbose=True)

# 创建LLM
llm = HelloAgentsLLM(
    model=os.getenv("MODEL_ID"),
    app_id=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    provider="openai"
)

# 创建SimpleAgent
agent = SimpleAgent(
    name="AI助手",
    llm=llm,
    system_prompt="你是一个有用的AI助手，请用中文回答问题。"
)

if __name__ == '__main__':
    # 同步对话
    response = agent.run("你好！请介绍一下自己")
    print(response)

    # 流式对话
    print("助手: ", end="", flush=True)
    for chunk in agent.stream_run("什么是人工智能？"):
        print(chunk, end="", flush=True)
    print()

    # 查看对话历史
    history = agent.get_history()
    for msg in history:
        print(f"{msg.role}: {msg.content}")
