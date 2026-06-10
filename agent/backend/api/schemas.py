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


# ============================================================================
# 业务分析报告相关模型
# ============================================================================

class PerformanceBottleneck(BaseModel):
    """
    性能瓶颈模型
    描述系统中检测到的性能瓶颈信息
    """
    target: Optional[str] = Field(default=None, description="目标资源，如 Pod 名称、节点名称等")
    type: str = Field(description="瓶颈类型: cpu/memory/network/disk")
    severity: str = Field(description="严重程度: critical/high/medium/low")
    description: str = Field(description="详细描述")
    metric_value: Optional[float] = Field(default=None, description="当前指标值")
    threshold: Optional[float] = Field(default=None, description="阈值")
    current_value: Optional[float] = Field(default=None, description="当前指标值（别名）")
    stats: Optional[Dict[str, Any]] = Field(default=None, description="统计信息")
    detected_at: Optional[str] = Field(default=None, description="检测时间")
    root_cause: Optional[str] = Field(default=None, description="根因分析（LLM 生成）")
    impact: Optional[str] = Field(default=None, description="影响范围（LLM 生成）")


class BusinessTrend(BaseModel):
    """
    业务趋势模型
    描述业务指标的变化趋势
    """
    metric_name: Optional[str] = Field(default=None, description="指标名称")
    direction: str = Field(description="趋势方向: up/down/stable 或 上升/下降/稳定")
    change_percent: Optional[float] = Field(default=None, description="变化百分比")
    start_value: Optional[float] = Field(default=None, description="起始值")
    end_value: Optional[float] = Field(default=None, description="结束值")
    data_points: List[Dict[str, Any]] = Field(default_factory=list, description="时间序列数据点列表")
    type: Optional[str] = Field(default=None, description="指标类型: cpu/memory/network")
    target: Optional[str] = Field(default=None, description="目标资源")
    change_rate: Optional[float] = Field(default=None, description="变化率（别名）")
    analyzed_at: Optional[str] = Field(default=None, description="分析时间")
    analysis: Optional[str] = Field(default=None, description="趋势分析（LLM 生成）")
    prediction: Optional[str] = Field(default=None, description="未来预测（LLM 生成）")


class OptimizationSuggestion(BaseModel):
    """
    优化建议模型
    提供针对性能问题的优化建议
    """
    priority: str = Field(description="优先级: high/medium/low")
    category: str = Field(description="建议分类，如 资源优化/配置调整/架构改进")
    suggestion: Optional[str] = Field(default=None, description="建议内容")
    impact: Optional[str] = Field(default=None, description="预期影响")
    id: Optional[str] = Field(default=None, description="建议 ID")
    target: Optional[str] = Field(default=None, description="目标资源")
    action: Optional[str] = Field(default=None, description="建议动作")
    details: List[str] = Field(default_factory=list, description="详细步骤")
    description: Optional[str] = Field(default=None, description="描述")
    expected_benefit: Optional[str] = Field(default=None, description="预期收益（LLM 生成）")
    risk: Optional[str] = Field(default=None, description="风险说明（LLM 生成）")


