"""
Kubernetes 工具模块
提供 Agent 可调用的 K8s 相关工具函数
"""

import logging
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolParameter, ToolResult
from tools.k8s_client import get_k8s_client

logger = logging.getLogger(__name__)


class GetClusterStatusTool(BaseTool):
    """
    获取集群状态工具
    查询 Kubernetes 集群的整体状态，包括节点、Pod、Deployment 等
    """
    
    name = "get_cluster_status"
    description = "获取 Kubernetes 集群的整体状态，包括节点数量、运行中的 Pod 数量、Deployment 状态等。当用户询问集群状态、集群是否正常时使用此工具。"
    
    parameters = [
        ToolParameter(
            name="namespace",
            type="string",
            description="要查询的命名空间，留空表示查询所有命名空间",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        namespace = kwargs.get("namespace")
        
        try:
            k8s_client = get_k8s_client()
            
            # 收集集群状态
            nodes = k8s_client.list_nodes()
            pods = k8s_client.list_pods(namespace=namespace)
            deployments = k8s_client.list_deployments(namespace=namespace)
            services = k8s_client.list_services(namespace=namespace)
            events = k8s_client.list_events(namespace=namespace, field_selector="type=Warning", limit=20)
            
            # 统计信息
            running_pods = sum(1 for p in pods if p.get("status") == "Running")
            ready_nodes = sum(
                1 for n in nodes
                for cond in n.get("conditions", [])
                if cond.get("type") == "Ready" and cond.get("status") == "True"
            )
            ready_deployments = sum(
                1 for d in deployments
                if d.get("ready_replicas", 0) == d.get("replicas", 0)
            )
            warning_events = len(events)
            
            return ToolResult.success(
                data={
                    "summary": {
                        "nodes_total": len(nodes),
                        "nodes_ready": ready_nodes,
                        "pods_total": len(pods),
                        "pods_running": running_pods,
                        "deployments_total": len(deployments),
                        "deployments_ready": ready_deployments,
                        "services_total": len(services),
                        "warning_events": warning_events,
                    },
                    "nodes": nodes[:5],
                    "pods": pods[:10],
                    "deployments": deployments[:10],
                    "warning_events": events[:10],
                },
                message="集群状态查询成功",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"查询集群状态失败: {str(e)}",
                message="无法连接到 Kubernetes 集群",
            )


class ListPodsTool(BaseTool):
    """
    列出 Pod 工具
    查询 Kubernetes 中的 Pod 列表
    """
    
    name = "list_pods"
    description = "列出 Kubernetes 集群中的 Pod。可以按命名空间筛选，查看 Pod 的状态、重启次数等信息。"
    
    parameters = [
        ToolParameter(
            name="namespace",
            type="string",
            description="要查询的命名空间，留空表示查询所有命名空间",
            required=False,
        ),
        ToolParameter(
            name="label_selector",
            type="string",
            description="标签选择器，如 'app=nginx'，用于筛选特定标签的 Pod",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        namespace = kwargs.get("namespace")
        label_selector = kwargs.get("label_selector")
        
        try:
            k8s_client = get_k8s_client()
            pods = k8s_client.list_pods(namespace=namespace, label_selector=label_selector)
            
            return ToolResult.success(
                data={
                    "total": len(pods),
                    "pods": pods,
                },
                message=f"成功获取 {len(pods)} 个 Pod",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"列出 Pod 失败: {str(e)}",
            )


class GetPodDetailTool(BaseTool):
    """
    获取 Pod 详情工具
    查询单个 Pod 的详细信息
    """
    
    name = "get_pod_detail"
    description = "获取指定 Pod 的详细信息，包括容器状态、事件、条件等。用于排查 Pod 问题。"
    
    parameters = [
        ToolParameter(
            name="name",
            type="string",
            description="Pod 名称",
            required=True,
        ),
        ToolParameter(
            name="namespace",
            type="string",
            description="Pod 所在的命名空间，默认为 default",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        name = kwargs.get("name")
        namespace = kwargs.get("namespace", "default")
        
        try:
            k8s_client = get_k8s_client()
            pod = k8s_client.get_pod(name=name, namespace=namespace)
            
            return ToolResult.success(
                data=pod,
                message=f"成功获取 Pod {name} 的详情",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"获取 Pod 详情失败: {str(e)}",
            )


class GetPodLogsTool(BaseTool):
    """
    获取 Pod 日志工具
    查询 Pod 的日志内容
    """
    
    name = "get_pod_logs"
    description = "获取 Pod 的日志内容。用于排查应用错误、崩溃等问题。"
    
    parameters = [
        ToolParameter(
            name="name",
            type="string",
            description="Pod 名称",
            required=True,
        ),
        ToolParameter(
            name="namespace",
            type="string",
            description="Pod 所在的命名空间，默认为 default",
            required=False,
        ),
        ToolParameter(
            name="container",
            type="string",
            description="容器名称，多容器 Pod 必需",
            required=False,
        ),
        ToolParameter(
            name="tail_lines",
            type="integer",
            description="获取最后多少行日志，默认 100 行",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        name = kwargs.get("name")
        namespace = kwargs.get("namespace", "default")
        container = kwargs.get("container")
        tail_lines = kwargs.get("tail_lines", 100)
        
        try:
            k8s_client = get_k8s_client()
            logs = k8s_client.get_pod_logs(
                name=name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
            )
            
            return ToolResult.success(
                data={
                    "pod_name": name,
                    "namespace": namespace,
                    "container": container,
                    "logs": logs,
                },
                message=f"成功获取 Pod {name} 的日志",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"获取 Pod 日志失败: {str(e)}",
            )


class ListDeploymentsTool(BaseTool):
    """
    列出 Deployment 工具
    查询 Kubernetes 中的 Deployment 列表
    """
    
    name = "list_deployments"
    description = "列出 Kubernetes 集群中的 Deployment。查看副本数、就绪状态等信息。"
    
    parameters = [
        ToolParameter(
            name="namespace",
            type="string",
            description="要查询的命名空间，留空表示查询所有命名空间",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        namespace = kwargs.get("namespace")
        
        try:
            k8s_client = get_k8s_client()
            deployments = k8s_client.list_deployments(namespace=namespace)
            
            return ToolResult.success(
                data={
                    "total": len(deployments),
                    "deployments": deployments,
                },
                message=f"成功获取 {len(deployments)} 个 Deployment",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"列出 Deployment 失败: {str(e)}",
            )


class ListServicesTool(BaseTool):
    """
    列出 Service 工具
    查询 Kubernetes 中的 Service 列表
    """
    
    name = "list_services"
    description = "列出 Kubernetes 集群中的 Service。查看服务类型、端口、选择器等信息。"
    
    parameters = [
        ToolParameter(
            name="namespace",
            type="string",
            description="要查询的命名空间，留空表示查询所有命名空间",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        namespace = kwargs.get("namespace")
        
        try:
            k8s_client = get_k8s_client()
            services = k8s_client.list_services(namespace=namespace)
            
            return ToolResult.success(
                data={
                    "total": len(services),
                    "services": services,
                },
                message=f"成功获取 {len(services)} 个 Service",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"列出 Service 失败: {str(e)}",
            )


class ListNodesTool(BaseTool):
    """
    列出 Node 工具
    查询 Kubernetes 中的 Node 列表
    """
    
    name = "list_nodes"
    description = "列出 Kubernetes 集群中的所有节点。查看节点状态、资源容量等信息。"
    
    parameters = []
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        try:
            k8s_client = get_k8s_client()
            nodes = k8s_client.list_nodes()
            
            return ToolResult.success(
                data={
                    "total": len(nodes),
                    "nodes": nodes,
                },
                message=f"成功获取 {len(nodes)} 个节点",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"列出节点失败: {str(e)}",
            )


class ListEventsTool(BaseTool):
    """
    列出 Event 工具
    查询 Kubernetes 中的事件
    """
    
    name = "list_events"
    description = "列出 Kubernetes 集群中的事件。特别适用于排查警告和错误事件。"
    
    parameters = [
        ToolParameter(
            name="namespace",
            type="string",
            description="要查询的命名空间，留空表示查询所有命名空间",
            required=False,
        ),
        ToolParameter(
            name="only_warnings",
            type="boolean",
            description="是否只显示警告类型的事件，默认 true",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="限制返回的事件数量，默认 50",
            required=False,
        ),
    ]
    
    def _execute(self, **kwargs: Any) -> ToolResult:
        namespace = kwargs.get("namespace")
        only_warnings = kwargs.get("only_warnings", True)
        limit = kwargs.get("limit", 50)
        
        try:
            k8s_client = get_k8s_client()
            
            field_selector = "type=Warning" if only_warnings else None
            events = k8s_client.list_events(
                namespace=namespace,
                field_selector=field_selector,
                limit=limit,
            )
            
            return ToolResult.success(
                data={
                    "total": len(events),
                    "only_warnings": only_warnings,
                    "events": events,
                },
                message=f"成功获取 {len(events)} 个事件",
            )
            
        except Exception as e:
            return ToolResult.failure(
                error=f"列出事件失败: {str(e)}",
            )


def register_k8s_tools() -> None:
    """
    注册所有 K8s 工具（幂等操作：已注册的工具不会重复注册）
    """
    from tools.base import get_tool_registry
    
    registry = get_tool_registry()
    
    tools = [
        GetClusterStatusTool,
        ListPodsTool,
        GetPodDetailTool,
        GetPodLogsTool,
        ListDeploymentsTool,
        ListServicesTool,
        ListNodesTool,
        ListEventsTool,
    ]
    
    for tool_class in tools:
        # 幂等检查：如果工具已注册则跳过
        if not registry.has_tool(tool_class.name):
            registry.register_class(tool_class)
        else:
            logger.debug(f"K8s 工具 {tool_class.name} 已注册，跳过")
