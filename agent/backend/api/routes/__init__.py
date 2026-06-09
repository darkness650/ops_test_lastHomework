"""
API 路由包
包含所有功能模块的路由
"""

import logging
from fastapi import APIRouter, status

from ..schemas import ApiResponse, HealthResponse


router = APIRouter(prefix="/api", tags=["通用接口"])
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="健康检查"
)
async def health_check() -> HealthResponse:
    logger.info("收到健康检查请求")
    return HealthResponse(status="ok")


@router.get(
    "/",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="根路径"
)
async def root() -> ApiResponse[dict]:
    logger.info("收到根路径请求")
    return ApiResponse(
        code=200,
        message="success",
        data={
            "name": "微服务运维智能体",
            "version": "0.1.0",
            "description": "用于微服务运维的智能体系统"
        }
    )
