"""
定时轮询调度器模块
基于 APScheduler 实现定时健康监测
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from agents.history import PollingRecord, get_history_store
from agents.anomaly_analyzer import get_anomaly_analyzer


logger = logging.getLogger(__name__)


class PollingScheduler:
    """
    定时轮询调度器
    基于 APScheduler 实现定时健康监测
    """
    
    def __init__(
        self,
        interval_minutes: int = 5,
        max_records: int = 100,
    ):
        """
        初始化轮询调度器
        
        Args:
            interval_minutes: 轮询间隔（分钟）
            max_records: 最大历史记录数
        """
        from config.settings import get_settings
        
        settings = get_settings()
        
        # 使用配置中的间隔，如果没有则使用默认值
        self.interval_minutes = settings.polling_interval_minutes or interval_minutes
        self._scheduler = None
        self._job = None
        self._is_running = False
        self._history_store = get_history_store(max_records=max_records)
        self._execution_count = 0
        
        logger.info(
            f"轮询调度器初始化完成，间隔: {self.interval_minutes} 分钟, "
            f"最大历史记录: {max_records}"
        )
    
    def _init_scheduler(self) -> None:
        """
        延迟初始化调度器
        """
        from apscheduler.schedulers.background import BackgroundScheduler
        
        if self._scheduler is None:
            self._scheduler = BackgroundScheduler()
            logger.info("APScheduler 已初始化")
    
    def _polling_task(
        self,
        namespace: Optional[str] = None,
        deep_analysis: bool = False,
    ) -> None:
        """
        执行轮询任务
        
        Args:
            namespace: 命名空间
            deep_analysis: 是否执行深度分析
        """
        start_time = time.time()
        self._execution_count += 1
        
        logger.info(f"开始第 {self._execution_count} 次轮询...")
        
        try:
            # 执行健康监测
            from agents.engine import quick_health_check, full_analysis
            
            if deep_analysis:
                result_obj = full_analysis(namespace=namespace)
                result = {
                    "status": result_obj.status,
                    "summary": result_obj.summary,
                    "anomaly_count": len(result_obj.anomalies),
                    "anomalies": [a.to_dict() for a in result_obj.anomalies],
                }
            else:
                result = quick_health_check(namespace=namespace)
            
            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000
            
            # 创建记录
            record = PollingRecord(
                status=result.get("status", "normal"),
                summary=result.get("summary", ""),
                anomaly_count=result.get("anomaly_count", 0),
                anomalies=result.get("anomalies", []),
                duration_ms=duration_ms,
            )
            
            # 保存历史记录
            self._history_store.add(record)
            
            # 如果检测到异常，自动触发后台 AI 分析
            if record.anomaly_count > 0:
                try:
                    analyzer = get_anomaly_analyzer()
                    analyzer.analyze_anomalies_batch(record.anomalies)
                    
                    # 确保分析器在运行
                    if not analyzer.get_status()["is_running"]:
                        analyzer.start()
                except Exception as e:
                    logger.warning(f"触发异常分析失败: {e}")
            
            logger.info(
                f"第 {self._execution_count} 次轮询完成: "
                f"status={record.status}, "
                f"anomaly_count={record.anomaly_count}, "
                f"duration={record.duration_ms:.1f}ms"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"轮询任务执行失败: {e}", exc_info=True)
            
            # 记录错误
            record = PollingRecord(
                status="error",
                summary=f"轮询执行失败: {str(e)}",
                anomaly_count=0,
                error=str(e),
                duration_ms=duration_ms,
            )
            self._history_store.add(record)
    
    def start(self) -> bool:
        """
        启动定时轮询
        
        Returns:
            bool: 是否成功启动
        """
        if self._is_running:
            logger.warning("轮询调度器已经在运行")
            return False
        
        try:
            self._init_scheduler()
            
            # 添加定时任务
            self._job = self._scheduler.add_job(
                self._polling_task,
                trigger="interval",
                minutes=self.interval_minutes,
                id="monitoring_polling_job",
                replace_existing=True,
                next_run_time=datetime.now(),
            )
            
            # 启动调度器
            self._scheduler.start()
            self._is_running = True
            
            logger.info(
                f"轮询调度器已启动，首次执行立即开始，"
                f"之后每 {self.interval_minutes} 分钟执行一次"
            )
            return True
            
        except Exception as e:
            logger.error(f"启动轮询调度器失败: {e}")
            return False
    
    def stop(self) -> bool:
        """
        停止定时轮询
        
        Returns:
            bool: 是否成功停止
        """
        if not self._is_running:
            logger.warning("轮询调度器未在运行")
            return False
        
        try:
            if self._scheduler:
                self._scheduler.shutdown(wait=False)
                self._scheduler = None
            
            self._is_running = False
            self._job = None
            
            logger.info("轮询调度器已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止轮询调度器失败: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        next_run = None
        if self._job and self._job.next_run_time:
            next_run = self._job.next_run_time.isoformat()
        
        stats = self._history_store.get_statistics()
        
        return {
            "is_running": self._is_running,
            "interval_minutes": self.interval_minutes,
            "execution_count": self._execution_count,
            "next_run": next_run,
            "history_count": stats.get("total", 0),
            "last_run": stats.get("latest_timestamp"),
            "history_statistics": stats,
        }
    
    def run_once(
        self,
        namespace: Optional[str] = None,
        deep_analysis: bool = False,
    ) -> Dict[str, Any]:
        """
        立即执行一次轮询（不影响定时任务）
        
        Args:
            namespace: 命名空间
            deep_analysis: 是否执行深度分析
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        logger.info(f"手动触发单次轮询 (namespace={namespace}, deep_analysis={deep_analysis})...")
        self._polling_task(namespace=namespace, deep_analysis=deep_analysis)
        
        # 返回最新记录
        latest = self._history_store.get_latest(1)
        return latest[0] if latest else {}
    
    def set_interval(self, minutes: int) -> bool:
        """
        动态修改轮询间隔
        
        Args:
            minutes: 新的间隔（分钟）
            
        Returns:
            bool: 是否成功修改
        """
        if minutes < 1:
            logger.error("轮询间隔不能小于 1 分钟")
            return False
        
        old_interval = self.interval_minutes
        self.interval_minutes = minutes
        
        # 如果调度器正在运行，需要重新添加任务
        if self._is_running and self._scheduler:
            try:
                # 移除旧任务
                if self._job:
                    self._scheduler.remove_job(self._job.id)
                
                # 添加新任务
                self._job = self._scheduler.add_job(
                    self._polling_task,
                    trigger="interval",
                    minutes=self.interval_minutes,
                    id="monitoring_polling_job",
                    replace_existing=True,
                    next_run_time=datetime.now(),
                )
                
                logger.info(f"轮询间隔已更新: {old_interval} 分钟 -> {minutes} 分钟")
                return True
                
            except Exception as e:
                logger.error(f"更新轮询间隔失败: {e}")
                self.interval_minutes = old_interval
                return False
        
        logger.info(f"轮询间隔已设置: {minutes} 分钟（下次启动时生效）")
        return True
    
    def get_history(
        self,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取历史记录
        
        Args:
            limit: 记录数量限制
            status: 按状态筛选
            
        Returns:
            Dict[str, Any]: 历史记录和统计信息
        """
        if status:
            records = self._history_store.get_by_status(status)
            records = records[:limit]
        else:
            records = self._history_store.get_latest(limit)
        
        return {
            "total": self._history_store.size(),
            "returned": len(records),
            "records": records,
            "statistics": self._history_store.get_statistics(),
        }
    
    def clear_history(self) -> bool:
        """
        清空历史记录
        
        Returns:
            bool: 是否成功
        """
        try:
            self._history_store.clear()
            logger.info("历史记录已清空")
            return True
        except Exception as e:
            logger.error(f"清空历史记录失败: {e}")
            return False


_scheduler_instance: Optional[PollingScheduler] = None


def get_polling_scheduler(
    interval_minutes: int = 5,
    max_records: int = 100,
) -> PollingScheduler:
    """
    获取轮询调度器单例
    
    Args:
        interval_minutes: 轮询间隔（首次创建时使用）
        max_records: 最大历史记录数（首次创建时使用）
        
    Returns:
        PollingScheduler: 调度器实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = PollingScheduler(
            interval_minutes=interval_minutes,
            max_records=max_records,
        )
    return _scheduler_instance
