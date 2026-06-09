"""
FastAPI 应用模块
创建和配置 FastAPI 应用实例
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .routes.chat import router as chat_router
from .routes.monitor import router as monitor_router
from .routes.polling import router as polling_router
from .routes.config import router as config_router
from .routes.anomaly import router as anomaly_router
from .exceptions import register_exception_handlers


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    logger.info("开始创建 FastAPI 应用...")
    
    app = FastAPI(
        title="微服务运维智能体",
        description="用于微服务运维的智能体系统，提供健康检查、监控告警、故障诊断等功能",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS 中间件已配置（允许所有来源）")
    
    # 注册路由
    app.include_router(router, prefix="", tags=["通用接口"])
    app.include_router(chat_router)
    app.include_router(monitor_router)
    app.include_router(polling_router)
    app.include_router(config_router)
    app.include_router(anomaly_router)
    
    # 注册异常处理器
    register_exception_handlers(app)
    
    logger.info("FastAPI 应用创建完成")
    
    return app


app = create_app()
