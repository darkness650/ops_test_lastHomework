"""
轮询控制相关路由
提供定时轮询的启动、停止、状态查询等 API 接口
"""

import logging

from fastapi import APIRouter, HTTPException, status, Query

from api.schemas import (
    ApiResponse,
    PollingStartRequest,
    PollingResponse,
    PollingStatus,
    PollingHistoryStats,
    HistoryQueryResponse,
    HistoryRecord,
)
from agents.scheduler import get_polling_scheduler


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/polling", tags=["轮询控制"])


@router.post(
    "/start",
    response_model=ApiResponse[PollingResponse],
    status_code=status.HTTP_200_OK,
    summary="启动定时轮询"
)
async def start_polling(request: PollingStartRequest) -> ApiResponse[PollingResponse]:
    """
    启动定时轮询任务
    
    Args:
        request: 启动请求
        
    Returns:
        ApiResponse[PollingResponse]: 操作结果
    """
    try:
        scheduler = get_polling_scheduler()
        
        # 如果指定了间隔，先更新
        if request.interval_minutes:
            scheduler.set_interval(request.interval_minutes)
        
        # 启动轮询
        started = scheduler.start()
        
        if started:
            status_info = scheduler.get_status()
            response = PollingResponse(
                success=True,
                message=f"定时轮询已启动，间隔 {status_info['interval_minutes']} 分钟",
                status=PollingStatus(
                    is_running=status_info["is_running"],
                    interval_minutes=status_info["interval_minutes"],
                    execution_count=status_info["execution_count"],
                    next_run=status_info["next_run"],
                    history_count=status_info.get("history_count", 0),
                    last_run=status_info.get("last_run"),
                ),
            )
        else:
            status_info = scheduler.get_status()
            response = PollingResponse(
                success=False,
                message="轮询已经在运行中",
                status=PollingStatus(
                    is_running=status_info["is_running"],
                    interval_minutes=status_info["interval_minutes"],
                    execution_count=status_info["execution_count"],
                    next_run=status_info["next_run"],
                    history_count=status_info.get("history_count", 0),
                    last_run=status_info.get("last_run"),
                ),
            )
        
        logger.info(f"启动轮询: success={response.success}")
        
        return ApiResponse[PollingResponse](
            code=200,
            message="success",
            data=response,
        )
        
    except Exception as e:
        logger.error(f"启动轮询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动轮询失败: {str(e)}",
        )


@router.post(
    "/stop",
    response_model=ApiResponse[PollingResponse],
    status_code=status.HTTP_200_OK,
    summary="停止定时轮询"
)
async def stop_polling() -> ApiResponse[PollingResponse]:
    """
    停止定时轮询任务
    
    Returns:
        ApiResponse[PollingResponse]: 操作结果
    """
    try:
        scheduler = get_polling_scheduler()
        
        stopped = scheduler.stop()
        
        if stopped:
            response = PollingResponse(
                success=True,
                message="定时轮询已停止",
                status=None,
            )
        else:
            status_info = scheduler.get_status()
            response = PollingResponse(
                success=False,
                message="轮询未在运行",
                status=PollingStatus(
                    is_running=status_info["is_running"],
                    interval_minutes=status_info["interval_minutes"],
                    execution_count=status_info["execution_count"],
                    next_run=status_info["next_run"],
                    history_count=status_info.get("history_count", 0),
                    last_run=status_info.get("last_run"),
                ),
            )
        
        logger.info(f"停止轮询: success={response.success}")
        
        return ApiResponse[PollingResponse](
            code=200,
            message="success",
            data=response,
        )
        
    except Exception as e:
        logger.error(f"停止轮询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止轮询失败: {str(e)}",
        )


@router.get(
    "/status",
    response_model=ApiResponse[PollingResponse],
    status_code=status.HTTP_200_OK,
    summary="获取轮询状态"
)
async def get_polling_status() -> ApiResponse[PollingResponse]:
    """
    获取定时轮询的运行状态
    
    Returns:
        ApiResponse[PollingResponse]: 状态信息
    """
    try:
        scheduler = get_polling_scheduler()
        status_info = scheduler.get_status()
        
        # 使用 .get() 安全访问字典，避免 KeyError
        response = PollingResponse(
            success=True,
            message="success",
            status=PollingStatus(
                is_running=status_info.get("is_running", False),
                interval_minutes=status_info.get("interval_minutes", 5),
                execution_count=status_info.get("execution_count", 0),
                next_run=status_info.get("next_run"),
                history_count=status_info.get("history_count", 0),
                last_run=status_info.get("last_run"),
            ),
        )
        
        return ApiResponse[PollingResponse](
            code=200,
            message="success",
            data=response,
        )
        
    except Exception as e:
        logger.error(f"获取轮询状态失败: {e}", exc_info=True)
        # 返回默认状态而不是 500 错误
        response = PollingResponse(
            success=True,
            message="success",
            status=PollingStatus(
                is_running=False,
                interval_minutes=5,
                execution_count=0,
                next_run=None,
                history_count=0,
                last_run=None,
            ),
        )
        return ApiResponse[PollingResponse](
            code=200,
            message="success",
            data=response,
        )


