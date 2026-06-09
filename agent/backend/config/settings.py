"""
配置管理模块
使用 Pydantic Settings 管理应用配置，支持从 .env 文件和环境变量加载配置
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# 获取 .env 文件的绝对路径
# 假设 settings.py 在 backend/config/ 目录下，.env 在 backend/ 目录下
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class LLMSettings(BaseSettings):
    """
    LLM（大语言模型）配置
    """
    # LLM API 基础 URL
    base_url: str = Field(alias="BASE_URL", default="https://api.openai.com/v1")
    # API 密钥（敏感信息）
    api_key: str = Field(alias="API_KEY", default="")
    # 使用的模型名称
    model: str = Field(alias="MODEL", default="gpt-4")
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class KubernetesSettings(BaseSettings):
    """
    Kubernetes 配置（可选）
    """
    # Kubeconfig 文件路径，如果为空则使用默认路径
    kubeconfig_path: Optional[str] = Field(alias="KUBECONFIG_PATH", default=None)
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class PrometheusSettings(BaseSettings):
    """
    Prometheus 配置
    """
    # Prometheus 服务地址
    prometheus_url: str = Field(alias="PROMETHEUS_URL", default="http://localhost:9090")
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class ElasticSearchSettings(BaseSettings):
    """
    ElasticSearch 配置（可选）
    """
    # ElasticSearch 服务地址
    es_url: Optional[str] = Field(alias="ES_URL", default=None)
    # 索引名称
    es_index: Optional[str] = Field(alias="ES_INDEX", default=None)
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


class Settings(BaseSettings):
    """
    应用全局配置
    """
    # LLM 配置
    llm: LLMSettings = Field(default_factory=LLMSettings)
    # Kubernetes 配置
    kubernetes: KubernetesSettings = Field(default_factory=KubernetesSettings)
    # Prometheus 配置
    prometheus: PrometheusSettings = Field(default_factory=PrometheusSettings)
    # ElasticSearch 配置
    elasticsearch: ElasticSearchSettings = Field(default_factory=ElasticSearchSettings)
    
    # 轮询配置：多少分钟轮询一次
    polling_interval_minutes: int = Field(alias="POLLING_INTERVAL_MINUTES", default=5)
    # 日志级别
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    
    @property
    def llm_configured(self) -> bool:
        """
        检查 LLM 是否配置完成
        
        Returns:
            bool: True 表示已配置 API 密钥和基础 URL
        """
        return bool(self.llm.api_key and self.llm.base_url)


# 创建全局配置单例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    获取全局配置单例
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
