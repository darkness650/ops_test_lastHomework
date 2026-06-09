"""
应用入口模块
初始化配置、日志系统，并启动 FastAPI 应用
"""

import uvicorn

from config import setup_logging
from api import app


def main() -> None:
    """
    主函数
    初始化日志系统，启动 FastAPI 应用
    """
    # 配置日志系统
    setup_logging()
    
    # 启动 Uvicorn 服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        access_log=True
    )


if __name__ == "__main__":
    main()
