"""
Kubernetes 客户端模块
封装 Kubernetes Python SDK，提供统一的集群访问接口
"""

import logging
from typing import Any, Dict, List, Optional

from config.settings import get_settings


# 获取日志记录器
logger = logging.getLogger(__name__)


class KubernetesClient:
    """
    Kubernetes 客户端封装
    提供对 Kubernetes 集群资源的访问
    """
    
    def __init__(self):
        """
        初始化 Kubernetes 客户端
        """
        self.settings = get_settings()
        self._core_api = None
        self._apps_api = None
        self._initialized = False
    
    def _ensure_initialized(self) -> None:
        """
        确保客户端已初始化
        延迟加载，避免在未配置 K8s 时导入失败
        """
        if self._initialized:
            return
        
        try:
            from kubernetes import client, config
            
            # 尝试加载配置
            kubeconfig_path = self.settings.kubernetes.kubeconfig_path
            
            if kubeconfig_path:
                # 使用指定的 kubeconfig 文件
                logger.info(f"使用指定的 kubeconfig: {kubeconfig_path}")
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                # 尝试默认方式加载
                try:
                    # 首先尝试 in-cluster 配置（在 Pod 内运行时）
                    config.load_incluster_config()
                    logger.info("使用 in-cluster 配置")
                except config.ConfigException:
                    # 然后尝试默认 kubeconfig 位置
                    logger.info("使用默认 kubeconfig 配置")
                    config.load_kube_config()
            
            # 创建 API 客户端
            self._core_api = client.CoreV1Api()
            self._apps_api = client.AppsV1Api()
            self._initialized = True
            
            logger.info("Kubernetes 客户端初始化成功")
            
        except Exception as e:
            logger.error(f"Kubernetes 客户端初始化失败: {e}")
            raise Exception(f"无法连接到 Kubernetes 集群: {e}")
    
    @property
    def core_api(self):
        """获取 CoreV1Api 实例"""
        self._ensure_initialized()
        return self._core_api
    
    @property
    def apps_api(self):
        """获取 AppsV1Api 实例"""
        self._ensure_initialized()
        return self._apps_api
    
    # ============================================================
    # Pod 相关操作
    # ============================================================
    
    def list_pods(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出 Pod
        
        Args:
            namespace: 命名空间（None 表示所有命名空间）
            label_selector: 标签选择器
            
        Returns:
            List[Dict[str, Any]]: Pod 列表
        """
        from kubernetes.client.rest import ApiException
        
        try:
            if namespace:
                pods = self.core_api.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=label_selector,
                )
            else:
                pods = self.core_api.list_pod_for_all_namespaces(
                    label_selector=label_selector,
                )
            
            return [self._pod_to_dict(pod) for pod in pods.items]
            
        except ApiException as e:
            logger.error(f"列出 Pod 失败: {e}")
            raise Exception(f"列出 Pod 失败: {e.reason}")
    
    def get_pod(
        self,
        name: str,
        namespace: str = "default",
    ) -> Dict[str, Any]:
        """
        获取单个 Pod 详情
        
        Args:
            name: Pod 名称
            namespace: 命名空间
            
        Returns:
            Dict[str, Any]: Pod 详情
        """
        from kubernetes.client.rest import ApiException
        
        try:
            pod = self.core_api.read_namespaced_pod(
                name=name,
                namespace=namespace,
            )
            return self._pod_to_dict(pod)
            
        except ApiException as e:
            logger.error(f"获取 Pod 失败: {e}")
            raise Exception(f"获取 Pod 失败: {e.reason}")
    
    def get_pod_logs(
        self,
        name: str,
        namespace: str = "default",
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
        since_seconds: Optional[int] = None,
        previous: bool = False,
    ) -> str:
        """
        获取 Pod 日志
        
        Args:
            name: Pod 名称
            namespace: 命名空间
            container: 容器名称（多容器 Pod 必需）
            tail_lines: 获取最后多少行
            since_seconds: 获取过去多少秒的日志
            previous: 是否获取上一个终止容器的日志
            
        Returns:
            str: 日志内容
        """
        from kubernetes.client.rest import ApiException
        
        try:
            kwargs: Dict[str, Any] = {}
            if container:
                kwargs["container"] = container
            if tail_lines:
                kwargs["tail_lines"] = tail_lines
            if since_seconds:
                kwargs["since_seconds"] = since_seconds
            if previous:
                kwargs["previous"] = previous
            
            logs = self.core_api.read_namespaced_pod_log(
                name=name,
                namespace=namespace,
                **kwargs,
            )
            return logs
            
        except ApiException as e:
            logger.error(f"获取 Pod 日志失败: {e}")
            raise Exception(f"获取 Pod 日志失败: {e.reason}")
    
    # ============================================================
    # Deployment 相关操作
    # ============================================================
    
    def list_deployments(
        self,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出 Deployment
        
        Args:
            namespace: 命名空间（None 表示所有命名空间）
            
        Returns:
            List[Dict[str, Any]]: Deployment 列表
        """
        from kubernetes.client.rest import ApiException
        
        try:
            if namespace:
                deployments = self.apps_api.list_namespaced_deployment(
                    namespace=namespace,
                )
            else:
                deployments = self.apps_api.list_deployment_for_all_namespaces()
            
            return [self._deployment_to_dict(dep) for dep in deployments.items]
            
        except ApiException as e:
            logger.error(f"列出 Deployment 失败: {e}")
            raise Exception(f"列出 Deployment 失败: {e.reason}")
    
    def get_deployment(
        self,
        name: str,
        namespace: str = "default",
    ) -> Dict[str, Any]:
        """
        获取单个 Deployment 详情
        
        Args:
            name: Deployment 名称
            namespace: 命名空间
            
        Returns:
            Dict[str, Any]: Deployment 详情
        """
        from kubernetes.client.rest import ApiException
        
        try:
            deployment = self.apps_api.read_namespaced_deployment(
                name=name,
                namespace=namespace,
            )
            return self._deployment_to_dict(deployment)
            
        except ApiException as e:
            logger.error(f"获取 Deployment 失败: {e}")
            raise Exception(f"获取 Deployment 失败: {e.reason}")
    
    # ============================================================
    # Service 相关操作
    # ============================================================
    
    def list_services(
        self,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出 Service
        
        Args:
            namespace: 命名空间（None 表示所有命名空间）
            
        Returns:
            List[Dict[str, Any]]: Service 列表
        """
        from kubernetes.client.rest import ApiException
        
        try:
            if namespace:
                services = self.core_api.list_namespaced_service(
                    namespace=namespace,
                )
            else:
                services = self.core_api.list_service_for_all_namespaces()
            
            return [self._service_to_dict(svc) for svc in services.items]
            
        except ApiException as e:
            logger.error(f"列出 Service 失败: {e}")
            raise Exception(f"列出 Service 失败: {e.reason}")
    
    def get_service(
        self,
        name: str,
        namespace: str = "default",
    ) -> Dict[str, Any]:
        """
        获取单个 Service 详情
        
        Args:
            name: Service 名称
            namespace: 命名空间
            
        Returns:
            Dict[str, Any]: Service 详情
        """
        from kubernetes.client.rest import ApiException
        
        try:
            service = self.core_api.read_namespaced_service(
                name=name,
                namespace=namespace,
            )
            return self._service_to_dict(service)
            
        except ApiException as e:
            logger.error(f"获取 Service 失败: {e}")
            raise Exception(f"获取 Service 失败: {e.reason}")
    
    # ============================================================
    # Node 相关操作
    # ============================================================
    
    def list_nodes(self) -> List[Dict[str, Any]]:
        """
        列出所有 Node
        
        Returns:
            List[Dict[str, Any]]: Node 列表
        """
        from kubernetes.client.rest import ApiException
        
        try:
            nodes = self.core_api.list_node()
            return [self._node_to_dict(node) for node in nodes.items]
            
        except ApiException as e:
            logger.error(f"列出 Node 失败: {e}")
            raise Exception(f"列出 Node 失败: {e.reason}")
    
    def get_node(
        self,
        name: str,
    ) -> Dict[str, Any]:
        """
        获取单个 Node 详情
        
        Args:
            name: Node 名称
            
        Returns:
            Dict[str, Any]: Node 详情
        """
        from kubernetes.client.rest import ApiException
        
        try:
            node = self.core_api.read_node(name=name)
            return self._node_to_dict(node)
            
        except ApiException as e:
            logger.error(f"获取 Node 失败: {e}")
            raise Exception(f"获取 Node 失败: {e.reason}")
    
    # ============================================================
    # Event 相关操作
    # ============================================================
    
    def list_events(
        self,
        namespace: Optional[str] = None,
        field_selector: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        列出 Event
        
        Args:
            namespace: 命名空间（None 表示所有命名空间）
            field_selector: 字段选择器（如 "type=Warning"）
            limit: 限制返回数量
            
        Returns:
            List[Dict[str, Any]]: Event 列表
        """
        from kubernetes.client.rest import ApiException
        
        try:
            if namespace:
                events = self.core_api.list_namespaced_event(
                    namespace=namespace,
                    field_selector=field_selector,
                    limit=limit,
                )
            else:
                events = self.core_api.list_event_for_all_namespaces(
                    field_selector=field_selector,
                    limit=limit,
                )
            
            return [self._event_to_dict(event) for event in events.items]
            
        except ApiException as e:
            logger.error(f"列出 Event 失败: {e}")
            raise Exception(f"列出 Event 失败: {e.reason}")
    
    # ============================================================
    # 辅助方法：将 K8s 对象转换为字典
    # ============================================================
    
    def _pod_to_dict(self, pod) -> Dict[str, Any]:
        """将 Pod 对象转换为字典"""
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "uid": pod.metadata.uid,
            "status": pod.status.phase,
            "qos_class": pod.status.qos_class,
            "node_name": pod.spec.node_name if pod.spec else None,
            "start_time": pod.status.start_time.isoformat() if pod.status.start_time else None,
            "labels": pod.metadata.labels or {},
            "annotations": pod.metadata.annotations or {},
            "containers": [
                {
                    "name": c.name,
                    "image": c.image,
                    "ready": cs.ready if cs else False,
                    "restart_count": cs.restart_count if cs else 0,
                    "state": self._get_container_state(cs.state if cs else None),
                }
                for c, cs in zip(
                    pod.spec.containers if pod.spec else [],
                    pod.status.container_statuses if pod.status.container_statuses else []
                )
            ],
            "conditions": [
                {
                    "type": cond.type,
                    "status": cond.status,
                    "reason": cond.reason,
                    "message": cond.message,
                }
                for cond in (pod.status.conditions or [])
            ],
        }
    
    def _deployment_to_dict(self, deployment) -> Dict[str, Any]:
        """将 Deployment 对象转换为字典"""
        return {
            "name": deployment.metadata.name,
            "namespace": deployment.metadata.namespace,
            "uid": deployment.metadata.uid,
            "replicas": deployment.spec.replicas,
            "ready_replicas": deployment.status.ready_replicas or 0,
            "updated_replicas": deployment.status.updated_replicas or 0,
            "available_replicas": deployment.status.available_replicas or 0,
            "unavailable_replicas": deployment.status.unavailable_replicas or 0,
            "labels": deployment.metadata.labels or {},
            "selector": deployment.spec.selector.match_labels if deployment.spec.selector else {},
            "strategy": deployment.spec.strategy.type,
        }
    
    def _service_to_dict(self, service) -> Dict[str, Any]:
        """将 Service 对象转换为字典"""
        return {
            "name": service.metadata.name,
            "namespace": service.metadata.namespace,
            "uid": service.metadata.uid,
            "type": service.spec.type,
            "cluster_ip": service.spec.cluster_ip,
            "external_ips": service.spec.external_ips or [],
            "ports": [
                {
                    "name": p.name,
                    "port": p.port,
                    "target_port": str(p.target_port),
                    "protocol": p.protocol,
                }
                for p in (service.spec.ports or [])
            ],
            "selector": service.spec.selector or {},
            "labels": service.metadata.labels or {},
        }
    
    def _node_to_dict(self, node) -> Dict[str, Any]:
        """将 Node 对象转换为字典"""
        # 获取节点资源容量和可分配资源
        capacity = node.status.capacity or {}
        allocatable = node.status.allocatable or {}
        
        return {
            "name": node.metadata.name,
            "uid": node.metadata.uid,
            "labels": node.metadata.labels or {},
            "annotations": node.metadata.annotations or {},
            "capacity": {
                "cpu": str(capacity.get("cpu", "")),
                "memory": str(capacity.get("memory", "")),
                "pods": str(capacity.get("pods", "")),
            },
            "allocatable": {
                "cpu": str(allocatable.get("cpu", "")),
                "memory": str(allocatable.get("memory", "")),
                "pods": str(allocatable.get("pods", "")),
            },
            "conditions": [
                {
                    "type": cond.type,
                    "status": cond.status,
                    "reason": cond.reason,
                    "message": cond.message,
                }
                for cond in (node.status.conditions or [])
            ],
            "node_info": {
                "os_image": node.status.node_info.os_image,
                "kubelet_version": node.status.node_info.kubelet_version,
                "container_runtime_version": node.status.node_info.container_runtime_version,
            } if node.status.node_info else {},
        }
    
    def _event_to_dict(self, event) -> Dict[str, Any]:
        """将 Event 对象转换为字典"""
        return {
            "name": event.metadata.name,
            "namespace": event.metadata.namespace,
            "type": event.type,
            "reason": event.reason,
            "message": event.message,
            "count": event.count,
            "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
            "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None,
            "involved_object": {
                "kind": event.involved_object.kind,
                "name": event.involved_object.name,
                "namespace": event.involved_object.namespace,
            } if event.involved_object else {},
            "source": {
                "component": event.source.component,
                "host": event.source.host,
            } if event.source else {},
        }
    
    def _get_container_state(self, state) -> str:
        """获取容器状态描述"""
        if state is None:
            return "unknown"
        if state.running:
            return "Running"
        if state.terminated:
            return f"Terminated (exit_code={state.terminated.exit_code}, reason={state.terminated.reason})"
        if state.waiting:
            return f"Waiting (reason={state.waiting.reason})"
        return "unknown"


# 创建全局 K8s 客户端单例
_k8s_client: Optional[KubernetesClient] = None


def get_k8s_client() -> KubernetesClient:
    """
    获取全局 Kubernetes 客户端单例
    
    Returns:
        KubernetesClient: K8s 客户端实例
    """
    global _k8s_client
    if _k8s_client is None:
        _k8s_client = KubernetesClient()
    return _k8s_client
