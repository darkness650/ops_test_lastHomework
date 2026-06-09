"""
示例工具模块
用于测试和演示工具系统的使用
"""

from typing import Any

from tools.base import BaseTool, ToolParameter, ToolResult


class EchoTool(BaseTool):
    """
    回显工具
    简单的测试工具，返回输入的参数
    """
    
    name = "echo"
    description = "回显输入的消息，用于测试工具调用功能"
    
    parameters = [
        ToolParameter(
            name="message",
            type="string",
            description="要回显的消息",
            required=True,
        ),
        ToolParameter(
            name="uppercase",
            type="boolean",
            description="是否转换为大写",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行回显逻辑
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        message = kwargs.get("message", "")
        uppercase = kwargs.get("uppercase", False)
        
        if uppercase:
            message = message.upper()
        
        return ToolResult.success(
            data={"echo": message},
            message=f"成功回显消息: {message}",
        )


class CalculatorTool(BaseTool):
    """
    计算器工具
    执行简单的数学运算
    """
    
    name = "calculator"
    description = "执行简单的数学运算，支持加法、减法、乘法、除法"
    
    parameters = [
        ToolParameter(
            name="operation",
            type="string",
            description="运算类型",
            required=True,
            enum=["add", "subtract", "multiply", "divide"],
        ),
        ToolParameter(
            name="a",
            type="number",
            description="第一个操作数",
            required=True,
        ),
        ToolParameter(
            name="b",
            type="number",
            description="第二个操作数",
            required=True,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行计算逻辑
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        operation = kwargs.get("operation")
        a = kwargs.get("a")
        b = kwargs.get("b")
        
        try:
            a = float(a)
            b = float(b)
        except (TypeError, ValueError):
            return ToolResult.failure("参数 a 和 b 必须是数字")
        
        if operation == "add":
            result = a + b
            op_symbol = "+"
        elif operation == "subtract":
            result = a - b
            op_symbol = "-"
        elif operation == "multiply":
            result = a * b
            op_symbol = "*"
        elif operation == "divide":
            if b == 0:
                return ToolResult.failure("除数不能为零")
            result = a / b
            op_symbol = "/"
        else:
            return ToolResult.failure(f"不支持的运算类型: {operation}")
        
        return ToolResult.success(
            data={
                "expression": f"{a} {op_symbol} {b}",
                "result": result,
            },
            message=f"计算成功: {a} {op_symbol} {b} = {result}",
        )


def register_example_tools() -> None:
    """
    注册所有示例工具（幂等操作：已注册的工具不会重复注册）
    """
    from tools.base import get_tool_registry
    
    registry = get_tool_registry()
    
    if not registry.has_tool(EchoTool.name):
        registry.register_class(EchoTool)
    
    if not registry.has_tool(CalculatorTool.name):
        registry.register_class(CalculatorTool)
