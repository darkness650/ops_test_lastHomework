"""
定时分析调度器模块
基于 APScheduler 实现每日定时业务分析
"""

import json
import logging
import os
import threading
from typing import Any, Dict, Optional

from agents.analysis_task_manager import get_analysis_task_manager


logger = logging.getLogger(__name__)


class ScheduleAnalyzer:
    """
    定时分析调度器
    基于 APScheduler 实现每日定时业务分析，支持配置持久化
    """

    def __init__(self):
        """
        初始化定时分析调度器
        """
        # 默认配置
        self._config: Dict[str, Any] = {
            "enabled": True,
            "hour": 2,
            "minute": 0,
            "analysis_period_hours": 24,
        }

        # 调度器相关变量
        self._scheduler = None
        self._job = None
        self._is_running = False

        # 配置文件路径
        self._config_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data"
        )
        self._config_file = os.path.join(
            self._config_dir,
            "analysis_schedule_config.json"
        )

        # 线程锁：保护配置和状态的并发访问
        self._lock = threading.Lock()

        # 加载配置
        self._load_config()

        logger.info("ScheduleAnalyzer 初始化完成")

    def _init_scheduler(self) -> None:
        """
        延迟初始化 APScheduler
        """
        from apscheduler.schedulers.background import BackgroundScheduler

        if self._scheduler is None:
            self._scheduler = BackgroundScheduler()
            logger.info("APScheduler 已初始化")

    def _load_config(self) -> None:
        """
        从 JSON 文件加载配置
        """
        try:
            # 确保配置目录存在
            if not os.path.exists(self._config_dir):
                os.makedirs(self._config_dir, exist_ok=True)
                logger.info(f"创建配置目录: {self._config_dir}")

            # 如果配置文件存在，加载配置
            if os.path.exists(self._config_file):
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)

                # 合并配置，确保所有必需字段存在
                for key, value in loaded_config.items():
                    if key in self._config:
                        self._config[key] = value

                logger.info(f"已加载配置: {self._config_file}")
            else:
                # 配置文件不存在，使用默认配置并保存
                self._save_config()
                logger.info(
                    f"配置文件不存在，已使用默认配置创建: {self._config_file}"
                )

        except Exception as e:
            logger.error(f"加载配置失败: {e}，使用默认配置")

    def _save_config(self) -> None:
        """
        保存配置到 JSON 文件
        """
        try:
            # 确保配置目录存在
            if not os.path.exists(self._config_dir):
                os.makedirs(self._config_dir, exist_ok=True)

            # 保存配置
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)

            logger.info(f"配置已保存: {self._config_file}")

        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def start(self) -> bool:
        """
        启动定时分析任务

        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if self._is_running:
                logger.warning("定时分析调度器已经在运行")
                return False

            try:
                # 延迟初始化调度器
                self._init_scheduler()

                # 只有 enabled 为 True 时才添加定时任务
                if self._config.get("enabled", True):
                    # 添加定时任务（每天指定时间执行）
                    self._job = self._scheduler.add_job(
                        self._scheduled_task,
                        trigger="cron",
                        hour=self._config["hour"],
                        minute=self._config["minute"],
                        id="daily_analysis_job",
                        replace_existing=True,
                    )

                # 启动调度器
                self._scheduler.start()
                self._is_running = True

                if self._config.get("enabled", True):
                    logger.info(
                        f"定时分析调度器已启动，每日 {self._config['hour']:02d}:"
                        f"{self._config['minute']:02d} 执行分析"
                    )
                else:
                    logger.info(
                        "定时分析调度器已启动，但定时任务已禁用（enabled=False）"
                    )

                return True

            except Exception as e:
                logger.error(f"启动定时分析调度器失败: {e}")
                return False

    def stop(self) -> bool:
        """
        停止定时分析任务

        Returns:
            bool: 是否成功停止
        """
        with self._lock:
            if not self._is_running:
                logger.warning("定时分析调度器未在运行")
                return False

            try:
                if self._scheduler:
                    self._scheduler.shutdown(wait=False)
                    self._scheduler = None

                self._is_running = False
                self._job = None

                logger.info("定时分析调度器已停止")
                return True

            except Exception as e:
                logger.error(f"停止定时分析调度器失败: {e}")
                return False

    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        with self._lock:
            next_run = None
            if self._job and self._job.next_run_time:
                next_run = self._job.next_run_time.isoformat()

            return {
                "is_running": self._is_running,
                "enabled": self._config.get("enabled", True),
                "schedule_time": {
                    "hour": self._config["hour"],
                    "minute": self._config["minute"],
                },
                "analysis_period_hours": self._config["analysis_period_hours"],
                "next_run": next_run,
                "config_file": self._config_file,
            }

    def update_config(
        self,
        hour: int = 2,
        minute: int = 0,
        period_hours: int = 24,
        enabled: Optional[bool] = None,
    ) -> bool:
        """
        更新配置

        Args:
            hour: 定时执行小时（0-23）
            minute: 定时执行分钟（0-59）
            period_hours: 分析周期（小时）
            enabled: 是否启用定时任务

        Returns:
            bool: 是否成功更新
        """
        # 参数验证
        if not (0 <= hour <= 23):
            logger.error(f"无效的小时值: {hour}，必须在 0-23 之间")
            return False

        if not (0 <= minute <= 59):
            logger.error(f"无效的分钟值: {minute}，必须在 0-59 之间")
            return False

        if period_hours <= 0:
            logger.error(f"无效的分析周期: {period_hours}，必须大于 0")
            return False

        with self._lock:
            old_config = self._config.copy()

            # 更新配置
            self._config["hour"] = hour
            self._config["minute"] = minute
            self._config["analysis_period_hours"] = period_hours
            if enabled is not None:
                self._config["enabled"] = enabled

            # 保存配置到文件
            self._save_config()

            # 如果调度器正在运行，需要更新定时任务
            if self._is_running and self._scheduler:
                try:
                    # 移除旧任务
                    if self._job:
                        self._scheduler.remove_job(self._job.id)
                        self._job = None

                    # 如果启用了定时任务，添加新任务
                    if self._config.get("enabled", True):
                        self._job = self._scheduler.add_job(
                            self._scheduled_task,
                            trigger="cron",
                            hour=hour,
                            minute=minute,
                            id="daily_analysis_job",
                            replace_existing=True,
                        )

                    logger.info(
                        f"定时分析配置已更新: hour={hour}, minute={minute}, "
                        f"period_hours={period_hours}, enabled={enabled}"
                    )
                    return True

                except Exception as e:
                    logger.error(f"更新定时任务失败: {e}")
                    # 恢复旧配置
                    self._config = old_config
                    self._save_config()
                    return False

            logger.info(
                f"定时分析配置已保存（下次启动时生效）: "
                f"hour={hour}, minute={minute}, period_hours={period_hours}, "
                f"enabled={enabled}"
            )
            return True

    def _scheduled_task(self) -> None:
        """
        定时执行的任务函数
        触发分析任务管理器执行分析
        """
        try:
            period_hours = self._config.get("analysis_period_hours", 24)
            logger.info(
                f"触发定时分析任务，分析周期: {period_hours} 小时"
            )

            # 获取分析任务管理器并触发分析
            task_manager = get_analysis_task_manager()
            task_id = task_manager.trigger_analysis(period_hours=period_hours)

            logger.info(f"定时分析任务已提交，task_id={task_id}")

        except Exception as e:
            logger.error(f"定时分析任务执行失败: {e}", exc_info=True)


# ============================================================================
# 单例模式实现
# ============================================================================

_schedule_analyzer: Optional[ScheduleAnalyzer] = None
_schedule_analyzer_lock = threading.Lock()


def get_schedule_analyzer() -> ScheduleAnalyzer:
    """
    获取定时分析调度器单例

    Returns:
        ScheduleAnalyzer: 定时分析调度器实例
    """
    global _schedule_analyzer

    if _schedule_analyzer is None:
        with _schedule_analyzer_lock:
            if _schedule_analyzer is None:
                _schedule_analyzer = ScheduleAnalyzer()

    return _schedule_analyzer
