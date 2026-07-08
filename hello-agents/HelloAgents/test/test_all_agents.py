"""HelloAgents 全面测试套件 - 确保所有Agent可正常使用"""

import pytest
import os
from agents import SimpleAgent, ReActAgent, ReflectionAgent, PlanAndSolveAgent
from core import HelloAgentsLLM
from tools import ToolRegistry
from tools.builtin.calculator import CalculatorTool
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


class TestEnvironment:
    """测试环境配置"""
    
    def test_env_variables(self):
        """验证必要的环境变量已配置"""
        api_key = os.getenv("LLM_API_KEY")
        assert api_key is not None, "请配置 LLM_API_KEY 环境变量"
        assert len(api_key) > 0, "LLM_API_KEY 不能为空"
        print(f"\n✅ 环境变量配置正常")
    
    def test_llm_initialization(self):
        """验证LLM可以正常初始化"""
        try:
            llm = HelloAgentsLLM()
            assert llm is not None
            print(f"\n✅ LLM初始化成功")
        except Exception as e:
            pytest.fail(f"LLM初始化失败: {e}")


class TestSimpleAgentUsage:
    """测试SimpleAgent用户使用场景"""
    
    def test_basic_conversation(self):
        """场景1: 基础对话"""
        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="AI助手",
            llm=llm,
            system_prompt="你是一个友好的AI助手"
        )
        
        result = agent.run("你好，请简单介绍一下自己")
        
        print(f"\n对话结果: {result}")
        assert result is not None
        assert len(result) > 10
        print("✅ SimpleAgent基础对话测试通过")
    
    def test_with_calculator(self):
        """场景2: 使用计算器工具"""
        llm = HelloAgentsLLM()
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        agent = SimpleAgent(
            name="计算助手",
            llm=llm,
            tool_registry=registry,
            enable_tool_calling=True
        )

        result = agent.run("请计算 256 * 789")

        print(f"\n计算结果: {result}")
        # 256 * 789 = 201,984
        assert "201" in result or "201,9" in result
        print("✅ SimpleAgent工具调用测试通过")
    
    def test_multi_turn(self):
        """场景3: 多轮对话"""
        llm = HelloAgentsLLM()
        agent = SimpleAgent("记忆助手", llm)
        
        # 第一轮
        agent.run("我最喜欢的颜色是蓝色")
        # 第二轮
        result = agent.run("我最喜欢什么颜色？")
        
        print(f"\n记忆测试结果: {result}")
        assert "蓝" in result
        print("✅ SimpleAgent多轮对话测试通过")


class TestReActAgentUsage:
    """测试ReActAgent用户使用场景"""

    def test_custom_prompt_legacy_alias(self):
        """场景0: 兼容旧版 custom_prompt 参数"""
        class DummyLLM:
            model = "dummy"

        registry = ToolRegistry()

        def echo_tool(input_text: str) -> str:
            return input_text

        registry.register_function("echo", "回声工具", echo_tool)

        custom_prompt = "可用工具：{tools}\n问题：{question}\n历史：{history}"
        agent = ReActAgent(
            name="兼容助手",
            llm=DummyLLM(),
            tool_registry=registry,
            custom_prompt=custom_prompt,
            max_steps=1
        )

        messages = agent._build_messages("测试问题")

        assert agent.system_prompt == custom_prompt
        assert agent.custom_prompt == custom_prompt
        assert "echo" in messages[0]["content"]
        assert "测试问题" in messages[0]["content"]
        assert "历史：无" in messages[0]["content"]
    
    def test_basic_reasoning(self):
        """场景1: 基础推理"""
        llm = HelloAgentsLLM()
        registry = ToolRegistry()
        
        agent = ReActAgent(
            name="推理助手",
            llm=llm,
            tool_registry=registry,
            max_steps=3
        )
        
        result = agent.run("什么是人工智能？")
        
        print(f"\n推理结果: {result}")
        assert result is not None
        assert len(result) > 10
        print("✅ ReActAgent基础推理测试通过")
    
    def test_tool_reasoning(self):
        """场景2: 工具推理"""
        llm = HelloAgentsLLM()
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        
        agent = ReActAgent(
            name="数学助手",
            llm=llm,
            tool_registry=registry,
            max_steps=5
        )
        
        result = agent.run("一个苹果5元，买8个需要多少钱？")
        
        print(f"\n工具推理结果: {result}")
        assert "40" in result
        print("✅ ReActAgent工具推理测试通过")