class ClusterHealth(BaseModel):
    """
    集群性能指标
    展示集群在过去一段时间内的各项性能指标统计
    """
    status: str = Field(description="整体状态: healthy/warning/critical")
    cpu_usage_pct: Optional[float] = Field(default=None, description="CPU 平均使用率百分比")
    memory_usage_pct: Optional[float] = Field(default=None, description="内存平均使用率百分比")
    disk_usage_pct: Optional[float] = Field(default=None, description="磁盘平均使用率百分比")
    network_bandwidth_pct: Optional[float] = Field(default=None, description="带宽平均使用率百分比")
    load_average: Optional[float] = Field(default=None, description="系统平均负载")
    network_traffic: Optional[float] = Field(default=None, description="网络流量（Mbps）")
    error_rate: Optional[float] = Field(default=None, description="错误率百分比")
    score: Optional[int] = Field(default=None, description="性能评分（0-100）")
    analysis: Optional[str] = Field(default=None, description="性能状态详细分析")
    bottleneck_count: Optional[int] = Field(default=None, description="瓶颈数量")
    high_count: Optional[int] = Field(default=None, description="高优先级瓶颈数量")
    medium_count: Optional[int] = Field(default=None, description="中优先级瓶颈数量")
    low_count: Optional[int] = Field(default=None, description="低优先级瓶颈数量")
    cpu_stats: Optional[Dict[str, Any]] = Field(default=None, description="CPU 详细统计（min/max/avg）")
    memory_stats: Optional[Dict[str, Any]] = Field(default=None, description="内存详细统计（min/max/avg）")
    disk_stats: Optional[Dict[str, Any]] = Field(default=None, description="磁盘详细统计（min/max/avg）")
    network_stats: Optional[Dict[str, Any]] = Field(default=None, description="网络详细统计（min/max/avg）")
    load_stats: Optional[Dict[str, Any]] = Field(default=None, description="负载详细统计（min/max/avg）")
    analysis_period: Optional[str] = Field(default=None, description="分析时间段")


class PerformanceReport(BaseModel):
    """
    完整性能分析报告模型
    包含完整的性能分析结果
    """
    id: str = Field(description="报告唯一标识符")
    created_at: str = Field(description="创建时间")
    analysis_period_hours: Optional[int] = Field(default=None, description="分析时长（小时）")
    period_hours: Optional[int] = Field(default=None, description="分析时长（小时），别名")
    namespace: Optional[str] = Field(default=None, description="命名空间，为 None 表示全集群")
    status: str = Field(description="报告状态: completed/basic/failed/analyzing")
    summary: str = Field(description="报告摘要")
    cluster_health: Optional[ClusterHealth] = Field(default=None, description="集群性能指标")
    bottlenecks: List[PerformanceBottleneck] = Field(default_factory=list, description="性能瓶颈列表")
    trends: List[BusinessTrend] = Field(default_factory=list, description="业务趋势列表")
    suggestions: List[OptimizationSuggestion] = Field(default_factory=list, description="优化建议列表")
    raw_summary: Optional[str] = Field(default=None, description="原始摘要（未格式化）")
    timestamp: Optional[str] = Field(default=None, description="时间戳")
    analysis_method: Optional[str] = Field(default=None, description="分析方法: rule_based/llm_enhanced")


class AnalysisTriggerRequest(BaseModel):
    """
    分析任务触发请求
    用于手动触发性能分析任务
    """
    analysis_period_hours: int = Field(default=24, description="分析时长（小时），默认 24 小时")
    namespace: Optional[str] = Field(default=None, description="命名空间，不填则分析全集群")


class AnalysisTaskStatus(BaseModel):
    """
    分析任务状态
    用于跟踪分析任务的执行状态
    """
    task_id: str = Field(description="任务唯一标识符")
    status: str = Field(description="任务状态: queued/running/completed/failed")
    progress: float = Field(default=0.0, description="任务进度（0-100）")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    report_id: Optional[str] = Field(default=None, description="生成的报告 ID（任务完成时）")
    error_message: Optional[str] = Field(default=None, description="错误信息（任务失败时）")


class ReportListResponse(BaseModel):
    """
    报告列表响应
    用于分页查询报告列表
    """
    total: int = Field(description="总报告数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    reports: List[PerformanceReport] = Field(description="报告列表")


class ScheduleConfig(BaseModel):
    """
    定时任务配置
    用于配置自动分析任务的执行计划
    """
    enabled: bool = Field(description="是否启用定时任务")
    hour: int = Field(default=2, description="执行时间（小时，0-23），默认凌晨 2 点")
    minute: int = Field(default=0, description="执行时间（分钟，0-59），默认 0 分")
    analysis_period_hours: int = Field(default=24, description="分析时长（小时），默认 24 小时")
