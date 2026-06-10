"""
Prometheus 指标查询工具模块
提供微服务集群指标查询功能
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, TypeVar

from tools.base import BaseTool, ToolParameter, ToolResult


# 获取日志记录器
logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 1.0  # 重试延迟（秒）

T = TypeVar('T')


def _with_retry(
    func: Callable[..., T],
    max_retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY,
    before_retry: Optional[Callable[[Exception, int], None]] = None,
) -> T:
    """
    带重试机制的函数执行器
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        before_retry: 重试前调用的回调函数，参数为 (异常, 尝试次数)
        
    Returns:
        T: 函数执行结果
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            # 检查是否是可重试的异常（连接错误、超时、远程主机关闭等）
            error_str = str(e).lower()
            is_retryable = any([
                "winerror 10054" in error_str,  # 远程主机强迫关闭
                "connection" in error_str,
                "timeout" in error_str,
                "timed out" in error_str,
                "reset" in error_str,
            ])
            
            if not is_retryable or attempt >= max_retries - 1:
                raise
            
            # 执行重试前回调
            if before_retry is not None:
                try:
                    before_retry(e, attempt + 1)
                except Exception as callback_error:
                    logger.warning(f"重试前回调执行失败: {callback_error}")
            
            logger.warning(
                f"Prometheus 请求失败，将在 {delay} 秒后重试 ({attempt + 1}/{max_retries}): {e}"
            )
            time.sleep(delay * (attempt + 1))  # 指数退避
    
    # 理论上不会到达这里
    raise last_exception


