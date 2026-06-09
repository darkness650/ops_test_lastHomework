"""
工具基类模块
定义所有工具的抽象基类和通用接口
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field


# 获取日志记录器
logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """
    工具参数描述
    用于定义工具函数的参数 Schema
    """
    # 参数名称
    name: str = Field(description="参数名称")
    # 参数类型（string, number, integer, boolean, array, object）
    type: str = Field(description="参数类型")
    # 参数描述
    description: str = Field(description="参数描述")
    # 是否必需
    required: bool = Field(default=False, description="是否必需")
    # 枚举值（可选）
    enum: Optional[List[Any]] = Field(default=None, description="可选的枚举值列表")
    # 默认值（可选）
    default: Optional[Any] = Field(default=None, description="默认值")
    # 数组项类型（当 type 为 array 时使用）
    items: Optional[Dict[str, Any]] = Field(default=None, description="数组项类型定义")
    # 对象属性（当 type 为 object 时使用）
    properties: Optional[Dict[str, Any]] = Field(default=None, description="对象属性定义")


class ToolResult:
    """
    工具执行结果
    封装工具执行的返回值和状态
    """
    
    def __init__(
        self,
        success: bool,
        data: Optional[Any] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """
        初始化工具执行结果
        
        Args:
            success: 是否执行成功
            data: 执行成功时返回的数据
            error: 执行失败时的错误信息
            message: 附加消息
        """
        self.success = success
        self.data = data
        self.error = error
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 结果字典
        """
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
        }
    
    def to_json(self) -> str:
        """
        转换为 JSON 字符串（用于返回给 LLM）
        
        Returns:
            str: JSON 字符串
        """
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"工具结果 JSON 序列化失败: {e}")
            return json.dumps({
                "success": self.success,
                "error": str(e) if self.success else self.error,
                "message": "JSON 序列化失败，部分数据可能丢失"
            }, ensure_ascii=False)
    
    @classmethod
    def success(cls, data: Any, message: Optional[str] = None) -> "ToolResult":
        """
        创建成功结果
        
        Args:
            data: 返回数据
            message: 附加消息
            
        Returns:
            ToolResult: 成功结果实例
        """
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def failure(cls, error: str, message: Optional[str] = None) -> "ToolResult":
        """
        创建失败结果
        
        Args:
            error: 错误信息
            message: 附加消息
            
        Returns:
            ToolResult: 失败结果实例
        """
        return cls(success=False, error=error, message=message)


class BaseTool(ABC):
    """
    工具抽象基类
    所有工具都需要继承此类并实现抽象方法
    """
    
    # 工具名称（必须由子类重写）
    name: str = ""
    # 工具描述（必须由子类重写，用于 LLM 理解工具用途）
    description: str = ""
    # 工具参数列表（必须由子类重写）
    parameters: List[ToolParameter] = []
    
    def __init__(self):
        """
        初始化工具
        """
        # 验证子类是否正确设置了必需属性
        if not self.name:
            raise ValueError(f"工具类 {self.__class__.__name__} 必须设置 name 属性")
        if not self.description:
            raise ValueError(f"工具类 {self.__class__.__name__} 必须设置 description 属性")
    
    @abstractmethod
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行工具的具体逻辑（子类必须实现）
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        pass
    
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        执行工具（公共入口，包含日志和错误处理）
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        logger.info(f"执行工具: {self.name}")
        logger.debug(f"工具参数: {kwargs}")
        
        try:
            # 验证参数
            validation_error = self._validate_parameters(kwargs)
            if validation_error:
                logger.warning(f"工具参数验证失败: {validation_error}")
                return ToolResult.failure(validation_error)
            
            # 执行具体逻辑
            result = self._execute(**kwargs)
            
            if result.success:
                logger.info(f"工具 {self.name} 执行成功")
            else:
                logger.warning(f"工具 {self.name} 执行失败: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"工具 {self.name} 执行异常: {str(e)}", exc_info=True)
            return ToolResult.failure(f"工具执行异常: {str(e)}")
    
    def _validate_parameters(self, kwargs: Dict[str, Any]) -> Optional[str]:
        """
        验证工具参数
        
        Args:
            kwargs: 参数字典
            
        Returns:
            Optional[str]: 验证失败时返回错误消息，成功时返回 None
        """
        # 检查必需参数
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return f"缺少必需参数: {param.name}"
        
        # 可以添加更多类型检查...
        return None
    
    def get_openai_function_schema(self) -> Dict[str, Any]:
        """
        生成 OpenAI Function Calling 格式的 Schema
        
        Returns:
            Dict[str, Any]: OpenAI Function Schema
        """
        # 构建 properties
        properties: Dict[str, Any] = {}
        required: List[str] = []
        
        for param in self.parameters:
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            
            if param.enum:
                prop["enum"] = param.enum
            
            if param.items:
                prop["items"] = param.items
            
            if param.properties:
                prop["properties"] = param.properties
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        # 构建完整的 function schema
        function_schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
        
        return function_schema
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取工具基本信息
        
        Returns:
            Dict[str, Any]: 工具信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.model_dump() for p in self.parameters],
        }


# 工具注册表
class ToolRegistry:
    """
    工具注册表
    管理所有可用工具的注册和发现
    """
    
    def __init__(self):
        """
        初始化工具注册表
        """
        self._tools: Dict[str, BaseTool] = {}
        logger.info("工具注册表初始化完成")
    
    def register(self, tool: BaseTool) -> None:
        """
        注册工具
        
        Args:
            tool: 工具实例
        """
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，将被覆盖")
        
        self._tools[tool.name] = tool
        logger.info(f"工具已注册: {tool.name}")
    
    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """
        注册工具类（自动实例化）
        
        Args:
            tool_class: 工具类
        """
        tool = tool_class()
        self.register(tool)
    
    def unregister(self, tool_name: str) -> None:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"工具已注销: {tool_name}")
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[BaseTool]: 工具实例，不存在则返回 None
        """
        return self._tools.get(tool_name)
    
    def get_all(self) -> List[BaseTool]:
        """
        获取所有已注册的工具
        
        Returns:
            List[BaseTool]: 工具列表
        """
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """
        获取所有已注册工具的名称
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self._tools.keys())
    
    def get_openai_functions(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的 OpenAI Function Schema 列表
        
        Returns:
            List[Dict[str, Any]]: Function Schema 列表
        """
        return [tool.get_openai_function_schema() for tool in self._tools.values()]
    
    def has_tool(self, tool_name: str) -> bool:
        """
        检查工具是否存在
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否存在
        """
        return tool_name in self._tools
    
    def execute_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        tool = self.get(tool_name)
        
        if not tool:
            logger.error(f"工具不存在: {tool_name}")
            return ToolResult.failure(f"工具不存在: {tool_name}")
        
        return tool.execute(**kwargs)


# 创建全局工具注册表单例
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    获取全局工具注册表单例
    
    Returns:
        ToolRegistry: 工具注册表实例
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
