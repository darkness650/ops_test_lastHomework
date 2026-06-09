"""
配置相关路由
提供配置查询等 API 接口（不含敏感信息）
"""

import logging

from fastapi import APIRouter, HTTPException, status

from api.schemas import ApiResponse, ConfigInfo
from config.settings import get_settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/config", tags=["配置查询"])


@router.get(
    "",
    response_model=ApiResponse[ConfigInfo],
    status_code=status.HTTP_200_OK,
    summary="获取系统配置"
)
async def get_config() -> ApiResponse[ConfigInfo]:
    """
    获取系统配置信息（不含敏感数据）
    
    Returns:
        ApiResponse[ConfigInfo]: 配置信息
    """
    try:
        settings = get_settings()
        
        # 检查各组件配置状态
        llm_configured = bool(settings.llm.api_key and settings.llm.base_url)
        k8s_configured = True  # K8s 总是尝试使用默认配置
        prometheus_configured = bool(settings.prometheus.prometheus_url)
        es_configured = bool(settings.elasticsearch.es_url)
        
        config = ConfigInfo(
            polling_interval_minutes=settings.polling_interval_minutes,
            max_history_records=100,
            llm_model=settings.llm.model if llm_configured else None,
            llm_configured=llm_configured,
            kubernetes_configured=k8s_configured,
            prometheus_configured=prometheus_configured,
            elasticsearch_configured=es_configured,
        )
        
        logger.info("获取系统配置")
        
        return ApiResponse[ConfigInfo](
            code=200,
            message="success",
            data=config,
        )
        
    except Exception as e:
        logger.error(f"获取配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}",
        )
