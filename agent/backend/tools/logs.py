"""
日志查询工具模块
提供 Pod 日志查询功能，支持 kubectl logs 和 ElasticSearch 两种方式
"""

import logging
import re
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolParameter, ToolResult
from tools.k8s_client import get_k8s_client


# 获取日志记录器
logger = logging.getLogger(__name__)


class K8sLogsTool(BaseTool):
    """
    Kubernetes Pod 日志查询工具
    通过 Kubernetes API 获取 Pod 日志
    """
    
    name = "k8s_get_pod_logs"
    description = (
        "获取 Kubernetes Pod 的日志信息，用于排查容器问题。"
        "支持按命名空间、Pod 名称、容器名称筛选，"
        "支持时间范围、条数限制、关键词过滤等功能。"
    )
    
    parameters = [
        ToolParameter(
            name="pod_name",
            type="string",
            description="Pod 名称（必需）",
            required=True,
        ),
        ToolParameter(
            name="namespace",
            type="string",
            description="Pod 所在的命名空间，默认为 'default'",
            required=False,
        ),
        ToolParameter(
            name="container",
            type="string",
            description="容器名称，多容器 Pod 必需指定",
            required=False,
        ),
        ToolParameter(
            name="tail_lines",
            type="integer",
            description="获取最后多少行日志，如 100、500、1000。默认 100 行",
            required=False,
        ),
        ToolParameter(
            name="since_seconds",
            type="integer",
            description="获取过去多少秒的日志，如 300（5分钟）、3600（1小时）。与 tail_lines 互斥，优先使用 tail_lines",
            required=False,
        ),
        ToolParameter(
            name="previous",
            type="boolean",
            description="是否获取上一个已终止容器的日志（用于排查 Pod 重启问题）。默认为 false",
            required=False,
        ),
        ToolParameter(
            name="keyword_filter",
            type="string",
            description="关键词过滤，只返回包含指定关键词的日志行。支持简单的字符串匹配",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行日志查询
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            pod_name = kwargs.get("pod_name")
            namespace = kwargs.get("namespace", "default")
            container = kwargs.get("container")
            tail_lines = kwargs.get("tail_lines", 100)
            since_seconds = kwargs.get("since_seconds")
            previous = kwargs.get("previous", False)
            keyword_filter = kwargs.get("keyword_filter")
            
            logger.info(
                f"查询 Pod 日志: pod={pod_name}, namespace={namespace}, "
                f"container={container}, tail_lines={tail_lines}, "
                f"since_seconds={since_seconds}, previous={previous}"
            )
            
            # 获取 K8s 客户端
            k8s_client = get_k8s_client()
            
            # 准备参数
            log_kwargs: Dict[str, Any] = {}
            if container:
                log_kwargs["container"] = container
            if tail_lines:
                log_kwargs["tail_lines"] = int(tail_lines)
            elif since_seconds:
                log_kwargs["since_seconds"] = int(since_seconds)
            else:
                log_kwargs["tail_lines"] = 100  # 默认 100 行
            
            if previous:
                log_kwargs["previous"] = True
            
            # 获取日志
            logs = k8s_client.get_pod_logs(
                name=pod_name,
                namespace=namespace,
                **log_kwargs,
            )
            
            # 关键词过滤
            if keyword_filter and logs:
                filtered_lines = []
                for line in logs.split("\n"):
                    if keyword_filter.lower() in line.lower():
                        filtered_lines.append(line)
                logs = "\n".join(filtered_lines)
            
            # 限制返回日志大小（防止过大）
            max_chars = 50000
            if len(logs) > max_chars:
                logs = logs[-max_chars:] + "\n...[日志已截断]"
                logger.warning(f"日志过长，已截断至 {max_chars} 字符")
            
            # 构建结果
            result_data = {
                "pod_name": pod_name,
                "namespace": namespace,
                "container": container,
                "tail_lines": tail_lines if tail_lines else None,
                "since_seconds": since_seconds if since_seconds else None,
                "previous": previous,
                "keyword_filter": keyword_filter,
                "log_content": logs,
                "total_lines": logs.count("\n") + 1 if logs else 0,
            }
            
            return ToolResult.success(
                data=result_data,
                message=f"成功获取 Pod {pod_name} 的日志，共 {result_data['total_lines']} 行",
            )
            
        except Exception as e:
            logger.error(f"获取 Pod 日志失败: {e}")
            return ToolResult.failure(
                error=f"获取 Pod 日志失败: {str(e)}",
                message="请检查 Pod 名称和命名空间是否正确，以及 Pod 是否正在运行",
            )


class ElasticSearchLogsTool(BaseTool):
    """
    ElasticSearch 日志查询工具
    通过 ElasticSearch 查询集群日志
    """
    
    name = "es_query_logs"
    description = (
        "通过 ElasticSearch 查询集群日志。"
        "支持按时间范围、命名空间、Pod、容器和关键词进行筛选。"
        "需要先配置 ElasticSearch 连接。"
    )
    
    parameters = [
        ToolParameter(
            name="namespace",
            type="string",
            description="按命名空间筛选日志",
            required=False,
        ),
        ToolParameter(
            name="pod_name",
            type="string",
            description="按 Pod 名称筛选日志，支持模糊匹配",
            required=False,
        ),
        ToolParameter(
            name="container",
            type="string",
            description="按容器名称筛选日志",
            required=False,
        ),
        ToolParameter(
            name="keyword",
            type="string",
            description="日志内容关键词，支持简单的全文搜索",
            required=False,
        ),
        ToolParameter(
            name="start_time",
            type="string",
            description="开始时间，格式为 ISO8601，如 '2024-01-01T00:00:00Z'。默认查询最近 15 分钟",
            required=False,
        ),
        ToolParameter(
            name="end_time",
            type="string",
            description="结束时间，格式为 ISO8601。默认为当前时间",
            required=False,
        ),
        ToolParameter(
            name="last_minutes",
            type="integer",
            description="查询最近 N 分钟的日志，如 15、60、1440。与 start_time/end_time 互斥",
            required=False,
        ),
        ToolParameter(
            name="size",
            type="integer",
            description="返回的日志条数，最大 1000。默认 100",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        """
        执行 ElasticSearch 日志查询
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            from elasticsearch import Elasticsearch
            from config.settings import get_settings
            
            settings = get_settings()
            
            # 检查 ES 配置
            if not settings.elasticsearch.es_url:
                return ToolResult.failure(
                    error="ElasticSearch 未配置",
                    message="请在 .env 文件中配置 ES_URL 以启用 ElasticSearch 日志查询",
                )
            
            # 获取参数
            namespace = kwargs.get("namespace")
            pod_name = kwargs.get("pod_name")
            container = kwargs.get("container")
            keyword = kwargs.get("keyword")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            last_minutes = kwargs.get("last_minutes", 15)
            size = min(int(kwargs.get("size", 100)), 1000)
            
            logger.info(
                f"ES 日志查询: namespace={namespace}, pod={pod_name}, "
                f"container={container}, keyword={keyword}, last_minutes={last_minutes}"
            )
            
            # 创建 ES 客户端
            es_client = Elasticsearch(settings.elasticsearch.es_url)
            
            # 检查连接
            if not es_client.ping():
                return ToolResult.failure(
                    error=f"无法连接到 ElasticSearch: {settings.elasticsearch.es_url}",
                    message="请检查 ElasticSearch 服务是否运行以及网络连接",
                )
            
            # 构建查询
            query = self._build_query(
                namespace=namespace,
                pod_name=pod_name,
                container=container,
                keyword=keyword,
                start_time=start_time,
                end_time=end_time,
                last_minutes=last_minutes,
            )
            
            # 执行查询
            index = settings.elasticsearch.es_index or "*"
            response = es_client.search(
                index=index,
                query=query,
                size=size,
                sort=[{"@timestamp": {"order": "desc"}}],
            )
            
            # 解析结果
            logs = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                logs.append({
                    "timestamp": source.get("@timestamp"),
                    "namespace": source.get("kubernetes", {}).get("namespace_name"),
                    "pod": source.get("kubernetes", {}).get("pod_name"),
                    "container": source.get("kubernetes", {}).get("container_name"),
                    "message": source.get("message") or source.get("log"),
                })
            
            result_data = {
                "total": response["hits"]["total"]["value"],
                "returned": len(logs),
                "query_params": {
                    "namespace": namespace,
                    "pod_name": pod_name,
                    "container": container,
                    "keyword": keyword,
                    "last_minutes": last_minutes,
                },
                "logs": logs,
            }
            
            return ToolResult.success(
                data=result_data,
                message=f"成功查询到 {result_data['total']} 条日志，返回 {len(logs)} 条",
            )
            
        except ImportError:
            return ToolResult.failure(
                error="elasticsearch 库未安装",
                message="请运行: pip install elasticsearch",
            )
        except Exception as e:
            logger.error(f"ES 日志查询失败: {e}")
            return ToolResult.failure(
                error=f"ElasticSearch 查询失败: {str(e)}",
                message="请检查 ES 配置和连接",
            )
    
    def _build_query(
        self,
        namespace: Optional[str],
        pod_name: Optional[str],
        container: Optional[str],
        keyword: Optional[str],
        start_time: Optional[str],
        end_time: Optional[str],
        last_minutes: int,
    ) -> Dict[str, Any]:
        """
        构建 ElasticSearch 查询 DSL
        
        Args:
            namespace: 命名空间
            pod_name: Pod 名称
            container: 容器名称
            keyword: 关键词
            start_time: 开始时间
            end_time: 结束时间
            last_minutes: 最近多少分钟
            
        Returns:
            Dict[str, Any]: ES 查询 DSL
        """
        must_conditions: List[Dict[str, Any]] = []
        filter_conditions: List[Dict[str, Any]] = []
        
        # 时间范围
        if start_time or end_time:
            time_range: Dict[str, Any] = {}
            if start_time:
                time_range["gte"] = start_time
            if end_time:
                time_range["lte"] = end_time
            filter_conditions.append({"range": {"@timestamp": time_range}})
        else:
            # 默认查询最近 N 分钟
            filter_conditions.append({
                "range": {
                    "@timestamp": {"gte": f"now-{last_minutes}m"}
                }
            })
        
        # 命名空间筛选
        if namespace:
            must_conditions.append({
                "match": {"kubernetes.namespace_name": namespace}
            })
        
        # Pod 名称筛选
        if pod_name:
            must_conditions.append({
                "wildcard": {"kubernetes.pod_name": f"*{pod_name}*"}
            })
        
        # 容器名称筛选
        if container:
            must_conditions.append({
                "match": {"kubernetes.container_name": container}
            })
        
        # 关键词搜索
        if keyword:
            must_conditions.append({
                "query_string": {
                    "query": keyword,
                    "fields": ["message", "log"]
                }
            })
        
        # 组合查询
        bool_query: Dict[str, Any] = {}
        if must_conditions:
            bool_query["must"] = must_conditions
        if filter_conditions:
            bool_query["filter"] = filter_conditions
        
        return {"bool": bool_query} if bool_query else {"match_all": {}}


def register_logs_tools() -> None:
    """
    注册所有日志工具（幂等操作：已注册的工具不会重复注册）
    """
    from tools.base import get_tool_registry
    
    registry = get_tool_registry()
    
    if not registry.has_tool(K8sLogsTool.name):
        registry.register_class(K8sLogsTool)
    
    # 检查是否配置了 ES，如果是则注册 ES 工具
    from config.settings import get_settings
    settings = get_settings()
    if settings.elasticsearch.es_url:
        if not registry.has_tool(ElasticSearchLogsTool.name):
            registry.register_class(ElasticSearchLogsTool)
            logger.info("已注册 ElasticSearch 日志查询工具")
    else:
        logger.info("ElasticSearch 未配置，跳过 ES 日志工具注册")
