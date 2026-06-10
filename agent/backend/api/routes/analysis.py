"""
业务分析相关路由
提供触发分析任务、查询任务状态、管理报告、配置定时任务等 API 接口
"""

import logging

from fastapi import APIRouter, HTTPException, status, Query

from api.schemas import (
    ApiResponse,
    AnalysisTriggerRequest,
    AnalysisTaskStatus,
    PerformanceReport,
    ReportListResponse,
    ScheduleConfig,
)
from agents.analysis_task_manager import get_analysis_task_manager
from agents.report_store import get_report_store
from agents.schedule_analyzer import get_schedule_analyzer


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["业务分析"])


@router.post(
    "/trigger",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发分析任务"
)
async def trigger_analysis(request: AnalysisTriggerRequest) -> ApiResponse[dict]:
    """
    手动触发业务分析任务（异步执行）
    
    Args:
        request: 分析触发请求，包含分析时长和命名空间
        
    Returns:
        ApiResponse[dict]: 202 Accepted，包含 task_id
    """
    try:
        logger.info(
            f"触发分析任务: analysis_period_hours={request.analysis_period_hours}, "
            f"namespace={request.namespace or '全集群'}"
        )
        
        # 获取分析任务管理器并触发分析
        task_manager = get_analysis_task_manager()
        task_id = task_manager.trigger_analysis(
            period_hours=request.analysis_period_hours,
            namespace=request.namespace
        )
        
        logger.info(f"分析任务已触发: task_id={task_id}")
        
        return ApiResponse[dict](
            code=202,
            message="已接受，分析任务已启动",
            data={"task_id": task_id},
        )
        
    except Exception as e:
        logger.error(f"触发分析任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发分析任务失败: {str(e)}",
        )


@router.get(
    "/task/latest",
    response_model=ApiResponse[AnalysisTaskStatus],
    status_code=status.HTTP_200_OK,
    summary="查询最近一次任务状态"
)
async def get_latest_task() -> ApiResponse[AnalysisTaskStatus]:
    """
    查询最近一次触发的分析任务状态
    
    Returns:
        ApiResponse[AnalysisTaskStatus]: 最近任务状态信息，data 为 null 表示没有任务记录
    """
    try:
        logger.info("查询最近一次任务状态")
        
        # 获取分析任务管理器并查询最近任务
        task_manager = get_analysis_task_manager()
        task_info = task_manager.get_latest_task()
        
        # 如果没有任务记录，返回 200 但 data 为 null
        if task_info is None:
            logger.info("没有找到任何任务记录，返回空响应")
            return ApiResponse[AnalysisTaskStatus](
                code=200,
                message="没有找到任何任务记录",
                data=None,
            )
        
        # 构建任务状态响应
        task_status = AnalysisTaskStatus(
            task_id=task_info["task_id"],
            status=task_info["status"],
            progress=task_info["progress"],
            created_at=task_info["created_at"],
            updated_at=task_info["updated_at"],
            report_id=task_info.get("report_id"),
            error_message=task_info.get("error_message"),
        )
        
        logger.info(
            f"最近任务查询成功: task_id={task_status.task_id}, "
            f"status={task_status.status}"
        )
        
        return ApiResponse[AnalysisTaskStatus](
            code=200,
            message="success",
            data=task_status,
        )
        
    except Exception as e:
        logger.error(f"查询最近任务状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询最近任务状态失败: {str(e)}",
        )


@router.get(
    "/task/{task_id}",
    response_model=ApiResponse[AnalysisTaskStatus],
    status_code=status.HTTP_200_OK,
    summary="查询指定任务状态"
)
async def get_task_status(task_id: str) -> ApiResponse[AnalysisTaskStatus]:
    """
    根据任务 ID 查询分析任务状态
    
    Args:
        task_id: 任务唯一标识符
        
    Returns:
        ApiResponse[AnalysisTaskStatus]: 任务状态信息
        
    Raises:
        HTTPException: 任务不存在时返回 404
    """
    try:
        logger.info(f"查询任务状态: task_id={task_id}")
        
        # 获取分析任务管理器并查询任务状态
        task_manager = get_analysis_task_manager()
        task_info = task_manager.get_task_status(task_id)
        
        if task_info is None:
            logger.warning(f"任务不存在: task_id={task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}",
            )
        
        # 构建任务状态响应
        task_status = AnalysisTaskStatus(
            task_id=task_info["task_id"],
            status=task_info["status"],
            progress=task_info["progress"],
            created_at=task_info["created_at"],
            updated_at=task_info["updated_at"],
            report_id=task_info.get("report_id"),
            error_message=task_info.get("error_message"),
        )
        
        logger.info(
            f"任务状态查询成功: task_id={task_id}, status={task_status.status}, "
            f"progress={task_status.progress}%"
        )
        
        return ApiResponse[AnalysisTaskStatus](
            code=200,
            message="success",
            data=task_status,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询任务状态失败: {str(e)}",
        )


