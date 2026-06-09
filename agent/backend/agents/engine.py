"""
Agent 推理引擎模块
实现健康监测、异常检测、根因分析、故障恢复建议等核心智能能力
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.agent import Agent, AgentContext, AgentResponse
from tools.base import ToolResult, get_tool_registry
from tools.k8s_client import get_k8s_client


# 获取日志记录器
logger = logging.getLogger(__name__)


# ============================================================================
# Prompt 模板定义
# ============================================================================

SYSTEM_PROMPT = """你是一个专业的微服务集群运维专家，负责监控和维护 Kubernetes 集群中的微服务。

你的职责：
1. 监测集群健康状态
2. 检测异常情况（Pod 崩溃、资源不足、网络问题等）
3. 分析问题根因
4. 提供具体、可操作的恢复建议

你可以使用以下工具来收集信息：
- Kubernetes 工具：查看 Pod、Deployment、Service、Event 状态
- 日志工具：获取 Pod 日志和 ElasticSearch 日志
- Prometheus 工具：查询 CPU、内存、网络等指标

分析问题时请遵循以下原则：
1. 先查看整体状态，再聚焦具体异常
2. 关联日志、指标和事件进行综合分析
3. 分类根因（资源问题、配置错误、网络问题、代码问题等）
4. 提供具体、可执行的恢复步骤
5. 标注高风险操作

输出格式要求（使用 JSON）：
{
  "analysis": {
    "status": "normal|warning|critical",
    "summary": "简要描述问题",
    "anomalies": [
      {"type": "异常类型", "target": "影响对象", "severity": "high|medium|low", "description": "详细描述"}
    ]
  },
  "root_cause": {
    "category": "资源不足|配置错误|网络问题|代码问题|依赖问题|其他",
    "analysis": "详细的根因分析",
    "evidence": ["证据1", "证据2"]
  },
  "recovery": {
    "steps": [
      {"order": 1, "action": "具体操作", "risk": "low|medium|high", "description": "操作说明"}
    ],
    "precautions": ["注意事项1", "注意事项2"]
  }
}
"""


ANOMALY_DETECTION_PROMPT = """请分析以下集群状态数据，识别所有异常情况。

Kubernetes 状态：
{k8s_status}

Prometheus 指标：
{metrics}

最近事件：
{events}

请输出异常检测结果（JSON 格式）：
"""


ROOT_CAUSE_ANALYSIS_PROMPT = """以下是检测到的异常情况，请进行根因分析。

异常信息：
{anomalies}

相关日志：
{logs}

相关指标趋势：
{metric_trends}

请输出根因分析结果（JSON 格式）：
"""


RECOVERY_SUGGESTION_PROMPT = """根据以下根因分析，生成具体的故障恢复建议。

根因分析：
{root_cause}

集群当前状态：
{current_status}

