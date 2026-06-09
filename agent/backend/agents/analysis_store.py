"""
异常分析结果存储模块
提供 SQLite 持久化存储，保存异常的根因分析和恢复建议
"""

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional


logger = logging.getLogger(__name__)

_ANALYSIS_DB_ENV = "OPS_AGENT_ANALYSIS_DB"


def _get_analysis_db_path() -> Path:
    """
    获取分析结果 SQLite 数据库文件路径
    
    Returns:
        Path: 数据库文件路径
    """
    env_path = os.getenv(_ANALYSIS_DB_ENV)
    if env_path:
        return Path(env_path)
    
    home = Path.home()
    analysis_dir = home / ".ops_agent"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir / "analysis.db"


class AnalysisStore:
    """
    异常分析结果存储器
    使用 SQLite 持久化存储根因分析和恢复建议
    """
    
    _conn: Optional[sqlite3.Connection] = None
    _lock = threading.Lock()
    
    def __init__(self, max_records: int = 500):
        self.max_records = max_records
        self._db_path = _get_analysis_db_path()
        
        self._init_db()
        
        logger.info(f"分析存储初始化完成，最大记录数: {max_records}, 数据库: {self._db_path}")
    
    def _init_db(self) -> None:
        """
        初始化数据库表
        """
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS anomaly_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anomaly_id TEXT UNIQUE NOT NULL,
                    root_cause_json TEXT,
                    recovery_plan_json TEXT,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_anomaly_id 
                ON anomaly_analysis (anomaly_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status 
                ON anomaly_analysis (status)
            ''')
            
            conn.commit()
            
            logger.info("分析结果数据库表初始化完成")
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        获取数据库连接（线程安全）
        
        Yields:
            sqlite3.Connection: 数据库连接
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            try:
                yield conn
            finally:
                conn.close()
    
    def create_pending(
        self,
        anomaly_id: str,
    ) -> bool:
        """
        创建待分析记录
        
        Args:
            anomaly_id: 异常唯一标识符
            
        Returns:
            bool: 是否成功创建
        """
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO anomaly_analysis 
                    (anomaly_id, status, created_at)
                    VALUES (?, ?, ?)
                ''', (
                    anomaly_id,
                    'pending',
                    datetime.now().isoformat(),
                ))
                conn.commit()
                
            logger.debug(f"已创建待分析记录: anomaly_id={anomaly_id}")
            return True
        except Exception as e:
            logger.error(f"创建待分析记录失败: {e}")
            return False
    
    def reset_to_pending(
        self,
        anomaly_id: str,
    ) -> bool:
        """
        重置分析状态为待分析（用于重新分析场景）
        
        如果记录存在，将状态重置为 pending 并清空之前的分析结果
        如果记录不存在，创建新的待分析记录
        
        Args:
            anomaly_id: 异常唯一标识符
            
        Returns:
            bool: 是否成功重置
        """
        try:
            with self._get_connection() as conn:
                # 先尝试更新现有记录
                cursor = conn.execute('''
                    UPDATE anomaly_analysis 
                    SET status = 'pending',
                        root_cause_json = NULL,
                        recovery_plan_json = NULL,
                        error_message = NULL,
                        completed_at = NULL,
                        created_at = ?
                    WHERE anomaly_id = ?
                ''', (
                    datetime.now().isoformat(),
                    anomaly_id,
                ))
                conn.commit()
                
                if cursor.rowcount > 0:
                    # 找到了并更新了现有记录
                    logger.info(f"已重置分析状态为待分析: anomaly_id={anomaly_id}")
                    return True
                else:
                    # 没有找到现有记录，创建新记录
                    conn.execute('''
                        INSERT INTO anomaly_analysis 
                        (anomaly_id, status, created_at)
                        VALUES (?, ?, ?)
                    ''', (
                        anomaly_id,
                        'pending',
                        datetime.now().isoformat(),
                    ))
                    conn.commit()
                    logger.debug(f"已创建新的待分析记录: anomaly_id={anomaly_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"重置分析状态失败: {e}")
            return False
    
    def start_analysis(self, anomaly_id: str) -> bool:
        """
        标记分析开始
        
        Args:
            anomaly_id: 异常唯一标识符
            
        Returns:
            bool: 是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    UPDATE anomaly_analysis 
                    SET status = 'analyzing'
                    WHERE anomaly_id = ? AND status IN ('pending', 'failed')
                ''', (anomaly_id,))
                conn.commit()
                
            logger.debug(f"已标记分析开始: anomaly_id={anomaly_id}")
            return True
        except Exception as e:
            logger.error(f"标记分析开始失败: {e}")
            return False
    
    def save_analysis(
        self,
        anomaly_id: str,
        root_cause: Optional[Dict[str, Any]] = None,
        recovery_plan: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        保存分析结果
        
        Args:
            anomaly_id: 异常唯一标识符
            root_cause: 根因分析结果
            recovery_plan: 恢复计划
            
        Returns:
            bool: 是否成功保存
        """
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    UPDATE anomaly_analysis 
                    SET root_cause_json = ?,
                        recovery_plan_json = ?,
                        status = 'completed',
                        completed_at = ?
                    WHERE anomaly_id = ?
                ''', (
                    json.dumps(root_cause, ensure_ascii=False) if root_cause else None,
                    json.dumps(recovery_plan, ensure_ascii=False) if recovery_plan else None,
                    datetime.now().isoformat(),
                    anomaly_id,
                ))
                conn.commit()
                
                self._cleanup_old_records(conn)
                
            logger.info(f"已保存分析结果: anomaly_id={anomaly_id}")
            return True
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return False
    
    def mark_failed(self, anomaly_id: str, error_message: str) -> bool:
        """
        标记分析失败
        
        Args:
            anomaly_id: 异常唯一标识符
            error_message: 错误信息
            
        Returns:
            bool: 是否成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    UPDATE anomaly_analysis 
                    SET status = 'failed',
                        error_message = ?,
                        completed_at = ?
                    WHERE anomaly_id = ?
                ''', (
                    error_message,
                    datetime.now().isoformat(),
                    anomaly_id,
                ))
                conn.commit()
                
            logger.warning(f"标记分析失败: anomaly_id={anomaly_id}, error={error_message}")
            return True
        except Exception as e:
            logger.error(f"标记分析失败时出错: {e}")
            return False
    
    def get_analysis(self, anomaly_id: str) -> Optional[Dict[str, Any]]:
        """
        获取异常的分析结果
        
        Args:
            anomaly_id: 异常唯一标识符
            
        Returns:
            Optional[Dict[str, Any]]: 分析结果，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                row = conn.execute('''
                    SELECT anomaly_id, root_cause_json, recovery_plan_json, 
                           status, error_message, created_at, completed_at
                    FROM anomaly_analysis 
                    WHERE anomaly_id = ?
                ''', (anomaly_id,)).fetchone()
                
                if not row:
                    return None
                
                root_cause = None
                if row["root_cause_json"]:
                    try:
                        root_cause = json.loads(row["root_cause_json"])
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析根因分析 JSON: anomaly_id={anomaly_id}")
                
                recovery_plan = None
                if row["recovery_plan_json"]:
                    try:
                        recovery_plan = json.loads(row["recovery_plan_json"])
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析恢复计划 JSON: anomaly_id={anomaly_id}")
                
                return {
                    "anomaly_id": row["anomaly_id"],
                    "root_cause": root_cause,
                    "recovery_plan": recovery_plan,
                    "status": row["status"],
                    "error_message": row["error_message"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"],
                }
        except Exception as e:
            logger.error(f"获取分析结果失败: {e}")
            return None
    
    def get_status(self, anomaly_id: str) -> Optional[str]:
        """
        获取分析状态
        
        Args:
            anomaly_id: 异常唯一标识符
            
        Returns:
            Optional[str]: 分析状态，不存在则返回 None
        """
        try:
            with self._get_connection() as conn:
                row = conn.execute('''
                    SELECT status
                    FROM anomaly_analysis 
                    WHERE anomaly_id = ?
                ''', (anomaly_id,)).fetchone()
                
                return row["status"] if row else None
        except Exception as e:
            logger.error(f"获取分析状态失败: {e}")
            return None
    
    def get_pending_count(self) -> int:
        """
        获取待分析的异常数量
        
        Returns:
            int: 待分析数量
        """
        try:
            with self._get_connection() as conn:
                count = conn.execute('''
                    SELECT COUNT(*) 
                    FROM anomaly_analysis 
                    WHERE status = 'pending'
                ''').fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"获取待分析数量失败: {e}")
            return 0
    
    def get_pending_anomalies(self, limit: int = 10) -> list:
        """
        获取待分析的异常列表
        
        Args:
            limit: 限制数量
            
        Returns:
            list: 待分析的异常 ID 列表
        """
        try:
            with self._get_connection() as conn:
                rows = conn.execute('''
                    SELECT anomaly_id
                    FROM anomaly_analysis 
                    WHERE status = 'pending'
                    ORDER BY id ASC
                    LIMIT ?
                ''', (limit,)).fetchall()
                
                return [row["anomaly_id"] for row in rows]
        except Exception as e:
            logger.error(f"获取待分析异常列表失败: {e}")
            return []
    
    def _cleanup_old_records(self, conn: sqlite3.Connection) -> None:
        """
        清理超出容量的旧记录
        
        Args:
            conn: 数据库连接
        """
        count = conn.execute('SELECT COUNT(*) FROM anomaly_analysis').fetchone()[0]
        if count > self.max_records:
            delete_count = count - self.max_records
            conn.execute('''
                DELETE FROM anomaly_analysis 
                WHERE id IN (
                    SELECT id FROM anomaly_analysis 
                    ORDER BY id ASC 
                    LIMIT ?
                )
            ''', (delete_count,))
            logger.debug(f"清理了 {delete_count} 条旧分析记录")
    
    def clear(self) -> None:
        """
        清空所有分析记录
        """
        with self._get_connection() as conn:
            conn.execute('DELETE FROM anomaly_analysis')
            conn.commit()
            
            logger.info("分析记录已清空")
    
    def size(self) -> int:
        """
        获取记录数量
        
        Returns:
            int: 记录总数
        """
        with self._get_connection() as conn:
            return conn.execute('SELECT COUNT(*) FROM anomaly_analysis').fetchone()[0]


_analysis_store: Optional[AnalysisStore] = None


def get_analysis_store(max_records: int = 500) -> AnalysisStore:
    """
    获取分析结果存储单例
    
    Args:
        max_records: 最大记录数（仅首次创建时生效）
        
    Returns:
        AnalysisStore: 分析结果存储器实例
    """
    global _analysis_store
    if _analysis_store is None:
        _analysis_store = AnalysisStore(max_records=max_records)
    return _analysis_store
