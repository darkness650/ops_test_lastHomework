"""
日志配置模块
配置 Python logging 系统，实现日志脱敏过滤器
"""

import logging
import re
from typing import List, Optional

from .settings import get_settings


class SensitiveDataFilter(logging.Filter):
    """
    日志脱敏过滤器
    用于过滤日志中的敏感信息，如 API_KEY 等
    """
    
    def __init__(self, sensitive_keys: Optional[List[str]] = None):
        """
        初始化日志脱敏过滤器
        
        Args:
            sensitive_keys: 需要脱敏的敏感信息键名列表
        """
        super().__init__()
        # 默认的敏感信息键名
        self.sensitive_keys = sensitive_keys or [
            "api_key",
            "api-key",
            "apikey",
            "secret",
            "password",
            "token",
            "authorization",
            "auth",
        ]
        
    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录，对敏感信息进行脱敏处理
        
        Args:
            record: 日志记录对象
            
        Returns:
            bool: 始终返回 True，表示日志记录将被输出（但内容已脱敏）
        """
        # 获取日志消息（会执行一次 % 格式化）
        msg = record.getMessage()
        
        # 对日志消息进行脱敏
        record.msg = self._mask_sensitive_data(msg)
        
        # 关键：清空 args，防止 logging 模块再次尝试执行 msg % args 格式化
        # 因为 record.msg 已经是格式化后的完整字符串，再次格式化会报错
        record.args = ()
        
        # 对异常信息进行脱敏（如果存在）
        if record.exc_info and record.exc_info[2]:
            # 这里不直接修改 exc_info，因为它是元组
            # 我们通过在日志格式化后处理，或者使用其他方式
            pass
        
        return True
    
    def _mask_sensitive_data(self, text: str) -> str:
        """
        对文本中的敏感信息进行脱敏处理
        
        Args:
            text: 原始文本
            
        Returns:
            str: 脱敏后的文本
        """
        result = text
        
        # 1. 处理键值对形式的敏感信息，如 api_key=xxx 或 "api_key": "xxx"
        for key in self.sensitive_keys:
            # 匹配 api_key=xxx 或 api-key=xxx 等形式
            pattern1 = rf'({re.escape(key)}[=:]\s*)["\']?[^"\',\s]+["\']?'
            result = re.sub(pattern1, r'\1"****"', result, flags=re.IGNORECASE)
            
            # 匹配 "api_key": "xxx" 形式
            pattern2 = rf'["\']{re.escape(key)}["\']\s*[:=]\s*["\'][^"\']+["\']'
            result = re.sub(
                pattern2, 
                f'"{key}": "****"', 
                result, 
                flags=re.IGNORECASE
            )
        
        # 2. 处理常见的 Token 格式（如 Bearer token）
        result = re.sub(
            r'Bearer\s+[A-Za-z0-9._-]+',
            'Bearer ****',
            result
        )
        
        # 3. 处理 API Key 常见格式（较长的随机字符串）
        # 匹配 sk- 开头的密钥（如 OpenAI 风格）
        result = re.sub(
            r'sk-[A-Za-z0-9_-]{20,}',
            'sk-****',
            result
        )
        
        # 匹配类似密钥的长字符串（20个字符以上的字母数字组合）
        # 注意：这个匹配可能会有误匹配，所以放在最后
        result = re.sub(
            r'(?<![A-Za-z0-9])[A-Za-z0-9]{30,}(?![A-Za-z0-9])',
            '****',
            result
        )
        
        return result


def setup_logging() -> None:
    """
    配置日志系统
    """
    # 获取配置
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # 清除已有的处理器（避免重复输出）
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建格式化器：包含时间、级别、模块名、消息
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 添加日志脱敏过滤器
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    # 将处理器添加到根日志记录器
    logger.addHandler(console_handler)
    
    # 记录配置完成的日志
    logger.info(f"日志系统配置完成，日志级别: {settings.log_level}")