请输出恢复建议（JSON 格式），要求：
1. 步骤具体、可执行
2. 标注操作风险等级
3. 包含验证步骤
"""


# ============================================================================
# 数据模型定义
# ============================================================================

ANOMALY_NAMESPACE = uuid.UUID('8e9c3f31-6d13-4d4d-8f1c-5b0a6e3f7d9a')


def generate_anomaly_id(anomaly_type: str, target: str) -> str:
    """
    基于异常类型和目标生成稳定的异常 ID
    
    使用 uuid5 确保相同的 (type, target) 组合始终生成相同的 ID
    这样前后端查询分析结果时 ID 能匹配
    
    Args:
        anomaly_type: 异常类型
        target: 目标资源
        
    Returns:
        str: 稳定的 UUID 字符串
    """
    key = f"{anomaly_type}:{target}"
    return str(uuid.uuid5(ANOMALY_NAMESPACE, key))


class Anomaly:
    """异常信息"""
    
    def __init__(
        self,
        anomaly_type: str,
        target: str,
        severity: str,
        description: str,
        evidence: Optional[List[str]] = None,
        anomaly_id: Optional[str] = None,
    ):
        self.id = anomaly_id or generate_anomaly_id(anomaly_type, target)
        self.anomaly_type = anomaly_type
        self.target = target
        self.severity = severity
        self.description = description
        self.evidence = evidence or []
        self.timestamp = datetime.now().isoformat()
        self.analysis_status = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.anomaly_type,
            "target": self.target,
            "severity": self.severity,
            "description": self.description,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "analysis_status": self.analysis_status,
        }


class RootCause:
    """根因分析结果"""
    
    def __init__(
        self,
        category: str,
        analysis: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.8,
    ):
        self.category = category
        self.analysis = analysis
        self.evidence = evidence or []
        self.confidence = confidence
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "analysis": self.analysis,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


class RecoveryStep:
    """恢复步骤"""
    
    def __init__(
        self,
        order: int,
        action: str,
        risk: str,
        description: str,
        validation: Optional[str] = None,
    ):
        self.order = order
        self.action = action
        self.risk = risk
        self.description = description
        self.validation = validation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "action": self.action,
            "risk": self.risk,
            "description": self.description,
            "validation": self.validation,
        }


class RecoveryPlan:
    """恢复计划"""
    
    def __init__(
        self,
        steps: List[RecoveryStep],
        precautions: Optional[List[str]] = None,
        estimated_time: Optional[str] = None,
    ):
        self.steps = steps
        self.precautions = precautions or []
        self.estimated_time = estimated_time
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "precautions": self.precautions,
            "estimated_time": self.estimated_time,
            "timestamp": self.timestamp,
        }


class AnalysisResult:
    """完整分析结果"""
    
    def __init__(
        self,
        status: str = "normal",
        summary: str = "",
        anomalies: Optional[List[Anomaly]] = None,
        root_cause: Optional[RootCause] = None,
        recovery_plan: Optional[RecoveryPlan] = None,
    ):
        self.status = status
        self.summary = summary
        self.anomalies = anomalies or []
        self.root_cause = root_cause
        self.recovery_plan = recovery_plan
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "root_cause": self.root_cause.to_dict() if self.root_cause else None,
            "recovery_plan": self.recovery_plan.to_dict() if self.recovery_plan else None,
            "timestamp": self.timestamp,
        }


# ============================================================================
# 规则引擎 - 基于规则的快速异常检测
# ============================================================================

class RuleBasedAnomalyDetector:
    """
    基于规则的异常检测器
    用于快速识别常见异常，无需 LLM 调用
    """
    
    # 异常严重程度定义
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict[str, Any]]:
        """加载检测规则"""
        return [
            {
                "name": "pod_not_running",
                "check": self._check_pod_not_running,
                "severity": self.SEVERITY_HIGH,
            },
            {
                "name": "pod_restarting",
                "check": self._check_pod_restarting,
                "severity": self.SEVERITY_HIGH,
            },
            {
                "name": "deployment_not_ready",
                "check": self._check_deployment_not_ready,
                "severity": self.SEVERITY_MEDIUM,
            },
            {
                "name": "node_not_ready",
                "check": self._check_node_not_ready,
                "severity": self.SEVERITY_CRITICAL,
            },
            {
                "name": "event_warnings",
                "check": self._check_event_warnings,
                "severity": self.SEVERITY_MEDIUM,
            },
        ]
    
    def detect(self, k8s_data: Dict[str, Any]) -> List[Anomaly]:
        """
        执行规则检测
        
        Args:
            k8s_data: Kubernetes 状态数据
            
        Returns:
            List[Anomaly]: 检测到的异常列表
        """
        anomalies = []
        
        for rule in self.rules:
            try:
                rule_anomalies = rule["check"](k8s_data)
                for anomaly in rule_anomalies:
                    anomaly.severity = rule["severity"]
                anomalies.extend(rule_anomalies)
            except Exception as e:
                logger.warning(f"规则 {rule['name']} 执行失败: {e}")
        
        return anomalies
    
    def _check_pod_not_running(self, data: Dict[str, Any]) -> List[Anomaly]:
        """检查未运行的 Pod"""
        anomalies = []
        pods = data.get("pods", [])
        
        for pod in pods:
            status = pod.get("status", "")
            if status in ["Pending", "Failed", "Unknown"]:
                anomalies.append(Anomaly(
                    anomaly_type="Pod状态异常",
                    target=pod.get("name", "unknown"),
                    severity=self.SEVERITY_HIGH,
                    description=f"Pod 状态为 {status}，不是 Running",
                    evidence=[f"Pod 状态: {status}"],
                ))
            elif status == "Running":
                # 检查容器状态
                container_statuses = pod.get("container_statuses", [])
                for cs in container_statuses:
                    if not cs.get("ready", True):
                        anomalies.append(Anomaly(
                            anomaly_type="容器未就绪",
                            target=f"{pod.get('name')}/{cs.get('name')}",
                            severity=self.SEVERITY_MEDIUM,
                            description=f"容器 {cs.get('name')} 未就绪",
                            evidence=[f"容器就绪状态: {cs.get('ready')}"],
                        ))
        
        return anomalies
    
    def _check_pod_restarting(self, data: Dict[str, Any]) -> List[Anomaly]:
        """检查频繁重启的 Pod"""
        anomalies = []
        pods = data.get("pods", [])
        RESTART_THRESHOLD = 5
        
        for pod in pods:
            container_statuses = pod.get("container_statuses", [])
            for cs in container_statuses:
                restart_count = cs.get("restart_count", 0)
                if restart_count >= RESTART_THRESHOLD:
                    anomalies.append(Anomaly(
                        anomaly_type="Pod频繁重启",
                        target=f"{pod.get('name')}/{cs.get('name')}",
                        severity=self.SEVERITY_HIGH,
                        description=f"容器 {cs.get('name')} 已重启 {restart_count} 次，超过阈值 {RESTART_THRESHOLD}",
                        evidence=[f"重启次数: {restart_count}"],
                    ))
        
        return anomalies
    
    def _check_deployment_not_ready(self, data: Dict[str, Any]) -> List[Anomaly]:
        """检查未就绪的 Deployment"""
        anomalies = []
        deployments = data.get("deployments", [])
        
        for dep in deployments:
            ready = dep.get("ready_replicas", 0)
            desired = dep.get("replicas", 0)
            
            if desired > 0 and ready < desired:
                anomalies.append(Anomaly(
                    anomaly_type="Deployment副本不足",
                    target=dep.get("name", "unknown"),
                    severity=self.SEVERITY_MEDIUM,
                    description=f"Deployment 就绪副本 {ready}/{desired}",
                    evidence=[f"就绪: {ready}, 期望: {desired}"],
                ))
        
        return anomalies
    
    def _check_node_not_ready(self, data: Dict[str, Any]) -> List[Anomaly]:
        """检查未就绪的 Node"""
        anomalies = []
        nodes = data.get("nodes", [])
        
        for node in nodes:
            conditions = node.get("conditions", [])
            for cond in conditions:
                if cond.get("type") == "Ready" and cond.get("status") != "True":
                    anomalies.append(Anomaly(
                        anomaly_type="节点未就绪",
                        target=node.get("name", "unknown"),
                        severity=self.SEVERITY_CRITICAL,
                        description=f"节点状态异常: {cond.get('reason', 'Unknown')}",
                        evidence=[f"Ready 状态: {cond.get('status')}, 原因: {cond.get('reason')}"],
                    ))
        
        return anomalies
    
    def _check_event_warnings(self, data: Dict[str, Any]) -> List[Anomaly]:
        """检查警告事件"""
        anomalies = []
        events = data.get("events", [])
        
        warning_events = [e for e in events if e.get("type") == "Warning"]
        if warning_events:
            # 按原因聚合
            reason_count: Dict[str, int] = {}
            for e in warning_events:
                reason = e.get("reason", "Unknown")
                reason_count[reason] = reason_count.get(reason, 0) + 1
            
            for reason, count in reason_count.items():
                if count >= 3:
                    anomalies.append(Anomaly(
                        anomaly_type="事件告警",
                        target="cluster",
                        severity=self.SEVERITY_MEDIUM,
                        description=f"检测到 {count} 次 {reason} 警告事件",
                        evidence=[f"{reason}: {count} 次"],
                    ))
        
        return anomalies


# ============================================================================
# 健康监测工作流
# ============================================================================

class HealthMonitor:
    """
    健康监测工作流
    聚合 K8s、Prometheus 数据，执行异常检测
    """
    
    def __init__(self):
        self.rule_detector = RuleBasedAnomalyDetector()
    
    def collect_k8s_status(
        self,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        收集 Kubernetes 状态数据
        
        Args:
            namespace: 命名空间，None 表示所有命名空间
            
        Returns:
            Dict[str, Any]: K8s 状态数据
        """
        try:
            k8s_client = get_k8s_client()
            
            # 收集 Pod 状态
            pods = k8s_client.list_pods(namespace=namespace)
            
            # 收集 Deployment 状态
            deployments = k8s_client.list_deployments(namespace=namespace)
            
            # 收集节点状态
            nodes = k8s_client.list_nodes()
            
            # 收集事件（最近 5 分钟）
            events = k8s_client.list_events(namespace=namespace)
            
            return {
                "pods": pods,
                "deployments": deployments,
                "nodes": nodes,
                "events": events,
                "collected_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"收集 K8s 状态失败: {e}")
            return {
                "pods": [],
                "deployments": [],
                "nodes": [],
                "events": [],
                "error": str(e),
                "collected_at": datetime.now().isoformat(),
            }
    
    def collect_metrics(
        self,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        收集 Prometheus 指标
        
        Args:
            namespace: 命名空间
            
        Returns:
            Dict[str, Any]: 指标数据
        """
        try:
            from tools.prometheus import get_prometheus_client
            
            client = get_prometheus_client()
            
            if not client.base_url:
                return {"error": "Prometheus 未配置"}
            
            # 检查连接
            if not client.is_available():
                return {"error": "Prometheus 不可用"}
            
            # 收集关键指标
            metrics = {}
            
            # CPU 使用情况
            try:
                cpu_query = (
                    f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}",container!="",container!="POD"}}[5m])) by (pod)'
                    if namespace
                    else 'sum(rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[5m])) by (pod)'
                )
                cpu_result = client.query(cpu_query)
                metrics["cpu_usage"] = self._parse_metric_result(cpu_result)
            except Exception as e:
                logger.warning(f"CPU 指标查询失败: {e}")
            
            # 内存使用情况
            try:
                mem_query = (
                    f'sum(container_memory_working_set_bytes{{namespace="{namespace}",container!="",container!="POD"}}) by (pod)'
                    if namespace
                    else 'sum(container_memory_working_set_bytes{container!="",container!="POD"}) by (pod)'
                )
                mem_result = client.query(mem_query)
                metrics["memory_usage"] = self._parse_metric_result(mem_result)
            except Exception as e:
                logger.warning(f"内存指标查询失败: {e}")
            
            return {
                **metrics,
                "collected_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"收集指标失败: {e}")
            return {"error": str(e)}
    
    def _parse_metric_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 Prometheus 查询结果"""
        parsed = []
        for series in result.get("result", []):
            metric = series.get("metric", {})
            value = series.get("value", [])
            if len(value) >= 2:
                parsed.append({
                    "labels": metric,
                    "value": float(value[1]),
                    "timestamp": datetime.fromtimestamp(value[0]).isoformat(),
                })
        return parsed
    
    def detect_anomalies(
        self,
        k8s_data: Dict[str, Any],
        metrics_data: Optional[Dict[str, Any]] = None,
    ) -> List[Anomaly]:
        """
        执行异常检测
        
        Args:
            k8s_data: K8s 状态数据
            metrics_data: 指标数据
            
        Returns:
            List[Anomaly]: 异常列表
        """
        anomalies = []
        
        # 规则检测（快速检测）
        rule_anomalies = self.rule_detector.detect(k8s_data)
        anomalies.extend(rule_anomalies)
        
        # TODO: 添加基于指标的异常检测
        
        return anomalies
    
    def run_health_check(
        self,
        namespace: Optional[str] = None,
        include_metrics: bool = True,
    ) -> Dict[str, Any]:
        """
        执行完整健康检查
        
        Args:
            namespace: 命名空间
            include_metrics: 是否包含指标
            
        Returns:
            Dict[str, Any]: 健康检查结果
        """
        # 收集数据
        k8s_data = self.collect_k8s_status(namespace=namespace)
        
        metrics_data = None
        if include_metrics:
            metrics_data = self.collect_metrics(namespace=namespace)
        
        # 检测异常
        anomalies = self.detect_anomalies(k8s_data, metrics_data)
        
        # 检查 K8s 连接是否失败
        if "error" in k8s_data:
            status = "error"
            anomalies.append(Anomaly(
                anomaly_type="集群连接失败",
                target="kubernetes",
                severity="critical",
                description=f"无法连接到 Kubernetes 集群: {k8s_data['error']}",
                evidence=[k8s_data['error']],
            ))
        else:
            # 确定整体状态
            status = "normal"
            critical_count = sum(1 for a in anomalies if a.severity == "critical")
            high_count = sum(1 for a in anomalies if a.severity == "high")
            
            if critical_count > 0:
                status = "critical"
            elif high_count > 0:
                status = "warning"
        
        # 生成摘要
        summary = self._generate_summary(k8s_data, anomalies)
        
        return {
            "status": status,
            "summary": summary,
            "k8s_data": k8s_data,
            "metrics_data": metrics_data,
            "anomalies": [a.to_dict() for a in anomalies],
            "anomaly_count": len(anomalies),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _generate_summary(
        self,
        k8s_data: Dict[str, Any],
        anomalies: List[Anomaly],
    ) -> str:
        """生成状态摘要"""
        # 检查是否有 K8s 连接错误
        if "error" in k8s_data:
            return f"无法连接到 Kubernetes 集群: {k8s_data['error']}"
        
        pods = k8s_data.get("pods", [])
        deployments = k8s_data.get("deployments", [])
        nodes = k8s_data.get("nodes", [])
        
        running_pods = sum(1 for p in pods if p.get("status") == "Running")
        
        if anomalies:
            critical = sum(1 for a in anomalies if a.severity == "critical")
            high = sum(1 for a in anomalies if a.severity == "high")
            return (
                f"检测到 {len(anomalies)} 个异常（critical: {critical}, high: {high}）。"
                f"Pod: {running_pods}/{len(pods)} 运行中, "
                f"Deployment: {len(deployments)} 个, "
                f"Node: {len(nodes)} 个"
            )
        else:
            return (
                f"集群状态正常。Pod: {running_pods}/{len(pods)} 运行中, "
                f"Deployment: {len(deployments)} 个, "
                f"Node: {len(nodes)} 个"
            )


# ============================================================================
# LLM 驱动的深度分析
# ============================================================================

class LLMAnalyst:
    """
    LLM 驱动的深度分析器
    用于根因分析和恢复建议生成
    """
    
    def __init__(self, agent: Optional[Agent] = None):
        self.agent = agent or Agent()
    
    def analyze_root_cause(
        self,
        anomalies: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[RootCause]:
        """
        使用 LLM 进行根因分析
        
        Args:
            anomalies: 异常列表
            context: 额外上下文（日志、指标等）
            
        Returns:
            Optional[RootCause]: 根因分析结果
        """
        if not anomalies:
            return None
        
        # 构建 Prompt
        anomaly_text = json.dumps(anomalies, ensure_ascii=False, indent=2)
        context_text = json.dumps(context or {}, ensure_ascii=False, indent=2)
        
        user_message = f"""请进行根因分析。

检测到的异常：
{anomaly_text}

上下文信息：
{context_text}

请按以下 JSON 格式输出根因分析结果：
{{
  "category": "问题分类（必须是以下之一：Pod异常、Node异常、Deployment异常、事件告警、资源不足、网络问题、存储问题、配置错误、其他）",
  "analysis": "详细的根因分析描述",
  "evidence": ["证据1", "证据2", "证据3"],
  "confidence": 0.85
}}

注意事项：
1. category 字段必须填写，且只能从上面的列表中选择一个最匹配的分类
2. 如果无法确定分类，请选择"其他"
3. confidence 是 0-1 之间的浮数字，表示分析的置信度"""
        
        # 调用 LLM
        try:
            response = self.agent.chat(user_message)
            
            # 解析响应
            parsed = self._parse_json_response(response.content)
            if parsed:
                # 规范化 category 字段
                category = parsed.get("category", "").strip()
                if not category:
                    # 如果 category 为空，根据异常类型推断
                    category = self._infer_category_from_anomalies(anomalies)
                
                return RootCause(
                    category=category,
                    analysis=parsed.get("analysis", ""),
                    evidence=parsed.get("evidence", []),
                    confidence=parsed.get("confidence", 0.7),
                )
        except Exception as e:
            logger.error(f"根因分析失败: {e}")
        
        # LLM 分析失败时，根据异常类型生成默认根因分析
        logger.warning("LLM 根因分析失败，使用默认根因分析")
        return self._get_default_root_cause(anomalies)
    
    def _infer_category_from_anomalies(self, anomalies: List[Dict[str, Any]]) -> str:
        """
        根据异常类型推断根因分类
        
        Args:
            anomalies: 异常列表
            
        Returns:
            str: 根因分类
        """
        if not anomalies:
            return "其他"
        
        # 获取第一个异常的类型
        first_anomaly = anomalies[0]
        anomaly_type = first_anomaly.get("type", first_anomaly.get("anomaly_type", "")).lower()
        anomaly_description = first_anomaly.get("description", first_anomaly.get("summary", "")).lower()
        
        # 根据异常类型推断分类
        if "pod" in anomaly_type or "pod" in anomaly_description:
            return "Pod异常"
        elif "node" in anomaly_type or "node" in anomaly_description or "节点" in anomaly_type:
            return "Node异常"
        elif "deployment" in anomaly_type or "deployment" in anomaly_description:
            return "Deployment异常"
        elif "event" in anomaly_type or "event" in anomaly_description or "事件" in anomaly_type:
            return "事件告警"
        elif "resource" in anomaly_type or "memory" in anomaly_type or "cpu" in anomaly_type or "内存" in anomaly_type:
            return "资源不足"
        elif "network" in anomaly_type or "网络" in anomaly_type:
            return "网络问题"
        elif "storage" in anomaly_type or "存储" in anomaly_type:
            return "存储问题"
        elif "config" in anomaly_type or "配置" in anomaly_type:
            return "配置错误"
        else:
            return "其他"
    
    def _get_default_root_cause(self, anomalies: List[Dict[str, Any]]) -> RootCause:
        """
        根据异常类型生成默认根因分析
        
        Args:
            anomalies: 异常列表
            
        Returns:
            RootCause: 默认根因分析
        """
        if not anomalies:
            return RootCause(
                category="其他",
                analysis="未检测到具体异常信息，建议进一步检查集群状态。",
                evidence=[],
                confidence=0.5,
            )
        
        # 推断分类
        category = self._infer_category_from_anomalies(anomalies)
        
        # 生成默认分析描述
        anomaly_count = len(anomalies)
        first_anomaly = anomalies[0]
        anomaly_type = first_anomaly.get("type", first_anomaly.get("anomaly_type", "未知类型"))
        anomaly_target = first_anomaly.get("target", "未知目标")
        
        analysis_texts = {
            "Pod异常": f"检测到 {anomaly_count} 个 Pod 相关异常，主要类型为 '{anomaly_type}'。问题可能与 Pod 配置、资源限制或依赖服务有关。建议检查 Pod 状态、日志和事件，确认 Pod 能否正常启动和运行。",
            "Node异常": f"检测到 {anomaly_count} 个 Node 相关异常，主要类型为 '{anomaly_type}'。问题可能与节点资源不足、网络问题或 kubelet 服务有关。建议检查节点状态、资源使用情况和 kubelet 日志。",
            "Deployment异常": f"检测到 {anomaly_count} 个 Deployment 相关异常，主要类型为 '{anomaly_type}'。问题可能与部署配置、副本数或镜像有关。建议检查 Deployment 配置、ReplicaSet 状态和事件。",
            "事件告警": f"检测到 {anomaly_count} 个事件告警，主要类型为 '{anomaly_type}'。告警可能由集群中的各种问题触发。建议查看具体事件详情，了解告警的触发原因和影响范围。",
            "资源不足": f"检测到 {anomaly_count} 个资源不足相关异常，主要类型为 '{anomaly_type}'。问题可能与 CPU、内存或存储资源不足有关。建议检查节点资源使用情况，考虑扩容或优化资源分配。",
            "网络问题": f"检测到 {anomaly_count} 个网络相关异常，主要类型为 '{anomaly_type}'。问题可能与网络插件、DNS 或服务连接有关。建议检查网络插件状态、DNS 服务和相关网络策略。",
            "存储问题": f"检测到 {anomaly_count} 个存储相关异常，主要类型为 '{anomaly_type}'。问题可能与存储类、PV/PVC 或后端存储有关。建议检查 StorageClass、PV/PVC 状态和后端存储服务。",
            "配置错误": f"检测到 {anomaly_count} 个配置相关异常，主要类型为 '{anomaly_type}'。问题可能与配置错误、环境变量或参数设置有关。建议检查相关配置，确保配置值正确有效。",
            "其他": f"检测到 {anomaly_count} 个异常，主要类型为 '{anomaly_type}'，影响目标 '{anomaly_target}'。建议进一步检查相关资源的详细状态和日志，以确定具体问题原因。",
        }
        
        analysis = analysis_texts.get(category, analysis_texts["其他"])
        
        # 生成证据列表
        evidence = []
        for i, anomaly in enumerate(anomalies[:5]):  # 最多显示 5 个证据
            anomaly_type = anomaly.get("type", anomaly.get("anomaly_type", "未知类型"))
            target = anomaly.get("target", "未知目标")
            desc = anomaly.get("description", anomaly.get("summary", ""))
            evidence.append(f"[{anomaly_type}] {target}: {desc[:50]}{'...' if len(desc) > 50 else ''}")
        
        return RootCause(
            category=category,
            analysis=analysis,
            evidence=evidence,
            confidence=0.6,
        )
    
    def _get_default_recovery_plan(self, root_cause: RootCause) -> RecoveryPlan:
        """
        根据根因分析生成默认恢复计划
        
        Args:
            root_cause: 根因分析结果
            
        Returns:
            RecoveryPlan: 默认恢复计划
        """
        category = root_cause.category.lower()
        analysis_text = root_cause.analysis.lower()
        
        steps = []
        
        # 基于根因分类提供默认恢复步骤
        if "pod" in category or "容器" in root_cause.category:
            steps.extend([
                RecoveryStep(
                    order=1,
                    action="检查 Pod 状态",
                    risk="low",
                    description="使用 kubectl get pods 命令检查 Pod 的当前状态，确认 Pod 是否处于 Running、Pending、Failed 或其他状态。",
                    validation="kubectl get pods -n <namespace>"
                ),
                RecoveryStep(
                    order=2,
                    action="查看 Pod 事件和日志",
                    risk="low",
                    description="查看 Pod 的事件历史和容器日志，了解 Pod 启动失败或异常的具体原因。",
                    validation="kubectl describe pod <pod-name> -n <namespace>; kubectl logs <pod-name> -n <namespace>"
                ),
                RecoveryStep(
                    order=3,
                    action="重启 Pod（删除重建）",
                    risk="medium",
                    description="删除问题 Pod，让 Deployment 或 StatefulSet 自动创建新的 Pod 实例。这是解决大多数 Pod 问题的快速方法。",
                    validation="kubectl delete pod <pod-name> -n <namespace>"
                ),
                RecoveryStep(
                    order=4,
                    action="检查 Deployment 配置",
                    risk="low",
                    description="检查 Deployment 的副本数、镜像版本、资源限制等配置是否正确。",
                    validation="kubectl get deployment <deployment-name> -n <namespace> -o yaml"
                ),
            ])
        elif "node" in category or "节点" in root_cause.category:
            steps.extend([
                RecoveryStep(
                    order=1,
                    action="检查节点状态",
                    risk="low",
                    description="使用 kubectl get nodes 命令检查所有节点的状态，确认节点是否处于 Ready 状态。",
                    validation="kubectl get nodes"
                ),
                RecoveryStep(
                    order=2,
                    action="查看节点详情",
                    risk="low",
                    description="查看节点的详细信息，包括资源使用情况、污点（Taints）、事件等。",
                    validation="kubectl describe node <node-name>"
                ),
                RecoveryStep(
                    order=3,
                    action="检查节点资源",
                    risk="low",
                    description="检查节点的 CPU、内存、磁盘等资源使用情况，确认是否存在资源不足的问题。",
                    validation="kubectl top nodes"
                ),
                RecoveryStep(
                    order=4,
                    action="排查节点故障",
                    risk="medium",
                    description="检查节点上的 kubelet 服务状态、网络连接、存储挂载等基础设施问题。",
                    validation="systemctl status kubelet; journalctl -u kubelet"
                ),
            ])
        elif "deployment" in category or "部署" in root_cause.category:
            steps.extend([
                RecoveryStep(
                    order=1,
                    action="检查 Deployment 状态",
                    risk="low",
                    description="检查 Deployment 的副本数、可用副本数、就绪副本数等状态。",
                    validation="kubectl get deployment <name> -n <namespace>"
                ),
                RecoveryStep(
                    order=2,
                    action="检查 ReplicaSet",
                    risk="low",
                    description="查看 Deployment 创建的 ReplicaSet，确认是哪个版本的 ReplicaSet 存在问题。",
                    validation="kubectl get replicaset -n <namespace> | grep <deployment-name>"
                ),
                RecoveryStep(
                    order=3,
                    action="回滚 Deployment",
                    risk="medium",
                    description="如果是新版本部署导致的问题，可以回滚到上一个稳定版本。",
                    validation="kubectl rollout undo deployment/<deployment-name> -n <namespace>"
                ),
                RecoveryStep(
                    order=4,
                    action="检查镜像和配置",
                    risk="low",
                    description="检查 Deployment 使用的镜像地址、镜像拉取策略、环境变量等配置。",
                    validation="kubectl get deployment <name> -n <namespace> -o yaml"
                ),
            ])
        elif "event" in category or "事件" in root_cause.category:
            steps.extend([
                RecoveryStep(
                    order=1,
                    action="查看 Warning 事件",
                    risk="low",
                    description="查看集群中的 Warning 级别事件，了解具体的告警来源。",
                    validation="kubectl get events --field-selector type=Warning -A"
                ),
                RecoveryStep(
                    order=2,
                    action="分析事件详情",
                    risk="low",
                    description="针对特定的事件类型（如 ImagePullBackOff、CrashLoopBackOff 等），查看详细信息。",
                    validation="kubectl describe <resource-type> <resource-name> -n <namespace>"
                ),
                RecoveryStep(
                    order=3,
                    action="解决具体问题",
                    risk="medium",
                    description="根据事件的具体原因采取相应措施，如修复镜像拉取问题、调整资源配额等。",
                    validation="根据具体事件类型处理"
                ),
            ])
        else:
            # 通用恢复步骤
            steps.extend([
                RecoveryStep(
                    order=1,
                    action="收集更多信息",
                    risk="low",
                    description="查看相关资源的详细状态和日志，获取更多诊断信息。",
                    validation="kubectl describe <resource> <name> -n <namespace>"
                ),
                RecoveryStep(
                    order=2,
                    action="检查资源配置",
                    risk="low",
                    description="检查相关资源的配置是否正确，包括标签选择器、资源限制、环境变量等。",
                    validation="kubectl get <resource> <name> -n <namespace> -o yaml"
                ),
                RecoveryStep(
                    order=3,
                    action="重启相关资源",
                    risk="medium",
                    description="对于无状态服务，可以尝试删除 Pod 或触发滚动更新来重置状态。",
                    validation="kubectl delete pod <pod-name> -n <namespace>"
                ),
                RecoveryStep(
                    order=4,
                    action="监控恢复情况",
                    risk="low",
                    description="持续监控集群状态，确认问题是否已解决或是否需要进一步干预。",
                    validation="持续观察相关资源状态"
                ),
            ])
        
        # 添加通用的验证步骤
        precautions = [
            "在执行操作前，请确保已备份重要数据",
            "建议先在测试环境验证恢复步骤",
            "执行删除操作时请谨慎，确认目标资源正确",
            "注意操作的影响范围，避免影响其他服务"
        ]
        
        return RecoveryPlan(
            steps=steps,
            precautions=precautions,
            estimated_time="根据具体情况约 5-30 分钟"
        )
    
    def generate_recovery_plan(
        self,
        root_cause: RootCause,
        current_status: Dict[str, Any],
    ) -> Optional[RecoveryPlan]:
        """
        生成恢复建议
        
        Args:
            root_cause: 根因分析结果
            current_status: 当前状态
            
        Returns:
            Optional[RecoveryPlan]: 恢复计划
        """
        # 构建 Prompt
        root_cause_text = json.dumps(root_cause.to_dict(), ensure_ascii=False, indent=2)
        status_text = json.dumps(current_status, ensure_ascii=False, indent=2)
        
        user_message = f"""请生成故障恢复建议。

根因分析：
{root_cause_text}

当前状态：
{status_text}

请按以下 JSON 格式输出恢复计划：
{{
  "steps": [
    {{
      "order": 1,
      "action": "步骤标题",
      "risk": "low|medium|high",
      "description": "详细说明",
      "validation": "验证命令或方法"
    }}
  ],
  "precautions": ["注意事项1", "注意事项2"],
  "estimated_time": "预计恢复时间"
}}"""
        
        # 调用 LLM
        try:
            response = self.agent.chat(user_message)
            
            # 解析响应
            parsed = self._parse_json_response(response.content)
            if parsed:
                steps = []
                for step_data in parsed.get("steps", []):
                    steps.append(RecoveryStep(
                        order=step_data.get("order", len(steps) + 1),
                        action=step_data.get("action", ""),
                        risk=step_data.get("risk", "medium"),
                        description=step_data.get("description", ""),
                        validation=step_data.get("validation"),
                    ))
                
                if len(steps) > 0:
                    return RecoveryPlan(
                        steps=steps,
                        precautions=parsed.get("precautions", []),
                        estimated_time=parsed.get("estimated_time"),
                    )
        except Exception as e:
            logger.error(f"生成恢复计划失败: {e}")
        
        # LLM 无法生成有效恢复计划时，使用默认恢复计划
        logger.warning("LLM 无法生成有效恢复计划，使用默认恢复计划")
        return self._get_default_recovery_plan(root_cause)
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 响应中的 JSON
        
        Args:
            response: LLM 响应文本
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的 JSON
        """
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        import re
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"无法解析 JSON 响应: {response[:200]}")
        return None


# ============================================================================
# 主分析引擎
# ============================================================================

class AnalysisEngine:
    """
    主分析引擎
    整合健康监测、异常检测、根因分析、恢复建议
    """
    
    def __init__(self, use_llm: bool = True):
        self.health_monitor = HealthMonitor()
        self.use_llm = use_llm
        self.llm_analyst = LLMAnalyst() if use_llm else None
    
    def run_full_analysis(
        self,
        namespace: Optional[str] = None,
        deep_analysis: bool = False,
    ) -> AnalysisResult:
        """
        执行完整分析流程
        
        Args:
            namespace: 命名空间
            deep_analysis: 是否执行深度分析（需要 LLM）
            
        Returns:
            AnalysisResult: 分析结果
        """
        logger.info(f"开始完整分析: namespace={namespace}, deep_analysis={deep_analysis}")
        
        # 1. 健康检查
        health_result = self.health_monitor.run_health_check(namespace=namespace)
        
        # 2. 构建基础结果
        anomalies = [
            Anomaly(
                anomaly_type=a["type"],
                target=a["target"],
                severity=a["severity"],
                description=a["description"],
                evidence=a.get("evidence", []),
                anomaly_id=a.get("id"),
            )
            for a in health_result.get("anomalies", [])
        ]
        
        result = AnalysisResult(
            status=health_result["status"],
            summary=health_result["summary"],
            anomalies=anomalies,
        )
        
        # 3. 如果有异常且启用了深度分析，执行根因分析和恢复建议
        if anomalies and deep_analysis and self.use_llm:
            try:
                # 根因分析
                root_cause = self.llm_analyst.analyze_root_cause(
                    anomalies=[a.to_dict() for a in anomalies],
                    context={
                        "k8s_data": health_result.get("k8s_data"),
                        "metrics": health_result.get("metrics_data"),
                    },
                )
                result.root_cause = root_cause
                
                # 恢复建议
                if root_cause:
                    recovery_plan = self.llm_analyst.generate_recovery_plan(
                        root_cause=root_cause,
                        current_status=health_result,
                    )
                    result.recovery_plan = recovery_plan
                    
            except Exception as e:
                logger.error(f"深度分析失败: {e}")
        
        logger.info(f"分析完成: status={result.status}, anomalies={len(anomalies)}")
        return result
    
    def quick_check(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        快速检查（仅状态和异常列表）
        
        Args:
            namespace: 命名空间
            
        Returns:
            Dict[str, Any]: 快速检查结果
        """
        return self.health_monitor.run_health_check(namespace=namespace, include_metrics=False)


# ============================================================================
# 便捷函数
# ============================================================================

_engine: Optional[AnalysisEngine] = None


def get_analysis_engine(use_llm: bool = True) -> AnalysisEngine:
    """
    获取分析引擎单例
    
    Args:
        use_llm: 是否使用 LLM 进行深度分析
        
    Returns:
        AnalysisEngine: 分析引擎实例
    """
    global _engine
    if _engine is None:
        _engine = AnalysisEngine(use_llm=use_llm)
    return _engine


def quick_health_check(namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    便捷函数：快速健康检查
    
    Args:
        namespace: 命名空间
        
    Returns:
        Dict[str, Any]: 健康检查结果
    """
    engine = get_analysis_engine(use_llm=False)
    return engine.quick_check(namespace=namespace)


def full_analysis(namespace: Optional[str] = None) -> AnalysisResult:
    """
    便捷函数：完整分析
    
    Args:
        namespace: 命名空间
        
    Returns:
        AnalysisResult: 分析结果
    """
    engine = get_analysis_engine(use_llm=True)
    return engine.run_full_analysis(namespace=namespace, deep_analysis=True)
