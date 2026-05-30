"""ReAct Agent实现 - 推理与行动结合的智能体"""

import re
from typing import Optional, List, Dict, Any, Tuple
from core.agent import Agent
from core.llm import HelloAgentsLLM
from core.config import Config
from core.message import Message
from tools.registry import ToolRegistry

# 默认ReAct提示词模板
DEFAULT_REACT_PROMPT = """\
你是一个有能力调用外部工具的 ReAct 智能体，必须严格按下面的格式输出。

可用工具:
{tools}

每一步只能输出两行，且都必须出现：
Thought: <你这一轮的思考>
Action: <下面两种格式之一>
  - 调用工具: <tool_name>[<tool_input>]
  - 输出最终答案: Finish[<最终答案>]

强制约束:
1. 即便不需要调用工具，也必须输出一行 Action: Finish[<答案>] 来结束。
2. Action 必须使用方括号包裹参数，不要使用中文括号、空格或省略方括号。
3. 不要输出多余的解释或代码块标记。

示例:
Thought: 这是一道简单算术题，可以直接计算。
Action: Finish[32]

现在开始解决问题。
Question: {question}
History:
{history}
"""


class ReActAgent(Agent):
    """
    ReAct (Reasoning and Acting) Agent
    
    结合推理和行动的智能体，能够：
    1. 分析问题并制定行动计划
    2. 调用外部工具获取信息
    3. 基于观察结果进行推理
    4. 迭代执行直到得出最终答案
    
    这是一个经典的Agent范式，特别适合需要外部信息的任务。
    """

    def __init__(
            self,
            name: str,
            llm: HelloAgentsLLM,
            tool_registry: ToolRegistry,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
            max_steps: int = 5,
            custom_prompt: Optional[str] = None
    ):
        """
        初始化ReActAgent

        Args:
            name: Agent名称
            llm: LLM实例
            tool_registry: 工具注册表
            system_prompt: 系统提示词
            config: 配置对象
            max_steps: 最大执行步数
            custom_prompt: 自定义提示词模板
        """
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []

        # 设置提示词模板：用户自定义优先，否则使用默认模板
        self.prompt_template = custom_prompt if custom_prompt else DEFAULT_REACT_PROMPT

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行ReAct Agent
        
        Args:
            input_text: 用户问题
            **kwargs: 其他参数
            
        Returns:
            最终答案
        """
        self.current_history = []
        current_step = 0

        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            # 构建提示词
            tools_desc = self.tool_registry.get_tools_description()
            history_str = "\n".join(self.current_history)
            prompt = self.prompt_template.format(
                tools=tools_desc,
                question=input_text,
                history=history_str
            )

            # 调用LLM
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm.invoke(messages, **kwargs)

            if not response_text:
                print("❌ 错误：LLM未能返回有效响应。")
                break

            # 解析输出
            thought, action = self._parse_output(response_text)

            if thought:
                print(f"🤔 思考: {thought}")

            if not action:
                print("⚠️ 警告：未能解析出有效的Action，已注入修正提示，重试。")
                self.current_history.append(
                    "System: 上一轮没有输出 Action 行。请严格输出 `Action: <tool>[<input>]` 或 `Action: Finish[<答案>]`。"
                )
                continue

            # 检查是否完成
            if action.startswith("Finish"):
                final_answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {final_answer}")

                # 保存到历史记录
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))

                return final_answer

            # 执行工具调用
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or tool_input is None:
                print(f"⚠️ 警告：Action 格式无效: {action!r}，已注入修正提示，重试。")
                self.current_history.append(f"Action: {action}")
                self.current_history.append(
                    "Observation: 上一行 Action 不符合格式 `<tool>[<input>]` 或 `Finish[<答案>]`，请重新输出。"
                )
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")

            # 调用工具
            observation = self.tool_registry.execute_tool(tool_name, tool_input)
            print(f"👀 观察: {observation}")

            # 更新历史
            self.current_history.append(f"Action: {action}")
            self.current_history.append(f"Observation: {observation}")

        print("⏰ 已达到最大步数，流程终止。")
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))

        return final_answer

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析 LLM 输出，提取 Thought 与 Action

        - 支持多行 Thought（`.` 跨行）
        - Action 取最后一次出现，避免示例中的 `Action: ...` 混淆
        - 容忍 Markdown / 反引号包裹
        """
        cleaned = text.replace("`", "")

        thought_match = re.search(r"Thought:\s*(.+?)(?:\n\s*Action:|\Z)", cleaned, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None

        action_matches = re.findall(r"Action:\s*(.+)", cleaned)
        action = action_matches[-1].strip() if action_matches else None

        # 兜底：模型把答案直接写在 Thought 里、完全没给 Action，但显式说了 "Finish"
        if not action and thought and "Finish[" in thought:
            m = re.search(r"Finish\[[^\]]*\]", thought)
            if m:
                action = m.group(0)

        return thought, action

    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析 Action 文本，提取工具名与入参，兼容嵌套方括号"""
        match = re.match(r"(\w+)\[(.*)\]\s*$", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _parse_action_input(self, action_text: str) -> str:
        """解析 Action 入参"""
        match = re.match(r"\w+\[(.*)\]\s*$", action_text, re.DOTALL)
        return match.group(1) if match else ""
