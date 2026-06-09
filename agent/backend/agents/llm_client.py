"""
LLM API 客户端模块
实现与大语言模型 API 的交互，支持工具调用（Tool Calling）
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from config.settings import get_settings


# 获取日志记录器
logger = logging.getLogger(__name__)


class LLMMessage:
    """
    LLM 消息类
    表示与 LLM 交互中的单条消息
    """
    
    ROLE_SYSTEM = "system"
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_TOOL = "tool"
    
    def __init__(
        self,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        """
        初始化 LLM 消息
        
        Args:
            role: 消息角色（system/user/assistant/tool）
            content: 消息内容
            tool_calls: 工具调用列表（assistant 消息使用）
            tool_call_id: 工具调用 ID（tool 消息使用）
            name: 工具名称（tool 消息使用）
        """
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.name = name
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将消息转换为字典格式（用于 API 请求）
        
        Returns:
            Dict[str, Any]: 消息字典
        """
        message: Dict[str, Any] = {"role": self.role}
        
        if self.content is not None:
            message["content"] = self.content
        
        if self.tool_calls is not None:
            message["tool_calls"] = self.tool_calls
        
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        
        if self.name is not None:
            message["name"] = self.name
        
        return message
    
    @classmethod
    def system(cls, content: str) -> "LLMMessage":
        """
        创建系统消息
        
        Args:
            content: 系统消息内容
            
        Returns:
            LLMMessage: 系统消息实例
        """
        return cls(role=cls.ROLE_SYSTEM, content=content)
    
    @classmethod
    def user(cls, content: str) -> "LLMMessage":
        """
        创建用户消息
        
        Args:
            content: 用户消息内容
            
        Returns:
            LLMMessage: 用户消息实例
        """
        return cls(role=cls.ROLE_USER, content=content)
    
    @classmethod
    def assistant(
        cls,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> "LLMMessage":
        """
        创建助手消息
        
        Args:
            content: 助手消息内容
            tool_calls: 工具调用列表
            
        Returns:
            LLMMessage: 助手消息实例
        """
        return cls(role=cls.ROLE_ASSISTANT, content=content, tool_calls=tool_calls)
    
    @classmethod
    def tool(
        cls,
        tool_call_id: str,
        name: str,
        content: str,
    ) -> "LLMMessage":
        """
        创建工具结果消息
        
        Args:
            tool_call_id: 工具调用 ID
            name: 工具名称
            content: 工具执行结果（JSON 字符串）
            
        Returns:
            LLMMessage: 工具结果消息实例
        """
        return cls(
            role=cls.ROLE_TOOL,
            content=content,
            tool_call_id=tool_call_id,
            name=name,
        )


class LLMResponse:
    """
    LLM 响应类
    封装 LLM API 的响应结果
    """
    
    def __init__(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        raw_response: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 LLM 响应
        
        Args:
            content: 文本响应内容
            tool_calls: 工具调用列表
            raw_response: 原始 API 响应
        """
        self.content = content
        self.tool_calls = tool_calls or []
        self.raw_response = raw_response
    
    def has_tool_calls(self) -> bool:
        """
        检查响应是否包含工具调用
        
        Returns:
            bool: 是否包含工具调用
        """
        return len(self.tool_calls) > 0
    
    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """
        获取工具调用列表
        
        Returns:
            List[Dict[str, Any]]: 工具调用列表
        """
        return self.tool_calls


class LLMClient:
    """
    LLM API 客户端
    负责与大语言模型 API 进行交互
    """
    
    def __init__(self):
        """
        初始化 LLM 客户端
        """
        settings = get_settings()
        self.base_url = settings.llm.base_url
        self.api_key = settings.llm.api_key
        self.model = settings.llm.model
        self.timeout = 120.0  # 超时时间 120 秒
        
        # 检查 base_url 是否已经包含 /chat/completions
        # 如果包含，则移除它，以便构建完整的 URL
        if self.base_url.endswith("/chat/completions"):
            self.base_url = self.base_url[:-len("/chat/completions")]
        
        logger.info(f"LLM 客户端初始化完成，模型: {self.model}")
    
    def _build_headers(self) -> Dict[str, str]:
        """
        构建请求头
        
        Returns:
            Dict[str, str]: 请求头字典
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
    
    def _build_url(self) -> str:
        """
        构建完整的 API URL
        
        Returns:
            str: 完整的 API URL
        """
        # 确保 base_url 不以 / 结尾
        base_url = self.base_url.rstrip("/")
        return f"{base_url}/chat/completions"
    
    def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        发送聊天请求到 LLM API
        
        Args:
            messages: 消息列表
            tools: 可用工具列表（JSON Schema 格式）
            temperature: 采样温度
            max_tokens: 最大生成 token 数
            
        Returns:
            LLMResponse: LLM 响应对象
            
        Raises:
            Exception: API 调用失败时抛出异常
        """
        url = self._build_url()
        headers = self._build_headers()
        
        # 构建请求体
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # 如果提供了工具，添加到请求体
        if tools:
            payload["tools"] = tools
            # 设置 tool_choice 为 auto，让模型自行决定是否调用工具
            payload["tool_choice"] = "auto"
        
        logger.debug(f"发送 LLM 请求，URL: {url}，消息数: {len(messages)}，工具数: {len(tools) if tools else 0}")
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"LLM API 请求失败，状态码: {response.status_code}，响应: {response.text}")
                raise Exception(f"LLM API 请求失败: {response.status_code} - {response.text}")
            
            # 解析响应
            response_data = response.json()
            logger.debug(f"LLM 响应接收成功")
            
            return self._parse_response(response_data)
            
        except httpx.TimeoutException:
            logger.error("LLM API 请求超时")
            raise Exception("LLM API 请求超时，请稍后重试")
        except httpx.RequestError as e:
            logger.error(f"LLM API 请求异常: {str(e)}")
            raise Exception(f"LLM API 请求异常: {str(e)}")
    
    def _parse_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """
        解析 LLM API 响应
        
        Args:
            response_data: API 响应数据
            
        Returns:
            LLMResponse: 解析后的响应对象
        """
        choices = response_data.get("choices", [])
        
        if not choices:
            logger.warning("LLM 响应中没有 choices")
            return LLMResponse(raw_response=response_data)
        
        choice = choices[0]
        message = choice.get("message", {})
        
        content = message.get("content")
        tool_calls_raw = message.get("tool_calls", [])
        
        # 解析工具调用
        tool_calls: List[Dict[str, Any]] = []
        
        # 1. 优先处理标准 OpenAI tool_calls 格式
        for tc in tool_calls_raw:
            tool_call = {
                "id": tc.get("id"),
                "type": tc.get("type", "function"),
                "function": {
                    "name": tc.get("function", {}).get("name"),
                    "arguments": tc.get("function", {}).get("arguments", "{}"),
                },
            }
            tool_calls.append(tool_call)
        
        # 2. 如果没有标准 tool_calls，检查 content 中是否包含自定义 JSON 格式的工具调用
        if not tool_calls and content:
            parsed_tool_call = self._parse_custom_tool_call(content)
            if parsed_tool_call:
                tool_calls.append(parsed_tool_call)
                # 将 content 设为 None，因为这是工具调用指令而非最终响应
                content = None
        
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            raw_response=response_data,
        )
    
    def _parse_custom_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """
        解析自定义 JSON 格式的工具调用
        
        支持的格式:
        - {"action": "tool_name", "parameters": {...}}
        - {"function": "tool_name", "arguments": {...}}
        
        Args:
            content: LLM 返回的文本内容
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的工具调用，不是工具调用则返回 None
        """
        import re
        
        # 提取 JSON 代码块或直接解析
        json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        match = re.search(json_pattern, content)
        
        try:
            if match:
                data = json.loads(match.group(1))
            else:
                # 尝试直接解析整个内容
                data = json.loads(content.strip())
        except json.JSONDecodeError:
            return None
        
        # 检查是否是工具调用格式
        if not isinstance(data, dict):
            return None
        
        # 解析 action + parameters 格式
        if "action" in data and "parameters" in data:
            tool_name = data["action"]
            arguments = data.get("parameters", {})
            return {
                "id": f"custom_{tool_name}_{id(data)}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        
        # 解析 function + arguments 格式
        if "function" in data and "arguments" in data:
            tool_name = data["function"]
            arguments = data.get("arguments", {})
            return {
                "id": f"custom_{tool_name}_{id(data)}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        
        return None


# 创建全局 LLM 客户端单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    获取全局 LLM 客户端单例
    
    Returns:
        LLMClient: LLM 客户端实例
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