@router.post(
    "/run-once",
    response_model=ApiResponse[PollingResponse],
    status_code=status.HTTP_200_OK,
    summary="立即执行一次轮询"
)
async def run_once() -> ApiResponse[PollingResponse]:
    """
    立即执行一次轮询（不影响定时任务）
    
    Returns:
        ApiResponse[PollingResponse]: 执行结果
    """
    try:
        scheduler = get_polling_scheduler()
        result = scheduler.run_once()
        
        status_info = scheduler.get_status()
        
        response = PollingResponse(
            success=True,
            message=f"单次轮询执行完成: {result.get('status', 'unknown')}",
            status=PollingStatus(
                is_running=status_info["is_running"],
                interval_minutes=status_info["interval_minutes"],
                execution_count=status_info["execution_count"],
                next_run=status_info["next_run"],
                history_count=status_info.get("history_count", 0),
                last_run=status_info.get("last_run"),
            ),
        )
        
        return ApiResponse[PollingResponse](
            code=200,
            message="success",
            data=response,
        )
        
    except Exception as e:
        logger.error(f"执行单次轮询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行单次轮询失败: {str(e)}",
        )


@router.get(
    "/history",
    response_model=ApiResponse[HistoryQueryResponse],
    status_code=status.HTTP_200_OK,
    summary="获取轮询历史记录"
)
async def get_polling_history(
    limit: int = Query(default=10, ge=1, le=100, description="返回记录数量"),
    query_status: str | None = Query(default=None, description="按状态筛选: normal/warning/critical/error", alias="status"),
) -> ApiResponse[HistoryQueryResponse]:
    """
    获取轮询历史记录
    
    Args:
        limit: 返回记录数量（1-100）
        query_status: 按状态筛选
        
    Returns:
        ApiResponse[HistoryQueryResponse]: 历史记录
    """
    try:
        from pydantic import ValidationError
        
        scheduler = get_polling_scheduler()
        history = scheduler.get_history(limit=limit, status=query_status)
        
        # 转换记录格式，容错处理无效数据
        records = []
        for r in history["records"]:
            try:
                records.append(HistoryRecord(
                    timestamp=r.get("timestamp", ""),
                    status=r.get("status", "normal"),
                    summary=r.get("summary", ""),
                    anomaly_count=r.get("anomaly_count", 0),
                    anomalies=r.get("anomalies", []),
                    duration_ms=float(r.get("duration_ms", 0)),
                    error=r.get("error"),
                ))
            except (ValidationError, Exception) as e:
                logger.warning(f"跳过无效的历史记录: {e}, 记录数据: {r}")
                continue
        
        # 构建统计信息
        stats = history.get("statistics", {
            "total": 0,
            "normal": 0,
            "warning": 0,
            "critical": 0,
            "error": 0,
            "latest_timestamp": None,
        })
        statistics = PollingHistoryStats(
            total=int(stats.get("total", 0)),
            normal=int(stats.get("normal", 0)),
            warning=int(stats.get("warning", 0)),
            critical=int(stats.get("critical", 0)),
            error=int(stats.get("error", 0)),
            latest_timestamp=stats.get("latest_timestamp"),
        )
        
        response = HistoryQueryResponse(
            total=history.get("total", 0),
            returned=len(records),
            records=records,
            statistics=statistics,
        )
        
        return ApiResponse[HistoryQueryResponse](
            code=200,
            message="success",
            data=response,
        )
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}", exc_info=True)
        # 返回空数据而不是 500 错误，避免前端显示错误提示
        empty_response = HistoryQueryResponse(
            total=0,
            returned=0,
            records=[],
            statistics=PollingHistoryStats(
                total=0,
                normal=0,
                warning=0,
                critical=0,
                error=0,
                latest_timestamp=None,
            ),
        )
        return ApiResponse[HistoryQueryResponse](
            code=200,
            message="success",
            data=empty_response,
        )


@router.delete(
    "/history",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="清空轮询历史记录"
)
async def clear_polling_history() -> ApiResponse[dict]:
    """
    清空所有轮询历史记录
    
    Returns:
        ApiResponse[dict]: 操作结果
    """
    try:
        scheduler = get_polling_scheduler()
        scheduler.clear_history()
        
        return ApiResponse[dict](
            code=200,
            message="success",
            data={"cleared": True},
        )
        
    except Exception as e:
        logger.error(f"清空历史记录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空历史记录失败: {str(e)}",
        )
