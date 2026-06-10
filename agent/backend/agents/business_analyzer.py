"""
业务分析引擎模块
实现基于 LLM 的业务指标分析，支持 LLM 不可用时的自动降级
当 LLM 可用时，集群性能指标数据由数据采集层生成，其他部分由 LLM 生成
"""

import logging
import json
import math
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents.agent import Agent, AgentContext
from agents.llm_client import get_llm_client


# 获取日志记录器
logger = logging.getLogger(__name__)


# ============================================================================
# 分析状态定义
# ============================================================================

class AnalysisStatus:
    """分析状态常量"""
    ANALYZING = "analyzing"      # 进行中
    COMPLETED = "completed"       # LLM 分析完成
    FAILED = "failed"             # 失败
    BASIC = "basic"               # 规则分析完成（降级时）


# ============================================================================
# 阈值配置
# ============================================================================

THRESHOLDS = {
    "cpu": 80.0,      # CPU 阈值百分比
    "memory": 85.0,   # 内存阈值百分比
}


# ============================================================================
# LLM 业务分析系统提示
# ============================================================================

BUSINESS_ANALYSIS_SYSTEM_PROMPT = """你是一位专业的 Kubernetes 集群性能分析专家，负责分析集群的性能指标数据并生成完整的业务性能分析报告。

## 你的职责

1. **分析集群性能数据**：基于提供的指标数据进行深度分析
2. **识别性能瓶颈**：找出 CPU、内存、网络等方面的性能问题
3. **分析业务趋势**：分析资源使用趋势和业务繁忙时段
4. **提供优化建议**：给出具体、可操作的优化建议
5. **生成分析摘要**：总结整体健康状态

## 可使用的工具

你可以调用以下工具来获取更多数据：
- Prometheus 查询工具：查询 CPU、内存、网络等实时指标
- Kubernetes 查询工具：查看 Pod、Deployment、Node 状态
- 日志工具：获取容器日志

## 工作原则

1. 如果初始数据不足以进行完整分析，主动调用工具补充数据
2. 不要编造数据，所有分析都必须基于实际数据
3. 分析要深入，给出具体原因而非表面描述
4. 建议要可操作，包含具体步骤
5. 严格按照要求的 JSON 格式输出

## 输入数据说明

你将收到以下预采集数据：
- cluster_health_summary: 集群性能指标摘要（已由数据采集层生成，你只需要使用，不需要修改）
- metrics_details: 详细的指标数据
- analysis_context: 分析上下文（时间段、命名空间等）

## 输出格式要求

你必须输出严格的 JSON 格式，不包含任何其他解释性文字。格式如下：

```json
{
  "bottlenecks": [
    {
      "id": "唯一ID",
      "type": "cpu|memory|network|disk|other",
      "target": "受影响的资源名称",
      "severity": "high|medium|low",
      "current_value": 数值,
      "threshold": 阈值,
      "root_cause": "根因分析",
      "impact": "影响范围描述",
      "description": "详细描述"
    }
  ],
  "trends": [
    {
      "id": "唯一ID",
      "type": "cpu|memory|network|overall",
      "target": "分析目标",
      "metric_name": "指标名称",
      "direction": "上升|下降|稳定",
      "change_percent": 变化率百分比,
      "analysis": "趋势分析描述",
      "prediction": "未来预测"
    }
  ],
  "suggestions": [
    {
      "id": "唯一ID",
      "category": "优化类别",
      "priority": "high|medium|low",
      "target": "目标资源",
      "action": "操作建议",
      "details": ["步骤1", "步骤2"],
      "expected_benefit": "预期收益",
      "risk_level": "low|medium|high"
    }
  ],
  "summary": "整体分析摘要，描述集群健康状态、主要问题和建议"
}
```

## 字段详细说明

### bottlenecks（性能瓶颈）
- id: 使用 UUID 格式
- type: 必须是 cpu/memory/network/disk/other 之一
- severity: high(>阈值30%以上), medium(>阈值10-30%), low(接近阈值)
- current_value: 当前指标值（百分比）
- threshold: 告警阈值（百分比）
- root_cause: 深入分析的根本原因
- impact: 对业务的影响

### trends（业务趋势）
- direction: 上升/下降/稳定
- change_percent: 相对变化率（可为负数表示下降）
- analysis: 包含具体数据支撑的分析
- prediction: 基于趋势的预测

### suggestions（优化建议）
- category: cpu_optimization/memory_optimization/network_optimization/scaling/configuration/other
- priority: high/medium/low
- risk_level: 操作风险等级
- expected_benefit: 实施后的预期收益描述

### summary（摘要）
- 整体健康状态评估
- 主要问题总结
- 关键建议概览

## 重要要求

1. **必须输出纯 JSON**，不要添加任何 Markdown 格式或解释文字
2. **集群性能指标数据（cluster_health_summary）不要修改**，只需要使用
3. **bottlenecks、trends、suggestions、summary 必须由你生成**
4. 如果数据有限，使用合理推断但要标注"基于有限数据"
5. 如果需要更多信息，请调用工具获取
6. 确保 JSON 格式完全正确，可以被 json.loads 解析
"""


# ============================================================================
# JSON 输出 Schema 定义（用于验证）
# ============================================================================

REQUIRED_FIELDS = {
    "root": ["bottlenecks", "trends", "suggestions", "summary"],
    "bottleneck": ["id", "type", "target", "severity", "current_value", "threshold", "root_cause", "impact", "description"],
    "trend": ["id", "type", "target", "metric_name", "direction", "change_percent", "analysis", "prediction"],
    "suggestion": ["id", "category", "priority", "target", "action", "details", "expected_benefit", "risk_level"],
}

VALID_VALUES = {
    "bottleneck_type": ["cpu", "memory", "network", "disk", "other"],
    "bottleneck_severity": ["high", "medium", "low"],
    "trend_type": ["cpu", "memory", "network", "overall"],
    "trend_direction": ["上升", "下降", "稳定"],
    "suggestion_category": ["cpu_optimization", "memory_optimization", "network_optimization", "scaling", "configuration", "other"],
    "suggestion_priority": ["high", "medium", "low"],
    "suggestion_risk_level": ["low", "medium", "high"],
}


# ============================================================================
# BusinessAnalyzer 类定义
# ============================================================================

