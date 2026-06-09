"""
验证 Task 2 完成情况的测试脚本
测试 LLM 客户端、工具抽象层和 Agent 核心循环
"""

import sys
import json
sys.path.insert(0, '.')

# 配置日志
from config.logging_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)


print("=" * 60)
print("Task 2 验证: LLM 客户端与 Tool Calling 抽象层")
print("=" * 60)

all_passed = True

# ============================================================
# 测试 1: LLM 消息类
# ============================================================
print("\n" + "-" * 60)
print("测试 1: LLMMessage 消息类")
print("-" * 60)

try:
    from agents.llm_client import LLMMessage
    
    # 测试系统消息
    system_msg = LLMMessage.system("你是一个助手")
    assert system_msg.role == "system"
    assert system_msg.content == "你是一个助手"
    print("  [PASS] 系统消息创建成功")
    
    # 测试用户消息
    user_msg = LLMMessage.user("你好")
    assert user_msg.role == "user"
    assert user_msg.content == "你好"
    print("  [PASS] 用户消息创建成功")
    
    # 测试助手消息
    assistant_msg = LLMMessage.assistant("你好！有什么可以帮助你的？")
    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == "你好！有什么可以帮助你的？"
    print("  [PASS] 助手消息创建成功")
    
    # 测试工具消息
    tool_msg = LLMMessage.tool(
        tool_call_id="call_123",
        name="echo",
        content='{"success": true, "data": {"echo": "test"}}'
    )
    assert tool_msg.role == "tool"
    assert tool_msg.tool_call_id == "call_123"
    assert tool_msg.name == "echo"
    print("  [PASS] 工具消息创建成功")
    
    # 测试 to_dict 方法
    msg_dict = system_msg.to_dict()
    assert "role" in msg_dict
    assert "content" in msg_dict
    print(f"  [PASS] to_dict 方法正常: {msg_dict}")
    
