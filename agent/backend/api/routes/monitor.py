"""
健康监测相关路由
提供触发健康检查、获取集群状态等 API 接口
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query

from api.schemas import (
    ApiResponse,
    MonitorRequest,
    MonitorResponse,
    AnomalyInfo,
)
from agents.engine import get_analysis_engine, quick_health_check, full_analysis
from agents.analysis_store import get_analysis_store


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitor", tags=["健康监测"])


@router.post(
    "/run",
    response_model=ApiResponse[MonitorResponse],
    status_code=status.HTTP_200_OK,
    summary="执行一次健康检查"
)
async def run_monitor(request: MonitorRequest) -> ApiResponse[MonitorResponse]:
    """
    立即执行一次健康检查
    
    Args:
        request: 监测请求
        
    Returns:
        ApiResponse[MonitorResponse]: 监测结果
    """
    try:
        logger.info(
            f"执行健康检查: namespace={request.namespace}, "
            f"deep_analysis={request.deep_analysis}"
        )
        
        # 执行监测
        if request.deep_analysis:
            result_obj = full_analysis(namespace=request.namespace)
            result = result_obj.to_dict()
        else:
            result = quick_health_check(namespace=request.namespace)
        
        # 构建异常信息列表
        analysis_store = get_analysis_store()
        anomalies = []
        for anomaly in result.get("anomalies", []):
            anomaly_id = anomaly.get("id", str(datetime.now().timestamp()))
            
            # 从分析存储中获取最新的分析状态（如果存在）
            # 这样可以同步已完成的分析状态
            stored_status = analysis_store.get_status(anomaly_id)
            if stored_status:
                analysis_status = stored_status
            else:
                analysis_status = anomaly.get("analysis_status", "pending")
            
            anomalies.append(AnomalyInfo(
                id=anomaly_id,
                type=anomaly.get("type", "unknown"),
                target=anomaly.get("target", "unknown"),
                severity=anomaly.get("severity", "medium"),
                description=anomaly.get("description", ""),
                evidence=anomaly.get("evidence", []),
                timestamp=anomaly.get("timestamp", datetime.now().isoformat()),
                analysis_status=analysis_status,
            ))
        
        # 构建响应
        response = MonitorResponse(
            status=result.get("status", "normal"),
            summary=result.get("summary", ""),
            anomaly_count=result.get("anomaly_count", 0),
            anomalies=anomalies,
            timestamp=result.get("timestamp", datetime.now().isoformat()),
        )
        
        logger.info(
            f"健康检查完成: status={response.status}, "
            f"anomaly_count={response.anomaly_count}"
        )
        
        return ApiResponse[MonitorResponse](
            code=200,
            message="success",
            data=response,
        )
        
    except Exception as e:
        logger.error(f"健康检查执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查执行失败: {str(e)}",
        )


@router.get(
    "/quick",
    response_model=ApiResponse[MonitorResponse],
    status_code=status.HTTP_200_OK,
    summary="快速健康检查"
)
async def quick_monitor(
    namespace: str | None = Query(default=None, description="命名空间"),
) -> ApiResponse[MonitorResponse]:
    """
    快速健康检查（GET 方式）
    
    Args:
        namespace: 命名空间
        
    Returns:
        ApiResponse[MonitorResponse]: 监测结果
    """
    try:
        logger.info(f"快速健康检查: namespace={namespace}")
        
        result = quick_health_check(namespace=namespace)
        
        # 构建异常信息列表
        analysis_store = get_analysis_store()
        anomalies = []
        for anomaly in result.get("anomalies", []):
            anomaly_id = anomaly.get("id", str(datetime.now().timestamp()))
            
            # 从分析存储中获取最新的分析状态（如果存在）
            stored_status = analysis_store.get_status(anomaly_id)
            if stored_status:
                analysis_status = stored_status
            else:
                analysis_status = anomaly.get("analysis_status", "pending")
            
            anomalies.append(AnomalyInfo(
                id=anomaly_id,
                type=anomaly.get("type", "unknown"),
                target=anomaly.get("target", "unknown"),
                severity=anomaly.get("severity", "medium"),
                description=anomaly.get("description", ""),
                evidence=anomaly.get("evidence", []),
                timestamp=anomaly.get("timestamp", datetime.now().isoformat()),
                analysis_status=analysis_status,
            ))
        
        response = MonitorResponse(
            status=result.get("status", "normal"),
            summary=result.get("summary", ""),
            anomaly_count=result.get("anomaly_count", 0),
            anomalies=anomalies,
            timestamp=result.get("timestamp", datetime.now().isoformat()),
        )
        
        return ApiResponse[MonitorResponse](
            code=200,
            message="success",
            data=response,
        )
        
    except Exception as e:
        logger.error(f"快速健康检查失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"快速健康检查失败: {str(e)}",
        )
