"""
Prometheus 指标查询工具模块
提供微服务集群指标查询功能
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolParameter, ToolResult


# 获取日志记录器
logger = logging.getLogger(__name__)


class PrometheusClient:
    """
    Prometheus API 客户端
    封装 Prometheus HTTP API
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
        
        import httpx
        self._httpx_client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self._initialized = True
    
    def query(
        self,
        query: str,
        time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        执行即时查询（instant query）
        
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
        
        response = self._httpx_client.get("/api/v1/query", params=params)
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") != "success":
            raise Exception(f"Prometheus 查询失败: {result.get('error')}")
        
        return result["data"]
    
    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "1m",
    ) -> Dict[str, Any]:
        """
        执行范围查询（range query）
        
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
        
        response = self._httpx_client.get("/api/v1/query_range", params=params)
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") != "success":
            raise Exception(f"Prometheus 范围查询失败: {result.get('error')}")
        
        return result["data"]
    
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
        if not registry.has_tool(PrometheusQueryTool.name):
            registry.register_class(PrometheusQueryTool)
        if not registry.has_tool(ClusterMetricsTool.name):
            registry.register_class(ClusterMetricsTool)
        logger.info("已注册 Prometheus 查询工具")
    else:
        logger.info("Prometheus 未配置，跳过 Prometheus 工具注册")