except Exception as e:
    logger.error(f"测试 1 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 2: LLM 客户端初始化
# ============================================================
print("\n" + "-" * 60)
print("测试 2: LLMClient 客户端初始化")
print("-" * 60)

try:
    from agents.llm_client import LLMClient, get_llm_client
    from config.settings import get_settings
    
    settings = get_settings()
    
    # 测试客户端初始化
    client = LLMClient()
    assert client.model == settings.llm.model
    print(f"  [PASS] LLM 客户端初始化成功，模型: {client.model}")
    print(f"  [PASS] API URL: {client._build_url()}")
    
    # 测试全局单例
    client2 = get_llm_client()
    assert client2 is not None
    print("  [PASS] 全局 LLM 客户端单例获取成功")
    
except Exception as e:
    logger.error(f"测试 2 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 3: 工具参数和结果
# ============================================================
print("\n" + "-" * 60)
print("测试 3: ToolParameter 和 ToolResult")
print("-" * 60)

try:
    from tools.base import ToolParameter, ToolResult
    
    # 测试 ToolParameter
    param = ToolParameter(
        name="test_param",
        type="string",
        description="测试参数",
        required=True,
    )
    assert param.name == "test_param"
    assert param.type == "string"
    assert param.required == True
    print("  [PASS] ToolParameter 创建成功")
    
    # 测试 ToolResult 成功
    success_result = ToolResult.success(
        data={"key": "value"},
        message="操作成功"
    )
    assert success_result.success == True
    assert success_result.data == {"key": "value"}
    print(f"  [PASS] ToolResult.success 正常: {success_result.to_dict()}")
    
    # 测试 ToolResult 失败
    fail_result = ToolResult.failure(
        error="出错了",
        message="详细说明"
    )
    assert fail_result.success == False
    assert fail_result.error == "出错了"
    print(f"  [PASS] ToolResult.failure 正常: {fail_result.to_dict()}")
    
    # 测试 JSON 序列化
    json_str = success_result.to_json()
    parsed = json.loads(json_str)
    assert parsed["success"] == True
    print(f"  [PASS] ToolResult JSON 序列化正常: {json_str[:80]}...")
    
except Exception as e:
    logger.error(f"测试 3 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 4: 工具基类
# ============================================================
print("\n" + "-" * 60)
print("测试 4: BaseTool 工具基类")
print("-" * 60)

try:
    from tools.base import BaseTool, ToolParameter, ToolResult
    from typing import Any
    
    # 创建一个测试工具
    class TestTool(BaseTool):
        name = "test_tool"
        description = "这是一个测试工具"
        parameters = [
            ToolParameter(
                name="input",
                type="string",
                description="输入参数",
                required=True,
            ),
        ]
        
        def _execute(self, **kwargs: Any) -> ToolResult:
            input_val = kwargs.get("input", "")
            return ToolResult.success(data={"output": f"processed: {input_val}"})
    
    # 测试工具初始化
    tool = TestTool()
    assert tool.name == "test_tool"
    assert tool.description == "这是一个测试工具"
    print("  [PASS] 自定义工具创建成功")
    
    # 测试工具信息
    tool_info = tool.get_info()
    assert tool_info["name"] == "test_tool"
    print(f"  [PASS] 工具信息获取成功: {tool_info}")
    
    # 测试 OpenAI Function Schema
    schema = tool.get_openai_function_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test_tool"
    print(f"  [PASS] OpenAI Function Schema 生成成功")
    print(f"         Schema: {json.dumps(schema, ensure_ascii=False, indent=2)[:400]}...")
    
    # 测试工具执行
    result = tool.execute(input="hello")
    assert result.success == True
    assert result.data == {"output": "processed: hello"}
    print(f"  [PASS] 工具执行成功: {result.to_dict()}")
    
    # 测试缺少必需参数
    result_fail = tool.execute()
    assert result_fail.success == False
    print(f"  [PASS] 参数验证工作正常: {result_fail.error}")
    
except Exception as e:
    logger.error(f"测试 4 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 5: 工具注册表
# ============================================================
print("\n" + "-" * 60)
print("测试 5: ToolRegistry 工具注册表")
print("-" * 60)

try:
    from tools.base import ToolRegistry, BaseTool, ToolParameter, ToolResult
    from typing import Any
    
    # 测试工具
    class ToolA(BaseTool):
        name = "tool_a"
        description = "工具 A"
        parameters = []
        def _execute(self, **kwargs: Any) -> ToolResult:
            return ToolResult.success(data="A")
    
    class ToolB(BaseTool):
        name = "tool_b"
        description = "工具 B"
        parameters = []
        def _execute(self, **kwargs: Any) -> ToolResult:
            return ToolResult.success(data="B")
    
    # 创建注册表
    registry = ToolRegistry()
    
    # 测试注册
    registry.register_class(ToolA)
    registry.register(ToolB())
    print(f"  [PASS] 工具注册成功，已注册: {registry.get_tool_names()}")
    
    # 测试获取
    tool_a = registry.get("tool_a")
    assert tool_a is not None
    assert tool_a.name == "tool_a"
    print("  [PASS] 工具获取成功")
    
    # 测试获取所有
    all_tools = registry.get_all()
    assert len(all_tools) == 2
    print(f"  [PASS] 获取所有工具成功，共 {len(all_tools)} 个")
    
    # 测试 OpenAI Functions
    functions = registry.get_openai_functions()
    assert len(functions) == 2
    print(f"  [PASS] OpenAI Functions 生成成功，共 {len(functions)} 个")
    
    # 测试执行
    result = registry.execute_tool("tool_a")
    assert result.success == True
    print(f"  [PASS] 通过注册表执行工具成功: {result.to_dict()}")
    
    # 测试不存在的工具
    result_fail = registry.execute_tool("not_exist")
    assert result_fail.success == False
    print(f"  [PASS] 不存在的工具返回错误: {result_fail.error}")
    
except Exception as e:
    logger.error(f"测试 5 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 6: 示例工具
# ============================================================
print("\n" + "-" * 60)
print("测试 6: 示例工具 (EchoTool, CalculatorTool)")
print("-" * 60)

try:
    from tools import EchoTool, CalculatorTool
    
    # 测试 EchoTool
    echo = EchoTool()
    result = echo.execute(message="hello world", uppercase=True)
    assert result.success == True
    assert result.data["echo"] == "HELLO WORLD"
    print(f"  [PASS] EchoTool 执行成功: {result.data}")
    
    # 测试 CalculatorTool
    calc = CalculatorTool()
    result_add = calc.execute(operation="add", a=2, b=3)
    assert result_add.success == True
    assert result_add.data["result"] == 5
    print(f"  [PASS] CalculatorTool 加法成功: {result_add.data}")
    
    result_div = calc.execute(operation="divide", a=10, b=2)
    assert result_div.success == True
    assert result_div.data["result"] == 5
    print(f"  [PASS] CalculatorTool 除法成功: {result_div.data}")
    
    # 测试除零错误
    result_zero = calc.execute(operation="divide", a=10, b=0)
    assert result_zero.success == False
    print(f"  [PASS] CalculatorTool 除零错误处理: {result_zero.error}")
    
except Exception as e:
    logger.error(f"测试 6 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 7: AgentContext 上下文管理
# ============================================================
print("\n" + "-" * 60)
print("测试 7: AgentContext 上下文管理")
print("-" * 60)

try:
    from agents.agent import AgentContext
    from agents.llm_client import LLMMessage
    from tools.base import ToolResult
    
    context = AgentContext(max_history=10)
    
    # 测试添加消息
    context.add_system_message("系统提示")
    context.add_user_message("用户消息")
    context.add_assistant_message("助手回复")
    
    messages = context.get_messages()
    assert len(messages) == 3
    print(f"  [PASS] 消息添加成功，共 {len(messages)} 条消息")
    
    # 测试工具调用记录
    context.record_tool_call(
        tool_name="test_tool",
        arguments={"param": "value"},
        result=ToolResult.success(data="ok"),
    )
    
    history = context.get_tool_call_history()
    assert len(history) == 1
    print(f"  [PASS] 工具调用记录成功，共 {len(history)} 条")
    
    # 测试清空
    context.clear()
    messages = context.get_messages()
    # 清空后应该只剩 system 消息
    assert len(messages) == 1
    assert messages[0].role == "system"
    print("  [PASS] 上下文清空成功（保留 system 消息）")
    
except Exception as e:
    logger.error(f"测试 7 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 8: Agent 初始化
# ============================================================
print("\n" + "-" * 60)
print("测试 8: Agent 智能体初始化")
print("-" * 60)

try:
    from agents import Agent, create_agent
    from tools import register_example_tools
    
    # 先注册示例工具
    register_example_tools()
    
    # 创建 Agent
    agent = create_agent(
        system_prompt="你是一个测试助手",
        max_tool_calls=5,
    )
    
    assert agent.system_prompt == "你是一个测试助手"
    assert agent.max_tool_calls == 5
    print(f"  [PASS] Agent 创建成功")
    print(f"         系统提示: {agent.system_prompt[:50]}...")
    print(f"         已注册工具: {agent.tool_registry.get_tool_names()}")
    
except Exception as e:
    logger.error(f"测试 8 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试结果汇总
# ============================================================
print("\n" + "=" * 60)
if all_passed:
    print("✓ Task 2 验证完成 - 所有测试通过!")
    print("=" * 60)
    print("\n已实现的功能:")
    print("  1. LLMMessage - 消息类（支持 system/user/assistant/tool 四种角色）")
    print("  2. LLMClient - LLM API 客户端（兼容 OpenAI 格式）")
    print("  3. ToolParameter - 工具参数描述")
    print("  4. ToolResult - 工具执行结果封装")
    print("  5. BaseTool - 工具抽象基类（可继承实现自定义工具）")
    print("  6. ToolRegistry - 工具注册表（注册、发现、执行）")
    print("  7. AgentContext - 对话上下文管理")
    print("  8. Agent - 智能体核心（Tool Calling 循环）")
    print("  9. 示例工具 - EchoTool, CalculatorTool")
else:
    print("✗ Task 2 验证完成 - 部分测试失败，请检查错误信息")
    print("=" * 60)
    sys.exit(1)
