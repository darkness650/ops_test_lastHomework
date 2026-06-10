"""
分析任务管理器模块
负责异步管理和执行业务分析任务，支持任务状态跟踪和并发控制
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from tools.metrics_collector import get_metrics_collector
from agents.business_analyzer import get_business_analyzer
from agents.report_store import get_report_store


logger = logging.getLogger(__name__)


# ============================================================================
# 任务状态常量定义
# ============================================================================

class TaskStatus:
    """任务状态常量"""
    QUEUED = "queued"        # 已排队
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败


# ============================================================================
# AnalysisTaskManager 类定义
# ============================================================================

class AnalysisTaskManager:
    """
    分析任务管理器
    负责异步触发和管理业务分析任务，维护任务状态，支持并发控制
    """

    def __init__(self):
        """
        初始化分析任务管理器
        """
        # 任务存储：task_id -> task_info
        self._tasks: Dict[str, Dict[str, Any]] = {}
        
        # 最近一次任务的 ID
        self._latest_task_id: Optional[str] = None
        
        # 线程锁：保护任务状态的并发访问
        self._lock = threading.Lock()
        
        # 并发控制锁：确保同一时间只有一个任务在执行
        self._execution_lock = threading.Lock()
        
        # 初始化依赖组件
        self._metrics_collector = get_metrics_collector()
        self._business_analyzer = get_business_analyzer()
        self._report_store = get_report_store()
        
        logger.info("AnalysisTaskManager 初始化完成")

    def _generate_task_id(self) -> str:
        """
        生成唯一的任务 ID

        Returns:
            str: 任务 ID
        """
        return f"task_{uuid.uuid4().hex[:12]}"

    def _create_task(
        self,
        task_id: str,
        period_hours: int,
        namespace: Optional[str],
    ) -> Dict[str, Any]:
        """
        创建新的任务记录

        Args:
            task_id: 任务 ID
            period_hours: 分析周期（小时）
            namespace: 命名空间

        Returns:
            Dict[str, Any]: 任务信息字典
        """
        now = datetime.now().isoformat()
        return {
            "task_id": task_id,
            "status": TaskStatus.QUEUED,
            "progress": 0.0,
            "created_at": now,
            "updated_at": now,
            "period_hours": period_hours,
            "namespace": namespace,
            "report_id": None,
            "error_message": None,
        }

    def _update_task_status(
        self,
        task_id: str,
        status: str,
        progress: float = 0.0,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 新状态
            progress: 进度（0-100）
            **kwargs: 其他要更新的字段（如 report_id、error_message）

        Returns:
            Optional[Dict[str, Any]]: 更新后的任务信息，任务不存在返回 None
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"尝试更新不存在的任务状态: task_id={task_id}")
                return None

            task = self._tasks[task_id]
            task["status"] = status
            task["progress"] = max(0.0, min(100.0, float(progress)))
            task["updated_at"] = datetime.now().isoformat()

            # 更新其他字段
            for key, value in kwargs.items():
                if key in ["report_id", "error_message"]:
                    task[key] = value

            logger.info(
                f"任务状态更新: task_id={task_id}, status={status}, "
                f"progress={progress}%"
            )
            return task.copy()

    def trigger_analysis(
        self,
        period_hours: int = 24,
        namespace: Optional[str] = None,
    ) -> str:
        """
        触发分析任务（异步，非阻塞）

        Args:
            period_hours: 分析周期（小时），默认为 24
            namespace: 命名空间，默认为 None 表示全集群

        Returns:
            str: 任务 ID
        """
        task_id = self._generate_task_id()

        with self._lock:
            # 创建任务记录
            task = self._create_task(task_id, period_hours, namespace)
            self._tasks[task_id] = task
            self._latest_task_id = task_id

        logger.info(
            f"已触发分析任务: task_id={task_id}, period={period_hours}h, "
            f"namespace={namespace or '所有'}"
        )

        # 启动线程执行任务
        thread = threading.Thread(
            target=self._run_analysis,
            args=(task_id, period_hours, namespace),
            name=f"AnalysisTask-{task_id}",
            daemon=True,
        )
        thread.start()

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        查询任务状态

        Args:
            task_id: 任务 ID

        Returns:
            Optional[Dict[str, Any]]: 任务状态信息，不存在返回 None
        """
        with self._lock:
            if task_id in self._tasks:
                return self._tasks[task_id].copy()
            return None

    def get_latest_task(self) -> Optional[Dict[str, Any]]:
        """
        获取最近一次分析任务

        Returns:
            Optional[Dict[str, Any]]: 最近一次任务信息，没有任务返回 None
        """
        with self._lock:
            if self._latest_task_id and self._latest_task_id in self._tasks:
                return self._tasks[self._latest_task_id].copy()
            return None

    def _run_analysis(
        self,
        task_id: str,
        period_hours: int,
        namespace: Optional[str],
    ) -> None:
        """
        实际执行分析的线程函数

        Args:
            task_id: 任务 ID
            period_hours: 分析周期（小时）
            namespace: 命名空间
        """
        # 首先检查并发锁，避免同时执行多个任务
        if not self._execution_lock.acquire(blocking=False):
            # 如果无法获取锁，说明有其他任务在执行
            logger.warning(
                f"任务排队等待执行: task_id={task_id}，已有任务在执行"
            )
            # 保持 QUEUED 状态
            return

        try:
            # 更新状态为 RUNNING
            self._update_task_status(task_id, TaskStatus.RUNNING, progress=10.0)
            logger.info(f"开始执行分析任务: task_id={task_id}")

            # 阶段1: 采集数据
            logger.info(f"阶段1: 采集指标数据 - task_id={task_id}")
            self._update_task_status(task_id, TaskStatus.RUNNING, progress=20.0)

            try:
                metrics_data = self._metrics_collector.collect(
                    period_hours=period_hours,
                    namespace=namespace,
                )

                if not metrics_data.get("success", False):
                    error_msg = metrics_data.get("error", "指标采集失败")
                    raise Exception(error_msg)

            except Exception as e:
                error_msg = f"指标数据采集失败: {str(e)}"
                logger.error(f"{error_msg} - task_id={task_id}")
                self._update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    progress=0.0,
                    error_message=error_msg,
                )
                return

            # 阶段2: AI 分析
            logger.info(f"阶段2: AI 业务分析 - task_id={task_id}")
            self._update_task_status(task_id, TaskStatus.RUNNING, progress=50.0)

            try:
                analysis_result = self._business_analyzer.analyze(
                    metrics_data=metrics_data,
                    period_hours=period_hours,
                    namespace=namespace,
                )

            except Exception as e:
                error_msg = f"业务分析执行失败: {str(e)}"
                logger.error(f"{error_msg} - task_id={task_id}")
                self._update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    progress=50.0,
                    error_message=error_msg,
                )
                return

            # 阶段3: 保存报告
            logger.info(f"阶段3: 保存分析报告 - task_id={task_id}")
            self._update_task_status(task_id, TaskStatus.RUNNING, progress=80.0)

            try:
                report_id = self._report_store.save(analysis_result)

            except Exception as e:
                error_msg = f"报告保存失败: {str(e)}"
                logger.error(f"{error_msg} - task_id={task_id}")
                self._update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    progress=80.0,
                    error_message=error_msg,
                )
                return

            # 任务完成
            self._update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                progress=100.0,
                report_id=report_id,
            )
            logger.info(
                f"分析任务完成: task_id={task_id}, report_id={report_id}"
            )

        except Exception as e:
            # 捕获未预期的异常
            error_msg = f"任务执行异常: {str(e)}"
            logger.error(f"{error_msg} - task_id={task_id}", exc_info=True)
            self._update_task_status(
                task_id,
                TaskStatus.FAILED,
                progress=0.0,
                error_message=error_msg,
            )

        finally:
            # 释放并发锁
            self._execution_lock.release()


# ============================================================================
# 单例模式实现
# ============================================================================

_analysis_task_manager: Optional[AnalysisTaskManager] = None
_analysis_task_manager_lock = threading.Lock()


def get_analysis_task_manager() -> AnalysisTaskManager:
    """
    获取分析任务管理器单例

    Returns:
        AnalysisTaskManager: 分析任务管理器实例
    """
    global _analysis_task_manager

    if _analysis_task_manager is None:
        with _analysis_task_manager_lock:
            if _analysis_task_manager is None:
                _analysis_task_manager = AnalysisTaskManager()

    return _analysis_task_manager
