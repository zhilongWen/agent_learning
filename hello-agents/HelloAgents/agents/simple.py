# """简单Agent实现"""
#
# from typing import Optional
#
# from langchain_core.messages import HumanMessage, SystemMessage
#
# from core.agent import Agent
# from core.config import Config
# from core.llm import HelloAgentsLLM
# from core.message import Message
#
#
# class SimpleAgent(Agent):
#     """简单的对话Agent"""
#
#     def __init__(
#             self,
#             name: str,
#             llm: HelloAgentsLLM,
#             system_prompt: Optional[str] = None,
#             config: Optional[Config] = None,
#     ):
#         super().__init__(name, llm, system_prompt, config)
#
#     def run(self, input_text: str, **kwargs) -> str:
#         """运行简单 Agent，返回 LLM 回复内容"""
#         messages = []
#
#         if self.system_prompt:
#             messages.append(SystemMessage(content=self.system_prompt))
#
#         for msg in self._history:
#             if msg.role == "user":
#                 messages.append(HumanMessage(content=msg.content))
#
#         messages.append(HumanMessage(content=input_text))
#
#         response = self.llm.invoke(messages)
#
#         self.add_message(Message(input_text, "user"))
#         self.add_message(Message(response.content, "assistant"))
#
#         return response.content