class PrometheusClient:
    """
    Prometheus API 客户端
    封装 Prometheus HTTP API，支持自动重试机制
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化 Prometheus 客户端
        
        Args:
            base_url: Prometheus 服务地址，如 http://localhost:9090
        """
        from config.settings import get_settings
        
        settings = get_settings()
        self.base_url = base_url or settings.prometheus.prometheus_url
        self._initialized = False
        self._httpx_client = None
    
    def _lazy_init(self) -> None:
        """
        延迟初始化 HTTP 客户端
        """
        if self._initialized:
            return
        
        self._create_client()
    
    def _create_client(self) -> None:
        """
        创建 HTTP 客户端
        """
        import httpx
        self._httpx_client = httpx.Client(
            base_url=self.base_url,
            timeout=30.0,
            # 禁用连接池，每次请求都创建新连接，避免连接被服务器关闭后导致 WinError 10054 错误
            limits=httpx.Limits(
                max_keepalive_connections=0,  # 不保留空闲连接
                keepalive_expiry=0,  # 连接立即使过期
            ),
        )
        self._initialized = True
    
    def reset_client(self) -> None:
        """
        重置 HTTP 客户端，关闭旧连接并创建新客户端
        用于处理连接被服务器关闭的情况（如 WinError 10054）
        """
        if self._httpx_client is not None:
            try:
                self._httpx_client.close()
            except Exception:
                pass
            self._httpx_client = None
            self._initialized = False
        self._lazy_init()
    
    def query(
        self,
        query: str,
        time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        执行即时查询（instant query），支持自动重试
        
        Args:
            query: PromQL 查询语句
            time: 查询时间点，默认为当前时间
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        self._lazy_init()
        
        params = {"query": query}
        if time:
            params["time"] = time.timestamp()
        
        def _do_query() -> Dict[str, Any]:
            response = self._httpx_client.get("/api/v1/query", params=params)
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") != "success":
                raise Exception(f"Prometheus 查询失败: {result.get('error')}")
            
            return result["data"]
        
        # 定义重试前回调：重置 HTTP 客户端以处理连接关闭问题
        def _before_retry(e: Exception, attempt: int) -> None:
            logger.info(f"重试前重置 Prometheus 客户端，尝试次数: {attempt}, 错误: {e}")
            self.reset_client()
        
        return _with_retry(_do_query, before_retry=_before_retry)
    
    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "1m",
    ) -> Dict[str, Any]:
        """
        执行范围查询（range query），支持自动重试
        
        Args:
            query: PromQL 查询语句
            start: 开始时间
            end: 结束时间
            step: 采样步长，如 1m、5m、1h
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        self._lazy_init()
        
        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }
        
        def _do_query() -> Dict[str, Any]:
            response = self._httpx_client.get("/api/v1/query_range", params=params)
            response.raise_for_status()
            
            result = response.json()
            if result.get("status") != "success":
                raise Exception(f"Prometheus 范围查询失败: {result.get('error')}")
            
            return result["data"]
        
        # 定义重试前回调：重置 HTTP 客户端以处理连接关闭问题
        def _before_retry(e: Exception, attempt: int) -> None:
            logger.info(f"重试前重置 Prometheus 客户端，尝试次数: {attempt}, 错误: {e}")
            self.reset_client()
        
        return _with_retry(_do_query, before_retry=_before_retry)
    
    def is_available(self) -> bool:
        """
        检查 Prometheus 是否可用
        
        Returns:
            bool: 是否可用
        """
        if not self.base_url:
            return False
        
        try:
            self._lazy_init()
            response = self._httpx_client.get("/api/v1/status/config")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Prometheus 不可用: {e}")
            return False


_prometheus_client: Optional[PrometheusClient] = None


def get_prometheus_client() -> PrometheusClient:
    """
    获取 Prometheus 客户端单例
    
    Returns:
        PrometheusClient: Prometheus 客户端实例
    """
    global _prometheus_client
    if _prometheus_client is None:
        _prometheus_client = PrometheusClient()
    return _prometheus_client


class PrometheusQueryTool(BaseTool):
    """
    Prometheus 查询工具
    执行自定义 PromQL 查询
    """
    
    name = "prometheus_query"
    description = (
        "执行自定义 PromQL 查询获取集群指标数据。"
        "支持即时查询和范围查询，用于获取 CPU、内存、网络等各项指标。"
    )
    
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="PromQL 查询语句，如 'sum(rate(container_cpu_usage_seconds_total{namespace=\"default\"}[5m])) by (pod)'",
            required=True,
        ),
        ToolParameter(
            name="query_type",
            type="string",
            description="查询类型: 'instant'（即时查询，返回当前值）或 'range'（范围查询，返回时间序列）。默认 instant",
            required=False,
        ),
        ToolParameter(
            name="last_minutes",
            type="integer",
            description="范围查询时，查询最近多少分钟的数据，如 5、15、60。默认 15 分钟。仅在 query_type=range 时有效",
            required=False,
        ),
        ToolParameter(
            name="step",
            type="string",
            description="范围查询时的采样步长，如 '1m'、'5m'、'1h'。默认 '1m'。仅在 query_type=range 时有效",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行 Prometheus 查询
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            query = kwargs.get("query")
            query_type = kwargs.get("query_type", "instant")
            last_minutes = kwargs.get("last_minutes", 15)
            step = kwargs.get("step", "1m")
            
            logger.info(
                f"Prometheus 查询: query_type={query_type}, query={query[:100]}..."
            )
            
            client = get_prometheus_client()
            
            # 检查 Prometheus 可用性
            if not client.base_url:
                return ToolResult.failure(
                    error="Prometheus 未配置",
                    message="请在 .env 文件中配置 PROMETHEUS_URL",
                )
            
            if query_type == "range":
                # 范围查询
                end = datetime.now()
                start = end - timedelta(minutes=int(last_minutes))
                
                result = client.query_range(
                    query=query,
                    start=start,
                    end=end,
                    step=step,
                )
            else:
                # 即时查询
                result = client.query(query=query)
            
            # 处理结果
            processed = self._process_result(result, query_type)
            
            return ToolResult.success(
                data={
                    "query": query,
                    "query_type": query_type,
                    "last_minutes": last_minutes if query_type == "range" else None,
                    "result_count": len(processed),
                    "results": processed,
                },
                message=f"Prometheus 查询成功，返回 {len(processed)} 个时间序列",
            )
            
        except Exception as e:
            logger.error(f"Prometheus 查询失败: {e}")
            return ToolResult.failure(
                error=f"Prometheus 查询失败: {str(e)}",
                message="请检查 PromQL 语法和 Prometheus 连接",
            )
    
    def _process_result(
        self,
        result: Dict[str, Any],
        query_type: str,
    ) -> List[Dict[str, Any]]:
        """
        处理 Prometheus 查询结果
        
        Args:
            result: 原始查询结果
            query_type: 查询类型
            
        Returns:
            List[Dict[str, Any]]: 处理后的结果列表
        """
        processed = []
        
        for series in result.get("result", []):
            metric = series.get("metric", {})
            values = series.get("values" if query_type == "range" else "value")
            
            if query_type == "range":
                # 范围查询：返回时间序列点
                data_points = []
                for ts, val in values:
                    dt = datetime.fromtimestamp(ts).isoformat()
                    data_points.append({"timestamp": dt, "value": float(val)})
                
                processed.append({
                    "metric": metric,
                    "data_points": data_points,
                    "start_value": data_points[0]["value"] if data_points else None,
                    "end_value": data_points[-1]["value"] if data_points else None,
                    "count": len(data_points),
                })
            else:
                # 即时查询：返回当前值
                if values:
                    timestamp = datetime.fromtimestamp(values[0]).isoformat()
                    value = float(values[1])
                    
                    processed.append({
                        "metric": metric,
                        "timestamp": timestamp,
                        "value": value,
                    })
        
        return processed


class ClusterMetricsTool(BaseTool):
    """
    集群整体指标查询工具
    快速获取集群 CPU、内存、磁盘等关键指标
    """
    
    name = "cluster_metrics"
    description = (
        "获取微服务集群的整体运行指标，包括 CPU、内存、磁盘等关键资源使用情况。"
        "无需编写 PromQL，直接获取集群概览数据。"
    )
    
    parameters = [
        ToolParameter(
            name="namespace",
            type="string",
            description="按命名空间筛选指标，不填则查询所有命名空间",
            required=False,
        ),
        ToolParameter(
            name="include_nodes",
            type="boolean",
            description="是否包含节点层面的指标。默认 true",
            required=False,
        ),
        ToolParameter(
            name="include_pods",
            type="boolean",
            description="是否包含 Pod 层面的指标（按 Pod 聚合）。默认 true",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行集群指标查询
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            namespace = kwargs.get("namespace")
            include_nodes = kwargs.get("include_nodes", True)
            include_pods = kwargs.get("include_pods", True)
            
            logger.info(f"集群指标查询: namespace={namespace}")
            
            client = get_prometheus_client()
            
            # 检查 Prometheus 可用性
            if not client.base_url:
                return ToolResult.failure(
                    error="Prometheus 未配置",
                    message="请在 .env 文件中配置 PROMETHEUS_URL",
                )
            
            result_data: Dict[str, Any] = {
                "summary": {},
                "nodes": [],
                "pods": [],
            }
            
            # 构建 namespace 过滤条件
            ns_filter = f'namespace="{namespace}"' if namespace else ''
            
            # 1. 查询集群总 CPU 使用情况
            try:
                cpu_query = (
                    f'sum(rate(container_cpu_usage_seconds_total{{{ns_filter},container!="",container!="POD"}}[5m]))'
                    if namespace
                    else 'sum(rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[5m]))'
                )
                cpu_result = client.query(cpu_query)
                if cpu_result.get("result"):
                    result_data["summary"]["cpu_usage_cores"] = float(
                        cpu_result["result"][0]["value"][1]
                    )
            except Exception as e:
                logger.warning(f"CPU 查询失败: {e}")
                result_data["summary"]["cpu_usage_cores"] = None
            
            # 2. 查询集群总内存使用情况
            try:
                mem_query = (
                    f'sum(container_memory_working_set_bytes{{{ns_filter},container!="",container!="POD"}})'
                    if namespace
                    else 'sum(container_memory_working_set_bytes{container!="",container!="POD"})'
                )
                mem_result = client.query(mem_query)
                if mem_result.get("result"):
                    mem_bytes = float(mem_result["result"][0]["value"][1])
                    result_data["summary"]["memory_usage_gb"] = mem_bytes / (1024 ** 3)
            except Exception as e:
                logger.warning(f"内存查询失败: {e}")
                result_data["summary"]["memory_usage_gb"] = None
            
            # 3. 查询节点指标（如果需要）
            if include_nodes:
                try:
                    nodes_query = 'sum by (instance) (1 - rate(node_cpu_seconds_total{mode="idle"}[5m]))'
                    nodes_result = client.query(nodes_query)
                    for node in nodes_result.get("result", []):
                        result_data["nodes"].append({
                            "instance": node["metric"].get("instance"),
                            "cpu_usage_pct": float(node["value"][1]) * 100,
                        })
                except Exception as e:
                    logger.warning(f"节点指标查询失败: {e}")
            
            # 4. 查询 Top 10 Pod CPU 使用
            if include_pods:
                try:
                    ns_part = f'{{{ns_filter}}}' if namespace else ''
                    pod_cpu_query = (
                        f'topk(10, sum by (pod) (rate(container_cpu_usage_seconds_total{ns_part}[5m])))'
                        if namespace
                        else 'topk(10, sum by (pod) (rate(container_cpu_usage_seconds_total[5m])))'
                    )
                    pod_cpu_result = client.query(pod_cpu_query)
                    for pod in pod_cpu_result.get("result", []):
                        result_data["pods"].append({
                            "pod": pod["metric"].get("pod"),
                            "cpu_usage_cores": float(pod["value"][1]),
                        })
                except Exception as e:
                    logger.warning(f"Pod CPU 指标查询失败: {e}")
            
            return ToolResult.success(
                data=result_data,
                message="集群指标查询成功",
            )
            
        except Exception as e:
            logger.error(f"集群指标查询失败: {e}")
            return ToolResult.failure(
                error=f"集群指标查询失败: {str(e)}",
                message="请检查 Prometheus 连接",
            )


class ServerMetricsTool(BaseTool):
    """
    服务器性能指标采集工具
    采集服务器的 CPU、内存、网络等历史指标数据，支持时间范围查询和趋势分析
    """
    
    name = "server_metrics"
    description = (
        "采集服务器的性能指标数据，包括 CPU 使用率、内存使用率、网络带宽等。"
        "支持按时间范围查询历史数据，自动生成统计摘要和趋势分析，帮助分析系统资源使用情况。"
    )
    
    parameters = [
        ToolParameter(
            name="metric_type",
            type="string",
            description="指标类型: 'cpu'（CPU使用率）、'memory'（内存使用）、'network'（网络带宽）、'all'（全部指标）。默认 all",
            required=False,
            enum=["cpu", "memory", "network", "all"],
        ),
        ToolParameter(
            name="period_hours",
            type="integer",
            description="查询时间范围（小时），支持 24（1天）、168（7天）、720（30天）。默认 24 小时",
            required=False,
            default=24,
            enum=[1, 6, 12, 24, 168, 720],
        ),
        ToolParameter(
            name="namespace",
            type="string",
            description="按命名空间筛选指标，不填则查询所有命名空间",
            required=False,
        ),
        ToolParameter(
            name="include_time_series",
            type="boolean",
            description="是否包含详细时间序列数据。默认 false，仅返回统计摘要",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行服务器性能指标采集
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            from tools.metrics_collector import get_metrics_collector
            
            metric_type = kwargs.get("metric_type", "all")
            period_hours = int(kwargs.get("period_hours", 24))
            namespace = kwargs.get("namespace")
            include_time_series = kwargs.get("include_time_series", False)
            
            logger.info(
                f"服务器指标采集: metric_type={metric_type}, "
                f"period_hours={period_hours}, namespace={namespace}"
            )
            
            collector = get_metrics_collector()
            
            # 检查 Prometheus 可用性
            if not collector.is_available():
                return ToolResult.failure(
                    error="Prometheus 服务不可用",
                    message="请检查 Prometheus 连接配置和服务状态",
                )
            
            # 计算时间范围
            end = datetime.now()
            start = end - timedelta(hours=period_hours)
            step = collector._get_step(period_hours)
            
            result_data: Dict[str, Any] = {
                "time_range": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "period_hours": period_hours,
                    "step": step,
                },
                "summary": {},
            }
            
            # 根据指标类型执行查询
            if metric_type in ["cpu", "all"]:
                cpu_data = collector.collect_cpu(start, end, namespace)
                result_data["cpu"] = self._extract_summary(cpu_data, include_time_series)
                result_data["summary"]["cpu"] = self._build_brief_summary(
                    result_data["cpu"], "CPU"
                )
            
            if metric_type in ["memory", "all"]:
                memory_data = collector.collect_memory(start, end, namespace)
                result_data["memory"] = self._extract_summary(memory_data, include_time_series)
                result_data["summary"]["memory"] = self._build_brief_summary(
                    result_data["memory"], "内存"
                )
            
            if metric_type in ["network", "all"]:
                network_data = collector.collect_network(start, end, namespace)
                result_data["network"] = self._extract_network_summary(
                    network_data, include_time_series
                )
                result_data["summary"]["network"] = self._build_network_brief_summary(
                    result_data["network"]
                )
            
            # 生成整体摘要
            result_data["summary"]["overall"] = self._build_overall_summary(result_data)
            
            return ToolResult.success(
                data=result_data,
                message=f"服务器性能指标采集成功，时间范围: {period_hours} 小时",
            )
            
        except Exception as e:
            logger.error(f"服务器指标采集失败: {e}")
            return ToolResult.failure(
                error=f"服务器指标采集失败: {str(e)}",
                message="请检查 Prometheus 服务状态和网络连接",
            )
    
    def _extract_summary(
        self,
        data: Dict[str, Any],
        include_time_series: bool,
    ) -> Dict[str, Any]:
        """
        提取指标摘要信息
        
        Args:
            data: 原始指标数据
            include_time_series: 是否包含时间序列
            
        Returns:
            Dict[str, Any]: 提取后的摘要数据
        """
        result: Dict[str, Any] = {
            "summary": data.get("summary", {}),
            "top_pods": data.get("top_pods", []),
        }
        
        if include_time_series:
            result["time_series"] = data.get("time_series", [])
        
        if "error" in data:
            result["error"] = data["error"]
        
        return result
    
    def _extract_network_summary(
        self,
        data: Dict[str, Any],
        include_time_series: bool,
    ) -> Dict[str, Any]:
        """
        提取网络指标摘要信息
        
        Args:
            data: 原始网络指标数据
            include_time_series: 是否包含时间序列
            
        Returns:
            Dict[str, Any]: 提取后的摘要数据
        """
        result: Dict[str, Any] = {
            "summary": data.get("summary", {}),
        }
        
        if include_time_series:
            result["time_series"] = data.get("time_series", {})
        
        if "error" in data:
            result["error"] = data["error"]
        
        return result
    
    def _build_brief_summary(
        self,
        data: Dict[str, Any],
        metric_name: str,
    ) -> Dict[str, Any]:
        """
        构建简要摘要
        
        Args:
            data: 指标数据
            metric_name: 指标名称
            
        Returns:
            Dict[str, Any]: 简要摘要
        """
        summary = data.get("summary", {})
        
        if "error" in data:
            return {
                "status": "error",
                "message": data["error"],
            }
        
        trend = summary.get("trend")
        trend_desc = self._format_trend(trend)
        
        return {
            "current": summary.get("current"),
            "avg": summary.get("avg"),
            "min": summary.get("min"),
            "max": summary.get("max"),
            "trend": trend,
            "trend_description": trend_desc,
        }
    
    def _build_network_brief_summary(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        构建网络指标简要摘要
        
        Args:
            data: 网络指标数据
            
        Returns:
            Dict[str, Any]: 简要摘要
        """
        summary = data.get("summary", {})
        
        if "error" in data:
            return {
                "status": "error",
                "message": data["error"],
            }
        
        receive_summary = summary.get("receive", {})
        transmit_summary = summary.get("transmit", {})
        
        receive_trend = self._format_trend(receive_summary.get("trend"))
        transmit_trend = self._format_trend(transmit_summary.get("trend"))
        
        return {
            "receive": {
                "current": receive_summary.get("current"),
                "avg": receive_summary.get("avg"),
                "trend_description": receive_trend,
            },
            "transmit": {
                "current": transmit_summary.get("current"),
                "avg": transmit_summary.get("avg"),
                "trend_description": transmit_trend,
            },
            "total_current": summary.get("total_current"),
        }
    
    def _build_overall_summary(
        self,
        result_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        构建整体摘要
        
        Args:
            result_data: 完整结果数据
            
        Returns:
            Dict[str, Any]: 整体摘要
        """
        summary = result_data.get("summary", {})
        issues: List[str] = []
        
        # 检查 CPU 使用率（假设阈值为 80% 或 8 核）
        cpu_summary = summary.get("cpu", {})
        if cpu_summary.get("avg") is not None and cpu_summary["avg"] > 8:
            issues.append("CPU 使用率较高")
        
        # 检查内存使用率（假设阈值为 80% 或 100GB，根据实际情况调整）
        memory_summary = summary.get("memory", {})
        if memory_summary.get("avg") is not None and memory_summary["avg"] > 100:
            issues.append("内存使用率较高")
        
        # 检查趋势
        for metric in ["cpu", "memory"]:
            metric_summary = summary.get(metric, {})
            trend = metric_summary.get("trend")
            if trend is not None and trend > 20:
                metric_name = "CPU" if metric == "cpu" else "内存"
                issues.append(f"{metric_name} 呈上升趋势（+{trend:.1f}%）")
        
        return {
            "issues": issues,
            "health_status": "warning" if len(issues) > 0 else "normal",
        }
    
    def _format_trend(self, trend: Optional[float]) -> str:
        """
        格式化趋势描述
        
        Args:
            trend: 趋势百分比
            
        Returns:
            str: 趋势描述
        """
        if trend is None:
            return "数据不足，无法判断趋势"
        if trend > 20:
            return f"明显上升（+{trend:.1f}%）"
        elif trend > 5:
            return f"小幅上升（+{trend:.1f}%）"
        elif trend < -20:
            return f"明显下降（{trend:.1f}%）"
        elif trend < -5:
            return f"小幅下降（{trend:.1f}%）"
        else:
            return f"基本稳定（{trend:+.1f}%）"


class NodeMetricsTool(BaseTool):
    """
    节点性能指标采集工具
    采集 Kubernetes 集群节点的资源使用情况，包括 CPU、内存、磁盘等
    """
    
    name = "node_metrics"
    description = (
        "采集 Kubernetes 集群中各节点的性能指标，包括 CPU 使用率、内存使用率、磁盘使用率等。"
        "帮助识别资源瓶颈节点和不均衡的资源分配情况。"
    )
    
    parameters = [
        ToolParameter(
            name="period_hours",
            type="integer",
            description="查询时间范围（小时），支持 1、6、12、24、168（7天）。默认 24 小时",
            required=False,
            default=24,
            enum=[1, 6, 12, 24, 168],
        ),
        ToolParameter(
            name="include_detail",
            type="boolean",
            description="是否包含每个节点的详细数据点。默认 false，仅返回统计摘要",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行节点性能指标采集
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            from tools.metrics_collector import get_metrics_collector
            
            period_hours = int(kwargs.get("period_hours", 24))
            include_detail = kwargs.get("include_detail", False)
            
            logger.info(f"节点指标采集: period_hours={period_hours}")
            
            collector = get_metrics_collector()
            
            # 检查 Prometheus 可用性
            if not collector.is_available():
                return ToolResult.failure(
                    error="Prometheus 服务不可用",
                    message="请检查 Prometheus 连接配置和服务状态",
                )
            
            # 计算时间范围
            end = datetime.now()
            start = end - timedelta(hours=period_hours)
            
            # 采集节点数据
            nodes_data = collector.collect_nodes(start, end)
            
            if "error" in nodes_data:
                return ToolResult.failure(
                    error=f"节点指标采集失败: {nodes_data['error']}",
                    message="请检查 Prometheus 指标数据",
                )
            
            # 处理节点数据
            nodes_list = nodes_data.get("list", [])
            nodes_summary = nodes_data.get("summary", {})
            
            # 构建结果
            result_nodes = []
            for node in nodes_list:
                node_result: Dict[str, Any] = {
                    "instance": node.get("instance"),
                    "cpu": node.get("cpu", {}),
                    "memory": node.get("memory", {}),
                }
                
                if "disk" in node:
                    node_result["disk"] = node["disk"]
                
                if include_detail and "data_points" in node.get("cpu", {}):
                    node_result["cpu"]["data_points"] = node["cpu"]["data_points"]
                
                result_nodes.append(node_result)
            
            # 识别高负载节点
            high_cpu_nodes = [
                n["instance"] for n in result_nodes
                if n.get("cpu", {}).get("avg_pct") is not None
                and n["cpu"]["avg_pct"] > 80
            ]
            high_memory_nodes = [
                n["instance"] for n in result_nodes
                if n.get("memory", {}).get("avg_pct") is not None
                and n["memory"]["avg_pct"] > 80
            ]
            
            result_data: Dict[str, Any] = {
                "time_range": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "period_hours": period_hours,
                },
                "summary": nodes_summary,
                "nodes": result_nodes,
                "alerts": {
                    "high_cpu_nodes": high_cpu_nodes,
                    "high_memory_nodes": high_memory_nodes,
                    "has_high_load": len(high_cpu_nodes) > 0 or len(high_memory_nodes) > 0,
                },
            }
            
            # 生成建议
            suggestions: List[str] = []
            if len(high_cpu_nodes) > 0:
                suggestions.append(f"以下节点 CPU 使用率较高（>80%）: {', '.join(high_cpu_nodes)}")
            if len(high_memory_nodes) > 0:
                suggestions.append(f"以下节点内存使用率较高（>80%）: {', '.join(high_memory_nodes)}")
            if len(high_cpu_nodes) == 0 and len(high_memory_nodes) == 0:
                suggestions.append("所有节点资源使用率正常")
            
            result_data["suggestions"] = suggestions
            
            return ToolResult.success(
                data=result_data,
                message=f"节点指标采集成功，共 {nodes_summary.get('total_nodes', 0)} 个节点",
            )
            
        except Exception as e:
            logger.error(f"节点指标采集失败: {e}")
            return ToolResult.failure(
                error=f"节点指标采集失败: {str(e)}",
                message="请检查 Prometheus 服务状态",
            )


class MetricsComparisonTool(BaseTool):
    """
    指标对比分析工具
    对比分析不同时间段的服务器性能指标，识别变化趋势和异常波动
    """
    
    name = "metrics_comparison"
    description = (
        "对比分析两个时间段的服务器性能指标，帮助识别性能变化趋势和异常波动。"
        "常用于故障排查和容量规划分析。"
    )
    
    parameters = [
        ToolParameter(
            name="metric_type",
            type="string",
            description="指标类型: 'cpu'、'memory'、'network'、'all'。默认 all",
            required=False,
            enum=["cpu", "memory", "network", "all"],
        ),
        ToolParameter(
            name="baseline_period_hours",
            type="integer",
            description="基线时间段（小时），作为对比基准。默认 24 小时",
            required=False,
            default=24,
        ),
        ToolParameter(
            name="target_period_hours",
            type="integer",
            description="目标时间段（小时），与基线对比。默认 6 小时",
            required=False,
            default=6,
        ),
        ToolParameter(
            name="namespace",
            type="string",
            description="按命名空间筛选，不填则查询所有命名空间",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行指标对比分析
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            from tools.metrics_collector import get_metrics_collector
            
            metric_type = kwargs.get("metric_type", "all")
            baseline_period = int(kwargs.get("baseline_period_hours", 24))
            target_period = int(kwargs.get("target_period_hours", 6))
            namespace = kwargs.get("namespace")
            
            logger.info(
                f"指标对比分析: metric_type={metric_type}, "
                f"baseline={baseline_period}h, target={target_period}h"
            )
            
            collector = get_metrics_collector()
            
            if not collector.is_available():
                return ToolResult.failure(
                    error="Prometheus 服务不可用",
                    message="请检查 Prometheus 连接配置",
                )
            
            # 计算时间范围
            now = datetime.now()
            
            # 目标时间段：最近的 target_period 小时
            target_end = now
            target_start = target_end - timedelta(hours=target_period)
            
            # 基线时间段：目标时间段之前的 baseline_period 小时
            baseline_end = target_start
            baseline_start = baseline_end - timedelta(hours=baseline_period)
            
            result_data: Dict[str, Any] = {
                "time_ranges": {
                    "baseline": {
                        "start": baseline_start.isoformat(),
                        "end": baseline_end.isoformat(),
                        "hours": baseline_period,
                    },
                    "target": {
                        "start": target_start.isoformat(),
                        "end": target_end.isoformat(),
                        "hours": target_period,
                    },
                },
                "comparisons": {},
            }
            
            # 对比 CPU 指标
            if metric_type in ["cpu", "all"]:
                baseline_cpu = collector.collect_cpu(baseline_start, baseline_end, namespace)
                target_cpu = collector.collect_cpu(target_start, target_end, namespace)
                result_data["comparisons"]["cpu"] = self._compare_metrics(
                    baseline_cpu, target_cpu, "CPU"
                )
            
            # 对比内存指标
            if metric_type in ["memory", "all"]:
                baseline_mem = collector.collect_memory(baseline_start, baseline_end, namespace)
                target_mem = collector.collect_memory(target_start, target_end, namespace)
                result_data["comparisons"]["memory"] = self._compare_metrics(
                    baseline_mem, target_mem, "内存"
                )
            
            # 对比网络指标
            if metric_type in ["network", "all"]:
                baseline_net = collector.collect_network(baseline_start, baseline_end, namespace)
                target_net = collector.collect_network(target_start, target_end, namespace)
                result_data["comparisons"]["network"] = self._compare_network_metrics(
                    baseline_net, target_net
                )
            
            # 生成总体分析
            result_data["analysis"] = self._generate_comparison_analysis(result_data["comparisons"])
            
            return ToolResult.success(
                data=result_data,
                message="指标对比分析完成",
            )
            
        except Exception as e:
            logger.error(f"指标对比分析失败: {e}")
            return ToolResult.failure(
                error=f"指标对比分析失败: {str(e)}",
                message="请检查 Prometheus 服务状态",
            )
    
    def _compare_metrics(
        self,
        baseline: Dict[str, Any],
        target: Dict[str, Any],
        metric_name: str,
    ) -> Dict[str, Any]:
        """
        对比两组指标数据
        
        Args:
            baseline: 基线数据
            target: 目标数据
            metric_name: 指标名称
            
        Returns:
            Dict[str, Any]: 对比结果
        """
        baseline_summary = baseline.get("summary", {})
        target_summary = target.get("summary", {})
        
        baseline_avg = baseline_summary.get("avg")
        target_avg = target_summary.get("avg")
        baseline_current = baseline_summary.get("current")
        target_current = target_summary.get("current")
        
        result: Dict[str, Any] = {
            "baseline": {
                "avg": baseline_avg,
                "current": baseline_current,
                "max": baseline_summary.get("max"),
            },
            "target": {
                "avg": target_avg,
                "current": target_current,
                "max": target_summary.get("max"),
            },
        }
        
        # 计算变化百分比
        if baseline_avg is not None and target_avg is not None and baseline_avg > 0:
            change_pct = ((target_avg - baseline_avg) / baseline_avg) * 100
            result["change_percentage"] = round(change_pct, 2)
            result["change_absolute"] = round(target_avg - baseline_avg, 4)
            
            if abs(change_pct) > 20:
                result["change_status"] = "significant_change"
                result["change_description"] = (
                    f"{metric_name}平均使用率{'上升' if change_pct > 0 else '下降'}"
                    f"{abs(change_pct):.1f}%"
                )
            elif abs(change_pct) > 5:
                result["change_status"] = "moderate_change"
                result["change_description"] = (
                    f"{metric_name}平均使用率{'上升' if change_pct > 0 else '下降'}"
                    f"{abs(change_pct):.1f}%"
                )
            else:
                result["change_status"] = "stable"
                result["change_description"] = f"{metric_name}平均使用率基本稳定"
        else:
            result["change_status"] = "insufficient_data"
            result["change_description"] = "数据不足，无法对比"
        
        # 对比 Top Pods
        if "top_pods" in baseline and "top_pods" in target:
            result["top_pods_changes"] = self._compare_top_pods(
                baseline.get("top_pods", []),
                target.get("top_pods", []),
            )
        
        return result
    
    def _compare_network_metrics(
        self,
        baseline: Dict[str, Any],
        target: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        对比两组网络指标数据
        
        Args:
            baseline: 基线数据
            target: 目标数据
            
        Returns:
            Dict[str, Any]: 对比结果
        """
        baseline_summary = baseline.get("summary", {})
        target_summary = target.get("summary", {})
        
        baseline_rx = baseline_summary.get("receive", {})
        target_rx = target_summary.get("receive", {})
        baseline_tx = baseline_summary.get("transmit", {})
        target_tx = target_summary.get("transmit", {})
        
        result: Dict[str, Any] = {
            "receive": {
                "baseline_avg": baseline_rx.get("avg"),
                "target_avg": target_rx.get("avg"),
                "baseline_current": baseline_rx.get("current"),
                "target_current": target_rx.get("current"),
            },
            "transmit": {
                "baseline_avg": baseline_tx.get("avg"),
                "target_avg": target_tx.get("avg"),
                "baseline_current": baseline_tx.get("current"),
                "target_current": target_tx.get("current"),
            },
            "total_current": {
                "baseline": baseline_summary.get("total_current"),
                "target": target_summary.get("total_current"),
            },
        }
        
        # 计算变化
        changes = []
        for direction in ["receive", "transmit"]:
            base = result[direction]["baseline_avg"]
            targ = result[direction]["target_avg"]
            if base is not None and targ is not None and base > 0:
                pct = ((targ - base) / base) * 100
                changes.append(abs(pct))
        
        if changes:
            max_change = max(changes)
            if max_change > 50:
                result["change_status"] = "significant_change"
            elif max_change > 20:
                result["change_status"] = "moderate_change"
            else:
                result["change_status"] = "stable"
        else:
            result["change_status"] = "insufficient_data"
        
        return result
    
    def _compare_top_pods(
        self,
        baseline_pods: List[Dict[str, Any]],
        target_pods: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        对比 Top Pods 变化
        
        Args:
            baseline_pods: 基线 Pod 列表
            target_pods: 目标 Pod 列表
            
        Returns:
            Dict[str, Any]: 对比结果
        """
        baseline_names = {p.get("pod") for p in baseline_pods}
        target_names = {p.get("pod") for p in target_pods}
        
        new_top_pods = target_names - baseline_names
        dropped_top_pods = baseline_names - target_names
        
        # 找增长最大的 Pod
        baseline_map = {p.get("pod"): p for p in baseline_pods}
        target_map = {p.get("pod"): p for p in target_pods}
        
        top_increases: List[Dict[str, Any]] = []
        for name in target_names & baseline_names:
            base = baseline_map.get(name, {})
            targ = target_map.get(name, {})
            
            # 比较核心指标
            base_val = base.get("avg_cores") or base.get("avg_gb") or 0
            targ_val = targ.get("avg_cores") or targ.get("avg_gb") or 0
            
            if base_val > 0:
                increase = ((targ_val - base_val) / base_val) * 100
                if increase > 20:
                    top_increases.append({
                        "pod": name,
                        "increase_pct": round(increase, 2),
                        "baseline_value": base_val,
                        "target_value": targ_val,
                    })
        
        return {
            "new_top_pods": list(new_top_pods),
            "dropped_top_pods": list(dropped_top_pods),
            "top_increases": sorted(top_increases, key=lambda x: x["increase_pct"], reverse=True)[:5],
        }
    
    def _generate_comparison_analysis(
        self,
        comparisons: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        生成对比分析摘要
        
        Args:
            comparisons: 对比数据
            
        Returns:
            Dict[str, Any]: 分析摘要
        """
        significant_changes: List[str] = []
        findings: List[str] = []
        
        for metric, data in comparisons.items():
            change_status = data.get("change_status", "stable")
            
            if change_status == "significant_change":
                desc = data.get("change_description", "")
                if desc:
                    significant_changes.append(desc)
                    findings.append(f"⚠️ {desc}")
            elif change_status == "moderate_change":
                desc = data.get("change_description", "")
                if desc:
                    findings.append(f"ℹ️ {desc}")
            elif change_status == "stable":
                metric_name = "CPU" if metric == "cpu" else "内存" if metric == "memory" else "网络"
                findings.append(f"✅ {metric_name}指标稳定")
        
        return {
            "has_significant_changes": len(significant_changes) > 0,
            "significant_changes": significant_changes,
            "findings": findings,
            "overall_status": "warning" if len(significant_changes) > 0 else "normal",
        }


def register_prometheus_tools() -> None:
    """
    注册所有 Prometheus 工具（幂等操作：已注册的工具不会重复注册）
    """
    from tools.base import get_tool_registry
    from config.settings import get_settings
    
    settings = get_settings()
    registry = get_tool_registry()
    
    # 检查 Prometheus 是否配置
    if settings.prometheus.prometheus_url:
        # 基础查询工具
        if not registry.has_tool(PrometheusQueryTool.name):
            registry.register_class(PrometheusQueryTool)
        if not registry.has_tool(ClusterMetricsTool.name):
            registry.register_class(ClusterMetricsTool)
        
        # 性能指标采集工具
        if not registry.has_tool(ServerMetricsTool.name):
            registry.register_class(ServerMetricsTool)
        if not registry.has_tool(NodeMetricsTool.name):
            registry.register_class(NodeMetricsTool)
        if not registry.has_tool(MetricsComparisonTool.name):
            registry.register_class(MetricsComparisonTool)
        
        logger.info("已注册所有 Prometheus 相关工具")
    else:
        logger.info("Prometheus 未配置，跳过 Prometheus 工具注册")
