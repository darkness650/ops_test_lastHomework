"""
轮询历史记录模块
提供 SQLite 持久化存储，保存最近 N 次轮询结果
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


logger = logging.getLogger(__name__)

_HISTORY_DB_ENV = "OPS_AGENT_HISTORY_DB"


def _get_history_db_path() -> Path:
    """
    获取 SQLite 数据库文件路径
    
    Returns:
        Path: 数据库文件路径
    """
    env_path = os.getenv(_HISTORY_DB_ENV)
    if env_path:
        return Path(env_path)
    
    home = Path.home()
    history_dir = home / ".ops_agent"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "history.db"


class PollingRecord:
    """
    轮询记录
    单次轮询的结果记录
    """
    
    def __init__(
        self,
        status: str,
        summary: str,
        anomaly_count: int = 0,
        anomalies: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        duration_ms: float = 0,
    ):
        self.timestamp = datetime.now().isoformat()
        self.status = status
        self.summary = summary
        self.anomaly_count = anomaly_count
        self.anomalies = anomalies or []
        self.error = error
        self.duration_ms = duration_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "summary": self.summary,
            "anomaly_count": self.anomaly_count,
            "anomalies": self.anomalies,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "PollingRecord":
        """
        从数据库行创建 PollingRecord
        
        Args:
            row: 数据库行（字典格式）
            
        Returns:
            PollingRecord: 创建的记录对象
        """
        record = cls(
            status=row["status"],
            summary=row["summary"],
            anomaly_count=row["anomaly_count"],
            anomalies=json.loads(row["anomalies_json"]) if row["anomalies_json"] else [],
            error=row["error"],
            duration_ms=row["duration_ms"],
        )
        record.timestamp = row["timestamp"]
        return record


class HistoryStore:
    """
    历史记录存储器
    使用 SQLite 持久化存储，自动淘汰最旧记录
    """
    
    _conn: Optional[sqlite3.Connection] = None
    
    def __init__(self, max_records: int = 100):
        self.max_records = max_records
        self._db_path = _get_history_db_path()
        
        self._init_db()
        
        logger.info(f"历史存储初始化完成，最大记录数: {max_records}, 数据库: {self._db_path}")
    
    def _init_db(self) -> None:
        """
        初始化数据库表
        """
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS polling_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    anomaly_count INTEGER DEFAULT 0,
                    anomalies_json TEXT,
                    error TEXT,
                    duration_ms REAL DEFAULT 0
                )
            ''')
            conn.commit()
            
            logger.info("数据库表初始化完成")
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        获取数据库连接（线程安全）
        
        Yields:
            sqlite3.Connection: 数据库连接
        """
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        try:
            yield conn
        finally:
            conn.close()
    
    def add(self, record: PollingRecord) -> None:
        """
        添加一条记录
        
        Args:
            record: 要添加的记录
        """
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO polling_history 
                (timestamp, status, summary, anomaly_count, anomalies_json, error, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.timestamp,
                record.status,
                record.summary,
                record.anomaly_count,
                json.dumps(record.anomalies, ensure_ascii=False),
                record.error,
                record.duration_ms,
            ))
            
            self._cleanup_old_records(conn)
            
            conn.commit()
        
        logger.info(f"已添加轮询记录: status={record.status}, anomaly_count={record.anomaly_count}")
    
    def _cleanup_old_records(self, conn: sqlite3.Connection) -> None:
        """
        清理超出容量的旧记录
        
        Args:
            conn: 数据库连接
        """
        count = conn.execute('SELECT COUNT(*) FROM polling_history').fetchone()[0]
        if count > self.max_records:
            delete_count = count - self.max_records
            conn.execute('''
                DELETE FROM polling_history 
                WHERE id IN (
                    SELECT id FROM polling_history 
                    ORDER BY id ASC 
                    LIMIT ?
                )
            ''', (delete_count,))
            logger.debug(f"清理了 {delete_count} 条旧记录")
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        获取所有记录（按时间倒序）
        
        Returns:
            List[Dict[str, Any]]: 所有记录列表
        """
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT timestamp, status, summary, anomaly_count, anomalies_json, error, duration_ms
                FROM polling_history 
                ORDER BY id DESC
            ''').fetchall()
            
            return [PollingRecord.from_db_row(dict(r)).to_dict() for r in rows]
    
    def get_latest(self, n: int = 1) -> List[Dict[str, Any]]:
        """
        获取最近 N 条记录
        
        Args:
            n: 记录数量
            
        Returns:
            List[Dict[str, Any]]: 记录列表
        """
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT timestamp, status, summary, anomaly_count, anomalies_json, error, duration_ms
                FROM polling_history 
                ORDER BY id DESC 
                LIMIT ?
            ''', (n,)).fetchall()
            
            return [PollingRecord.from_db_row(dict(r)).to_dict() for r in rows]
    
    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        按状态筛选记录
        
        Args:
            status: 状态值
            
        Returns:
            List[Dict[str, Any]]: 匹配的记录列表
        """
        with self._get_connection() as conn:
            rows = conn.execute('''
                SELECT timestamp, status, summary, anomaly_count, anomalies_json, error, duration_ms
                FROM polling_history 
                WHERE status = ? 
                ORDER BY id DESC
            ''', (status,)).fetchall()
            
            return [PollingRecord.from_db_row(dict(r)).to_dict() for r in rows]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            with self._get_connection() as conn:
                total = conn.execute('SELECT COUNT(*) FROM polling_history').fetchone()[0]
                
                if total == 0:
                    return {
                        "total": 0,
                        "normal": 0,
                        "warning": 0,
                        "critical": 0,
                        "error": 0,
                        "latest_timestamp": None,
                    }
                
                # 按状态统计
                status_counts = conn.execute('''
                    SELECT status, COUNT(*) as cnt 
                    FROM polling_history 
                    GROUP BY status
                ''').fetchall()
                
                counts = {"normal": 0, "warning": 0, "critical": 0, "error": 0}
                for row in status_counts:
                    if row["status"] in counts:
                        counts[row["status"]] = row["cnt"]
                
                # 获取最新和最早的时间戳
                timestamps = conn.execute('''
                    SELECT timestamp FROM polling_history 
                    WHERE id = (SELECT MIN(id) FROM polling_history) 
                       OR id = (SELECT MAX(id) FROM polling_history)
                    ORDER BY id ASC
                ''').fetchall()
                
                earliest_ts = timestamps[0]["timestamp"] if timestamps else None
                latest_ts = timestamps[-1]["timestamp"] if len(timestamps) > 1 else earliest_ts
                
                return {
                    "total": total,
                    "normal": counts["normal"],
                    "warning": counts["warning"],
                    "critical": counts["critical"],
                    "error": counts["error"],
                    "latest_timestamp": latest_ts,
                    "earliest_timestamp": earliest_ts,
                }
        except Exception as e:
            logger.warning(f"获取统计信息失败: {e}")
            return {
                "total": 0,
                "normal": 0,
                "warning": 0,
                "critical": 0,
                "error": 0,
                "latest_timestamp": None,
            }
    
    def clear(self) -> None:
        """
        清空所有历史记录
        """
        with self._get_connection() as conn:
            conn.execute('DELETE FROM polling_history')
            conn.commit()
            
            logger.info("历史记录已清空")
    
    def size(self) -> int:
        """
        获取记录数量
        
        Returns:
            int: 记录总数
        """
        try:
            with self._get_connection() as conn:
                return conn.execute('SELECT COUNT(*) FROM polling_history').fetchone()[0]
        except Exception as e:
            logger.warning(f"获取记录数量失败: {e}")
            return 0


_history_store: Optional[HistoryStore] = None


def get_history_store(max_records: int = 100) -> HistoryStore:
    """
    获取历史记录存储单例
    
    Args:
        max_records: 最大记录数（仅首次创建时生效）
        
    Returns:
        HistoryStore: 历史记录存储器实例
    """
    global _history_store
    if _history_store is None:
        _history_store = HistoryStore(max_records=max_records)
    return _history_store
