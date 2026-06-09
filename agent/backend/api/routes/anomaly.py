"""
异常分析相关路由
提供获取异常分析详情、触发手动分析等 API 接口
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Path

from api.schemas import (
    ApiResponse,
    AnomalyAnalysis,
    RootCauseAnalysis,
    RecoveryPlan,
    RecoveryStep,
)
from agents.analysis_store import get_analysis_store
from agents.anomaly_analyzer import get_anomaly_analyzer


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/anomalies", tags=["异常分析"])


@router.get(
    "/{anomaly_id}/analysis",
    response_model=ApiResponse[AnomalyAnalysis],
    status_code=status.HTTP_200_OK,
    summary="获取异常分析详情"
)
async def get_anomaly_analysis(
    anomaly_id: str = Path(..., description="异常唯一标识符")
) -> ApiResponse[AnomalyAnalysis]:
    """
    获取异常的根因分析和恢复建议
    
    Args:
        anomaly_id: 异常唯一标识符
        
    Returns:
        ApiResponse[AnomalyAnalysis]: 分析结果
    """
    try:
        logger.info(f"获取异常分析详情: anomaly_id={anomaly_id}")
        
        analysis_store = get_analysis_store()
        analysis_data = analysis_store.get_analysis(anomaly_id)
        
        if not analysis_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到异常分析记录: {anomaly_id}",
            )
        
        # 解析根因分析
        root_cause = None
        if analysis_data.get("root_cause"):
            rc = analysis_data["root_cause"]
            
            # 处理 evidence 字段：LLM 可能返回字典列表，需要转换为字符串列表
            # 因为 RootCauseAnalysis.evidence 期望的是 List[str]
            evidence_list = rc.get("evidence", [])
            normalized_evidence = []
            for ev in evidence_list:
                if isinstance(ev, dict):
                    # 如果是字典，转换为 JSON 字符串
                    normalized_evidence.append(json.dumps(ev, ensure_ascii=False))
                elif isinstance(ev, str):
                    normalized_evidence.append(ev)
                else:
                    # 其他类型，转换为字符串
                    normalized_evidence.append(str(ev))
            
            root_cause = RootCauseAnalysis(
                category=rc.get("category", "其他"),
                analysis=rc.get("analysis", ""),
                evidence=normalized_evidence,
                confidence=rc.get("confidence", 0.7),
            )
        
        # 解析恢复计划
        recovery_plan = None
        if analysis_data.get("recovery_plan"):
            rp = analysis_data["recovery_plan"]
            steps = []
            for step_data in rp.get("steps", []):
                steps.append(RecoveryStep(
                    order=step_data.get("order", len(steps) + 1),
                    action=step_data.get("action", ""),
                    risk=step_data.get("risk", "medium"),
                    description=step_data.get("description", ""),
                    validation=step_data.get("validation"),
                ))
            
            recovery_plan = RecoveryPlan(
                steps=steps,
                precautions=rp.get("precautions", []),
                estimated_time=rp.get("estimated_time"),
            )
        
        # 构建响应
        analysis = AnomalyAnalysis(
            anomaly_id=analysis_data["anomaly_id"],
            root_cause=root_cause,
            recovery_plan=recovery_plan,
            status=analysis_data["status"],
            error_message=analysis_data.get("error_message"),
            created_at=analysis_data["created_at"],
            completed_at=analysis_data.get("completed_at"),
        )
        
        return ApiResponse[AnomalyAnalysis](
            code=200,
            message="success",
            data=analysis,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取异常分析详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取异常分析详情失败: {str(e)}",
        )


@router.post(
    "/{anomaly_id}/analyze",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
    summary="触发异常分析"
)
async def trigger_anomaly_analysis(
    anomaly_id: str = Path(..., description="异常唯一标识符")
) -> ApiResponse[dict]:
    """
    手动触发异常的 AI 分析
    如果异常正在分析中，则返回 409 冲突状态，不允许重复触发
    
    Args:
        anomaly_id: 异常唯一标识符
        
    Returns:
        ApiResponse[dict]: 操作结果
    """
    try:
        logger.info(f"手动触发异常分析: anomaly_id={anomaly_id}")
        
        analyzer = get_anomaly_analyzer()
        
        if not analyzer.get_status()["llm_available"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM 未配置，无法执行 AI 分析",
            )
        
        # 检查是否正在分析中
        if analyzer.is_analyzing(anomaly_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"异常 {anomaly_id} 正在分析中，请等待分析完成后再重试",
            )
        
        # 检查数据库中的分析状态
        analysis_store = get_analysis_store()
        db_status = analysis_store.get_status(anomaly_id)
        if db_status == "analyzing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"异常 {anomaly_id} 正在分析中，请等待分析完成后再重试",
            )
        
        # 提交分析任务
        success = analyzer.analyze_anomaly_async(anomaly_id=anomaly_id)
        
        # 确保分析器在运行
        if not analyzer.get_status()["is_running"]:
            analyzer.start()
        
        return ApiResponse[dict](
            code=202,
            message="analysis_submitted" if success else "analysis_already_exists",
            data={
                "anomaly_id": anomaly_id,
                "status": "queued" if success else "exists",
                "message": "分析任务已提交，正在后台执行" if success else "分析任务已存在",
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发异常分析失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发异常分析失败: {str(e)}",
        )


@router.get(
    "/{anomaly_id}/analysis/status",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="获取异常分析状态"
)
async def get_anomaly_analysis_status(
    anomaly_id: str = Path(..., description="异常唯一标识符")
) -> ApiResponse[dict]:
    """
    获取异常分析的当前状态
    
    Args:
        anomaly_id: 异常唯一标识符
        
    Returns:
        ApiResponse[dict]: 分析状态
    """
    try:
        logger.info(f"获取异常分析状态: anomaly_id={anomaly_id}")
        
        analysis_store = get_analysis_store()
        status_value = analysis_store.get_status(anomaly_id)
        
        if status_value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到异常分析记录: {anomaly_id}",
            )
        
        return ApiResponse[dict](
            code=200,
            message="success",
            data={
                "anomaly_id": anomaly_id,
                "status": status_value,
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取异常分析状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取异常分析状态失败: {str(e)}",
        )


@router.get(
    "/analysis/status",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="获取分析器状态"
)
async def get_analyzer_status() -> ApiResponse[dict]:
    """
    获取异常分析器的整体状态
    
    Returns:
        ApiResponse[dict]: 分析器状态
    """
    try:
        analyzer = get_anomaly_analyzer()
        analyzer_status = analyzer.get_status()
        
        return ApiResponse[dict](
            code=200,
            message="success",
            data=analyzer_status,
        )
        
    except Exception as e:
        logger.error(f"获取分析器状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分析器状态失败: {str(e)}",
        )
