"""
API 响应模型和数据模式
定义统一的响应格式和业务模型
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


# 定义通用类型变量
T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    统一的 API 响应格式
    """
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")


class HealthResponse(BaseModel):
    """
    健康检查响应
    """
    status: str = Field(description="健康状态")


class ErrorResponse(BaseModel):
    """
    错误响应
    """
    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    detail: Optional[str] = Field(default=None, description="错误详情")


# ============================================================================
# 对话相关模型
# ============================================================================

class ChatRequest(BaseModel):
    """
    对话请求
    """
    message: str = Field(description="用户消息")
    context_id: Optional[str] = Field(default=None, description="会话上下文 ID，用于多轮对话")


class ToolCall(BaseModel):
    """
    工具调用记录
    """
    name: str = Field(description="工具名称")
    arguments: Dict[str, Any] = Field(description="工具参数")
    result: Dict[str, Any] = Field(description="工具执行结果")


class ChatResponse(BaseModel):
    """
    对话响应
    """
    response: str = Field(description="AI 响应内容")
    context_id: str = Field(description="会话上下文 ID")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用列表")
    thinking: Optional[str] = Field(default=None, description="思考过程（可选）")


# ============================================================================
# 健康监测相关模型
# ============================================================================

class MonitorRequest(BaseModel):
    """
    健康监测请求
    """
    namespace: Optional[str] = Field(default=None, description="命名空间，不填则监测所有命名空间")
    deep_analysis: bool = Field(default=False, description="是否执行深度分析（需要 LLM）")


class AnomalyInfo(BaseModel):
    """
    异常信息
    """
    id: str = Field(description="异常唯一标识符")
    type: str = Field(description="异常类型")
    target: str = Field(description="影响对象")
    severity: str = Field(description="严重程度: critical/high/medium/low")
    description: str = Field(description="详细描述")
    evidence: List[str] = Field(default_factory=list, description="证据")
    timestamp: str = Field(description="检测时间")
    analysis_status: str = Field(default="pending", description="分析状态: pending/analyzing/completed/failed")


class RecoveryStep(BaseModel):
    """
    恢复步骤
    """
    order: int = Field(description="步骤序号")
    action: str = Field(description="具体操作")
    risk: str = Field(description="风险等级: low/medium/high")
    description: str = Field(description="操作说明")
    validation: Optional[str] = Field(default=None, description="验证步骤")


class RootCauseAnalysis(BaseModel):
    """
    根因分析结果
    """
    category: str = Field(description="根因分类: 资源不足/配置错误/网络问题/代码问题/依赖问题/其他")
    analysis: str = Field(description="详细的根因分析")
    evidence: List[str] = Field(default_factory=list, description="证据")
    confidence: float = Field(default=0.7, description="置信度")


class RecoveryPlan(BaseModel):
    """
    恢复计划
    """
    steps: List[RecoveryStep] = Field(default_factory=list, description="恢复步骤列表")
    precautions: List[str] = Field(default_factory=list, description="注意事项")
    estimated_time: Optional[str] = Field(default=None, description="预计恢复时间")


class AnomalyAnalysis(BaseModel):
    """
    异常分析结果（包含根因分析和恢复建议）
    """
    anomaly_id: str = Field(description="异常唯一标识符")
    root_cause: Optional[RootCauseAnalysis] = Field(default=None, description="根因分析")
    recovery_plan: Optional[RecoveryPlan] = Field(default=None, description="恢复计划")
    status: str = Field(default="pending", description="分析状态: pending/analyzing/completed/failed")
    error_message: Optional[str] = Field(default=None, description="错误信息（分析失败时）")
    created_at: str = Field(description="创建时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")


class MonitorResponse(BaseModel):
    """
    健康监测响应
    """
    status: str = Field(description="整体状态: normal/warning/critical/error")
    summary: str = Field(description="状态摘要")
    anomaly_count: int = Field(description="异常数量")
    anomalies: List[AnomalyInfo] = Field(default_factory=list, description="异常详情列表")
    timestamp: str = Field(description="监测时间")


# ============================================================================
# 轮询控制相关模型
# ============================================================================

class PollingStartRequest(BaseModel):
    """
    启动轮询请求
    """
    interval_minutes: Optional[int] = Field(default=None, description="轮询间隔（分钟），不填则使用配置值")
    namespace: Optional[str] = Field(default=None, description="监测的命名空间")


class PollingStatus(BaseModel):
    """
    轮询状态
    """
    is_running: bool = Field(description="是否正在运行")
    interval_minutes: int = Field(description="轮询间隔（分钟）")
    execution_count: int = Field(description="已执行次数")
    next_run: Optional[str] = Field(default=None, description="下次执行时间")
    history_count: Optional[int] = Field(default=None, description="历史记录总数")
    last_run: Optional[str] = Field(default=None, description="上次执行时间")


class PollingHistoryStats(BaseModel):
    """
    轮询历史统计
    """
    total: int = Field(description="总记录数")
    normal: int = Field(description="正常次数")
    warning: int = Field(description="警告次数")
    critical: int = Field(description="严重次数")
    error: int = Field(description="错误次数")
    latest_timestamp: Optional[str] = Field(default=None, description="最新记录时间")


class PollingResponse(BaseModel):
    """
    轮询控制响应
    """
    success: bool = Field(description="操作是否成功")
    message: str = Field(description="操作消息")
    status: Optional[PollingStatus] = Field(default=None, description="当前状态")


# ============================================================================
# 历史记录相关模型
# ============================================================================

class HistoryRecord(BaseModel):
    """
    历史记录
    """
    timestamp: str = Field(description="记录时间")
    status: str = Field(description="状态: normal/warning/critical/error")
    summary: str = Field(description="摘要")
    anomaly_count: int = Field(description="异常数量")
    anomalies: List[AnomalyInfo] = Field(default_factory=list, description="异常详情列表")
    duration_ms: float = Field(description="执行耗时（毫秒）")
    error: Optional[str] = Field(default=None, description="错误信息")


class HistoryQueryResponse(BaseModel):
    """
    历史查询响应
    """
    total: int = Field(description="总记录数")
    returned: int = Field(description="返回记录数")
    records: List[HistoryRecord] = Field(description="记录列表")
    statistics: PollingHistoryStats = Field(description="统计信息")


# ============================================================================
# 配置相关模型
# ============================================================================

class ConfigInfo(BaseModel):
    """
    配置信息（不含敏感数据）
    """
    polling_interval_minutes: int = Field(description="轮询间隔（分钟）")
    max_history_records: int = Field(description="最大历史记录数")
    llm_model: Optional[str] = Field(default=None, description="LLM 模型名称")
    llm_configured: bool = Field(description="LLM 是否已配置")
    kubernetes_configured: bool = Field(description="Kubernetes 是否已配置")
    prometheus_configured: bool = Field(description="Prometheus 是否已配置")
    elasticsearch_configured: bool = Field(description="ElasticSearch 是否已配置")
