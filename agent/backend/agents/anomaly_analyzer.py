"""
异常分析器模块
负责在后台自动执行 AI 根因分析和恢复建议生成
支持并行执行和会话隔离，提高分析速度
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from agents.analysis_store import get_analysis_store
from agents.engine import LLMAnalyst, RootCause, RecoveryPlan
from config.settings import get_settings


logger = logging.getLogger(__name__)


class AnomalyAnalyzer:
    """
    异常分析器
    在后台自动执行 AI 根因分析和恢复建议生成
    支持并行执行，每个分析任务使用独立的 Agent 会话
    """
    
    def __init__(
        self,
        poll_interval_seconds: int = 10,
        max_workers: int = 4,
    ):
        """
        初始化异常分析器
        
        Args:
            poll_interval_seconds: 轮询待分析任务的间隔（秒）
            max_workers: 最大并行工作线程数
        """
        self._poll_interval = poll_interval_seconds
        self._max_workers = max_workers
        self._is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self._analysis_store = get_analysis_store()
        
        # 线程池用于并行执行分析任务
        self._executor: Optional[ThreadPoolExecutor] = None
        
        # 跟踪正在分析的异常 ID（用于防止重复触发）
        self._analyzing_ids: Set[str] = set()
        self._analyzing_lock = threading.Lock()
        
        # 跟踪提交的 Future
        self._futures: List[Future] = []
        self._futures_lock = threading.Lock()
        
        # 检查 LLM 是否配置
        settings = get_settings()
        self._llm_available = bool(settings.llm.api_key and settings.llm.base_url)
        
        if not self._llm_available:
            logger.warning("LLM 未配置，异常分析器将无法执行 AI 分析")
        
        logger.info(
            f"异常分析器初始化完成，轮询间隔: {self._poll_interval}秒，"
            f"最大并行数: {self._max_workers}"
        )
    
    def _create_llm_analyst(self) -> Optional[LLMAnalyst]:
        """
        创建新的 LLM 分析器实例（会话隔离）
        每个分析任务使用独立的 Agent 实例
        
        Returns:
            Optional[LLMAnalyst]: 新的 LLM 分析器实例
        """
        if not self._llm_available:
            return None
        
        try:
            # 延迟导入，避免循环依赖
            from agents.agent import create_agent
            
            # 创建独立的 Agent 实例，确保会话隔离
            agent = create_agent(
                system_prompt=None,  # 使用默认系统提示
                max_tool_calls=10,
            )
            llm_analyst = LLMAnalyst(agent=agent)
            logger.debug("已创建新的 LLM 分析器实例（会话隔离）")
            return llm_analyst
        except Exception as e:
            logger.error(f"创建 LLM 分析器失败: {e}")
            return None
    
    def start(self) -> bool:
        """
        启动后台分析线程和线程池
        
        Returns:
            bool: 是否成功启动
        """
        if self._is_running:
            logger.warning("异常分析器已经在运行")
            return False
        
        if not self._llm_available:
            logger.warning("LLM 未配置，无法启动异常分析器")
            return False
        
        self._stop_event.clear()
        self._is_running = True
        
        # 初始化线程池
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="AnomalyAnalyzer-Worker",
        )
        logger.info(f"分析线程池已初始化，最大工作线程数: {self._max_workers}")
        
        # 启动主工作线程
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="AnomalyAnalyzer-Main",
            daemon=True,
        )
        self._worker_thread.start()
        
        logger.info("异常分析器后台线程已启动")
        return True
    
    def stop(self) -> bool:
        """
        停止后台分析线程和线程池
        
        Returns:
            bool: 是否成功停止
        """
        if not self._is_running:
            logger.warning("异常分析器未在运行")
            return False
        
        self._stop_event.set()
        self._is_running = False
        
        # 关闭线程池，等待正在执行的任务完成
        if self._executor:
            logger.info("正在关闭分析线程池，等待正在执行的任务完成...")
            self._executor.shutdown(wait=True)
            self._executor = None
            logger.info("分析线程池已关闭")
        
        if self._worker_thread:
            self._worker_thread.join(timeout=30)
            self._worker_thread = None
        
        # 清空正在分析的列表
        with self._analyzing_lock:
            self._analyzing_ids.clear()
        
        logger.info("异常分析器已停止")
        return True
    
    def _worker_loop(self) -> None:
        """
        后台工作线程主循环
        负责轮询待分析任务并提交到线程池
        """
        logger.info("异常分析器主工作线程开始运行")
        
        while not self._stop_event.is_set():
            try:
                # 清理已完成的 Future
                self._cleanup_completed_futures()
                
                # 检查是否有待分析的任务
                pending_count = self._analysis_store.get_pending_count()
                
                if pending_count > 0:
                    logger.info(f"发现 {pending_count} 个待分析的异常")
                    
                    # 获取当前正在分析的数量
                    with self._analyzing_lock:
                        current_analyzing = len(self._analyzing_ids)
                    
                    # 计算还能提交多少任务
                    available_slots = self._max_workers - current_analyzing
                    
                    if available_slots > 0:
                        # 获取待分析的异常列表
                        pending_anomalies = self._analysis_store.get_pending_anomalies(
                            limit=available_slots * 2
                        )
                        
                        # 过滤掉已经在分析中的异常
                        anomalies_to_process = []
                        with self._analyzing_lock:
                            for anomaly_id in pending_anomalies:
                                if anomaly_id not in self._analyzing_ids:
                                    anomalies_to_process.append(anomaly_id)
                                    if len(anomalies_to_process) >= available_slots:
                                        break
                        
                        # 提交到线程池
                        for anomaly_id in anomalies_to_process:
                            if self._stop_event.is_set():
                                break
                            
                            # 标记为正在分析
                            with self._analyzing_lock:
                                self._analyzing_ids.add(anomaly_id)
                            
                            # 提交任务
                            future = self._executor.submit(
                                self._analyze_anomaly_task,
                                anomaly_id,
                            )
                            
                            with self._futures_lock:
                                self._futures.append(future)
                            
                            logger.info(f"已提交异常分析任务: {anomaly_id}")
                
                # 等待下一次轮询
                self._stop_event.wait(self._poll_interval)
                
            except Exception as e:
                logger.error(f"异常分析器工作循环出错: {e}", exc_info=True)
                self._stop_event.wait(self._poll_interval)
        
        logger.info("异常分析器主工作线程已退出")
    
    def _cleanup_completed_futures(self) -> None:
        """
        清理已完成的 Future 对象
        """
        with self._futures_lock:
            self._futures = [f for f in self._futures if not f.done()]
    
    def _analyze_anomaly_task(self, anomaly_id: str) -> bool:
        """
        单个异常分析任务（在线程池中执行）
        
        Args:
            anomaly_id: 异常唯一标识符
            
        Returns:
            bool: 是否分析成功
        """
        logger.info(f"开始分析异常: {anomaly_id}")
        
        # 标记分析开始
        if not self._analysis_store.start_analysis(anomaly_id):
            logger.warning(f"无法标记分析开始，可能已被其他线程处理: {anomaly_id}")
            with self._analyzing_lock:
                self._analyzing_ids.discard(anomaly_id)
            return False
        
        try:
            # 创建独立的 LLM 分析器（会话隔离）
            llm_analyst = self._create_llm_analyst()
            if not llm_analyst:
                raise Exception("LLM 分析器不可用")
            
            # 获取异常信息（这里简化处理，实际可以从历史记录中获取更完整的上下文）
            anomaly_info = {
                "id": anomaly_id,
                "analysis_time": datetime.now().isoformat(),
            }
            
            # 执行根因分析
            logger.info(f"执行根因分析: {anomaly_id}")
            root_cause = llm_analyst.analyze_root_cause(
                anomalies=[anomaly_info],
                context={"source": "auto_analysis"},
            )
            
            root_cause_dict = root_cause.to_dict() if root_cause else None
            
            # 生成恢复计划
            recovery_plan_dict = None
            if root_cause:
                logger.info(f"生成恢复计划: {anomaly_id}")
                recovery_plan = llm_analyst.generate_recovery_plan(
                    root_cause=root_cause,
                    current_status={"anomaly_id": anomaly_id},
                )
                recovery_plan_dict = recovery_plan.to_dict() if recovery_plan else None
            
            # 保存分析结果
            success = self._analysis_store.save_analysis(
                anomaly_id=anomaly_id,
                root_cause=root_cause_dict,
                recovery_plan=recovery_plan_dict,
            )
            
            if success:
                logger.info(f"异常分析完成并保存: {anomaly_id}")
            else:
                logger.error(f"保存分析结果失败: {anomaly_id}")
            
            return success
                
        except Exception as e:
            error_msg = f"分析异常时出错: {str(e)}"
            logger.error(f"{error_msg}", exc_info=True)
            
            # 标记分析失败
            self._analysis_store.mark_failed(
                anomaly_id=anomaly_id,
                error_message=error_msg,
            )
            return False
        finally:
            # 从正在分析列表中移除
            with self._analyzing_lock:
                self._analyzing_ids.discard(anomaly_id)
    
    def analyze_anomaly_async(
        self,
        anomaly_id: str,
        anomaly_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        异步触发异常分析（非阻塞）
        
        Args:
            anomaly_id: 异常唯一标识符
            anomaly_data: 异常数据（可选，用于传递上下文）
            
        Returns:
            bool: 是否成功提交分析任务
        """
        if not self._llm_available:
            logger.warning("LLM 未配置，跳过自动分析")
            return False
        
        # 检查是否已经在分析中
        with self._analyzing_lock:
            if anomaly_id in self._analyzing_ids:
                logger.warning(f"异常正在分析中，跳过重复提交: {anomaly_id}")
                return False
        
        # 重置为待分析状态（支持重新分析）
        # 如果记录已存在（如已分析完成或失败），会重置状态为 pending 并清空之前的结果
        # 如果记录不存在，会创建新的待分析记录
        success = self._analysis_store.reset_to_pending(anomaly_id=anomaly_id)
        
        if success:
            logger.info(f"已提交异常分析任务: {anomaly_id}")
        else:
            logger.error(f"重置分析状态失败: {anomaly_id}")
        
        return success
    
    def analyze_anomalies_batch(
        self,
        anomalies: List[Dict[str, Any]],
    ) -> int:
        """
        批量触发异常分析
        
        Args:
            anomalies: 异常列表，每个异常包含 'id' 字段
            
        Returns:
            int: 成功提交的任务数
        """
        if not self._llm_available:
            logger.warning("LLM 未配置，跳过自动分析")
            return 0
        
        submitted = 0
        for anomaly in anomalies:
            anomaly_id = anomaly.get("id")
            if anomaly_id:
                if self.analyze_anomaly_async(anomaly_id=anomaly_id, anomaly_data=anomaly):
                    submitted += 1
        
        logger.info(f"批量提交了 {submitted}/{len(anomalies)} 个异常分析任务")
        return submitted
    
    def is_analyzing(self, anomaly_id: str) -> bool:
        """
        检查指定异常是否正在分析中
        
        Args:
            anomaly_id: 异常唯一标识符
            
        Returns:
            bool: 是否正在分析
        """
        with self._analyzing_lock:
            return anomaly_id in self._analyzing_ids
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取分析器状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        with self._analyzing_lock:
            analyzing_count = len(self._analyzing_ids)
        
        return {
            "is_running": self._is_running,
            "llm_available": self._llm_available,
            "pending_count": self._analysis_store.get_pending_count(),
            "analyzing_count": analyzing_count,
            "total_records": self._analysis_store.size(),
            "poll_interval_seconds": self._poll_interval,
            "max_workers": self._max_workers,
        }


_anomaly_analyzer: Optional[AnomalyAnalyzer] = None


def get_anomaly_analyzer() -> AnomalyAnalyzer:
    """
    获取异常分析器单例
    
    Returns:
        AnomalyAnalyzer: 异常分析器实例
    """
    global _anomaly_analyzer
    if _anomaly_analyzer is None:
        _anomaly_analyzer = AnomalyAnalyzer()
    return _anomaly_analyzer


def start_anomaly_analyzer() -> bool:
    """
    便捷函数：启动异常分析器
    
    Returns:
        bool: 是否成功启动
    """
    analyzer = get_anomaly_analyzer()
    return analyzer.start()


def stop_anomaly_analyzer() -> bool:
    """
    便捷函数：停止异常分析器
    
    Returns:
        bool: 是否成功停止
    """
    global _anomaly_analyzer
    if _anomaly_analyzer:
        return _anomaly_analyzer.stop()
    return False
