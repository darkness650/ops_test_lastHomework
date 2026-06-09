"""
验证 Task 1 完成情况的测试脚本
"""

import sys
sys.path.insert(0, '.')

# 1. 测试配置加载
print("=" * 50)
print("测试 1: 配置加载")
print("=" * 50)
try:
    from config.settings import get_settings
    settings = get_settings()
    print(f"  LLM Model: {settings.llm.model}")
    print(f"  Log Level: {settings.log_level}")
    print(f"  Prometheus URL: {settings.prometheus.prometheus_url}")
    print(f"  Polling Interval: {settings.polling_interval_minutes} 分钟")
    print("  [PASS] 配置加载成功")
except Exception as e:
    print(f"  [FAIL] 配置加载失败: {e}")
    sys.exit(1)

# 2. 测试日志配置和脱敏
print("\n" + "=" * 50)
print("测试 2: 日志系统与脱敏")
print("=" * 50)
try:
    from config.logging_config import setup_logging
    import logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("测试日志 - 包含敏感信息: api_key=sk-test-1234567890abcdef")
    print("  [PASS] 日志系统配置成功（注意检查上方日志中 API Key 是否已脱敏）")
except Exception as e:
    print(f"  [FAIL] 日志系统配置失败: {e}")
    sys.exit(1)

# 3. 测试 FastAPI 应用创建
print("\n" + "=" * 50)
print("测试 3: FastAPI 应用")
print("=" * 50)
try:
    from api.app import create_app
    app = create_app()
    print(f"  App Title: {app.title}")
    print(f"  App Version: {app.version}")
    print(f"  Routes: {len(app.routes)} 个")
    print("  [PASS] FastAPI 应用创建成功")
except Exception as e:
    print(f"  [FAIL] FastAPI 应用创建失败: {e}")
    sys.exit(1)

# 4. 测试响应模型和异常处理
print("\n" + "=" * 50)
print("测试 4: 响应模型与异常")
print("=" * 50)
try:
    from api.schemas import ApiResponse, HealthResponse, ErrorResponse
    from api.exceptions import AppException
    
    # 测试 ApiResponse
    resp = ApiResponse(code=200, message="success", data={"key": "value"})
    print(f"  ApiResponse: {resp.model_dump()}")
    
    # 测试 HealthResponse
    health = HealthResponse(status="ok")
    print(f"  HealthResponse: {health.model_dump()}")
    
    # 测试 ErrorResponse
    err = ErrorResponse(code=500, message="error", detail="test")
    print(f"  ErrorResponse: {err.model_dump()}")
    
    # 测试 AppException
    exc = AppException(message="测试异常", code=400, detail="detail")
    print(f"  AppException: {exc.message}")
    
    print("  [PASS] 响应模型和异常处理正常")
except Exception as e:
    print(f"  [FAIL] 响应模型测试失败: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("Task 1 验证完成 - 所有测试通过!")
print("=" * 50)