@router.get(
    "/reports",
    response_model=ApiResponse[ReportListResponse],
    status_code=status.HTTP_200_OK,
    summary="分页查询报告列表"
)
async def list_reports(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量，最大 100"),
) -> ApiResponse[ReportListResponse]:
    """
    分页查询性能分析报告列表（按时间倒序）
    
    Args:
        page: 页码，默认 1
        page_size: 每页数量，默认 10
        
    Returns:
        ApiResponse[ReportListResponse]: 分页报告列表
    """
    try:
        logger.info(f"查询报告列表: page={page}, page_size={page_size}")
        
        # 获取报告存储器并分页查询
        report_store = get_report_store()
        result = report_store.list(page=page, page_size=page_size)
        
        # 构建报告列表响应
        reports = []
        for report_data in result["reports"]:
            report = PerformanceReport(**report_data)
            reports.append(report)
        
        report_list = ReportListResponse(
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            reports=reports,
        )
        
        logger.info(
            f"报告列表查询成功: total={report_list.total}, "
            f"returned={len(report_list.reports)}"
        )
        
        return ApiResponse[ReportListResponse](
            code=200,
            message="success",
            data=report_list,
        )
        
    except Exception as e:
        logger.error(f"查询报告列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询报告列表失败: {str(e)}",
        )


@router.get(
    "/reports/{report_id}",
    response_model=ApiResponse[PerformanceReport],
    status_code=status.HTTP_200_OK,
    summary="查询报告详情"
)
async def get_report(report_id: str) -> ApiResponse[PerformanceReport]:
    """
    根据报告 ID 查询性能分析报告详情
    
    Args:
        report_id: 报告唯一标识符
        
    Returns:
        ApiResponse[PerformanceReport]: 报告详情
        
    Raises:
        HTTPException: 报告不存在时返回 404
    """
    try:
        logger.info(f"查询报告详情: report_id={report_id}")
        
        # 获取报告存储器并查询报告
        report_store = get_report_store()
        report_data = report_store.get(report_id)
        
        if report_data is None:
            logger.warning(f"报告不存在: report_id={report_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"报告不存在: {report_id}",
            )
        
        # 构建报告响应
        report = PerformanceReport(**report_data)
        
        logger.info(f"报告查询成功: report_id={report_id}")
        
        return ApiResponse[PerformanceReport](
            code=200,
            message="success",
            data=report,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询报告详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询报告详情失败: {str(e)}",
        )


@router.delete(
    "/reports/{report_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="删除报告"
)
async def delete_report(report_id: str) -> ApiResponse[dict]:
    """
    根据报告 ID 删除性能分析报告
    
    Args:
        report_id: 报告唯一标识符
        
    Returns:
        ApiResponse[dict]: 成功消息
        
    Raises:
        HTTPException: 报告不存在时返回 404
    """
    try:
        logger.info(f"删除报告: report_id={report_id}")
        
        # 获取报告存储器并删除报告
        report_store = get_report_store()
        success = report_store.delete(report_id)
        
        if not success:
            logger.warning(f"报告不存在，无法删除: report_id={report_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"报告不存在: {report_id}",
            )
        
        logger.info(f"报告删除成功: report_id={report_id}")
        
        return ApiResponse[dict](
            code=200,
            message="报告删除成功",
            data={"report_id": report_id},
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除报告失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除报告失败: {str(e)}",
        )


