"""
智能体核心模块
实现 Agent 的核心逻辑，包括 Tool Calling 循环和上下文管理
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from agents.llm_client import LLMClient, LLMMessage, LLMResponse, get_llm_client
from tools.base import BaseTool, ToolRegistry, ToolResult, get_tool_registry


ToolCallCallback = Callable[[str, Dict[str, Any]], None]
ToolResultCallback = Callable[[str, Dict[str, Any], ToolResult], None]


# 获取日志记录器
logger = logging.getLogger(__name__)


class AgentContext:
    """
    智能体上下文
    管理对话历史和工具调用记录
    """
    
    def __init__(self, max_history: int = 20):
        """
        初始化智能体上下文
        
        Args:
            max_history: 最大历史消息数（防止上下文过长）
        """
        self.messages: List[LLMMessage] = []
        self.max_history = max_history
        self.tool_call_history: List[Dict[str, Any]] = []
    
    def add_message(self, message: LLMMessage) -> None:
        """
        添加消息到上下文
        
        Args:
            message: LLM 消息
        """
        self.messages.append(message)
        
        # 如果超过最大历史长度，删除最早的非 system 消息
        if len(self.messages) > self.max_history:
            # 保留第一条 system 消息（如果有）
            system_indices = [
                i for i, msg in enumerate(self.messages)
                if msg.role == LLMMessage.ROLE_SYSTEM
            ]
            
            if system_indices:
                first_system_idx = system_indices[0]
                # 删除 system 消息之后的最早消息
                del self.messages[first_system_idx + 1]
            else:
                # 没有 system 消息，删除最早的
                del self.messages[0]
    
    def add_system_message(self, content: str) -> None:
        """
        添加系统提示消息
        
        Args:
            content: 系统提示内容
        """
        # 如果已有 system 消息，替换它；否则添加到开头
        for i, msg in enumerate(self.messages):
            if msg.role == LLMMessage.ROLE_SYSTEM:
                self.messages[i] = LLMMessage.system(content)
                return
        
        # 没有 system 消息，插入到开头
        self.messages.insert(0, LLMMessage.system(content))
    
    def add_user_message(self, content: str) -> None:
        """
        添加用户消息
        
        Args:
            content: 用户消息内容
        """
        self.add_message(LLMMessage.user(content))
    
    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        添加助手消息
        
        Args:
            content: 助手消息内容
            tool_calls: 工具调用列表
        """
        self.add_message(LLMMessage.assistant(content=content, tool_calls=tool_calls))
    
    def add_tool_message(
        self,
        tool_call_id: str,
        name: str,
        content: str,
    ) -> None:
        """
        添加工具结果消息
        
        Args:
            tool_call_id: 工具调用 ID
            name: 工具名称
            content: 工具执行结果
        """
        self.add_message(LLMMessage.tool(
            tool_call_id=tool_call_id,
            name=name,
            content=content,
        ))
    
    def record_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: ToolResult,
    ) -> None:
        """
        记录工具调用历史
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            result: 执行结果
        """
        self.tool_call_history.append({
            "tool_name": tool_name,
            "arguments": arguments,
            "success": result.success,
            "error": result.error,
        })
    
    def get_messages(self) -> List[LLMMessage]:
        """
        获取所有消息
        
        Returns:
            List[LLMMessage]: 消息列表
        """
        return self.messages
    
    def get_tool_call_history(self) -> List[Dict[str, Any]]:
        """
        获取工具调用历史
        
        Returns:
            List[Dict[str, Any]]: 工具调用历史列表
        """
        return self.tool_call_history
    
    def clear(self) -> None:
        """
        清空上下文（保留 system 消息）
        """
        system_messages = [
            msg for msg in self.messages
            if msg.role == LLMMessage.ROLE_SYSTEM
        ]
        self.messages = system_messages
        self.tool_call_history = []


