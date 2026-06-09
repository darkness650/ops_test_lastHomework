"""
异常处理模块
定义统一的异常处理机制
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from .schemas import ErrorResponse


# 获取日志记录器
logger = logging.getLogger(__name__)


class AppException(Exception):
    """
    应用自定义异常基类
    """
    
    def __init__(
        self, 
        message: str, 
        code: int = status.HTTP_400_BAD_REQUEST,
        detail: Any = None
    ):
        """
        初始化应用异常
        
        Args:
            message: 异常消息
            code: 异常状态码
            detail: 异常详情
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册异常处理器
    
    Args:
        app: FastAPI 应用实例
    """
    
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, 
        exc: AppException
    ) -> JSONResponse:
        """
        处理应用自定义异常
        """
        logger.warning(f"应用异常: {exc.message} (code={exc.code})")
        
        return JSONResponse(
            status_code=exc.code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                detail=str(exc.detail) if exc.detail else None
            ).model_dump()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, 
        exc: RequestValidationError
    ) -> JSONResponse:
        """
        处理请求验证异常
        """
        logger.warning(f"请求验证失败: {exc.errors()}")
        
        # 提取错误详情
        errors = exc.errors()
        error_messages = []
        for err in errors:
            field = ".".join(map(str, err.get("loc", [])))
            msg = err.get("msg", "验证失败")
            error_messages.append(f"{field}: {msg}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="请求参数验证失败",
                detail="; ".join(error_messages)
            ).model_dump()
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, 
        exc: ValidationError
    ) -> JSONResponse:
        """
        处理 Pydantic 验证异常
        """
        logger.warning(f"数据验证失败: {exc.errors()}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message="数据验证失败",
                detail=str(exc)
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, 
        exc: Exception
    ) -> JSONResponse:
        """
        处理通用异常（兜底）
        """
        logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="服务器内部错误",
                detail="请稍后重试或联系管理员"
            ).model_dump()
        )
