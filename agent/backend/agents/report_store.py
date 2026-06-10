"""
性能报告存储模块
提供 JSON 文件持久化存储，保存性能分析报告
"""

import json
import logging
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class ReportStore:
    """
    性能报告存储器
    使用 JSON 文件持久化存储性能分析报告
    支持保存、查询、分页列表、删除和自动清理
    """
    
    def __init__(self, max_records: int = 100, storage_dir: Optional[str] = None):
        """
        初始化报告存储器
        
        Args:
            max_records: 最大记录数，超过时自动清理最旧的报告
            storage_dir: 存储目录路径，默认为 backend/data/reports/
        """
        self.max_records = max_records
        self._lock = threading.Lock()
        
        # 设置存储目录
        if storage_dir:
            self._storage_dir = Path(storage_dir)
        else:
            # 默认存储路径：backend/data/reports/
            backend_dir = Path(__file__).resolve().parent.parent
            self._storage_dir = backend_dir / "data" / "reports"
        
        # 确保存储目录存在
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"报告存储初始化完成，最大记录数: {max_records}, 存储目录: {self._storage_dir}")
    
    def _get_file_pattern(self) -> str:
        """
        获取报告文件的通配符模式
        
        Returns:
            str: 通配符模式
        """
        return "*.json"
    
    def _parse_filename(self, filename: str) -> Optional[tuple]:
        """
        解析文件名，提取时间戳和报告ID
        
        文件名格式：{timestamp}_{report_id}.json
        
        Args:
            filename: 文件名
            
        Returns:
            Optional[tuple]: (timestamp, report_id) 或 None
        """
        match = re.match(r'^(\d+)_(.+)\.json$', filename)
        if match:
            return int(match.group(1)), match.group(2)
        return None
    
    def _list_files(self) -> List[tuple]:
        """
        列出所有报告文件，按时间戳排序（从旧到新）
        
        Returns:
            List[tuple]: [(timestamp, report_id, file_path), ...]
        """
        files = []
        pattern = self._get_file_pattern()
        
        for file_path in self._storage_dir.glob(pattern):
            if file_path.is_file():
                parsed = self._parse_filename(file_path.name)
                if parsed:
                    timestamp, report_id = parsed
                    files.append((timestamp, report_id, file_path))
        
        # 按时间戳排序（从旧到新）
        files.sort(key=lambda x: x[0])
        return files
    
    def _find_file_by_id(self, report_id: str) -> Optional[Path]:
        """
        根据报告ID查找文件路径
        
        Args:
            report_id: 报告ID
            
        Returns:
            Optional[Path]: 文件路径，不存在则返回 None
        """
        pattern = f"*_{report_id}.json"
        matches = list(self._storage_dir.glob(pattern))
        return matches[0] if matches else None
    
    def _generate_report_id(self) -> str:
        """
        生成唯一的报告ID
        
        Returns:
            str: 报告ID
        """
        return f"report_{uuid.uuid4().hex[:12]}"
    
    def save(self, report: Dict[str, Any]) -> str:
        """
        保存报告到本地 JSON 文件
        
        Args:
            report: 报告数据字典，与 PerformanceReport 模型兼容
            
        Returns:
            str: 报告ID
        """
        with self._lock:
            # 生成报告ID（如果没有提供）
            report_id = report.get("id") or self._generate_report_id()
            report["id"] = report_id
            
            # 设置创建时间（如果没有提供）
            if "created_at" not in report:
                report["created_at"] = datetime.now().isoformat()
            
            # 生成文件名：{timestamp}_{report_id}.json
            timestamp = int(datetime.now().timestamp() * 1000)
            filename = f"{timestamp}_{report_id}.json"
            file_path = self._storage_dir / filename
            
            # 保存到文件
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                
                logger.info(f"报告已保存: report_id={report_id}, 文件={file_path}")
                
                # 清理旧记录
                self._cleanup_old_records()
                
                return report_id
            except Exception as e:
                logger.error(f"保存报告失败: report_id={report_id}, 错误={e}")
                raise
    
    def get(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        按 ID 查询报告
        
        Args:
            report_id: 报告ID
            
        Returns:
            Optional[Dict[str, Any]]: 报告数据，不存在则返回 None
        """
        with self._lock:
            file_path = self._find_file_by_id(report_id)
            
            if not file_path:
                logger.debug(f"报告不存在: report_id={report_id}")
                return None
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                
                logger.debug(f"已读取报告: report_id={report_id}")
                return report
            except Exception as e:
                logger.error(f"读取报告失败: report_id={report_id}, 错误={e}")
                return None
    
    def list(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        分页列表查询（按时间倒序）
        
        Args:
            page: 页码，从 1 开始
            page_size: 每页数量
            
        Returns:
            Dict[str, Any]: 分页结果，包含 total, page, page_size, reports
        """
        with self._lock:
            # 获取所有文件并按时间倒序排序
            files = self._list_files()
            files.reverse()  # 从新到旧
            
            total = len(files)
            
            # 计算分页
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 10
            
            start = (page - 1) * page_size
            end = start + page_size
            
            # 读取当前页的报告
            reports = []
            for _, _, file_path in files[start:end]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        report = json.load(f)
                        reports.append(report)
                except Exception as e:
                    logger.warning(f"读取报告文件失败: {file_path}, 错误={e}")
                    continue
            
            logger.debug(f"分页查询: page={page}, page_size={page_size}, total={total}")
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "reports": reports,
            }
    
    def delete(self, report_id: str) -> bool:
        """
        删除报告
        
        Args:
            report_id: 报告ID
            
        Returns:
            bool: 是否删除成功
        """
        with self._lock:
            file_path = self._find_file_by_id(report_id)
            
            if not file_path:
                logger.debug(f"报告不存在，无法删除: report_id={report_id}")
                return False
            
            try:
                file_path.unlink()
                logger.info(f"报告已删除: report_id={report_id}")
                return True
            except Exception as e:
                logger.error(f"删除报告失败: report_id={report_id}, 错误={e}")
                return False
    
    def size(self) -> int:
        """
        获取总报告数量
        
        Returns:
            int: 报告总数
        """
        with self._lock:
            return len(self._list_files())
    
    def _cleanup_old_records(self):
        """
        清理超过限制的旧记录
        当记录数超过 max_records 时，删除最旧的记录
        """
        files = self._list_files()
        count = len(files)
        
        if count > self.max_records:
            delete_count = count - self.max_records
            files_to_delete = files[:delete_count]  # 最旧的记录
            
            for timestamp, report_id, file_path in files_to_delete:
                try:
                    file_path.unlink()
                    logger.debug(f"清理旧报告: report_id={report_id}")
                except Exception as e:
                    logger.warning(f"清理旧报告失败: report_id={report_id}, 错误={e}")
            
            logger.info(f"已清理 {delete_count} 条旧报告")


# 单例实例
_report_store: Optional[ReportStore] = None
# 单例锁
_report_store_lock = threading.Lock()


def get_report_store(max_records: int = 100, storage_dir: Optional[str] = None) -> ReportStore:
    """
    获取报告存储单例
    
    Args:
        max_records: 最大记录数（仅首次创建时生效）
        storage_dir: 存储目录路径（仅首次创建时生效）
        
    Returns:
        ReportStore: 报告存储器实例
    """
    global _report_store
    
    if _report_store is None:
        with _report_store_lock:
            if _report_store is None:
                _report_store = ReportStore(
                    max_records=max_records,
                    storage_dir=storage_dir
                )
    
    return _report_store