class AgentResponse:
    """
    智能体响应
    封装 Agent 的最终响应和中间过程
    """
    
    def __init__(
        self,
        content: str,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
    ):
        """
        初始化智能体响应
        
        Args:
            content: 最终文本响应
            tool_calls: 执行的工具调用列表
            context: 智能体上下文
        """
        self.content = content
        self.tool_calls = tool_calls
        self.context = context


class Agent:
    """
    智能体核心类
    实现与 LLM 的交互循环和工具调用
    """
    
    # 默认系统提示
    DEFAULT_SYSTEM_PROMPT = """你是一个专业的微服务运维智能体，帮助用户进行 Kubernetes 集群的运维管理。

你的能力包括：
1. 查询 Kubernetes 集群资源状态（Pods、Deployments、Services、Nodes 等）
2. 查询 Pod 日志进行故障排查
3. 查询 Prometheus 监控指标
4. 分析异常情况并提供根因分析
5. 提供故障恢复建议

工作原则：
1. 当需要获取集群信息时，主动调用相应的工具
2. 不要编造或猜测数据，所有信息必须来自工具调用
3. 分析要基于事实，给出可操作的建议
4. 如果工具调用失败，向用户说明情况
5. 保持回答简洁、专业、有条理

注意：调用工具时，请确保参数正确。"""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        max_tool_calls: int = 10,
        on_tool_call: Optional[ToolCallCallback] = None,
        on_tool_result: Optional[ToolResultCallback] = None,
    ):
        """
        初始化智能体
        
        Args:
            llm_client: LLM 客户端（为 None 时使用全局单例）
            tool_registry: 工具注册表（为 None 时使用全局单例）
            system_prompt: 自定义系统提示
            max_tool_calls: 最大工具调用次数（防止无限循环）
            on_tool_call: 工具调用前的回调函数，参数为 (工具名称, 参数字典)
            on_tool_result: 工具执行后的回调函数，参数为 (工具名称, 参数字典, 执行结果)
        """
        self.llm_client = llm_client or get_llm_client()
        self.tool_registry = tool_registry or get_tool_registry()
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.max_tool_calls = max_tool_calls
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        
        self._register_default_tools()
        
        logger.info(f"智能体初始化完成，已注册工具: {self.tool_registry.get_tool_names()}")
    
    def _register_default_tools(self) -> None:
        """
        注册默认工具
        """
        try:
            from tools.k8s_tools import register_k8s_tools
            register_k8s_tools()
            logger.info("已注册 K8s 工具")
        except Exception as e:
            logger.warning(f"注册 K8s 工具失败: {e}")
        
        try:
            from tools.examples import register_example_tools
            register_example_tools()
            logger.info("已注册示例工具")
        except Exception as e:
            logger.warning(f"注册示例工具失败: {e}")
    
    def chat(
        self,
        user_message: str,
        context: Optional[AgentContext] = None,
        on_tool_call: Optional[ToolCallCallback] = None,
        on_tool_result: Optional[ToolResultCallback] = None,
    ) -> AgentResponse:
        """
        与智能体进行对话
        
        Args:
            user_message: 用户消息
            context: 可选的上下文（用于多轮对话）
            on_tool_call: 工具调用前的回调，覆盖初始化时的设置
            on_tool_result: 工具执行后的回调，覆盖初始化时的设置
            
        Returns:
            AgentResponse: 智能体响应
        """
        # 使用传入的回调或初始化时的回调
        current_on_tool_call = on_tool_call or self.on_tool_call
        current_on_tool_result = on_tool_result or self.on_tool_result
        
        # 创建或使用上下文
        if context is None:
            context = AgentContext()
            context.add_system_message(self.system_prompt)
        
        # 添加用户消息
        context.add_user_message(user_message)
        
        # 执行 Agent 循环
        tool_calls_executed: List[Dict[str, Any]] = []
        
        for iteration in range(self.max_tool_calls):
            logger.info(f"Agent 循环第 {iteration + 1} 次迭代")
            
            # 获取可用工具的 Function Schema
            tools = self.tool_registry.get_openai_functions()
            
            # 调用 LLM
            try:
                response = self.llm_client.chat(
                    messages=context.get_messages(),
                    tools=tools if tools else None,
                )
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}")
                error_msg = f"抱歉，AI 服务暂时不可用：{str(e)}"
                return AgentResponse(
                    content=error_msg,
                    tool_calls=tool_calls_executed,
                    context=context,
                )
            
            # 检查是否有工具调用
            if not response.has_tool_calls():
                # 没有工具调用，返回最终响应
                content = response.content or "抱歉，我无法生成响应。"
                logger.info("Agent 循环完成，无工具调用")
                return AgentResponse(
                    content=content,
                    tool_calls=tool_calls_executed,
                    context=context,
                )
            
            # 有工具调用，执行工具
            logger.info(f"LLM 请求执行 {len(response.get_tool_calls())} 个工具调用")
            
            # 记录助手的工具调用消息
            context.add_assistant_message(
                content=response.content,
                tool_calls=response.get_tool_calls(),
            )
            
            # 执行每个工具调用
            for tool_call in response.get_tool_calls():
                tool_call_info = self._execute_tool_call(
                    tool_call,
                    context,
                    on_tool_call=current_on_tool_call,
                    on_tool_result=current_on_tool_result,
                )
                tool_calls_executed.append(tool_call_info)
        
        # 达到最大工具调用次数
        logger.warning(f"Agent 达到最大工具调用次数 ({self.max_tool_calls})")
        return AgentResponse(
            content="我已经进行了多次查询，但还需要更多信息才能给出完整回答。请尝试提供更具体的问题。",
            tool_calls=tool_calls_executed,
            context=context,
        )
    
    def _execute_tool_call(
        self,
        tool_call: Dict[str, Any],
        context: AgentContext,
        on_tool_call: Optional[ToolCallCallback] = None,
        on_tool_result: Optional[ToolResultCallback] = None,
    ) -> Dict[str, Any]:
        """
        执行单个工具调用
        
        Args:
            tool_call: 工具调用信息
            context: 智能体上下文
            on_tool_call: 工具调用前的回调
            on_tool_result: 工具执行后的回调
            
        Returns:
            Dict[str, Any]: 工具调用结果信息
        """
        tool_call_id = tool_call.get("id", "")
        function_info = tool_call.get("function", {})
        tool_name = function_info.get("name", "")
        arguments_str = function_info.get("arguments", "{}")
        
        logger.info(f"执行工具调用: {tool_name}")
        
        # 解析参数
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError as e:
            logger.error(f"工具参数解析失败: {e}")
            result = ToolResult.failure(f"参数解析失败: {str(e)}")
            arguments = {}
        else:
            # 调用工具开始回调
            if on_tool_call:
                try:
                    on_tool_call(tool_name, arguments)
                except Exception as e:
                    logger.warning(f"工具调用回调执行失败: {e}")
            
            # 执行工具
            result = self.tool_registry.execute_tool(tool_name, **arguments)
        
        # 调用工具结果回调
        if on_tool_result:
            try:
                on_tool_result(tool_name, arguments, result)
            except Exception as e:
                logger.warning(f"工具结果回调执行失败: {e}")
        
        # 记录工具调用
        context.record_tool_call(tool_name, arguments, result)
        
        # 将结果添加到上下文
        context.add_tool_message(
            tool_call_id=tool_call_id,
            name=tool_name,
            content=result.to_json(),
        )
        
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "success": result.success,
            "error": result.error,
        }


# 创建全局智能体单例
_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """
    获取全局智能体单例
    
    Returns:
        Agent: 智能体实例
    """
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


def create_agent(
    system_prompt: Optional[str] = None,
    max_tool_calls: int = 10,
) -> Agent:
    """
    创建新的智能体实例
    
    Args:
        system_prompt: 自定义系统提示
        max_tool_calls: 最大工具调用次数
        
    Returns:
        Agent: 新的智能体实例
    """
    return Agent(
        system_prompt=system_prompt,
        max_tool_calls=max_tool_calls,
    )
