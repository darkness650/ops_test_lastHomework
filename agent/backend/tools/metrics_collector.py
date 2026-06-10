"""
Prometheus 历史数据采集器模块
提供微服务集群历史指标数据采集和分析功能
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tools.prometheus import get_prometheus_client, PrometheusClient

# 获取日志记录器
logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Prometheus 历史数据采集器
    采集指定时间段的各类指标数据，支持时间序列分析
    """

    # 采样步长配置
    STEP_CONFIG = {
        24: "5m",  # 24小时：5分钟步长
        168: "1h",  # 7天：1小时步长（24*7=168）
        720: "4h",  # 30天：4小时步长（24*30=720）
    }

    def __init__(self):
        """
        初始化指标采集器
        复用现有的 PrometheusClient
        """
        self.prometheus_client: PrometheusClient = get_prometheus_client()
        logger.info("MetricsCollector 初始化完成")

    def _get_step(self, period_hours: int) -> str:
        """
        根据时长计算采样步长

        Args:
            period_hours: 时间范围（小时）

        Returns:
            str: 采样步长，如 "5m"、"1h"、"4h"
        """
        # 精确匹配：24h、7d（168h）、30d（720h）
        if period_hours <= 24:
            return "5m"
        elif period_hours <= 168:
            return "1h"
        else:
            return "4h"

    def is_available(self) -> bool:
        """
        检查 Prometheus 是否可用

        Returns:
            bool: 是否可用
        """
        try:
            return self.prometheus_client.is_available()
        except Exception as e:
            logger.warning(f"检查 Prometheus 可用性时出错: {e}")
            return False

    def _build_namespace_filter(self, namespace: Optional[str]) -> str:
        """
        构建命名空间过滤条件

        Args:
            namespace: 命名空间名称

        Returns:
            str: PromQL 过滤条件字符串
        """
        if namespace:
            return f'namespace="{namespace}",'
        return ""

    def _process_time_series(
        self,
        result: Dict[str, Any],
        value_key: str = "value",
    ) -> List[Dict[str, Any]]:
        """
        处理 Prometheus 范围查询结果，转换为时间序列数据

        Args:
            result: Prometheus 查询结果
            value_key: 数值键名

        Returns:
            List[Dict[str, Any]]: 处理后的时间序列数据
        """
        time_series = []
        for series in result.get("result", []):
            metric = series.get("metric", {})
            values = series.get("values", [])

            data_points = []
            for ts, val in values:
                data_points.append({
                    "timestamp": datetime.fromtimestamp(float(ts)).isoformat(),
                    value_key: float(val),
                })

            time_series.append({
                "metric": metric,
                "data_points": data_points,
                "start_value": float(values[0][1]) if values else None,
                "end_value": float(values[-1][1]) if values else None,
                "min_value": min(float(v[1]) for v in values) if values else None,
                "max_value": max(float(v[1]) for v in values) if values else None,
                "avg_value": (
                    sum(float(v[1]) for v in values) / len(values)
                    if values else None
                ),
            })

        return time_series

    def _calculate_summary(
        self,
        time_series: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        计算时间序列的汇总统计信息

        Args:
            time_series: 时间序列数据

        Returns:
            Dict[str, Any]: 汇总统计信息
        """
        if not time_series:
            return {
                "min": None,
                "max": None,
                "avg": None,
                "current": None,
                "trend": None,
            }

        all_values = []
        current_values = []
        for series in time_series:
            for dp in series["data_points"]:
                # 获取数值（跳过 timestamp 键，取非 timestamp 的数值）
                value = None
                for key, val in dp.items():
                    if key != "timestamp" and isinstance(val, (int, float)):
                        value = val
                        break
                if value is not None:
                    all_values.append(value)
            if series["end_value"] is not None:
                current_values.append(series["end_value"])

        if not all_values:
            return {
                "min": None,
                "max": None,
                "avg": None,
                "current": None,
                "trend": None,
            }

        summary = {
            "min": min(all_values),
            "max": max(all_values),
            "avg": sum(all_values) / len(all_values),
            "current": sum(current_values) if current_values else None,
            "trend": None,
        }

        # 计算趋势（比较前10%和后10%数据的平均值）
        if len(all_values) >= 10:
            split_point = len(all_values) // 10
            first_10 = all_values[:split_point]
            last_10 = all_values[-split_point:]
            first_avg = sum(first_10) / len(first_10)
            last_avg = sum(last_10) / len(last_10)
            if first_avg > 0:
                summary["trend"] = ((last_avg - first_avg) / first_avg) * 100

        return summary

    def collect_cpu(
        self,
        start: datetime,
        end: datetime,
        namespace: Optional[str],
    ) -> Dict[str, Any]:
        """
        采集 CPU 使用率指标

        Args:
            start: 开始时间
            end: 结束时间
            namespace: 命名空间过滤（可选）

        Returns:
            Dict[str, Any]: CPU 指标数据，如果数据获取失败，error 字段将包含错误信息
        """
        try:
            step = self._get_step(int((end - start).total_seconds() / 3600))
            ns_filter = self._build_namespace_filter(namespace)

            cpu_total_result = None
            pod_cpu_result = None

            # 尝试多个查询策略，增加兼容性
            cpu_queries = [
                # 策略 1：标准 Kubernetes cAdvisor 查询
                (
                    f'sum(rate(container_cpu_usage_seconds_total{{{ns_filter}'
                    f'container!="",container!="POD"}}[{step}]))'
                ),
                # 策略 2：不限制 container 标签的查询
                f'sum(rate(container_cpu_usage_seconds_total{{{ns_filter}}}[{step}]))',
                # 策略 3：使用 node-exporter 的节点 CPU 指标
                f'sum(1 - rate(node_cpu_seconds_total{{mode="idle"}}[{step}]))',
            ]

            for query in cpu_queries:
                try:
                    result = self.prometheus_client.query_range(
                        query=query,
                        start=start,
                        end=end,
                        step=step,
                    )
                    if result and result.get("result") and len(result["result"]) > 0:
                        cpu_total_result = result
                        logger.info(f"CPU 查询成功: {query[:60]}...")
                        break
                except Exception:
                    continue

            # 查询按 Pod 聚合的 CPU 使用
            pod_cpu_queries = [
                f'sum by (pod) (rate(container_cpu_usage_seconds_total{{{ns_filter}'
                f'container!="",container!="POD"}}[{step}]))',
                f'sum by (pod) (rate(container_cpu_usage_seconds_total{{{ns_filter}}}[{step}]))',
            ]

            for query in pod_cpu_queries:
                try:
                    result = self.prometheus_client.query_range(
                        query=query,
                        start=start,
                        end=end,
                        step=step,
                    )
                    if result and result.get("result") and len(result["result"]) > 0:
                        pod_cpu_result = result
                        break
                except Exception:
                    continue

            # 处理时间序列
            time_series = self._process_time_series(cpu_total_result) if cpu_total_result else []
            pod_time_series = self._process_time_series(pod_cpu_result) if pod_cpu_result else []

            # 检查是否有有效数据
            has_data = len(time_series) > 0
            if not has_data:
                logger.warning("CPU 指标采集：所有查询策略都返回空结果")
                return {
                    "summary": {
                        "min": None,
                        "max": None,
                        "avg": None,
                        "current": None,
                        "trend": None,
                    },
                    "time_series": [],
                    "top_pods": [],
                    "error": "CPU 指标获取失败：Prometheus 查询返回空结果，请检查是否有相关指标数据",
                }

            # 计算 Top Pods（基于平均值）
            top_pods = []
            for series in pod_time_series:
                if series["avg_value"] is not None:
                    top_pods.append({
                        "pod": series["metric"].get("pod"),
                        "avg_cores": round(series["avg_value"], 4),
                        "max_cores": round(series["max_value"], 4),
                        "current_cores": round(series["end_value"], 4),
                    })

            top_pods = sorted(top_pods, key=lambda x: x["avg_cores"], reverse=True)[:10]

            # 计算汇总
            summary = self._calculate_summary(time_series)
            if summary.get("current") is not None:
                summary["current"] = round(summary["current"], 4)
            if summary.get("avg") is not None:
                summary["avg"] = round(summary["avg"], 4)

            logger.info(f"CPU 指标采集完成，时间范围: {start} - {end}")

            return {
                "summary": summary,
                "time_series": time_series,
                "top_pods": top_pods,
            }

        except Exception as e:
            logger.error(f"CPU 指标采集失败: {e}")
            return {
                "summary": {
                    "min": None,
                    "max": None,
                    "avg": None,
                    "current": None,
                    "trend": None,
                },
                "time_series": [],
                "top_pods": [],
                "error": f"CPU 指标获取失败: {str(e)}",
            }

    def collect_memory(
        self,
        start: datetime,
        end: datetime,
        namespace: Optional[str],
    ) -> Dict[str, Any]:
        """
        采集内存使用率指标

        Args:
            start: 开始时间
            end: 结束时间
            namespace: 命名空间过滤（可选）

        Returns:
            Dict[str, Any]: 内存指标数据，如果数据获取失败，error 字段将包含错误信息
        """
        try:
            step = self._get_step(int((end - start).total_seconds() / 3600))
            ns_filter = self._build_namespace_filter(namespace)

            mem_total_result = None
            pod_mem_result = None

            # 尝试多个查询策略，增加兼容性
            mem_queries = [
                # 策略 1：标准 Kubernetes cAdvisor working set 查询
                f'sum(container_memory_working_set_bytes{{{ns_filter}'
                f'container!="",container!="POD"}})',
                # 策略 2：不限制 container 标签的查询
                f'sum(container_memory_working_set_bytes{{{ns_filter}}})',
                # 策略 3：使用 RSS 内存
                f'sum(container_memory_rss{{{ns_filter}'
                f'container!="",container!="POD"}})',
                # 策略 4：使用节点内存指标
                'sum(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)',
            ]

            for query in mem_queries:
                try:
                    result = self.prometheus_client.query_range(
                        query=query,
                        start=start,
                        end=end,
                        step=step,
                    )
                    if result and result.get("result") and len(result["result"]) > 0:
                        mem_total_result = result
                        logger.info(f"Memory 查询成功: {query[:60]}...")
                        break
                except Exception:
                    continue

            # 查询按 Pod 聚合的内存使用
            pod_mem_queries = [
                f'sum by (pod) (container_memory_working_set_bytes{{{ns_filter}'
                f'container!="",container!="POD"}})',
                f'sum by (pod) (container_memory_working_set_bytes{{{ns_filter}}})',
                f'sum by (pod) (container_memory_rss{{{ns_filter}'
                f'container!="",container!="POD"}})',
            ]

            for query in pod_mem_queries:
                try:
                    result = self.prometheus_client.query_range(
                        query=query,
                        start=start,
                        end=end,
                        step=step,
                    )
                    if result and result.get("result") and len(result["result"]) > 0:
                        pod_mem_result = result
                        break
                except Exception:
                    continue

            # 检查是否有有效数据
            if mem_total_result is None:
                logger.warning("Memory 指标采集：所有查询策略都返回空结果")
                return {
                    "summary": {
                        "min": None,
                        "max": None,
                        "avg": None,
                        "current": None,
                        "trend": None,
                    },
                    "time_series": [],
                    "top_pods": [],
                    "error": "内存指标获取失败：Prometheus 查询返回空结果，请检查是否有相关指标数据",
                }

            # 处理时间序列（转换为 GB）
            def convert_to_gb(data_point):
                result = {}
                for key, value in data_point.items():
                    if key == "timestamp":
                        result[key] = value
                    else:
                        result[key] = round(value / (1024 ** 3), 4)
                return result

            time_series = []
            for series in self._process_time_series(mem_total_result):
                series["data_points"] = [
                    convert_to_gb(dp) for dp in series["data_points"]
                ]
                if series["start_value"] is not None:
                    series["start_value"] = round(series["start_value"] / (1024 ** 3), 4)
                if series["end_value"] is not None:
                    series["end_value"] = round(series["end_value"] / (1024 ** 3), 4)
                if series["min_value"] is not None:
                    series["min_value"] = round(series["min_value"] / (1024 ** 3), 4)
                if series["max_value"] is not None:
                    series["max_value"] = round(series["max_value"] / (1024 ** 3), 4)
                if series["avg_value"] is not None:
                    series["avg_value"] = round(series["avg_value"] / (1024 ** 3), 4)
                time_series.append(series)

            # 处理 Pod 内存数据
            top_pods = []
            if pod_mem_result:
                for series in self._process_time_series(pod_mem_result):
                    if series["avg_value"] is not None:
                        top_pods.append({
                            "pod": series["metric"].get("pod"),
                            "avg_gb": round(series["avg_value"] / (1024 ** 3), 4),
                            "max_gb": round(series["max_value"] / (1024 ** 3), 4),
                            "current_gb": round(series["end_value"] / (1024 ** 3), 4),
                        })

            top_pods = sorted(top_pods, key=lambda x: x["avg_gb"], reverse=True)[:10]

            # 计算汇总
            summary = self._calculate_summary(time_series)
            if summary.get("current") is not None:
                summary["current"] = round(summary["current"], 4)
            if summary.get("avg") is not None:
                summary["avg"] = round(summary["avg"], 4)

            logger.info(f"内存指标采集完成，时间范围: {start} - {end}")

            return {
                "summary": summary,
                "time_series": time_series,
                "top_pods": top_pods,
            }

        except Exception as e:
            logger.error(f"内存指标采集失败: {e}")
            return {
                "summary": {
                    "min": None,
                    "max": None,
                    "avg": None,
                    "current": None,
                    "trend": None,
                },
                "time_series": [],
                "top_pods": [],
                "error": f"内存指标获取失败: {str(e)}",
            }

    def collect_network(
        self,
        start: datetime,
        end: datetime,
        namespace: Optional[str],
    ) -> Dict[str, Any]:
        """
        采集网络带宽指标

        Args:
            start: 开始时间
            end: 结束时间
            namespace: 命名空间过滤（可选）

        Returns:
            Dict[str, Any]: 网络指标数据，如果数据获取失败，error 字段将包含错误信息
        """
        try:
            step = self._get_step(int((end - start).total_seconds() / 3600))
            ns_filter = self._build_namespace_filter(namespace)

            rx_result = None
            tx_result = None

            # 尝试多个查询策略
            rx_queries = [
                f'sum(rate(container_network_receive_bytes_total{{{ns_filter}'
                f'pod!=""}}[{step}]))',
                f'sum(rate(container_network_receive_bytes_total{{{ns_filter}}}[{step}]))',
            ]

            tx_queries = [
                f'sum(rate(container_network_transmit_bytes_total{{{ns_filter}'
                f'pod!=""}}[{step}]))',
                f'sum(rate(container_network_transmit_bytes_total{{{ns_filter}}}[{step}]))',
            ]

            for query in rx_queries:
                try:
                    result = self.prometheus_client.query_range(
                        query=query,
                        start=start,
                        end=end,
                        step=step,
                    )
                    if result and result.get("result") and len(result["result"]) > 0:
                        rx_result = result
                        logger.info(f"Network RX 查询成功: {query[:60]}...")
                        break
                except Exception:
                    continue

            for query in tx_queries:
                try:
                    result = self.prometheus_client.query_range(
                        query=query,
                        start=start,
                        end=end,
                        step=step,
                    )
                    if result and result.get("result") and len(result["result"]) > 0:
                        tx_result = result
                        logger.info(f"Network TX 查询成功: {query[:60]}...")
                        break
                except Exception:
                    continue

            # 检查是否有有效数据（至少要有一个方向有数据）
            if rx_result is None and tx_result is None:
                logger.warning("Network 指标采集：所有查询策略都返回空结果")
                return {
                    "summary": {
                        "receive": {
                            "min": None,
                            "max": None,
                            "avg": None,
                            "current": None,
                            "trend": None,
                        },
                        "transmit": {
                            "min": None,
                            "max": None,
                            "avg": None,
                            "current": None,
                            "trend": None,
                        },
                        "total_current": None,
                    },
                    "time_series": {
                        "receive": [],
                        "transmit": [],
                    },
                    "error": "网络指标获取失败：Prometheus 查询返回空结果，请检查是否有相关指标数据",
                }

            # 处理接收流量时间序列（转换为 Mbps）
            def convert_to_mbps(data_point):
                result = {}
                for key, value in data_point.items():
                    if key == "timestamp":
                        result[key] = value
                    else:
                        # bytes/s -> Mbps: * 8 / 1024 / 1024
                        result[key] = round(value * 8 / (1024 ** 2), 4)
                return result

            rx_series = []
            if rx_result is not None:
                for series in self._process_time_series(rx_result):
                    series["data_points"] = [
                        convert_to_mbps(dp) for dp in series["data_points"]
                    ]
                    if series["start_value"] is not None:
                        series["start_value"] = round(
                            series["start_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["end_value"] is not None:
                        series["end_value"] = round(
                            series["end_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["min_value"] is not None:
                        series["min_value"] = round(
                            series["min_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["max_value"] is not None:
                        series["max_value"] = round(
                            series["max_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["avg_value"] is not None:
                        series["avg_value"] = round(
                            series["avg_value"] * 8 / (1024 ** 2), 4
                        )
                    rx_series.append(series)

            # 处理发送流量时间序列
            tx_series = []
            if tx_result is not None:
                for series in self._process_time_series(tx_result):
                    series["data_points"] = [
                        convert_to_mbps(dp) for dp in series["data_points"]
                    ]
                    if series["start_value"] is not None:
                        series["start_value"] = round(
                            series["start_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["end_value"] is not None:
                        series["end_value"] = round(
                            series["end_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["min_value"] is not None:
                        series["min_value"] = round(
                            series["min_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["max_value"] is not None:
                        series["max_value"] = round(
                            series["max_value"] * 8 / (1024 ** 2), 4
                        )
                    if series["avg_value"] is not None:
                        series["avg_value"] = round(
                            series["avg_value"] * 8 / (1024 ** 2), 4
                        )
                    tx_series.append(series)

            # 计算汇总
            rx_summary = self._calculate_summary(rx_series)
            tx_summary = self._calculate_summary(tx_series)

            logger.info(f"网络指标采集完成，时间范围: {start} - {end}")

            return {
                "summary": {
                    "receive": rx_summary,
                    "transmit": tx_summary,
                    "total_current": (
                        (rx_summary.get("current") or 0)
                        + (tx_summary.get("current") or 0)
                        if rx_summary.get("current") is not None
                        and tx_summary.get("current") is not None
                        else None
                    ),
                },
                "time_series": {
                    "receive": rx_series,
                    "transmit": tx_series,
                },
            }

        except Exception as e:
            logger.error(f"网络指标采集失败: {e}")
            return {
                "summary": {
                    "receive": {
                        "min": None,
                        "max": None,
                        "avg": None,
                        "current": None,
                        "trend": None,
                    },
                    "transmit": {
                        "min": None,
                        "max": None,
                        "avg": None,
                        "current": None,
                        "trend": None,
                    },
                    "total_current": None,
                },
                "time_series": {
                    "receive": [],
                    "transmit": [],
                },
                "error": str(e),
            }

    def collect_nodes(
        self,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        """
        采集节点资源使用情况

        Args:
            start: 开始时间
            end: 结束时间

        Returns:
            Dict[str, Any]: 节点指标数据
        """
        try:
            step = self._get_step(int((end - start).total_seconds() / 3600))

            # 1. 查询节点 CPU 使用率（排除 idle）
            node_cpu_query = (
                'sum by (instance) (1 - rate(node_cpu_seconds_total{mode="idle"}[5m]))'
            )
            node_cpu_result = self.prometheus_client.query_range(
                query=node_cpu_query,
                start=start,
                end=end,
                step=step,
            )

            # 2. 查询节点内存使用率
            node_mem_query = (
                '1 - sum by (instance) (node_memory_MemAvailable_bytes) / '
                'sum by (instance) (node_memory_MemTotal_bytes)'
            )
            node_mem_result = self.prometheus_client.query_range(
                query=node_mem_query,
                start=start,
                end=end,
                step=step,
            )

            # 3. 查询节点磁盘使用率
            node_disk_query = (
                '1 - sum by (instance, mountpoint) (node_filesystem_avail_bytes) / '
                'sum by (instance, mountpoint) (node_filesystem_size_bytes)'
            )
            try:
                node_disk_result = self.prometheus_client.query_range(
                    query=node_disk_query,
                    start=start,
                    end=end,
                    step=step,
                )
            except Exception:
                node_disk_result = {"result": []}

            # 处理节点数据
            nodes_dict: Dict[str, Dict[str, Any]] = {}

            # 处理 CPU 数据
            for series in self._process_time_series(node_cpu_result):
                instance = series["metric"].get("instance")
                if instance not in nodes_dict:
                    nodes_dict[instance] = {"instance": instance}
                nodes_dict[instance]["cpu"] = {
                    "avg_pct": round(series["avg_value"] * 100, 2)
                    if series["avg_value"] is not None
                    else None,
                    "max_pct": round(series["max_value"] * 100, 2)
                    if series["max_value"] is not None
                    else None,
                    "current_pct": round(series["end_value"] * 100, 2)
                    if series["end_value"] is not None
                    else None,
                    "data_points": series["data_points"] if "data_points" in series else None,
                }

            # 处理内存数据
            for series in self._process_time_series(node_mem_result):
                instance = series["metric"].get("instance")
                if instance not in nodes_dict:
                    nodes_dict[instance] = {"instance": instance}
                nodes_dict[instance]["memory"] = {
                    "avg_pct": round(series["avg_value"] * 100, 2)
                    if series["avg_value"] is not None
                    else None,
                    "max_pct": round(series["max_value"] * 100, 2)
                    if series["max_value"] is not None
                    else None,
                    "current_pct": round(series["end_value"] * 100, 2)
                    if series["end_value"] is not None
                    else None,
                }

            # 处理磁盘数据
            disk_usage: Dict[str, List[Dict[str, Any]]] = {}
            for series in self._process_time_series(node_disk_result):
                instance = series["metric"].get("instance")
                mountpoint = series["metric"].get("mountpoint")
                if instance not in disk_usage:
                    disk_usage[instance] = []
                if series["avg_value"] is not None:
                    disk_usage[instance].append({
                        "mountpoint": mountpoint,
                        "avg_pct": round(series["avg_value"] * 100, 2),
                        "max_pct": round(series["max_value"] * 100, 2)
                        if series["max_value"] is not None
                        else None,
                        "current_pct": round(series["end_value"] * 100, 2)
                        if series["end_value"] is not None
                        else None,
                    })

            # 合并磁盘数据到节点
            for instance, disks in disk_usage.items():
                if instance not in nodes_dict:
                    nodes_dict[instance] = {"instance": instance}
                nodes_dict[instance]["disk"] = disks

            # 转换为列表
            nodes_list = list(nodes_dict.values())

            # 计算集群汇总
            cpu_values = [
                node["cpu"]["avg_pct"]
                for node in nodes_list
                if node.get("cpu", {}).get("avg_pct") is not None
            ]
            mem_values = [
                node["memory"]["avg_pct"]
                for node in nodes_list
                if node.get("memory", {}).get("avg_pct") is not None
            ]

            summary = {
                "total_nodes": len(nodes_list),
                "avg_cpu_pct": round(sum(cpu_values) / len(cpu_values), 2)
                if cpu_values
                else None,
                "avg_memory_pct": round(sum(mem_values) / len(mem_values), 2)
                if mem_values
                else None,
                "max_cpu_node": (
                    max(nodes_list, key=lambda x: x.get("cpu", {}).get("avg_pct") or 0)
                    [ "instance"]
                    if nodes_list
                    else None
                ),
                "max_memory_node": (
                    max(nodes_list, key=lambda x: x.get("memory", {}).get("avg_pct") or 0)
                    [ "instance"]
                    if nodes_list
                    else None
                ),
            }

            logger.info(f"节点指标采集完成，共 {len(nodes_list)} 个节点")

            return {
                "list": nodes_list,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"节点指标采集失败: {e}")
            return {
                "list": [],
                "summary": {
                    "total_nodes": 0,
                    "avg_cpu_pct": None,
                    "avg_memory_pct": None,
                    "max_cpu_node": None,
                    "max_memory_node": None,
                },
                "error": str(e),
            }

    def collect(
        self,
        period_hours: int = 24,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        采集所有指标

        Args:
            period_hours: 时间范围（小时），默认为 24 小时
            namespace: 命名空间过滤（可选）

        Returns:
            Dict[str, Any]: 所有指标数据
        """
        try:
            # 检查 Prometheus 可用性
            if not self.is_available():
                logger.warning("Prometheus 不可用，返回错误信息")
                return {
                    "success": False,
                    "error": "Prometheus 服务不可用",
                    "message": "请检查 Prometheus 连接配置和服务状态",
                    "time_range": None,
                    "cpu": None,
                    "memory": None,
                    "network": None,
                    "nodes": None,
                }

            # 计算时间范围
            end = datetime.now()
            start = end - timedelta(hours=period_hours)

            logger.info(
                f"开始采集指标，时间范围: {start} - {end} "
                f"({period_hours} 小时)，命名空间: {namespace or '所有'}"
            )

            # 采集各类指标
            cpu_data = self.collect_cpu(start, end, namespace)
            memory_data = self.collect_memory(start, end, namespace)
            network_data = self.collect_network(start, end, namespace)
            nodes_data = self.collect_nodes(start, end)

            result = {
                "success": True,
                "time_range": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "period_hours": period_hours,
                    "step": self._get_step(period_hours),
                },
                "cpu": cpu_data,
                "memory": memory_data,
                "network": network_data,
                "nodes": nodes_data,
            }

            logger.info("指标采集完成")
            return result

        except Exception as e:
            logger.error(f"指标采集失败: {e}")
            return {
                "success": False,
                "error": f"指标采集失败: {str(e)}",
                "message": "请检查 Prometheus 服务状态和网络连接",
                "time_range": None,
                "cpu": None,
                "memory": None,
                "network": None,
                "nodes": None,
            }


# 单例模式实例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    获取指标采集器单例

    Returns:
        MetricsCollector: 指标采集器实例
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