@router.get(
    "/schedule/status",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="查询定时任务状态"
)
async def get_schedule_status() -> ApiResponse[dict]:
    """
    查询定时分析任务的配置和运行状态
    
    Returns:
        ApiResponse[dict]: 包含 ScheduleConfig 和运行状态
    """
    try:
        logger.info("查询定时任务状态")
        
        # 获取定时分析调度器并查询状态
        schedule_analyzer = get_schedule_analyzer()
        status_info = schedule_analyzer.get_status()
        
        # 构建调度配置
        schedule_config = ScheduleConfig(
            enabled=status_info["enabled"],
            hour=status_info["schedule_time"]["hour"],
            minute=status_info["schedule_time"]["minute"],
            analysis_period_hours=status_info["analysis_period_hours"],
        )
        
        # 构建完整的状态响应
        response_data = {
            "is_running": status_info["is_running"],
            "next_run": status_info.get("next_run"),
            "config": schedule_config.model_dump(),
            "config_file": status_info.get("config_file"),
        }
        
        logger.info(
            f"定时任务状态查询成功: is_running={response_data['is_running']}, "
            f"enabled={schedule_config.enabled}"
        )
        
        return ApiResponse[dict](
            code=200,
            message="success",
            data=response_data,
        )
        
    except Exception as e:
        logger.error(f"查询定时任务状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询定时任务状态失败: {str(e)}",
        )


@router.post(
    "/schedule/start",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="启动定时任务"
)
async def start_schedule() -> ApiResponse[dict]:
    """
    启动定时分析任务调度器
    
    Returns:
        ApiResponse[dict]: 操作结果
    """
    try:
        logger.info("启动定时任务")
        
        # 获取定时分析调度器并启动
        schedule_analyzer = get_schedule_analyzer()
        success = schedule_analyzer.start()
        
        if success:
            logger.info("定时任务启动成功")
            return ApiResponse[dict](
                code=200,
                message="定时任务启动成功",
                data={"success": True},
            )
        else:
            logger.warning("定时任务已经在运行")
            return ApiResponse[dict](
                code=200,
                message="定时任务已经在运行",
                data={"success": False},
            )
        
    except Exception as e:
        logger.error(f"启动定时任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动定时任务失败: {str(e)}",
        )


@router.post(
    "/schedule/stop",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="停止定时任务"
)
async def stop_schedule() -> ApiResponse[dict]:
    """
    停止定时分析任务调度器
    
    Returns:
        ApiResponse[dict]: 操作结果
    """
    try:
        logger.info("停止定时任务")
        
        # 获取定时分析调度器并停止
        schedule_analyzer = get_schedule_analyzer()
        success = schedule_analyzer.stop()
        
        if success:
            logger.info("定时任务停止成功")
            return ApiResponse[dict](
                code=200,
                message="定时任务停止成功",
                data={"success": True},
            )
        else:
            logger.warning("定时任务未在运行")
            return ApiResponse[dict](
                code=200,
                message="定时任务未在运行",
                data={"success": False},
            )
        
    except Exception as e:
        logger.error(f"停止定时任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止定时任务失败: {str(e)}",
        )


@router.put(
    "/schedule/config",
    response_model=ApiResponse[ScheduleConfig],
    status_code=status.HTTP_200_OK,
    summary="更新定时配置"
)
async def update_schedule_config(request: ScheduleConfig) -> ApiResponse[ScheduleConfig]:
    """
    更新定时分析任务的配置
    
    Args:
        request: 定时配置请求
        
    Returns:
        ApiResponse[ScheduleConfig]: 更新后的配置
        
    Raises:
        HTTPException: 更新失败时返回 500
    """
    try:
        logger.info(
            f"更新定时配置: hour={request.hour}, minute={request.minute}, "
            f"period_hours={request.analysis_period_hours}, enabled={request.enabled}"
        )
        
        # 获取定时分析调度器并更新配置
        schedule_analyzer = get_schedule_analyzer()
        success = schedule_analyzer.update_config(
            hour=request.hour,
            minute=request.minute,
            period_hours=request.analysis_period_hours,
            enabled=request.enabled,
        )
        
        if not success:
            logger.error("更新定时配置失败")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新定时配置失败，请检查参数是否有效",
            )
        
        # 获取更新后的配置
        status_info = schedule_analyzer.get_status()
        updated_config = ScheduleConfig(
            enabled=status_info["enabled"],
            hour=status_info["schedule_time"]["hour"],
            minute=status_info["schedule_time"]["minute"],
            analysis_period_hours=status_info["analysis_period_hours"],
        )
        
        logger.info("定时配置更新成功")
        
        return ApiResponse[ScheduleConfig](
            code=200,
            message="定时配置更新成功",
            data=updated_config,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新定时配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新定时配置失败: {str(e)}",
        )
