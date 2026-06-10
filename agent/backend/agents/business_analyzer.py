"""
业务分析引擎模块
实现基于规则和 LLM 的业务指标分析，支持 LLM 不可用时的自动降级
"""

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents.agent import Agent


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
# BusinessAnalyzer 类定义
# ============================================================================

class BusinessAnalyzer:
    """
    业务分析引擎
    结合规则分析和 LLM 深度分析，支持 LLM 不可用时的自动降级
    """
    
    def __init__(self, use_llm: bool = True):
        """
        初始化业务分析器
        
        Args:
            use_llm: 是否启用 LLM 深度分析，默认为 True
        """
        self.use_llm = use_llm
        self.agent = Agent() if use_llm else None
        
        # 阈值配置
        self.cpu_threshold = THRESHOLDS["cpu"]
        self.memory_threshold = THRESHOLDS["memory"]
        
        logger.info(f"BusinessAnalyzer 初始化完成，use_llm={use_llm}")
    
    # ============================================================================
    # 主分析入口
    # ============================================================================
    
    def _convert_metrics_format(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换 metrics_collector 的新数据格式为旧格式（兼容层）
        
        metrics_collector 返回的新格式:
        {
            "cpu": {
                "summary": { "current": 1.2, "avg": 1.0, "max": 1.5, ... },
                "time_series": [...],
                "top_pods": [
                    { "pod": "xxx", "avg_cores": 1.2, "max_cores": 1.5, "current_cores": 1.0 },
                    ...
                ]
            },
            "memory": { ... },
            "network": { ... },
            "nodes": { ... }
        }
        
        转换为旧格式（business_analyzer 期望）:
        {
            "cpu_usage": [
                {
                    "labels": { "pod": "xxx" },
                    "values": [[timestamp1, value1], [timestamp2, value2], ...],
                    "value": 1.2
                },
                ...
            ],
            "memory_usage": [...],
            ...
        }
        
        Args:
            metrics_data: metrics_collector 返回的原始数据
            
        Returns:
            Dict[str, Any]: 转换后的兼容格式数据
        """
        converted = {}
        
        def generate_time_series_values(start_value: float, avg_value: float, end_value: float, num_points: int = 10) -> List[List[float]]:
            """
            根据统计数据生成时间序列数据点（用于趋势分析）
            
            Args:
                start_value: 起始值
                avg_value: 平均值
                end_value: 结束值
                num_points: 数据点数量
                
            Returns:
                List[List[float]]: [[timestamp, value], ...]
            """
            if num_points < 2:
                num_points = 2
            
            now = datetime.now()
            values = []
            
            for i in range(num_points):
                progress = i / (num_points - 1)
                # 线性插值从 start 到 end
                if start_value is not None and end_value is not None:
                    value = start_value + (end_value - start_value) * progress
                elif avg_value is not None:
                    value = avg_value
                else:
                    value = 0
                
                timestamp = (now - timedelta(minutes=(num_points - 1 - i) * 5)).timestamp()
                values.append([timestamp, float(value)])
            
            return values
        
        # 转换 CPU 数据
        cpu_data = metrics_data.get("cpu", {})
        top_pods = cpu_data.get("top_pods", [])
        cpu_time_series = cpu_data.get("time_series", [])
        
        # 从节点数据获取 CPU 核心数，用于计算使用率百分比
        nodes_data = metrics_data.get("nodes", {})
        nodes_list = nodes_data.get("list", [])
        total_cpu_cores = 4.0  # 默认值
        if nodes_list:
            cores_list = []
            for node in nodes_list:
                node_summary = node.get("summary", {})
                cpu_cores = node_summary.get("cpu_cores")
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
                
                # CPU 核数转换为百分比，限制不超过 100%
                avg_value = min((avg_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                max_value = min((max_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                current_value = min((current_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                
                pod_values = []
                # 尝试从 Pod 级别的 time_series 中找到对应的数据
                for series in cpu_time_series:
                    if series.get("metric", {}).get("pod") == pod_name:
                        for dp in series.get("data_points", []):
                            value = dp.get("value", 0)
                            value_pct = min((value / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                            pod_values.append([
                                datetime.fromisoformat(dp["timestamp"]).timestamp(),
                                value_pct
                            ])
                
                # 如果没有找到 Pod 级别的数据，使用统计数据生成
                if len(pod_values) < 2:
                    start_cores = pod_data.get("start_cores", avg_cores) or avg_cores
                    start_value = min((start_cores / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
                    pod_values = generate_time_series_values(
                        start_value,
                        avg_value,
                        current_value,
                        num_points=12
                    )
                
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
            
            # 转换为百分比，限制不超过 100%
            current_pct = min((current / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            avg_pct = min((avg / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            max_pct = min((max_val / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            min_pct = min((min_val / total_cpu_cores) * 100, 100) if total_cpu_cores > 0 else 0
            
            # 生成时间序列数据
            values = generate_time_series_values(
                min_pct,
                avg_pct,
                current_pct,
                num_points=12
            )
            
            converted["cpu_usage"] = [{
                "labels": {"pod": "cluster_total"},
                "values": values,
                "value": current_pct,
                "avg": avg_pct,
                "max": max_pct,
            }]
        
        # 转换内存数据
        memory_data = metrics_data.get("memory", {})
        top_pods_memory = memory_data.get("top_pods", [])
        mem_time_series = memory_data.get("time_series", [])
        
        # 从节点数据获取总内存大小，用于计算使用率百分比（更准确）
        total_memory_gb = 0
        nodes_list = nodes_data.get("list", [])
        if nodes_list:
            memory_list = []
            for node in nodes_list:
                node_summary = node.get("summary", {})
                memory_total = node_summary.get("memory_total_gb")
                if memory_total:
                    memory_list.append(memory_total)
            if memory_list:
                total_memory_gb = sum(memory_list)
        
        # 默认内存限制
        container_limit_gb = 4.0
        
        if top_pods_memory:
            memory_usage = []
            for pod_data in top_pods_memory:
                pod_name = pod_data.get("pod", "unknown")
                avg_gb = pod_data.get("avg_gb", 0) or 0
                max_gb = pod_data.get("max_gb", 0) or 0
                current_gb = pod_data.get("current_gb", 0) or 0
                
                # 使用节点总内存计算（更准确），如果没有节点数据则使用默认值
                memory_limit = total_memory_gb if total_memory_gb > 0 else container_limit_gb
                
                avg_pct = min((avg_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                max_pct = min((max_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                current_pct = min((current_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                
                pod_values = []
                # 尝试从 Pod 级别的 time_series 中找到对应的数据
                for series in mem_time_series:
                    if series.get("metric", {}).get("pod") == pod_name:
                        for dp in series.get("data_points", []):
                            value_gb = dp.get("value", 0)
                            value_pct = min((value_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                            pod_values.append([
                                datetime.fromisoformat(dp["timestamp"]).timestamp(),
                                value_pct
                            ])
                
                # 如果没有找到 Pod 级别的数据，使用统计数据生成
                if len(pod_values) < 2:
                    start_gb = pod_data.get("start_gb", avg_gb) or avg_gb
                    start_pct = min((start_gb / memory_limit) * 100, 100) if memory_limit > 0 else 0
                    pod_values = generate_time_series_values(
                        start_pct,
                        avg_pct,
                        current_pct,
                        num_points=12
                    )
                
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
            
            # 使用节点总内存计算
            memory_limit = total_memory_gb if total_memory_gb > 0 else 1
            current_pct = min((current / memory_limit) * 100, 100) if memory_limit > 0 else current
            avg_pct = min((avg / memory_limit) * 100, 100) if memory_limit > 0 else avg
            max_pct = min((max_val / memory_limit) * 100, 100) if memory_limit > 0 else max_val
            min_pct = min((min_val / memory_limit) * 100, 100) if memory_limit > 0 else min_val
            
            values = generate_time_series_values(
                min_pct,
                avg_pct,
                current_pct,
                num_points=12
            )
            
            converted["memory_usage"] = [{
                "labels": {"pod": "cluster_total"},
                "values": values,
                "value": current_pct,
                "avg": avg_pct,
                "max": max_pct,
            }]
        
        # 添加节点数据供参考
        converted["nodes"] = nodes_data
        
        # 添加网络数据供参考
        network_data = metrics_data.get("network", {})
        converted["network"] = network_data
        
        # 保存原始数据引用，供详细分析使用
        converted["original_data"] = metrics_data
        
        logger.info(f"数据格式转换完成: cpu={len(converted.get('cpu_usage', []))} 个 Pod, memory={len(converted.get('memory_usage', []))} 个 Pod")
        
        return converted
    
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
            Dict[str, Any]: 完整的分析结果，包含状态、瓶颈、趋势、建议等
        """
        logger.info(f"开始业务分析，period={period_hours}h, namespace={namespace}")
        
        # 0. 数据格式转换（兼容 metrics_collector 的新格式）
        try:
            # 检查是否是新格式（包含 cpu/memory/network/nodes 字段）
            if "cpu" in metrics_data or "memory" in metrics_data:
                logger.info("检测到 metrics_collector 新格式，进行数据转换")
                metrics_data = self._convert_metrics_format(metrics_data)
            else:
                logger.info("使用旧格式数据，无需转换")
        except Exception as e:
            logger.warning(f"数据格式转换失败，使用原始数据: {e}")
        
        # 1. 执行规则分析（始终执行，作为基础和降级备选）
        try:
            rule_result = self._rule_based_analysis(metrics_data)
        except Exception as e:
            logger.error(f"规则分析执行失败: {e}")
            return {
                "status": AnalysisStatus.FAILED,
                "error": f"规则分析失败: {str(e)}",
                "cluster_health": {"status": "unknown", "score": 0},
                "bottlenecks": [],
                "trends": [],
                "suggestions": [],
                "summary": "分析失败，规则引擎执行异常",
                "timestamp": datetime.now().isoformat(),
                "namespace": namespace,
                "period_hours": period_hours,
            }
        
        # 2. 尝试 LLM 深度分析（如果启用）
        llm_result = None
        if self.use_llm:
            try:
                llm_result = self._llm_analysis(metrics_data, rule_result)
            except Exception as e:
                logger.warning(f"LLM 分析失败，使用规则分析结果降级: {e}")
        
        # 3. 构建最终结果
        if llm_result:
            # LLM 分析成功
            final_result = self._merge_results(rule_result, llm_result)
            final_result["status"] = AnalysisStatus.COMPLETED
            logger.info("业务分析完成（LLM 深度分析）")
        else:
            # 使用规则分析结果（降级）
            final_result = self._build_basic_result(rule_result)
            final_result["status"] = AnalysisStatus.BASIC
            logger.info("业务分析完成（规则分析降级）")
        
        # 添加元数据
        final_result["timestamp"] = datetime.now().isoformat()
        final_result["namespace"] = namespace
        final_result["period_hours"] = period_hours
        final_result["analysis_period_hours"] = period_hours
        
        return final_result
    
    # ============================================================================
    # 规则分析方法
    # ============================================================================
    
    def _rule_based_analysis(self, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于规则的分析（降级策略）
        
        Args:
            metrics_data: 指标数据
            
        Returns:
            Dict[str, Any]: 规则分析结果
        """
        logger.debug("开始执行规则分析")
        
        # 1. 检测瓶颈
        bottlenecks = self._detect_bottlenecks(metrics_data)
        
        # 2. 分析趋势
        trends = self._analyze_trends(metrics_data)
        
        # 3. 生成建议
        suggestions = self._generate_suggestions(bottlenecks, trends)
        
        # 4. 计算集群健康概览
        cluster_health = self._calculate_cluster_health(metrics_data, bottlenecks)
        
        # 5. 生成基础摘要
        summary = self._generate_basic_summary(bottlenecks, trends, cluster_health)
        
        return {
            "cluster_health": cluster_health,
            "bottlenecks": bottlenecks,
            "trends": trends,
            "suggestions": suggestions,
            "summary": summary,
        }
    
    def _detect_bottlenecks(self, metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于阈值规则识别性能瓶颈
        
        Args:
            metrics_data: 指标数据
            
        Returns:
            List[Dict[str, Any]]: 瓶颈列表
        """
        bottlenecks = []
        
        # 分析 CPU 使用情况
        cpu_metrics = metrics_data.get("cpu_usage", [])
        for metric in cpu_metrics:
            stats = self._calculate_stats(metric)
            if stats["max"] > self.cpu_threshold:
                bottlenecks.append({
                    "type": "cpu",
                    "target": metric.get("labels", {}).get("pod", "unknown"),
                    "severity": self._get_severity(stats["max"], self.cpu_threshold),
                    "current_value": round(stats["max"], 2),
                    "threshold": self.cpu_threshold,
                    "stats": stats,
                    "description": f"CPU 使用率超过阈值 {self.cpu_threshold}%，最高达到 {round(stats['max'], 2)}%",
                    "detected_at": datetime.now().isoformat(),
                })
        
        # 分析内存使用情况
        memory_metrics = metrics_data.get("memory_usage", [])
        for metric in memory_metrics:
            stats = self._calculate_stats(metric)
            if stats["max"] > self.memory_threshold:
                bottlenecks.append({
                    "type": "memory",
                    "target": metric.get("labels", {}).get("pod", "unknown"),
                    "severity": self._get_severity(stats["max"], self.memory_threshold),
                    "current_value": round(stats["max"], 2),
                    "threshold": self.memory_threshold,
                    "stats": stats,
                    "description": f"内存使用率超过阈值 {self.memory_threshold}%，最高达到 {round(stats['max'], 2)}%",
                    "detected_at": datetime.now().isoformat(),
                })
        
        return bottlenecks
    
    def _analyze_trends(self, metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分析业务趋势
        基于各项指标变化分析业务总量与变化趋势，识别繁忙时间段
        
        Args:
            metrics_data: 指标数据（包含转换后的 cpu_usage, memory_usage）
            
        Returns:
            List[Dict[str, Any]]: 趋势列表
        """
        trends = []
        original_data = metrics_data.get("original_data", {})
        
        # 从原始数据中提取时间序列，用于业务趋势分析
        time_range = original_data.get("time_range", {})
        period_hours = time_range.get("period_hours", 24)
        
        # 使用转换后的数据（已经是百分比格式）
        cpu_metrics_list = metrics_data.get("cpu_usage", [])
        memory_metrics_list = metrics_data.get("memory_usage", [])
        
        # 分析网络数据来判断业务繁忙程度（网络数据不需要转换，直接使用原始数据）
        network_data = original_data.get("network", {})
        network_summary = network_data.get("summary", {})
        
        # 分析集群级别的整体 CPU 趋势（基于转换后的数据聚合）
        if cpu_metrics_list:
            # 聚合所有 Pod 的 CPU 数据
            all_cpu_values = []
            for metric in cpu_metrics_list:
                stats = self._calculate_stats(metric)
                all_cpu_values.append({
                    "min": stats["min"],
                    "max": stats["max"],
                    "avg": stats["avg"],
                })
            
            if all_cpu_values:
                cluster_cpu_min = min(v["min"] for v in all_cpu_values)
                cluster_cpu_max = min(max(v["max"] for v in all_cpu_values), 100)
                cluster_cpu_avg = sum(v["avg"] for v in all_cpu_values) / len(all_cpu_values)
                
                # 计算趋势（基于第一个和最后一个 Pod 的数据对比）
                first_metric = cpu_metrics_list[0]
                trend_data = self._calculate_trend(first_metric)
                direction = "稳定"
                change_percent = 0
                if trend_data:
                    change_percent = trend_data["change_rate"]
                    direction = trend_data["direction"]
                
                trends.append({
                    "type": "cpu",
                    "target": "集群整体",
                    "metric_name": "CPU 使用率",
                    "direction": direction,
                    "change_percent": round(change_percent, 2),
                    "start_value": round(cluster_cpu_min, 2),
                    "end_value": round(cluster_cpu_max, 2),
                    "avg_value": round(cluster_cpu_avg, 2),
                    "analysis": f"集群整体 CPU 使用率呈{direction}趋势，变化率 {round(change_percent, 2)}%。平均使用率 {round(cluster_cpu_avg, 2)}%，峰值 {round(cluster_cpu_max, 2)}%，范围 {round(cluster_cpu_min, 2)}% - {round(cluster_cpu_max, 2)}%。",
                    "analyzed_at": datetime.now().isoformat(),
                })
        
        # 分析网络流量趋势 - 这是判断业务繁忙的关键指标
        network_rx = network_summary.get("receive", {}) if network_summary else {}
        network_tx = network_summary.get("transmit", {}) if network_summary else {}
        
        rx_avg = network_rx.get("avg")
        rx_max = network_rx.get("max")
        tx_avg = network_tx.get("avg")
        tx_max = network_tx.get("max")
        
        if rx_avg is not None or tx_avg is not None:
            total_avg = (rx_avg or 0) + (tx_avg or 0)
            total_max = (rx_max or 0) + (tx_max or 0)
            
            # 判断是否有繁忙时段
            busy_description = ""
            if total_max > 50:  # 超过 50Mbps 认为是繁忙
                busy_description = f"检测到高流量时段，峰值流量达到 {round(total_max, 2)} Mbps，可能对应业务繁忙期。"
            elif total_avg > 10:
                busy_description = f"平均流量 {round(total_avg, 2)} Mbps，业务负载处于正常水平。"
            else:
                busy_description = f"平均流量 {round(total_avg, 2)} Mbps，业务负载较低。"
            
            trends.append({
                "type": "network",
                "target": "集群整体",
                "metric_name": "网络流量",
                "direction": "稳定",
                "change_percent": 0,
                "start_value": round(network_rx.get("min", 0) + network_tx.get("min", 0), 2) if network_rx.get("min") is not None else None,
                "end_value": round((network_rx.get("current") or 0) + (network_tx.get("current") or 0), 2),
                "analysis": f"集群整体网络流量分析：接收平均 {round(rx_avg, 2) if rx_avg else '-'} Mbps，发送平均 {round(tx_avg, 2) if tx_avg else '-'} Mbps。{busy_description}分析时段：{period_hours} 小时。",
                "analyzed_at": datetime.now().isoformat(),
            })
        
        # 收集所有 Pod 的趋势
        pod_trends = []
        
        for metric in cpu_metrics_list:
            trend_data = self._calculate_trend(metric)
            if trend_data:
                stats = self._calculate_stats(metric)
                pod_name = metric.get("labels", {}).get("pod", "unknown")
                
                # 限制最大值不超过 100%
                stats_max = min(stats["max"], 100)
                
                # 计算时间序列数据点
                data_points = []
                values = metric.get("values", [])
                for ts, val in values:
                    # 限制每个数据点不超过 100%
                    val_clamped = min(val, 100)
                    data_points.append({
                        "timestamp": datetime.fromtimestamp(ts).isoformat(),
                        "value": round(val_clamped, 2),
                    })
                
                # 识别高峰时段
                peak_times = []
                if data_points:
                    sorted_points = sorted(data_points, key=lambda x: x.get("value", 0), reverse=True)
                    top_points = sorted_points[:3]
                    for p in top_points:
                        if p.get("value", 0) > stats["avg"] * 1.5:
                            peak_times.append(p.get("timestamp"))
                
                peak_description = ""
                if peak_times:
                    peak_description = f"检测到高峰时段：{', '.join(peak_times[:2])}"
                
                pod_trends.append({
                    "type": "cpu",
                    "target": pod_name,
                    "metric_name": "CPU 使用率",
                    "direction": trend_data["direction"],
                    "change_percent": round(trend_data["change_rate"], 2),
                    "start_value": round(stats["min"], 2),
                    "end_value": round(stats_max, 2),
                    "avg_value": round(stats["avg"], 2),
                    "data_points": data_points,
                    "analysis": f"Pod {pod_name} 的 CPU 使用率呈{trend_data['direction']}趋势，变化率 {round(trend_data['change_rate'], 2)}%。平均使用率 {round(stats['avg'], 2)}%，峰值 {round(stats_max, 2)}%。{peak_description}",
                    "analyzed_at": datetime.now().isoformat(),
                })
        
        for metric in memory_metrics_list:
            trend_data = self._calculate_trend(metric)
            if trend_data:
                stats = self._calculate_stats(metric)
                pod_name = metric.get("labels", {}).get("pod", "unknown")
                
                # 计算时间序列数据点
                data_points = []
                values = metric.get("values", [])
                for ts, val in values:
                    data_points.append({
                        "timestamp": datetime.fromtimestamp(ts).isoformat(),
                        "value": round(val, 2),
                    })
                
                pod_trends.append({
                    "type": "memory",
                    "target": pod_name,
                    "metric_name": "内存使用率",
                    "direction": trend_data["direction"],
                    "change_percent": round(trend_data["change_rate"], 2),
                    "start_value": round(stats["min"], 2),
                    "end_value": round(stats["max"], 2),
                    "avg_value": round(stats["avg"], 2),
                    "data_points": data_points,
                    "analysis": f"Pod {pod_name} 的内存使用率呈{trend_data['direction']}趋势，变化率 {round(trend_data['change_rate'], 2)}%。平均使用率 {round(stats['avg'], 2)}%，峰值 {round(stats['max'], 2)}%。",
                    "analyzed_at": datetime.now().isoformat(),
                })
        
        # 按变化率绝对值排序，只保留最显著的趋势
        pod_trends.sort(key=lambda x: abs(x.get("change_percent", 0)), reverse=True)
        trends.extend(pod_trends[:10])  # 最多保留 10 个 Pod 级别的趋势
        
        # 添加整体业务趋势分析
        overall_analysis = self._generate_overall_trend_analysis(metrics_data, period_hours)
        if overall_analysis:
            trends.insert(0, overall_analysis)
        
        return trends
    
    def _generate_overall_trend_analysis(
        self,
        metrics_data: Dict[str, Any],
        period_hours: int,
    ) -> Optional[Dict[str, Any]]:
        """
        生成整体业务趋势分析
        
        Args:
            metrics_data: 指标数据（包含转换后的 cpu_usage, memory_usage）
            period_hours: 分析时段（小时）
            
        Returns:
            Optional[Dict[str, Any]]: 整体趋势分析
        """
        original_data = metrics_data.get("original_data", {})
        network_data = original_data.get("network", {})
        
        # 使用转换后的数据计算 CPU 趋势变化率（百分比格式）
        cpu_metrics_list = metrics_data.get("cpu_usage", [])
        
        # 从网络数据获取流量信息
        network_summary = network_data.get("summary", {})
        network_rx = network_summary.get("receive", {}) if network_summary else {}
        network_tx = network_summary.get("transmit", {}) if network_summary else {}
        
        total_network = (network_rx.get("avg") or 0) + (network_tx.get("avg") or 0)
        
        # 基于转换后的 CPU 数据计算趋势变化率
        cpu_trend = 0
        if cpu_metrics_list and len(cpu_metrics_list) > 0:
            first_metric = cpu_metrics_list[0]
            trend_data = self._calculate_trend(first_metric)
            if trend_data:
                cpu_trend = trend_data["change_rate"]
        
        # 判断业务趋势
        trend_direction = "稳定"
        trend_analysis_parts = []
        
        if cpu_trend > 10:
            trend_direction = "上升"
            trend_analysis_parts.append("CPU 使用率呈明显上升趋势")
        elif cpu_trend < -10:
            trend_direction = "下降"
            trend_analysis_parts.append("CPU 使用率呈明显下降趋势")
        
        if total_network > 50:
            trend_analysis_parts.append(f"网络流量较高（{round(total_network, 2)} Mbps），业务活动频繁")
        elif total_network > 10:
            trend_analysis_parts.append(f"网络流量适中（{round(total_network, 2)} Mbps），业务活动正常")
        else:
            trend_analysis_parts.append(f"网络流量较低（{round(total_network, 2)} Mbps），业务活动较少")
        
        # 分析时间段特征
        time_description = f"分析时段：过去 {period_hours} 小时"
        if period_hours >= 168:
            time_description = f"分析时段：过去 7 天"
        elif period_hours >= 24:
            time_description = f"分析时段：过去 {period_hours // 24} 天"
        
        analysis_text = "。".join([time_description] + trend_analysis_parts) + "。"
        
        return {
            "type": "overall",
            "target": "业务整体",
            "metric_name": "业务趋势",
            "direction": trend_direction,
            "change_percent": round(cpu_trend, 2) if cpu_trend is not None else 0,
            "analysis": analysis_text,
            "prediction": self._generate_trend_prediction(cpu_trend, total_network),
            "analyzed_at": datetime.now().isoformat(),
        }
    
    def _generate_trend_prediction(
        self,
        cpu_trend: float,
        network_traffic: float,
    ) -> str:
        """
        生成趋势预测
        
        Args:
            cpu_trend: CPU 趋势变化率
            network_traffic: 网络流量
            
        Returns:
            str: 预测描述
        """
        predictions = []
        
        if cpu_trend > 10:
            predictions.append("如果 CPU 使用率持续上升，需要考虑扩容或优化性能热点")
        elif cpu_trend > 5:
            predictions.append("CPU 使用率有上升趋势，建议加强监控")
        elif cpu_trend < -10:
            predictions.append("CPU 使用率呈下降趋势，资源可能存在过剩")
        
        if network_traffic > 100:
            predictions.append("高网络流量可能导致带宽瓶颈，建议检查网络配置")
        elif network_traffic > 50:
            predictions.append("网络流量较高，关注是否存在异常数据传输")
        
        if not predictions:
            predictions.append("当前趋势稳定，建议持续监控")
        
        return "。".join(predictions) + "。"
    
    def _generate_suggestions(
        self,
        bottlenecks: List[Dict[str, Any]],
        trends: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        生成基础的优化建议
        
        Args:
            bottlenecks: 瓶颈列表
            trends: 趋势列表
            
        Returns:
            List[Dict[str, Any]]: 建议列表
        """
        suggestions = []
        
        # 基于瓶颈生成建议
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "cpu":
                suggestions.append({
                    "id": f"cpu_suggestion_{bottleneck['target']}",
                    "category": "cpu_optimization",
                    "priority": bottleneck["severity"],
                    "target": bottleneck["target"],
                    "action": "检查代码逻辑，优化 CPU 密集型操作",
                    "details": [
                        "分析应用代码中的循环和计算密集型操作",
                        "检查是否存在死循环或资源竞争",
                        "考虑水平扩容增加 Pod 副本数",
                        "检查是否需要调整 CPU 资源限制",
                    ],
                    "description": f"Pod {bottleneck['target']} 的 CPU 使用率持续高于阈值，建议进行代码优化或扩容。",
                })
            elif bottleneck["type"] == "memory":
                suggestions.append({
                    "id": f"memory_suggestion_{bottleneck['target']}",
                    "category": "memory_optimization",
                    "priority": bottleneck["severity"],
                    "target": bottleneck["target"],
                    "action": "检查内存泄漏，优化内存使用",
                    "details": [
                        "分析应用的内存使用模式",
                        "检查是否存在内存泄漏",
                        "检查缓存策略是否合理",
                        "考虑增加内存资源限制或水平扩容",
                    ],
                    "description": f"Pod {bottleneck['target']} 的内存使用率持续高于阈值，建议检查内存泄漏或增加资源。",
                })
        
        # 基于趋势生成建议
        for trend in trends:
            change_rate = trend.get("change_rate") or trend.get("change_percent", 0)
            if trend["direction"] == "上升" and change_rate > 10:
                suggestions.append({
                    "id": f"trend_suggestion_{trend['target']}_{trend['type']}",
                    "category": "capacity_planning",
                    "priority": "medium",
                    "target": trend["target"],
                    "action": "关注资源使用增长趋势",
                    "details": [
                        "监控资源使用的持续增长",
                        "提前规划扩容计划",
                        "评估是否需要优化资源使用",
                    ],
                    "description": f"Pod {trend['target']} 的{trend['type']}使用率呈快速上升趋势（{change_rate}%），建议提前规划扩容。",
                })
        
        # 如果没有任何问题，添加通用建议
        if not suggestions:
            suggestions.append({
                "id": "general_maintenance",
                "category": "general",
                "priority": "low",
                "target": "cluster",
                "action": "保持常规监控和维护",
                "details": [
                    "持续监控集群资源使用情况",
                    "定期检查应用性能指标",
                    "保持操作系统和应用依赖的更新",
                ],
                "description": "当前集群资源使用正常，建议保持常规监控和维护。",
            })
        
        return suggestions
    
    # ============================================================================
    # LLM 深度分析方法
    # ============================================================================
    
    def _llm_analysis(
        self,
        metrics_data: Dict[str, Any],
        rule_result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        LLM 深度分析
        
        Args:
            metrics_data: 原始指标数据
            rule_result: 规则分析结果
            
        Returns:
            Optional[Dict[str, Any]]: LLM 分析结果，失败则返回 None
        """
        if not self.agent:
            logger.warning("LLM 客户端未初始化，跳过 LLM 分析")
            return None
        
        logger.debug("开始执行 LLM 深度分析")
        
        try:
            # 1. 构建指标摘要
            metrics_summary = self._build_metrics_summary(metrics_data)
            
            # 2. 构建 Prompt
            prompt = self._build_prompt(metrics_summary, rule_result)
            
            # 3. 调用 LLM
            response = self.agent.chat(prompt)
            
            # 4. 解析 LLM 响应
            llm_result = self._parse_llm_response(response.content)
            
            if llm_result:
                logger.info("LLM 分析成功")
                return llm_result
            else:
                logger.warning("无法解析 LLM 响应，使用规则分析降级")
                return None
                
        except Exception as e:
            logger.error(f"LLM 分析执行异常: {e}")
            return None
    
    def _build_prompt(self, metrics_summary: str, rule_result: Dict[str, Any]) -> str:
        """
        构建适合分析报告的 Prompt
        
        Args:
            metrics_summary: 指标摘要
            rule_result: 规则分析结果
            
        Returns:
            str: 构建好的 Prompt
        """
        rule_summary = json.dumps(rule_result, ensure_ascii=False, indent=2)
        
        return f"""你是一个专业的 Kubernetes 运维专家和性能分析师。请根据以下指标数据和规则分析结果，进行深度业务分析。

## 指标数据摘要
{metrics_summary}

## 规则分析结果
{rule_summary}

## 分析要求
1. 请结合规则分析结果，进行更深入的根因分析
2. 识别潜在的性能风险点
3. 提供更具体的优化建议
4. 分析业务趋势的可能原因

## 输出格式要求（严格使用 JSON 格式）
{{
  "cluster_health": {{
    "status": "healthy|warning|critical",
    "score": 0-100,
    "analysis": "健康状态详细分析"
  }},
  "bottlenecks": [
    {{
      "type": "cpu|memory|network|storage",
      "target": "影响的 Pod/Node/Service",
      "severity": "high|medium|low",
      "root_cause": "根因分析",
      "impact": "影响范围",
      "description": "详细描述"
    }}
  ],
  "trends": [
    {{
      "type": "cpu|memory",
      "target": "目标资源",
      "direction": "上升|下降|稳定",
      "analysis": "趋势分析",
      "prediction": "未来预测"
    }}
  ],
  "suggestions": [
    {{
      "id": "建议ID",
      "category": "分类",
      "priority": "high|medium|low",
      "action": "建议动作",
      "details": ["详细步骤1", "详细步骤2"],
      "expected_benefit": "预期收益",
      "risk": "风险说明"
    }}
  ],
  "summary": "整体分析摘要"
}}

请直接返回 JSON 格式的分析结果，不要包含其他文字说明。"""
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 输出的 JSON 格式
        
        Args:
            response: LLM 响应文本
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的字典，失败返回 None
        """
        if not response:
            logger.warning("LLM 响应为空")
            return None
        
        # 1. 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 2. 尝试提取 JSON 代码块
        json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        match = re.search(json_pattern, response)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 3. 尝试提取第一个完整的 JSON 对象
        try:
            # 找到第一个 { 和对应的 }
            start = response.find('{')
            if start != -1:
                # 简单的括号匹配
                balance = 0
                in_string = False
                escape = False
                for i, char in enumerate(response[start:]):
                    if escape:
                        escape = False
                        continue
                    if char == '\\':
                        escape = True
                        continue
                    if char == '"':
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            balance += 1
                        elif char == '}':
                            balance -= 1
                            if balance == 0:
                                json_str = response[start:start + i + 1]
                                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        logger.warning(f"无法解析 LLM JSON 响应: {response[:200]}")
        return None
    
    # ============================================================================
    # 辅助方法
    # ============================================================================
    
    def _calculate_stats(self, metric: Dict[str, Any]) -> Dict[str, float]:
        """
        计算基础统计指标（平均、最大、最小）
        
        Args:
            metric: 单个指标数据
            
        Returns:
            Dict[str, float]: 统计结果
        """
        values = metric.get("values", [metric.get("value", 0)])
        if not values:
            return {"avg": 0, "max": 0, "min": 0}
        
        # 处理可能的嵌套值格式
        numeric_values = []
        for v in values:
            if isinstance(v, (int, float)):
                numeric_values.append(float(v))
            elif isinstance(v, list) and len(v) >= 2:
                # Prometheus 格式: [timestamp, value]
                try:
                    numeric_values.append(float(v[1]))
                except (ValueError, TypeError):
                    pass
        
        if not numeric_values:
            return {"avg": 0, "max": 0, "min": 0}
        
        return {
            "avg": sum(numeric_values) / len(numeric_values),
            "max": max(numeric_values),
            "min": min(numeric_values),
        }
    
    def _calculate_trend(self, metric: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        计算变化趋势
        
        Args:
            metric: 单个指标数据
            
        Returns:
            Optional[Dict[str, Any]]: 趋势数据，无法计算返回 None
        """
        values = metric.get("values", [metric.get("value", 0)])
        if len(values) < 2:
            return None
        
        # 提取数值
        numeric_values = []
        for v in values:
            if isinstance(v, (int, float)):
                numeric_values.append(float(v))
            elif isinstance(v, list) and len(v) >= 2:
                try:
                    numeric_values.append(float(v[1]))
                except (ValueError, TypeError):
                    pass
        
        if len(numeric_values) < 2:
            return None
        
        # 计算趋势（简单的首尾比较）
        first = numeric_values[0]
        last = numeric_values[-1]
        
        if first == 0:
            change_rate = 0.0
        else:
            change_rate = ((last - first) / first) * 100
        
        # 确定趋势方向
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
        """
        根据超出阈值的程度确定严重程度
        
        Args:
            value: 当前值
            threshold: 阈值
            
        Returns:
            str: 严重程度（high/medium/low）
        """
        excess = (value - threshold) / threshold * 100
        
        if excess >= 20:
            return "high"
        elif excess >= 10:
            return "medium"
        else:
            return "low"
    
    def _calculate_cluster_health(
        self,
        metrics_data: Dict[str, Any],
        bottlenecks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        计算集群性能指标
        展示集群在过去一段时间内的各项性能指标统计
        
        Args:
            metrics_data: 指标数据
            bottlenecks: 瓶颈列表
            
        Returns:
            Dict[str, Any]: 性能指标数据
        """
        # 计算性能分数（0-100）
        high_count = sum(1 for b in bottlenecks if b["severity"] == "high")
        medium_count = sum(1 for b in bottlenecks if b["severity"] == "medium")
        low_count = sum(1 for b in bottlenecks if b["severity"] == "low")
        
        score = 100 - (high_count * 20) - (medium_count * 10) - (low_count * 5)
        score = max(0, min(100, score))
        
        # 确定性能状态
        if score >= 80:
            status = "healthy"
        elif score >= 50:
            status = "warning"
        else:
            status = "critical"
        
        # 从原始数据中提取详细指标
        original_data = metrics_data.get("original_data", {})
        
        # 从转换后的数据中获取 Pod 级别的聚合数据（与摘要保持一致）
        cpu_metrics_converted = metrics_data.get("cpu_usage", [])
        memory_metrics_converted = metrics_data.get("memory_usage", [])
        
        # 从 nodes 数据中获取节点级别的聚合数据
        nodes_data = original_data.get("nodes", {})
        nodes_list = nodes_data.get("list", [])
        nodes_summary = nodes_data.get("summary", {})
        
        # CPU 指标统计 - 使用转换后的数据（与摘要保持一致）
        cpu_stats = {
            "min": None,
            "max": None,
            "avg": None,
            "trend": None,
        }
        if cpu_metrics_converted:
            cpu_agg_values = []
            for m in cpu_metrics_converted:
                stats = self._calculate_stats(m)
                cpu_agg_values.append(stats["avg"])
            if cpu_agg_values:
                cpu_stats = {
                    "min": round(min(cpu_agg_values), 2),
                    "max": round(max(cpu_agg_values), 2),
                    "avg": round(sum(cpu_agg_values) / len(cpu_agg_values), 2),
                    "trend": None,
                }
        # 如果转换后的数据没有，尝试从原始数据获取
        if cpu_stats["avg"] is None:
            cpu_data = original_data.get("cpu", {})
            cpu_summary = cpu_data.get("summary", {})
            if cpu_summary.get("avg") is not None:
                # CPU 原始数据是核数，假设最大使用 4 核，转换为百分比
                max_cores = 4.0
                cpu_stats = {
                    "min": round(min(cpu_summary.get("min", 0), max_cores) / max_cores * 100, 2) if cpu_summary.get("min") is not None else None,
                    "max": round(min(cpu_summary.get("max", 0), max_cores) / max_cores * 100, 2) if cpu_summary.get("max") is not None else None,
                    "avg": round(min(cpu_summary.get("avg", 0), max_cores) / max_cores * 100, 2) if cpu_summary.get("avg") is not None else None,
                    "trend": round(cpu_summary.get("trend", 0), 2) if cpu_summary.get("trend") is not None else None,
                }
        
        # 内存指标统计 - 使用节点级别的数据（更准确）
        memory_stats = {
            "min": None,
            "max": None,
            "avg": None,
            "trend": None,
        }
        # 优先使用节点汇总数据
        if nodes_list:
            node_memory_values = []
            for node in nodes_list:
                node_summary = node.get("summary", {})
                if node_summary.get("memory_pct") is not None:
                    node_memory_values.append(node_summary["memory_pct"])
            if node_memory_values:
                memory_stats = {
                    "min": round(min(node_memory_values), 2),
                    "max": round(max(node_memory_values), 2),
                    "avg": round(sum(node_memory_values) / len(node_memory_values), 2),
                    "trend": None,
                }
        # 如果节点数据没有，使用转换后的数据（与摘要保持一致）
        if memory_stats["avg"] is None and memory_metrics_converted:
            mem_agg_values = []
            for m in memory_metrics_converted:
                stats = self._calculate_stats(m)
                mem_agg_values.append(stats["avg"])
            if mem_agg_values:
                memory_stats = {
                    "min": round(min(mem_agg_values), 2),
                    "max": round(max(mem_agg_values), 2),
                    "avg": round(sum(mem_agg_values) / len(mem_agg_values), 2),
                    "trend": None,
                }
        
        # 网络指标统计
        network_data = original_data.get("network", {})
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
        
        # 磁盘指标统计（从节点数据）
        disk_stats = {
            "min": None,
            "max": None,
            "avg": None,
        }
        disk_values = []
        for node in nodes_list:
            for disk in node.get("disk", []):
                if disk.get("avg_pct") is not None:
                    disk_values.append(disk["avg_pct"])
        if disk_values:
            disk_stats = {
                "min": round(min(disk_values), 2),
                "max": round(max(disk_values), 2),
                "avg": round(sum(disk_values) / len(disk_values), 2),
            }
        
        # 系统负载统计 - 使用 CPU 使用率作为负载参考
        load_stats = {
            "min": None,
            "max": None,
            "avg": None,
        }
        if cpu_stats.get("avg") is not None:
            load_stats = {
                "min": cpu_stats.get("min"),
                "max": cpu_stats.get("max"),
                "avg": cpu_stats.get("avg"),
            }
        
        # 分析时间段
        time_range = original_data.get("time_range", {})
        analysis_period = None
        if time_range.get("start") and time_range.get("end"):
            analysis_period = f"{time_range['start']} ~ {time_range['end']}"
        
        # 计算平均网络带宽使用率
        network_bandwidth_pct = None
        if network_stats.get("total_current") is not None:
            network_bandwidth_pct = round(network_stats["total_current"], 2)
        
        # 生成详细分析描述
        analysis_parts = []
        if status == "healthy":
            analysis_parts.append(f"集群整体性能良好（得分: {score}）")
        elif status == "warning":
            analysis_parts.append(f"集群存在一些性能问题（得分: {score}），检测到 {len(bottlenecks)} 个瓶颈")
        else:
            analysis_parts.append(f"集群存在严重性能瓶颈（得分: {score}），检测到 {len(bottlenecks)} 个瓶颈")
        
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
            "bottleneck_count": len(bottlenecks),
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
    
    def _generate_basic_summary(
        self,
        bottlenecks: List[Dict[str, Any]],
        trends: List[Dict[str, Any]],
        cluster_health: Dict[str, Any],
    ) -> str:
        """
        生成基础摘要
        
        Args:
            bottlenecks: 瓶颈列表
            trends: 趋势列表
            cluster_health: 集群健康概览
            
        Returns:
            str: 摘要文本
        """
        parts = []
        
        # 健康状态
        parts.append(f"集群健康状态: {cluster_health['status']}（分数: {cluster_health['score']}）")
        
        # 瓶颈信息
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
        
        # 趋势信息
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
    
    def _build_metrics_summary(self, metrics_data: Dict[str, Any]) -> str:
        """
        构建指标摘要（用于 LLM Prompt）
        
        Args:
            metrics_data: 原始指标数据
            
        Returns:
            str: 指标摘要文本
        """
        summary_parts = []
        
        # CPU 指标摘要
        cpu_metrics = metrics_data.get("cpu_usage", [])
        if cpu_metrics:
            summary_parts.append(f"## CPU 使用率指标（共 {len(cpu_metrics)} 个 Pod）")
            for metric in cpu_metrics:
                pod_name = metric.get("labels", {}).get("pod", "unknown")
                stats = self._calculate_stats(metric)
                trend = self._calculate_trend(metric)
                trend_info = ""
                if trend:
                    trend_info = f", 趋势: {trend['direction']} ({trend['change_rate']:.1f}%)"
                summary_parts.append(
                    f"- {pod_name}: 平均 {stats['avg']:.1f}%, 最高 {stats['max']:.1f}%, 最低 {stats['min']:.1f}%{trend_info}"
                )
        
        # 内存指标摘要
        memory_metrics = metrics_data.get("memory_usage", [])
        if memory_metrics:
            summary_parts.append(f"\n## 内存使用率指标（共 {len(memory_metrics)} 个 Pod）")
            for metric in memory_metrics:
                pod_name = metric.get("labels", {}).get("pod", "unknown")
                stats = self._calculate_stats(metric)
                trend = self._calculate_trend(metric)
                trend_info = ""
                if trend:
                    trend_info = f", 趋势: {trend['direction']} ({trend['change_rate']:.1f}%)"
                summary_parts.append(
                    f"- {pod_name}: 平均 {stats['avg']:.1f}%, 最高 {stats['max']:.1f}%, 最低 {stats['min']:.1f}%{trend_info}"
                )
        
        if not summary_parts:
            return "暂无指标数据"
        
        return "\n".join(summary_parts)
    
    def _build_basic_result(self, rule_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建基础结果（规则分析降级时使用）
        
        Args:
            rule_result: 规则分析结果
            
        Returns:
            Dict[str, Any]: 完整的基础结果
        """
        return {
            "status": AnalysisStatus.BASIC,
            "cluster_health": rule_result["cluster_health"],
            "bottlenecks": rule_result["bottlenecks"],
            "trends": rule_result["trends"],
            "suggestions": rule_result["suggestions"],
            "summary": rule_result["summary"],
            "analysis_method": "rule_based",
        }
    
    def _merge_results(
        self,
        rule_result: Dict[str, Any],
        llm_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        合并规则分析和 LLM 分析结果
        
        Args:
            rule_result: 规则分析结果
            llm_result: LLM 分析结果
            
        Returns:
            Dict[str, Any]: 合并后的结果
        """
        merged = {
            "status": AnalysisStatus.COMPLETED,
            "analysis_method": "llm_enhanced",
        }
        
        def merge_dict(rule_dict: Dict[str, Any], llm_dict: Dict[str, Any]) -> Dict[str, Any]:
            """
            合并两个字典，优先使用 LLM 的非空值
            """
            result = {}
            for key, value in rule_dict.items():
                result[key] = value
            if llm_dict:
                for key, value in llm_dict.items():
                    if value is not None and (value != "" if isinstance(value, str) else True):
                        result[key] = value
            return result
        
        def merge_bottlenecks(rule_bottlenecks: List[Dict], llm_bottlenecks: List[Dict]) -> List[Dict]:
            """
            合并瓶颈列表，用 LLM 的详细信息补充规则分析的基础数据
            """
            if not llm_bottlenecks:
                return rule_bottlenecks
            
            merged_bottlenecks = []
            for rule_b in rule_bottlenecks:
                target = rule_b.get("target", "")
                b_type = rule_b.get("type", "")
                
                matching_llm = None
                for llm_b in llm_bottlenecks:
                    if llm_b.get("target") == target and llm_b.get("type") == b_type:
                        matching_llm = llm_b
                        break
                
                if matching_llm:
                    merged_b = merge_dict(rule_b, matching_llm)
                    merged_bottlenecks.append(merged_b)
                else:
                    merged_bottlenecks.append(rule_b)
            
            for llm_b in llm_bottlenecks:
                target = llm_b.get("target", "")
                b_type = llm_b.get("type", "")
                exists = any(
                    b.get("target") == target and b.get("type") == b_type
                    for b in merged_bottlenecks
                )
                if not exists:
                    merged_bottlenecks.append(llm_b)
            
            return merged_bottlenecks
        
        def merge_trends(rule_trends: List[Dict], llm_trends: List[Dict]) -> List[Dict]:
            """
            合并趋势列表，用 LLM 的详细信息补充规则分析的基础数据
            """
            if not llm_trends:
                return rule_trends
            
            merged_trends = []
            for rule_t in rule_trends:
                target = rule_t.get("target", "")
                t_type = rule_t.get("type", "")
                
                matching_llm = None
                for llm_t in llm_trends:
                    if llm_t.get("target") == target and llm_t.get("type") == t_type:
                        matching_llm = llm_t
                        break
                
                if matching_llm:
                    merged_t = merge_dict(rule_t, matching_llm)
                    merged_trends.append(merged_t)
                else:
                    merged_trends.append(rule_t)
            
            for llm_t in llm_trends:
                target = llm_t.get("target", "")
                t_type = llm_t.get("type", "")
                exists = any(
                    t.get("target") == target and t.get("type") == t_type
                    for t in merged_trends
                )
                if not exists:
                    merged_trends.append(llm_t)
            
            return merged_trends
        
        rule_health = rule_result.get("cluster_health", {})
        llm_health = llm_result.get("cluster_health", {})
        merged["cluster_health"] = merge_dict(rule_health, llm_health)
        
        rule_bottlenecks = rule_result.get("bottlenecks", [])
        llm_bottlenecks = llm_result.get("bottlenecks", [])
        merged["bottlenecks"] = merge_bottlenecks(rule_bottlenecks, llm_bottlenecks)
        
        rule_trends = rule_result.get("trends", [])
        llm_trends = llm_result.get("trends", [])
        merged["trends"] = merge_trends(rule_trends, llm_trends)
        
        rule_suggestions = rule_result.get("suggestions", [])
        llm_suggestions = llm_result.get("suggestions", [])
        merged["suggestions"] = llm_suggestions if llm_suggestions else rule_suggestions
        
        llm_summary = llm_result.get("summary")
        rule_summary = rule_result.get("summary", "")
        merged["summary"] = llm_summary if llm_summary else rule_summary
        
        return merged


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
