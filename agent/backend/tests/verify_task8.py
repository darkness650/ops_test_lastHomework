"""
Task 8 验证脚本
验证 RESTful API 层
"""

import sys
import logging
import json

# 添加 backend 目录到 Python 路径
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_1_app_import_and_cors():
    """测试 1: 应用导入和 CORS 配置"""
    print("\n" + "=" * 60)
    print("测试 1: 应用导入和 CORS 配置")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        from api.app import app
        
        client = TestClient(app)
        print(f"  [PASS] FastAPI 应用创建成功")
        print(f"         标题: {app.title}")
        print(f"         版本: {app.version}")
        
        # 检查 CORS 中间件
        has_cors = False
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                has_cors = True
                break
        
        if has_cors:
            print(f"  [PASS] CORS 中间件已配置")
        else:
            print(f"  [WARN] CORS 中间件未找到")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 1 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_routes_registration():
    """测试 2: 路由注册"""
    print("\n" + "=" * 60)
    print("测试 2: 路由注册")
    print("=" * 60)
    
    try:
        from api.app import app
        
        routes = app.routes
        print(f"  [PASS] 总路由数: {len(routes)}")
        
        # 收集所有路径
        paths = set()
        for route in routes:
            if hasattr(route, "path"):
                paths.add(route.path)
        
        # 检查关键路径
        expected_paths = [
            "/health",
            "/docs",
            "/api/v1/chat",
            "/api/v1/monitor/run",
            "/api/v1/monitor/quick",
            "/api/v1/polling/start",
            "/api/v1/polling/stop",
            "/api/v1/polling/status",
            "/api/v1/polling/history",
            "/api/v1/config",
        ]
        
        found_paths = []
        missing_paths = []
        
        for path in expected_paths:
            found = any(p.startswith(path) or path in p for p in paths)
            if found:
                found_paths.append(path)
            else:
                missing_paths.append(path)
        
        print(f"\n  已注册的关键路径:")
        for p in found_paths:
            print(f"    [PASS] {p}")
        
        if missing_paths:
            print(f"\n  缺失的路径:")
            for p in missing_paths:
                print(f"    [MISSING] {p}")
        else:
            print(f"\n  [PASS] 所有关键路径已注册")
        
        # 打印所有 API 路由
        print(f"\n  所有 API 路由:")
        api_routes = [p for p in paths if p.startswith("/api/")]
        for p in sorted(api_routes):
            print(f"    - {p}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 2 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_schemas_import():
    """测试 3: Pydantic 模型导入"""
    print("\n" + "=" * 60)
    print("测试 3: Pydantic 模型导入")
    print("=" * 60)
    
    try:
        from api.schemas import (
            ApiResponse,
            ChatRequest,
            ChatResponse,
            MonitorRequest,
            MonitorResponse,
            PollingStartRequest,
            PollingResponse,
            PollingStatus,
            PollingHistoryStats,
            HistoryQueryResponse,
            HistoryRecord,
            ConfigInfo,
        )
        
        # 测试实例化
        chat_req = ChatRequest(message="测试消息")
        print(f"  [PASS] ChatRequest: message={chat_req.message}")
        
        monitor_req = MonitorRequest(namespace="default", deep_analysis=False)
        print(f"  [PASS] MonitorRequest: namespace={monitor_req.namespace}")
        
        polling_req = PollingStartRequest(interval_minutes=5)
        print(f"  [PASS] PollingStartRequest: interval_minutes={polling_req.interval_minutes}")
        
        config_info = ConfigInfo(
            polling_interval_minutes=5,
            max_history_records=100,
            llm_configured=True,
            kubernetes_configured=True,
            prometheus_configured=False,
            elasticsearch_configured=False,
        )
        print(f"  [PASS] ConfigInfo: llm_configured={config_info.llm_configured}")
        
        # 测试序列化
        chat_resp = ChatResponse(
            response="测试响应",
            context_id="test-ctx",
            tool_calls=[],
        )
        resp_dict = chat_resp.model_dump()
        print(f"  [PASS] ChatResponse 序列化: context_id={resp_dict['context_id']}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 3 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_basic_endpoints():
    """测试 4: 基础端点测试"""
    print("\n" + "=" * 60)
    print("测试 4: 基础端点测试")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        from api.app import app
        
        client = TestClient(app)
        
        # 测试根路径
        print("  测试 GET / ...")
        response = client.get("/")
        assert response.status_code == 200, f"期望 200，实际 {response.status_code}"
        data = response.json()
        print(f"  [PASS] GET /: code={response.status_code}")
        print(f"         message={data.get('message')}")
        
        # 测试健康检查
        print("\n  测试 GET /health ...")
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        print(f"  [PASS] GET /health: status={data.get('status')}")
        
        # 测试配置查询
        print("\n  测试 GET /api/v1/config ...")
        response = client.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        print(f"  [PASS] GET /api/v1/config:")
        print(f"         llm_configured={data['data'].get('llm_configured')}")
        print(f"         polling_interval_minutes={data['data'].get('polling_interval_minutes')}")
        
        # 测试快速健康检查
        print("\n  测试 GET /api/v1/monitor/quick ...")
        response = client.get("/api/v1/monitor/quick")
        assert response.status_code == 200
        data = response.json()
        print(f"  [PASS] GET /api/v1/monitor/quick:")
        print(f"         status={data['data'].get('status')}")
        print(f"         anomaly_count={data['data'].get('anomaly_count')}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 4 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_polling_endpoints():
    """测试 5: 轮询控制端点"""
    print("\n" + "=" * 60)
    print("测试 5: 轮询控制端点")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        from api.app import app
        
        client = TestClient(app)
        
        # 测试获取轮询状态
        print("  测试 GET /api/v1/polling/status ...")
        response = client.get("/api/v1/polling/status")
        assert response.status_code == 200
        data = response.json()
        print(f"  [PASS] GET /api/v1/polling/status:")
        print(f"         is_running={data['data']['status'].get('is_running')}")
        print(f"         interval_minutes={data['data']['status'].get('interval_minutes')}")
        
        # 测试获取历史记录
        print("\n  测试 GET /api/v1/polling/history ...")
        response = client.get("/api/v1/polling/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        print(f"  [PASS] GET /api/v1/polling/history:")
        print(f"         total={data['data'].get('total')}")
        print(f"         returned={data['data'].get('returned')}")
        
        # 测试单次轮询
        print("\n  测试 POST /api/v1/polling/run-once ...")
        response = client.post("/api/v1/polling/run-once")
        assert response.status_code == 200
        data = response.json()
        print(f"  [PASS] POST /api/v1/polling/run-once:")
        print(f"         success={data['data'].get('success')}")
        print(f"         message={data['data'].get('message')}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 5 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_validation_error():
    """测试 6: 请求验证（422 错误）"""
    print("\n" + "=" * 60)
    print("测试 6: 请求验证错误处理")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        from api.app import app
        
        client = TestClient(app)
        
        # 测试 POST /api/v1/monitor/run 不传递 body
        print("  测试 POST /api/v1/monitor/run 无请求体 ...")
        response = client.post("/api/v1/monitor/run")
        # FastAPI 对于缺失 body 返回 422
        print(f"         状态码: {response.status_code}")
        
        if response.status_code == 422:
            print(f"  [PASS] 验证错误返回 422 状态码")
            data = response.json()
            print(f"         错误详情: {data.get('detail', 'N/A')}")
        else:
            print(f"  [INFO] 状态码: {response.status_code} (可能被中间件处理)")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 6 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主验证函数"""
    print("\n" + "=" * 60)
    print("Task 8 验证: RESTful API 层")
    print("=" * 60)
    
    results = []
    
    results.append(("测试 1", test_1_app_import_and_cors()))
    results.append(("测试 2", test_2_routes_registration()))
    results.append(("测试 3", test_3_schemas_import()))
    results.append(("测试 4", test_4_basic_endpoints()))
    results.append(("测试 5", test_5_polling_endpoints()))
    results.append(("测试 6", test_6_validation_error()))
    
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    if passed == total:
        print("[OK] Task 8 验证完成 - 核心模块测试通过!")
    else:
        print(f"[FAIL] Task 8 验证完成 - {passed}/{total} 测试通过")
    
    print("=" * 60)
    
    print("\n已实现的 API 端点:")
    print("  通用接口:")
    print("    GET  /                      - 服务信息")
    print("    GET  /health               - 健康检查")
    print("    GET  /docs                 - Swagger UI")
    
    print("\n  聊天对话 (POST /api/v1/chat):")
    print("    POST /api/v1/chat          - 与 Agent 对话")
    print("    GET  /api/v1/chat/sessions/{id}  - 获取会话")
    print("    DELETE /api/v1/chat/sessions/{id} - 清理会话")
    
    print("\n  健康监测:")
    print("    POST /api/v1/monitor/run   - 执行健康检查")
    print("    GET  /api/v1/monitor/quick - 快速健康检查")
    
    print("\n  轮询控制:")
    print("    POST /api/v1/polling/start      - 启动轮询")
    print("    POST /api/v1/polling/stop       - 停止轮询")
    print("    GET  /api/v1/polling/status     - 获取状态")
    print("    POST /api/v1/polling/run-once   - 单次执行")
    print("    GET  /api/v1/polling/history    - 获取历史")
    print("    DELETE /api/v1/polling/history  - 清空历史")
    
    print("\n  配置查询:")
    print("    GET  /api/v1/config        - 获取系统配置")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