class BusinessAnalyzer:
    """
    业务分析引擎
    当 LLM 可用时，集群性能指标由数据采集层生成，其他部分由 LLM 生成
    当 LLM 不可用时，自动降级到规则分析
    """
    
    def __init__(self, use_llm: bool = True):
        """
        初始化业务分析器
        
        Args:
            use_llm: 是否启用 LLM 深度分析，默认为 True
        """
        self.use_llm = use_llm
        self.agent = Agent(
            system_prompt=BUSINESS_ANALYSIS_SYSTEM_PROMPT,
            max_tool_calls=5,  # 最多 5 次工具调用
        ) if use_llm else None
        
        # 阈值配置
        self.cpu_threshold = THRESHOLDS["cpu"]
        self.memory_threshold = THRESHOLDS["memory"]
        
        logger.info(f"BusinessAnalyzer 初始化完成，use_llm={use_llm}")
    
    # ============================================================================
    # 主分析入口
    # ============================================================================
    
    def analyze(
        self,
        metrics_data: Dict[str, Any],
        period_hours: int = 24,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        主分析入口
        
        Args:
            metrics_data: 指标数据字典
            period_hours: 分析周期（小时），默认为 24
            namespace: 命名空间，默认为 None 表示全集群
            
        Returns:
            Dict[str, Any]: 完整的分析结果
        """
        logger.info(f"开始业务分析，period={period_hours}h, namespace={namespace}")
        
        # 1. 提取集群性能指标数据（由数据采集层生成，直接使用）
        try:
            cluster_health = self._extract_cluster_health(metrics_data, period_hours)
        except Exception as e:
            logger.error(f"提取集群性能指标失败: {e}")
            return {
                "status": AnalysisStatus.FAILED,
                "error": f"提取集群性能指标失败: {str(e)}",
                "cluster_health": {"status": "unknown", "score": 0},
                "bottlenecks": [],
                "trends": [],
                "suggestions": [],
                "summary": "分析失败，无法提取性能指标",
                "timestamp": datetime.now().isoformat(),
                "namespace": namespace,
                "period_hours": period_hours,
            }
        
        # 2. 尝试 LLM 分析（如果启用）
        llm_result = None
        if self.use_llm:
            try:
                # 检查 LLM 是否可用
                if self._check_llm_available():
                    llm_result = self._llm_based_analysis(metrics_data, cluster_health, period_hours, namespace)
                else:
                    logger.warning("LLM 不可用，降级到规则分析")
            except Exception as e:
                logger.warning(f"LLM 分析失败，使用规则分析降级: {e}")
        
        # 3. 构建最终结果
        if llm_result:
            final_result = {
                "status": AnalysisStatus.COMPLETED,
                "analysis_method": "llm",
                "cluster_health": cluster_health,
                "bottlenecks": llm_result.get("bottlenecks", []),
                "trends": llm_result.get("trends", []),
                "suggestions": llm_result.get("suggestions", []),
                "summary": llm_result.get("summary", ""),
            }
            logger.info("业务分析完成（LLM 深度分析）")
        else:
            # 规则分析降级
            rule_result = self._rule_based_analysis(metrics_data)
            final_result = {
                "status": AnalysisStatus.BASIC,
                "analysis_method": "rule_based",
                "cluster_health": cluster_health,
                "bottlenecks": rule_result.get("bottlenecks", []),
                "trends": rule_result.get("trends", []),
                "suggestions": rule_result.get("suggestions", []),
                "summary": rule_result.get("summary", ""),
            }
            logger.info("业务分析完成（规则分析降级）")
        
        # 添加元数据
        final_result["timestamp"] = datetime.now().isoformat()
        final_result["namespace"] = namespace
        final_result["period_hours"] = period_hours
        final_result["analysis_period_hours"] = period_hours
        
        return final_result
    
    # ============================================================================
    # LLM 可用性检查
    # ============================================================================
    
    def _check_llm_available(self) -> bool:
        """
        检查 LLM 是否可用
        
        Returns:
            bool: LLM 是否可用
        """
        try:
            llm_client = get_llm_client()
            # 检查 base_url 是否配置
            if not llm_client.base_url or llm_client.base_url == "":
                logger.warning("LLM base_url 未配置")
                return False
            if not llm_client.api_key or llm_client.api_key == "":
                logger.warning("LLM api_key 未配置")
                return False
            return True
        except Exception as e:
            logger.warning(f"LLM 客户端初始化失败: {e}")
            return False
    
    # ============================================================================
    # 集群性能指标提取（数据采集层生成，直接使用）
    # ============================================================================
    
    def _extract_cluster_health(
        self,
        metrics_data: Dict[str, Any],
        period_hours: int,
    ) -> Dict[str, Any]:
        """
        从数据采集层提取集群性能指标
        这部分直接使用数据采集层的数据，不进行 LLM 分析
        
        Args:
            metrics_data: 原始指标数据
            period_hours: 分析周期（小时）
            
        Returns:
            Dict[str, Any]: 集群健康概览
        """
        logger.info("从数据采集层提取集群性能指标")
        
        # 检测数据格式
        if "cpu" in metrics_data or "memory" in metrics_data:
            return self._extract_from_new_format(metrics_data, period_hours)
        else:
            return self._extract_from_old_format(metrics_data, period_hours)
    
    def _extract_from_new_format(
        self,
        metrics_data: Dict[str, Any],
        period_hours: int,
    ) -> Dict[str, Any]:
        """
        从新格式（metrics_collector 格式）提取集群性能指标
        
        Args:
            metrics_data: metrics_collector 格式的数据
            period_hours: 分析周期
            
        Returns:
            Dict[str, Any]: 集群健康概览
        """
        cpu_data = metrics_data.get("cpu", {})
        memory_data = metrics_data.get("memory", {})
        network_data = metrics_data.get("network", {})
        nodes_data = metrics_data.get("nodes", {})
        nodes_list = nodes_data.get("list", [])
        
        # CPU 指标统计
        cpu_summary = cpu_data.get("summary", {})
        cpu_stats = {
            "min": cpu_summary.get("min"),
            "max": cpu_summary.get("max"),
            "avg": cpu_summary.get("avg"),
            "trend": None,
        }
        
        # 内存指标统计
        memory_summary = memory_data.get("summary", {})
        memory_stats = {
            "min": memory_summary.get("min"),
            "max": memory_summary.get("max"),
            "avg": memory_summary.get("avg"),
            "trend": None,
        }
        
        # 如果节点数据存在，使用更准确的节点数据
        node_cpu_values = []
        node_memory_values = []
        for node in nodes_list:
            node_summary = node.get("summary", {})
            if node_summary.get("cpu_pct") is not None:
                node_cpu_values.append(node_summary["cpu_pct"])
            if node_summary.get("memory_pct") is not None:
                node_memory_values.append(node_summary["memory_pct"])
        
        if node_cpu_values:
            cpu_stats = {
                "min": round(min(node_cpu_values), 2),
                "max": round(max(node_cpu_values), 2),
                "avg": round(sum(node_cpu_values) / len(node_cpu_values), 2),
                "trend": None,
            }
        
        if node_memory_values:
            memory_stats = {
                "min": round(min(node_memory_values), 2),
                "max": round(max(node_memory_values), 2),
                "avg": round(sum(node_memory_values) / len(node_memory_values), 2),
                "trend": None,
            }
        
        # 网络指标统计
        network_summary = network_data.get("summary", {})
        rx_stats = network_summary.get("receive", {})
        tx_stats = network_summary.get("transmit", {})
        network_stats = {
            "receive_avg": rx_stats.get("avg"),
            "receive_max": rx_stats.get("max"),
            "receive_min": rx_stats.get("min"),
            "transmit_avg": tx_stats.get("avg"),
            "transmit_max": tx_stats.get("max"),
            "transmit_min": tx_stats.get("min"),
            "total_current": network_summary.get("total_current"),
        }
        
        # 磁盘指标统计
        disk_stats = {"min": None, "max": None, "avg": None}
        disk_values = []
        for node in nodes_list:
            for disk in node.get("disk", []):
                avg_pct = disk.get("avg_pct")
                if avg_pct is not None and not (isinstance(avg_pct, float) and math.isnan(avg_pct)):
                    disk_values.append(avg_pct)
        if disk_values:
            disk_stats = {
                "min": round(min(disk_values), 2),
                "max": round(max(disk_values), 2),
                "avg": round(sum(disk_values) / len(disk_values), 2),
            }
        
        # 系统负载（使用 CPU 作为参考）
        load_stats = {"min": None, "max": None, "avg": None}
        if cpu_stats.get("avg") is not None:
            load_stats = {
                "min": cpu_stats.get("min"),
                "max": cpu_stats.get("max"),
                "avg": cpu_stats.get("avg"),
            }
        
        # 分析时间段
        time_range = metrics_data.get("time_range", {})
        analysis_period = None
        if time_range.get("start") and time_range.get("end"):
            analysis_period = f"{time_range['start']} ~ {time_range['end']}"
        
        # 网络带宽使用率
        network_bandwidth_pct = None
        if network_stats.get("total_current") is not None:
            network_bandwidth_pct = round(network_stats["total_current"], 2)
        
        # 计算健康状态（基于统计数据）
        # 这里不进行深入分析，只基于阈值计算基础健康分
        bottleneck_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        
        if cpu_stats["avg"] is not None:
            if cpu_stats["avg"] >= self.cpu_threshold:
                bottleneck_count += 1
                if cpu_stats["avg"] >= self.cpu_threshold + 30:
                    high_count += 1
                elif cpu_stats["avg"] >= self.cpu_threshold + 10:
                    medium_count += 1
                else:
                    low_count += 1
        
        if memory_stats["avg"] is not None:
            if memory_stats["avg"] >= self.memory_threshold:
                bottleneck_count += 1
                if memory_stats["avg"] >= self.memory_threshold + 30:
                    high_count += 1
                elif memory_stats["avg"] >= self.memory_threshold + 10:
                    medium_count += 1
                else:
                    low_count += 1
        
        # 计算健康评分
        if bottleneck_count == 0:
            score = 90
            status = "healthy"
        elif high_count > 0:
            score = 40
            status = "critical"
        elif medium_count > 0:
            score = 65
            status = "warning"
        else:
            score = 75
            status = "warning"
        
        # 生成分析描述
        analysis_parts = []
        if status == "healthy":
            analysis_parts.append(f"集群整体性能良好（得分: {score}）")
        elif status == "warning":
            analysis_parts.append(f"集群存在一些性能问题（得分: {score}），检测到 {bottleneck_count} 个潜在瓶颈")
        else:
            analysis_parts.append(f"集群存在严重性能瓶颈（得分: {score}），检测到 {bottleneck_count} 个瓶颈")
        
        if cpu_stats["avg"] is not None:
            cpu_min_str = f"{cpu_stats['min']}%" if cpu_stats['min'] is not None else "-"
            cpu_max_str = f"{cpu_stats['max']}%" if cpu_stats['max'] is not None else "-"
            analysis_parts.append(f"CPU 平均使用率: {cpu_stats['avg']}%（范围: {cpu_min_str} - {cpu_max_str}）")
        if memory_stats["avg"] is not None:
            mem_min_str = f"{memory_stats['min']}%" if memory_stats['min'] is not None else "-"
            mem_max_str = f"{memory_stats['max']}%" if memory_stats['max'] is not None else "-"
            analysis_parts.append(f"内存平均使用率: {memory_stats['avg']}%（范围: {mem_min_str} - {mem_max_str}）")
        if disk_stats["avg"] is not None:
            disk_min_str = f"{disk_stats['min']}%" if disk_stats['min'] is not None else "-"
            disk_max_str = f"{disk_stats['max']}%" if disk_stats['max'] is not None else "-"
            analysis_parts.append(f"磁盘平均使用率: {disk_stats['avg']}%（范围: {disk_min_str} - {disk_max_str}）")
        if network_stats.get("receive_avg") is not None or network_stats.get("transmit_avg") is not None:
            rx = network_stats.get("receive_avg") or 0
            tx = network_stats.get("transmit_avg") or 0
            analysis_parts.append(f"网络平均流量: 接收 {rx} Mbps, 发送 {tx} Mbps")
        
        analysis = "。".join(analysis_parts) + "。"
        
        return {
            "status": status,
            "score": score,
            "analysis": analysis,
            "bottleneck_count": bottleneck_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "cpu_usage_pct": cpu_stats["avg"],
            "memory_usage_pct": memory_stats["avg"],
            "disk_usage_pct": disk_stats["avg"],
            "network_bandwidth_pct": network_bandwidth_pct,
            "load_average": load_stats["avg"],
            "network_traffic": network_stats.get("total_current"),
            "error_rate": None,
            "cpu_stats": cpu_stats,
            "memory_stats": memory_stats,
            "disk_stats": disk_stats,
            "network_stats": network_stats,
            "load_stats": load_stats,
            "analysis_period": analysis_period,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _extract_from_old_format(
        self,
        metrics_data: Dict[str, Any],
        period_hours: int,
    ) -> Dict[str, Any]:
        """
        从旧格式提取集群性能指标
        
        Args:
            metrics_data: 旧格式数据
            period_hours: 分析周期
            
        Returns:
            Dict[str, Any]: 集群健康概览
        """
        original_data = metrics_data.get("original_data", metrics_data)
        return self._extract_from_new_format(original_data, period_hours)
    
    # ============================================================================
    # LLM 分析方法
    # ============================================================================
    
    def _llm_based_analysis(
        self,
        metrics_data: Dict[str, Any],
        cluster_health: Dict[str, Any],
        period_hours: int,
        namespace: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        基于 LLM 的深度分析
        集群性能指标已由数据采集层生成，这里只生成其他部分
        
        Args:
            metrics_data: 原始指标数据
            cluster_health: 数据采集层生成的集群健康指标
            period_hours: 分析周期
            namespace: 命名空间
            
        Returns:
            Optional[Dict[str, Any]]: LLM 生成的分析结果，失败返回 None
        """
        logger.info("开始 LLM 深度分析")
        
        # 构建 LLM 输入
        llm_input = self._build_llm_input(metrics_data, cluster_health, period_hours, namespace)
        
        # 执行 LLM 分析（支持工具调用）
        response = self._execute_llm_analysis(llm_input)
        
        if response is None:
            return None
        
        # 解析和验证 JSON
        parsed_data = self._parse_and_validate_llm_response(response)
        
        if parsed_data is None:
            logger.warning("LLM 响应解析验证失败，降级到规则分析")
            return None
        
        logger.info("LLM 分析完成，验证通过")
        return parsed_data
    
    def _build_llm_input(
        self,
        metrics_data: Dict[str, Any],
        cluster_health: Dict[str, Any],
        period_hours: int,
        namespace: Optional[str],
    ) -> str:
        """
        构建 LLM 输入数据
        
        Args:
            metrics_data: 原始指标数据
            cluster_health: 集群健康指标
            period_hours: 分析周期
            namespace: 命名空间
            
        Returns:
            str: LLM 输入文本
        """
        # 精简指标数据，避免过长
        simplified_metrics = self._simplify_metrics(metrics_data)
        
        input_data = {
            "cluster_health_summary": cluster_health,
            "metrics_details": simplified_metrics,
            "analysis_context": {
                "period_hours": period_hours,
                "namespace": namespace or "全集群",
                "analysis_time": datetime.now().isoformat(),
            },
            "instructions": """
请基于以上数据，生成完整的业务性能分析报告。

## 你的任务

1. 分析 bottlenecks（性能瓶颈）：基于指标数据识别 CPU、内存、网络、磁盘等方面的性能瓶颈
2. 分析 trends（业务趋势）：分析资源使用趋势、识别业务繁忙时段
3. 生成 suggestions（优化建议）：基于瓶颈和趋势给出具体的优化建议
4. 生成 summary（分析摘要）：总结整体健康状态和关键建议

## 集群性能指标说明

cluster_health_summary 中的数据已由数据采集层生成，你可以直接使用这些数据进行分析。

## 重要要求

1. 必须输出纯 JSON 格式，不要包含任何其他文字
2. 严格按照系统提示中的 JSON 格式输出
3. 如果数据不足以进行深入分析，调用工具获取更多数据
4. 确保所有数值类型字段使用正确的数值类型（不是字符串）
5. 确保所有枚举字段使用正确的枚举值
""",
        }
        
        return json.dumps(input_data, ensure_ascii=False, indent=2)
    
    def _simplify_metrics(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        精简指标数据，避免 LLM 输入过长
        
        Args:
            metrics_data: 原始指标数据
            
        Returns:
            Dict[str, Any]: 精简后的指标数据
        """
        simplified = {}
        
        # 检测数据格式
        if "cpu" in metrics_data:
            # 新格式
            cpu_data = metrics_data.get("cpu", {})
            memory_data = metrics_data.get("memory", {})
            network_data = metrics_data.get("network", {})
            nodes_data = metrics_data.get("nodes", {})
            
            simplified = {
                "cpu_summary": cpu_data.get("summary", {}),
                "memory_summary": memory_data.get("summary", {}),
                "network_summary": network_data.get("summary", {}),
                "top_cpu_pods": cpu_data.get("top_pods", [])[:5],  # 只保留前 5 个
                "top_memory_pods": memory_data.get("top_pods", [])[:5],  # 只保留前 5 个
                "nodes_summary": [
                    {
                        "name": node.get("name"),
                        "summary": node.get("summary", {}),
                    }
                    for node in nodes_data.get("list", [])[:3]  # 只保留前 3 个节点
                ],
                "time_range": metrics_data.get("time_range", {}),
            }
        else:
            # 旧格式
            original_data = metrics_data.get("original_data", metrics_data)
            simplified = self._simplify_metrics(original_data)
        
        return simplified
    
    def _execute_llm_analysis(self, user_message: str) -> Optional[str]:
        """
        执行 LLM 分析，支持工具调用
        
        Args:
            user_message: 用户消息
            
        Returns:
            Optional[str]: LLM 响应内容
        """
        logger.info("调用 LLM 进行业务分析")
        
        try:
            # 使用 Agent 的 chat 方法，支持工具调用
            agent_response = self.agent.chat(user_message)
            
            logger.debug(f"LLM 响应: {agent_response.content[:500]}...")
            return agent_response.content
            
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None
    
    # ============================================================================
    # LLM 响应解析和验证
    # ============================================================================
    
    def _parse_and_validate_llm_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """
        解析和验证 LLM 响应
        
        Args:
            response_content: LLM 响应内容
            
        Returns:
            Optional[Dict[str, Any]]: 解析并验证后的结果，失败返回 None
        """
        # 1. 提取 JSON
        parsed_json = self._extract_json_from_response(response_content)
        if parsed_json is None:
            return None
        
        # 2. 验证 JSON 结构
        if not self._validate_json_structure(parsed_json):
            return None
        
        # 3. 规范化数据（生成缺失的 ID、修复枚举值等）
        normalized = self._normalize_llm_data(parsed_json)
        
        return normalized
    
    def _extract_json_from_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 响应中提取 JSON
        
        Args:
            response_content: LLM 响应内容
            
        Returns:
            Optional[Dict[str, Any]]: 提取的 JSON 对象
        """
        if not response_content:
            logger.warning("LLM 响应为空")
            return None
        
        # 尝试直接解析
        try:
            return json.loads(response_content)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 代码块
        json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        match = re.search(json_pattern, response_content, re.MULTILINE)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取第一个完整的 JSON 对象
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(response_content):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    try:
                        return json.loads(response_content[start_idx:i+1])
                    except json.JSONDecodeError:
                        break
        
        logger.warning(f"无法从响应中提取有效的 JSON: {response_content[:300]}...")
        return None
    
    def _validate_json_structure(self, data: Dict[str, Any]) -> bool:
        """
        验证 JSON 结构是否符合要求
        
        Args:
            data: 解析后的 JSON 数据
            
        Returns:
            bool: 是否有效
        """
        # 检查根级必需字段
        for field in REQUIRED_FIELDS["root"]:
            if field not in data:
                logger.warning(f"缺少必需字段: {field}")
                return False
        
        # 验证 bottlenecks
        bottlenecks = data.get("bottlenecks", [])
        if not isinstance(bottlenecks, list):
            logger.warning("bottlenecks 必须是数组")
            return False
        
        for i, b in enumerate(bottlenecks):
            if not self._validate_bottleneck(b, i):
                return False
        
        # 验证 trends
        trends = data.get("trends", [])
        if not isinstance(trends, list):
            logger.warning("trends 必须是数组")
            return False
        
        for i, t in enumerate(trends):
            if not self._validate_trend(t, i):
                return False
        
        # 验证 suggestions
        suggestions = data.get("suggestions", [])
        if not isinstance(suggestions, list):
            logger.warning("suggestions 必须是数组")
            return False
        
        for i, s in enumerate(suggestions):
            if not self._validate_suggestion(s, i):
                return False
        
        # 验证 summary
        summary = data.get("summary", "")
        if not isinstance(summary, str) or not summary.strip():
            logger.warning("summary 必须是非空字符串")
            # 不返回 False，而是尝试填充默认值
            data["summary"] = "集群性能分析报告"
        
        return True
    
    def _validate_bottleneck(self, bottleneck: Dict[str, Any], index: int) -> bool:
        """验证单个瓶颈数据"""
        if not isinstance(bottleneck, dict):
            logger.warning(f"bottlenecks[{index}] 必须是对象")
            return False
        
        # 检查必需字段（允许缺少，会自动填充）
        # 验证 type
        b_type = bottleneck.get("type")
        if b_type and b_type not in VALID_VALUES["bottleneck_type"]:
            logger.warning(f"bottlenecks[{index}].type 无效: {b_type}，将自动修复")
            bottleneck["type"] = "other"
        
        # 验证 severity
        severity = bottleneck.get("severity")
        if severity and severity not in VALID_VALUES["bottleneck_severity"]:
            logger.warning(f"bottlenecks[{index}].severity 无效: {severity}，将自动修复")
            bottleneck["severity"] = "medium"
        
        # 确保数值字段是数值类型
        for field in ["current_value", "threshold"]:
            value = bottleneck.get(field)
            if value is not None:
                try:
                    bottleneck[field] = float(value)
                except (ValueError, TypeError):
                    bottleneck[field] = 0.0
        
        return True
    
    def _validate_trend(self, trend: Dict[str, Any], index: int) -> bool:
        """验证单个趋势数据"""
        if not isinstance(trend, dict):
            logger.warning(f"trends[{index}] 必须是对象")
            return False
        
        # 验证 type
        t_type = trend.get("type")
        if t_type and t_type not in VALID_VALUES["trend_type"]:
            logger.warning(f"trends[{index}].type 无效: {t_type}，将自动修复")
            trend["type"] = "overall"
        
        # 验证 direction
        direction = trend.get("direction")
        if direction and direction not in VALID_VALUES["trend_direction"]:
            logger.warning(f"trends[{index}].direction 无效: {direction}，将自动修复")
            trend["direction"] = "稳定"
        
        # 确保数值字段是数值类型
        if trend.get("change_percent") is not None:
            try:
                trend["change_percent"] = float(trend["change_percent"])
            except (ValueError, TypeError):
                trend["change_percent"] = 0.0
        
        return True
    
    def _validate_suggestion(self, suggestion: Dict[str, Any], index: int) -> bool:
        """验证单个建议数据"""
        if not isinstance(suggestion, dict):
            logger.warning(f"suggestions[{index}] 必须是对象")
            return False
        
        # 验证 category
        category = suggestion.get("category")
        if category and category not in VALID_VALUES["suggestion_category"]:
            logger.warning(f"suggestions[{index}].category 无效: {category}，将自动修复")
            suggestion["category"] = "other"
        
        # 验证 priority
        priority = suggestion.get("priority")
        if priority and priority not in VALID_VALUES["suggestion_priority"]:
            logger.warning(f"suggestions[{index}].priority 无效: {priority}，将自动修复")
            suggestion["priority"] = "medium"
        
        # 验证 risk_level
        risk_level = suggestion.get("risk_level")
        if risk_level and risk_level not in VALID_VALUES["suggestion_risk_level"]:
            logger.warning(f"suggestions[{index}].risk_level 无效: {risk_level}，将自动修复")
            suggestion["risk_level"] = "medium"
        
        # 确保 details 是数组
        details = suggestion.get("details")
        if details is None:
            suggestion["details"] = []
        elif not isinstance(details, list):
            suggestion["details"] = [str(details)]
        
        return True
    
    def _normalize_llm_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        规范化 LLM 数据，填充缺失字段，生成 UUID
        
        Args:
            data: 原始数据
            
        Returns:
            Dict[str, Any]: 规范化后的数据
        """
        normalized = data.copy()
        
        # 规范化 bottlenecks
        bottlenecks = normalized.get("bottlenecks", [])
        normalized_bottlenecks = []
        for b in bottlenecks:
            nb = self._normalize_bottleneck(b)
            if nb:
                normalized_bottlenecks.append(nb)
        normalized["bottlenecks"] = normalized_bottlenecks
        
        # 规范化 trends
        trends = normalized.get("trends", [])
        normalized_trends = []
        for t in trends:
            nt = self._normalize_trend(t)
            if nt:
                normalized_trends.append(nt)
        normalized["trends"] = normalized_trends
        
        # 规范化 suggestions
        suggestions = normalized.get("suggestions", [])
        normalized_suggestions = []
        for s in suggestions:
            ns = self._normalize_suggestion(s)
            if ns:
                normalized_suggestions.append(ns)
        normalized["suggestions"] = normalized_suggestions
        
        # 确保 summary 存在
        normalized["summary"] = normalized.get("summary", "") or "集群性能分析报告"
        
        return normalized
    
    def _normalize_bottleneck(self, bottleneck: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """规范化单个瓶颈数据"""
        target = bottleneck.get("target", "unknown")
        b_type = bottleneck.get("type", "other")
        
        normalized = {
            "id": bottleneck.get("id") or str(uuid.uuid4()),
            "type": b_type if b_type in VALID_VALUES["bottleneck_type"] else "other",
            "target": target,
            "severity": bottleneck.get("severity") or "medium",
            "current_value": bottleneck.get("current_value") or 0.0,
            "threshold": bottleneck.get("threshold") or self._get_default_threshold(b_type),
            "root_cause": bottleneck.get("root_cause") or "需要进一步分析",
            "impact": bottleneck.get("impact") or "可能影响服务性能",
            "description": bottleneck.get("description") or f"检测到 {b_type} 性能问题",
            "detected_at": bottleneck.get("detected_at") or datetime.now().isoformat(),
        }
        
        # 确保数值类型
        for field in ["current_value", "threshold"]:
            try:
                normalized[field] = float(normalized[field])
            except (ValueError, TypeError):
                normalized[field] = 0.0
        
        return normalized
    
    def _get_default_threshold(self, b_type: str) -> float:
        """获取默认阈值"""
        if b_type == "cpu":
            return self.cpu_threshold
        elif b_type == "memory":
            return self.memory_threshold
        elif b_type == "disk":
            return 90.0
        else:
            return 80.0
    
    def _normalize_trend(self, trend: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """规范化单个趋势数据"""
        target = trend.get("target", "unknown")
        t_type = trend.get("type", "overall")
        
        normalized = {
            "id": trend.get("id") or str(uuid.uuid4()),
            "type": t_type if t_type in VALID_VALUES["trend_type"] else "overall",
            "target": target,
            "metric_name": trend.get("metric_name") or f"{t_type} 使用趋势",
            "direction": trend.get("direction") or "稳定",
            "change_percent": trend.get("change_percent") or 0.0,
            "analysis": trend.get("analysis") or f"{target} 的 {t_type} 使用趋势稳定",
            "prediction": trend.get("prediction") or "建议持续监控",
            "analyzed_at": trend.get("analyzed_at") or datetime.now().isoformat(),
        }
        
        # 确保数值类型
        try:
            normalized["change_percent"] = float(normalized["change_percent"])
        except (ValueError, TypeError):
            normalized["change_percent"] = 0.0
        
        return normalized
    
    def _normalize_suggestion(self, suggestion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """规范化单个建议数据"""
        target = suggestion.get("target", "unknown")
        category = suggestion.get("category", "other")
        
        normalized = {
            "id": suggestion.get("id") or str(uuid.uuid4()),
            "category": category if category in VALID_VALUES["suggestion_category"] else "other",
            "priority": suggestion.get("priority") or "medium",
            "target": target,
            "action": suggestion.get("action") or "建议进一步分析",
            "details": suggestion.get("details") or [],
            "expected_benefit": suggestion.get("expected_benefit") or "可能改善性能",
            "risk_level": suggestion.get("risk_level") or "medium",
        }
        
        # 确保 details 是数组
        if not isinstance(normalized["details"], list):
            normalized["details"] = [str(normalized["details"])]
        
        return normalized
    
    # ============================================================================
    # 规则分析方法（降级策略）
    # ============================================================================
    
    def _rule_based_analysis(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于规则的分析（降级策略）
        
        Args:
            metrics_data: 指标数据
            
        Returns:
            Dict[str, Any]: 规则分析结果
        """
        logger.debug("开始执行规则分析（降级）")
        
        # 转换数据格式（如果需要）
        try:
            if "cpu" in metrics_data or "memory" in metrics_data:
                metrics_data = self._convert_metrics_format(metrics_data)
        except Exception as e:
            logger.warning(f"数据格式转换失败，使用原始数据: {e}")
        
        # 1. 检测瓶颈
        bottlenecks = self._detect_bottlenecks(metrics_data)
        
        # 2. 分析趋势
        trends = self._analyze_trends(metrics_data)
        
        # 3. 生成建议
        suggestions = self._generate_suggestions(bottlenecks, trends)
        
        # 4. 计算集群健康概览（这只是降级时的补充）
        cluster_health = self._extract_cluster_health(metrics_data.get("original_data", metrics_data), 24)
        
        # 5. 生成基础摘要
        summary = self._generate_basic_summary(bottlenecks, trends, cluster_health)
        
        return {
            "cluster_health": cluster_health,
            "bottlenecks": bottlenecks,
            "trends": trends,
            "suggestions": suggestions,
            "summary": summary,
        }
    
    def _convert_metrics_format(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换 metrics_collector 的新数据格式为旧格式（兼容层）
        
        Args:
            metrics_data: metrics_collector 返回的原始数据
            
        Returns:
            Dict[str, Any]: 转换后的兼容格式数据
        """
        converted = {}
        
        def generate_time_series_values(start_value: float, avg_value: float, end_value: float, num_points: int = 10) -> List[List[float]]:
            if num_points < 2:
                num_points = 2
            now = datetime.now()
            values = []
            for i in range(num_points):
                progress = i / (num_points - 1)
                if start_value is not None and end_value is not None:
                    value = start_value + (end_value - start_value) * progress
                elif avg_value is not None:
                    value = avg_value
                else:
                    value = 0
                timestamp = (now - timedelta(minutes=(num_points - 1 - i) * 5)).timestamp()
                values.append([timestamp, float(value)])
            return values
        
        cpu_data = metrics_data.get("cpu", {})
        top_pods = cpu_data.get("top_pods", [])
        cpu_time_series = cpu_data.get("time_series", [])
        
        nodes_data = metrics_data.get("nodes", {})
        nodes_list = nodes_data.get("list", [])
        total_cpu_cores = 4.0
        if nodes_list:
            cores_list = []
            for node in nodes_list:
                cpu_cores = node.get("summary", {}).get("cpu_cores")
                if cpu_cores:
                    cores_list.append(cpu_cores)
            if cores_list:
                total_cpu_cores = sum(cores_list)
        
        if top_pods:
            cpu_usage = []
            for pod_data in top_pods:
                pod_name = pod_data.get("pod", "unknown")
                avg_cores = pod_data.get("avg_cores", 0) or 0
                max_cores = pod_data.get("max_cores", 0) or 0
                current_cores = pod_data.get("current_cores", 0) or 0
                
                avg_value = min((avg_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                max_value = min((max_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                current_value = min((current_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                
                pod_values = []
                for series in cpu_time_series:
                    if series.get("metric", {}).get("pod") == pod_name:
                        for dp in series.get("data_points", []):
                            value = dp.get("value", 0)
                            value_pct = min((value / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                            pod_values.append([
                                datetime.fromisoformat(dp["timestamp"]).timestamp(),
                                value_pct
                            ])
                
                if len(pod_values) < 2:
                    start_cores = pod_data.get("start_cores", avg_cores) or avg_cores
                    start_value = min((start_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                    pod_values = generate_time_series_values(start_value, avg_value, current_value, num_points=12)
                
                cpu_usage.append({
                    "labels": {"pod": pod_name},
                    "values": pod_values,
                    "value": current_value,
                    "avg": avg_value,
                    "max": max_value,
                })
            converted["cpu_usage"] = cpu_usage
        else:
            summary = cpu_data.get("summary", {})
            current = summary.get("current", 0) or 0
            avg = summary.get("avg", 0) or 0
            max_val = summary.get("max", 0) or 0
            min_val = summary.get("min", 0) or 0
            
            current_pct = min((current / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            avg_pct = min((avg / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            max_pct = min((max_val / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            min_pct = min((min_val / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            
            values = generate_time_series_values(min_pct, avg_pct, current_pct, num_points=12)
            
            converted["cpu_usage"] = [{
                "labels": {"pod": "cluster_total"},
                "values": values,
                "value": current_pct,
                "avg": avg_pct,
                "max": max_pct,
            }]
        
        memory_data = metrics_data.get("memory", {})
        top_pods_memory = memory_data.get("top_pods", [])
        
        total_memory_gb = 0
        if nodes_list:
            memory_list = []
            for node in nodes_list:
                memory_total = node.get("summary", {}).get("memory_total_gb")
                if memory_total:
                    memory_list.append(memory_total)
            if memory_list:
                total_memory_gb = sum(memory_list)
        
        container_limit_gb = 4.0
        
        if top_pods_memory:
            memory_usage = []
            for pod_data in top_pods_memory:
                pod_name = pod_data.get("pod", "unknown")
                avg_gb = pod_data.get("avg_gb", 0) or 0
                max_gb = pod_data.get("max_gb", 0) or 0
                current_gb = pod_data.get("current_gb", 0) or 0
                
                memory_limit = total_memory_gb if total_memory_gb > 0 else container_limit_gb
                
                avg_pct = min((avg_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                max_pct = min((max_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                current_pct = min((current_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                
                start_gb = pod_data.get("start_gb", avg_gb) or avg_gb
                start_pct = min((start_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                pod_values = generate_time_series_values(start_pct, avg_pct, current_pct, num_points=12)
                
                memory_usage.append({
                    "labels": {"pod": pod_name},
                    "values": pod_values,
                    "value": current_pct,
                    "avg": avg_pct,
                    "max": max_pct,
                })
            converted["memory_usage"] = memory_usage
        else:
            summary = memory_data.get("summary", {})
            current = summary.get("current", 0) or 0
            avg = summary.get("avg", 0) or 0
            max_val = summary.get("max", 0) or 0
            min_val = summary.get("min", 0) or 0
            
            memory_limit = total_memory_gb if total_memory_gb > 0 else 1
            current_pct = min((current / memory_limit) * 100, 100) if memory_limit > 0 else current
            avg_pct = min((avg / memory_limit) * 100, 100) if memory_limit > 0 else avg
            max_pct = min((max_val / memory_limit) * 100, 100) if memory_limit > 0 else max_val
            min_pct = min((min_val / memory_limit) * 100, 100) if memory_limit > 0 else min_val
            
            values = generate_time_series_values(min_pct, avg_pct, current_pct, num_points=12)
            
            converted["memory_usage"] = [{
                "labels": {"pod": "cluster_total"},
                "values": values,
                "value": current_pct,
                "avg": avg_pct,
                "max": max_pct,
            }]
        
        converted["nodes"] = nodes_data
        converted["network"] = metrics_data.get("network", {})
        converted["original_data"] = metrics_data
        
        return converted
    
    def _detect_bottlenecks(self, metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于阈值规则识别性能瓶颈"""
        bottlenecks = []
        
        cpu_metrics = metrics_data.get("cpu_usage", [])
        for metric in cpu_metrics:
            stats = self._calculate_stats(metric)
            if stats["max"] > self.cpu_threshold:
                bottlenecks.append({
                    "id": str(uuid.uuid4()),
                    "type": "cpu",
                    "target": metric.get("labels", {}).get("pod", "unknown"),
                    "severity": self._get_severity(stats["max"], self.cpu_threshold),
                    "current_value": round(stats["max"], 2),
                    "threshold": self.cpu_threshold,
                    "root_cause": "资源使用率超过阈值",
                    "impact": "可能导致服务响应变慢",
                    "description": f"CPU 使用率超过阈值 {self.cpu_threshold}%，最高达到 {round(stats['max'], 2)}%",
                    "detected_at": datetime.now().isoformat(),
                })
        
        memory_metrics = metrics_data.get("memory_usage", [])
        for metric in memory_metrics:
            stats = self._calculate_stats(metric)
            if stats["max"] > self.memory_threshold:
                bottlenecks.append({
                    "id": str(uuid.uuid4()),
                    "type": "memory",
                    "target": metric.get("labels", {}).get("pod", "unknown"),
                    "severity": self._get_severity(stats["max"], self.memory_threshold),
                    "current_value": round(stats["max"], 2),
                    "threshold": self.memory_threshold,
                    "root_cause": "内存使用量超过阈值",
                    "impact": "可能导致 OOM 或服务不稳定",
                    "description": f"内存使用率超过阈值 {self.memory_threshold}%，最高达到 {round(stats['max'], 2)}%",
                    "detected_at": datetime.now().isoformat(),
                })
        
        return bottlenecks
    
    def _analyze_trends(self, metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析业务趋势"""
        trends = []
        original_data = metrics_data.get("original_data", {})
        time_range = original_data.get("time_range", {})
        period_hours = time_range.get("period_hours", 24)
        
        cpu_metrics_list = metrics_data.get("cpu_usage", [])
        network_data = original_data.get("network", {})
        network_summary = network_data.get("summary", {})
        
        if cpu_metrics_list:
            all_cpu_values = []
            for metric in cpu_metrics_list:
                stats = self._calculate_stats(metric)
                all_cpu_values.append({
                    "min": stats["min"],
                    "max": min(stats["max"], 100),
                    "avg": stats["avg"],
                })
            
            if all_cpu_values:
                cluster_cpu_min = min(v["min"] for v in all_cpu_values)
                cluster_cpu_max = min(max(v["max"] for v in all_cpu_values), 100)
                cluster_cpu_avg = sum(v["avg"] for v in all_cpu_values) / len(all_cpu_values)
                
                first_metric = cpu_metrics_list[0]
                trend_data = self._calculate_trend(first_metric)
                direction = "稳定"
                change_percent = 0
                if trend_data:
                    change_percent = trend_data["change_rate"]
                    direction = trend_data["direction"]
                
                trends.append({
                    "id": str(uuid.uuid4()),
                    "type": "cpu",
                    "target": "集群整体",
                    "metric_name": "CPU 使用率",
                    "direction": direction,
                    "change_percent": round(change_percent, 2),
                    "analysis": f"集群整体 CPU 使用率呈{direction}趋势，变化率 {round(change_percent, 2)}%。平均使用率 {round(cluster_cpu_avg, 2)}%，峰值 {round(cluster_cpu_max, 2)}%。",
                    "prediction": "建议持续监控" if direction == "稳定" else f"{'需要关注趋势变化' if direction == '上升' else '资源可能存在过剩'}",
                    "analyzed_at": datetime.now().isoformat(),
                })
        
        network_rx = network_summary.get("receive", {}) if network_summary else {}
        network_tx = network_summary.get("transmit", {}) if network_summary else {}
        rx_avg = network_rx.get("avg")
        tx_avg = network_tx.get("avg")
        
        if rx_avg is not None or tx_avg is not None:
            total_avg = (rx_avg or 0) + (tx_avg or 0)
            busy_description = ""
            if total_avg > 50:
                busy_description = f"检测到高流量时段，峰值流量达到 {round(total_avg, 2)} Mbps，可能对应业务繁忙期。"
            elif total_avg > 10:
                busy_description = f"平均流量 {round(total_avg, 2)} Mbps，业务负载处于正常水平。"
            else:
                busy_description = f"平均流量 {round(total_avg, 2)} Mbps，业务负载较低。"
            
            trends.append({
                "id": str(uuid.uuid4()),
                "type": "network",
                "target": "集群整体",
                "metric_name": "网络流量",
                "direction": "稳定",
                "change_percent": 0,
                "analysis": f"集群整体网络流量分析：接收平均 {round(rx_avg, 2) if rx_avg else '-'} Mbps，发送平均 {round(tx_avg, 2) if tx_avg else '-'} Mbps。{busy_description}分析时段：{period_hours} 小时。",
                "prediction": "建议持续监控网络流量变化",
                "analyzed_at": datetime.now().isoformat(),
            })
        
        return trends
    
    def _generate_suggestions(
        self,
        bottlenecks: List[Dict[str, Any]],
        trends: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """生成基础的优化建议"""
        suggestions = []
        
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "cpu":
                suggestions.append({
                    "id": str(uuid.uuid4()),
                    "category": "cpu_optimization",
                    "priority": bottleneck["severity"],
                    "target": bottleneck["target"],
                    "action": "检查代码逻辑，优化 CPU 密集型操作",
                    "details": [
                        "分析应用代码中的循环和计算密集型操作",
                        "检查是否存在死循环或资源竞争",
                        "考虑水平扩容增加 Pod 副本数",
                    ],
                    "expected_benefit": "降低 CPU 使用率，提升响应速度",
                    "risk_level": "low",
                })
            elif bottleneck["type"] == "memory":
                suggestions.append({
                    "id": str(uuid.uuid4()),
                    "category": "memory_optimization",
                    "priority": bottleneck["severity"],
                    "target": bottleneck["target"],
                    "action": "检查内存泄漏，优化内存使用",
                    "details": [
                        "分析应用的内存使用模式",
                        "检查是否存在内存泄漏",
                        "考虑调整内存资源限制",
                    ],
                    "expected_benefit": "降低内存使用率，避免 OOM",
                    "risk_level": "low",
                })
        
        for trend in trends:
            if trend["direction"] == "上升":
                suggestions.append({
                    "id": str(uuid.uuid4()),
                    "category": "scaling",
                    "priority": "medium",
                    "target": trend["target"],
                    "action": "准备扩容策略，应对持续增长的资源需求",
                    "details": [
                        f"监控 {trend['metric_name']} 趋势变化",
                        "设置告警阈值",
                        "准备自动扩容策略",
                    ],
                    "expected_benefit": "提前应对资源增长，避免性能问题",
                    "risk_level": "low",
                })
        
        if not suggestions:
            suggestions.append({
                "id": str(uuid.uuid4()),
                "category": "other",
                "priority": "low",
                "target": "集群整体",
                "action": "持续监控，保持当前配置",
                "details": [
                    "定期检查集群健康状态",
                    "设置合理的告警阈值",
                    "维护监控体系",
                ],
                "expected_benefit": "维持集群良好运行状态",
                "risk_level": "low",
            })
        
        return suggestions
    
    def _generate_basic_summary(
        self,
        bottlenecks: List[Dict[str, Any]],
        trends: List[Dict[str, Any]],
        cluster_health: Dict[str, Any],
    ) -> str:
        """生成基础摘要"""
        parts = []
        
        parts.append(f"集群健康状态: {cluster_health.get('status', 'unknown')}（分数: {cluster_health.get('score', 0)}）")
        
        if bottlenecks:
            cpu_bottlenecks = [b for b in bottlenecks if b["type"] == "cpu"]
            memory_bottlenecks = [b for b in bottlenecks if b["type"] == "memory"]
            
            bottleneck_info = []
            if cpu_bottlenecks:
                bottleneck_info.append(f"{len(cpu_bottlenecks)} 个 CPU 瓶颈")
            if memory_bottlenecks:
                bottleneck_info.append(f"{len(memory_bottlenecks)} 个内存瓶颈")
            
            parts.append(f"检测到 {len(bottlenecks)} 个瓶颈: " + ", ".join(bottleneck_info))
        else:
            parts.append("未检测到性能瓶颈")
        
        if trends:
            up_trends = [t for t in trends if t["direction"] == "上升"]
            down_trends = [t for t in trends if t["direction"] == "下降"]
            stable_trends = [t for t in trends if t["direction"] == "稳定"]
            
            trend_info = []
            if up_trends:
                trend_info.append(f"{len(up_trends)} 个上升趋势")
            if down_trends:
                trend_info.append(f"{len(down_trends)} 个下降趋势")
            if stable_trends:
                trend_info.append(f"{len(stable_trends)} 个稳定趋势")
            
            parts.append("趋势分析: " + ", ".join(trend_info))
        
        return "。".join(parts) + "。"
    
    # ============================================================================
    # 辅助方法
    # ============================================================================
    
    def _calculate_stats(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """计算统计数据"""
        values = metric.get("values", [])
        if not values:
            return {"min": 0, "max": 0, "avg": 0}
        
        numeric_values = [float(v) for _, v in values if v is not None]
        if not numeric_values:
            return {"min": 0, "max": 0, "avg": 0}
        
        return {
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": sum(numeric_values) / len(numeric_values),
        }
    
    def _calculate_trend(self, metric: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """计算趋势"""
        values = metric.get("values", [])
        if len(values) < 2:
            return None
        
        first_value = float(values[0][1]) if values[0][1] is not None else 0
        last_value = float(values[-1][1]) if values[-1][1] is not None else 0
        
        if first_value == 0:
            change_rate = 0
        else:
            change_rate = ((last_value - first_value) / first_value) * 100
        
        if change_rate > 5:
            direction = "上升"
        elif change_rate < -5:
            direction = "下降"
        else:
            direction = "稳定"
        
        return {
            "direction": direction,
            "change_rate": change_rate,
        }
    
    def _get_severity(self, value: float, threshold: float) -> str:
        """获取严重程度"""
        if value >= threshold + 30:
            return "high"
        elif value >= threshold + 10:
            return "medium"
        else:
            return "low"


# ============================================================================
# 单例模式实现
# ============================================================================

_analyzer: Optional[BusinessAnalyzer] = None


def get_business_analyzer(use_llm: bool = True) -> BusinessAnalyzer:
    """
    获取业务分析器单例
    
    Args:
        use_llm: 是否启用 LLM 深度分析
        
    Returns:
        BusinessAnalyzer: 业务分析器实例
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = BusinessAnalyzer(use_llm=use_llm)
    return _analyzer