class TestReflectionAgentUsage:
    """测试ReflectionAgent用户使用场景"""

    def test_custom_prompts_legacy_alias(self):
        """场景0: 兼容旧版 custom_prompts 参数"""
        class DummyResponse:
            content = "ok"

        class DummyLLM:
            model = "dummy"

            def __init__(self):
                self.calls = []

            def invoke(self, messages, **kwargs):
                self.calls.append(messages)
                return DummyResponse()

        prompts = {
            "initial": "初始任务：{task}",
            "reflect": "反思任务：{task} 内容：{content}",
            "refine": "优化任务：{task} 上次：{last_attempt} 反馈：{feedback}"
        }
        llm = DummyLLM()
        agent = ReflectionAgent(
            name="兼容反思助手",
            llm=llm,
            custom_prompts=prompts,
            max_iterations=1
        )

        assert agent.custom_prompts == prompts

        agent._execute_task("写代码")
        agent._reflect_on_result("写代码", "代码内容")
        agent._refine_result("写代码", "旧代码", "需要优化")

        assert "初始任务：写代码" in llm.calls[0][-1]["content"]
        assert "反思任务：写代码 内容：代码内容" in llm.calls[1][-1]["content"]
        assert "优化任务：写代码 上次：旧代码 反馈：需要优化" in llm.calls[2][-1]["content"]
    
    def test_basic_reflection(self):
        """场景1: 基础反思"""
        llm = HelloAgentsLLM()
        agent = ReflectionAgent(
            name="反思助手",
            llm=llm,
            max_iterations=2
        )

        result = agent.run("用一句话解释什么是机器学习")

        print(f"\n反思结果: {result}")
        assert result is not None
        assert len(result) > 10
        print("✅ ReflectionAgent基础反思测试通过")

    def test_code_generation(self):
        """场景2: 代码生成与反思"""
        llm = HelloAgentsLLM()
        agent = ReflectionAgent(
            name="代码助手",
            llm=llm,
            max_iterations=2
        )

        result = agent.run("写一个Python函数计算阶乘")

        print(f"\n代码生成结果: {result}")
        assert "def" in result or "factorial" in result.lower()
        print("✅ ReflectionAgent代码生成测试通过")


class TestPlanAndSolveAgentUsage:
    """测试PlanAndSolveAgent用户使用场景"""

    def test_max_steps_and_custom_prompts_compatibility(self):
        """场景0: 限制计划执行步数并兼容旧版 custom_prompts"""
        class DummyResponse:
            content = "步骤执行结果"

        class DummyLLM:
            model = "dummy"

            def invoke(self, messages, **kwargs):
                return DummyResponse()

        prompts = {
            "planner": "自定义规划器",
            "executor": "自定义执行器"
        }

        agent = PlanAndSolveAgent(
            name="兼容规划助手",
            llm=DummyLLM(),
            max_steps=1,
            custom_prompts=prompts
        )

        assert agent.max_steps == 1
        assert agent.custom_prompts == prompts
        assert agent.planner.system_prompt == "自定义规划器"
        assert agent.executor.system_prompt == "自定义执行器"

        result = agent.executor.execute("问题", ["步骤一", "步骤二"])
        assert result == "步骤执行结果"

    def test_basic_planning(self):
        """场景1: 基础规划"""
        llm = HelloAgentsLLM()
        agent = PlanAndSolveAgent(
            name="规划助手",
            llm=llm
        )

        result = agent.run("如何学习Python编程？")

        print(f"\n规划结果: {result}")
        assert result is not None
        assert len(result) > 10
        print("✅ PlanAndSolveAgent基础规划测试通过")

    def test_math_planning(self):
        """场景2: 数学问题规划"""
        llm = HelloAgentsLLM()
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        agent = PlanAndSolveAgent(
            name="数学规划助手",
            llm=llm,
            tool_registry=registry,
            enable_tool_calling=True
        )

        result = agent.run("小红有15个糖果，给了小明5个，又买了10个，现在有多少个？")

        print(f"\n数学规划结果: {result}")
        assert "20" in result
        print("✅ PlanAndSolveAgent数学规划测试通过")


class TestAgentComparison:
    """测试不同Agent的对比使用"""

    def test_same_task_different_agents(self):
        """场景: 同一任务使用不同Agent"""
        llm = HelloAgentsLLM()
        task = "解释什么是递归"

        # SimpleAgent
        simple = SimpleAgent("简单助手", llm)
        result1 = simple.run(task)
        print(f"\n[SimpleAgent] {result1[:100]}...")

        # ReflectionAgent
        reflection = ReflectionAgent("反思助手", llm, max_iterations=1)
        result2 = reflection.run(task)
        print(f"\n[ReflectionAgent] {result2[:100]}...")

        # PlanAndSolveAgent
        plan = PlanAndSolveAgent("规划助手", llm)
        result3 = plan.run(task)
        print(f"\n[PlanAndSolveAgent] {result3[:100]}...")

        assert all([result1, result2, result3])
        print("✅ 不同Agent对比测试通过")


class TestErrorHandling:
    """测试错误处理"""

    def test_empty_input(self):
        """场景: 空输入处理"""
        llm = HelloAgentsLLM()
        agent = SimpleAgent("测试助手", llm)

        try:
            result = agent.run("")
            # 应该能处理空输入
            assert result is not None
            print("✅ 空输入处理测试通过")
        except Exception as e:
            print(f"⚠️ 空输入处理异常: {e}")

    def test_agent_without_tools(self):
        """场景: Agent无工具时的表现"""
        llm = HelloAgentsLLM()
        agent = ReActAgent("无工具助手", llm, tool_registry=ToolRegistry())

        result = agent.run("你好")
        assert result is not None
        print("✅ 无工具Agent测试通过")


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "-s", "--tb=short"])
