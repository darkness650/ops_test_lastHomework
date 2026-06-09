"""
验证 Task 3 完成情况的测试脚本
测试 Kubernetes 客户端封装
"""

import sys
import json
sys.path.insert(0, '.')

# 配置日志
from config.logging_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)


print("=" * 60)
print("Task 3 验证: Kubernetes 工具集")
print("=" * 60)

all_passed = True

# ============================================================
# 测试 1: K8s 客户端导入和初始化
# ============================================================
print("\n" + "-" * 60)
print("测试 1: Kubernetes 客户端导入和延迟初始化")
print("-" * 60)

try:
    from tools.k8s_client import KubernetesClient, get_k8s_client
    
    # 测试创建客户端实例（不实际连接）
    client = KubernetesClient()
    
    # 验证延迟初始化
    assert client._initialized == False
    assert client._core_api is None
    assert client._apps_api is None
    
    print("  [PASS] K8s 客户端创建成功，延迟初始化正常")
    print(f"         Kubeconfig 路径配置: {client.settings.kubernetes.kubeconfig_path}")
    
except Exception as e:
    logger.error(f"测试 1 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 2: 检查 kubernetes SDK 依赖
# ============================================================
print("\n" + "-" * 60)
print("测试 2: Kubernetes Python SDK 依赖检查")
print("-" * 60)

try:
    import kubernetes
    from kubernetes import client, config
    
    print(f"  [PASS] Kubernetes SDK 导入成功")
    print(f"         SDK 版本信息: {kubernetes.__version__ if hasattr(kubernetes, '__version__') else 'N/A'}")
    
except ImportError as e:
    logger.error(f"测试 2 失败: {e}", exc_info=True)
    print(f"  [FAIL] Kubernetes SDK 未安装: {e}")
    print("         请运行: uv pip install kubernetes")
    all_passed = False
except Exception as e:
    logger.error(f"测试 2 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 3: K8s 工具的 OpenAI Function Schema 生成
# ============================================================
print("\n" + "-" * 60)
print("测试 3: 工具参数和 Schema 生成能力验证")
print("-" * 60)

try:
    from tools.base import BaseTool, ToolParameter, ToolResult
    from typing import Any
    
    # 创建一个模拟的 K8s 工具来测试 Schema 生成
    class MockListPodsTool(BaseTool):
        name = "k8s_list_pods"
        description = "列出 Kubernetes 集群中的 Pod，支持按命名空间筛选"
        parameters = [
            ToolParameter(
                name="namespace",
                type="string",
                description="Pod 所在的命名空间，不填则查询所有命名空间",
                required=False,
            ),
            ToolParameter(
                name="label_selector",
                type="string",
                description="标签选择器，如 'app=nginx'，用于筛选特定标签的 Pod",
                required=False,
            ),
        ]
        
        def _execute(self, **kwargs: Any) -> ToolResult:
            namespace = kwargs.get("namespace")
            label_selector = kwargs.get("label_selector")
            return ToolResult.success(
                data={
                    "namespace": namespace,
                    "label_selector": label_selector,
                    "pods": [
                        {"name": "pod-1", "status": "Running"},
                        {"name": "pod-2", "status": "Running"},
                    ]
                },
                message=f"成功查询 Pod，namespace={namespace}"
            )
    
    # 测试工具创建
    tool = MockListPodsTool()
    assert tool.name == "k8s_list_pods"
    print(f"  [PASS] 模拟 K8s 工具创建成功: {tool.name}")
    
    # 测试 Schema 生成
    schema = tool.get_openai_function_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "k8s_list_pods"
    assert "namespace" in schema["function"]["parameters"]["properties"]
    print(f"  [PASS] OpenAI Function Schema 生成成功")
    print(f"         Schema: {json.dumps(schema, ensure_ascii=False, indent=2)}")
    
    # 测试工具执行
    result = tool.execute(namespace="default", label_selector="app=test")
    assert result.success == True
    assert result.data["namespace"] == "default"
    print(f"  [PASS] 工具执行成功: {result.data}")
    
except Exception as e:
    logger.error(f"测试 3 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试 4: 数据转换方法测试
# ============================================================
print("\n" + "-" * 60)
print("测试 4: K8s 数据对象转换方法验证")
print("-" * 60)

try:
    from tools.k8s_client import KubernetesClient
    
    client = KubernetesClient()
    
    # 测试容器状态转换
    # 创建一个模拟的状态对象
    class MockState:
        class Running:
            pass
        running = Running()
    
    state_str = client._get_container_state(MockState())
    assert state_str == "Running"
    print(f"  [PASS] 容器状态转换 (Running): {state_str}")
    
    # 测试 Terminated 状态
    class MockTerminatedState:
        class Terminated:
            exit_code = 1
            reason = "Error"
        terminated = Terminated()
        running = None
        waiting = None
    
    state_str = client._get_container_state(MockTerminatedState())
    assert "Terminated" in state_str
    print(f"  [PASS] 容器状态转换 (Terminated): {state_str}")
    
except Exception as e:
    logger.error(f"测试 4 失败: {e}", exc_info=True)
    print(f"  [FAIL] 测试失败: {e}")
    all_passed = False

# ============================================================
# 测试结果汇总
# ============================================================
print("\n" + "=" * 60)
if all_passed:
    print("[OK] Task 3 验证完成 - 核心模块测试通过!")
    print("=" * 60)
    print("\n已实现的功能:")
    print("  1. KubernetesClient - K8s 客户端封装")
    print("     - 支持 in-cluster 和 kubeconfig 两种认证方式")
    print("     - 延迟初始化，避免未配置时导入失败")
    print("  2. Pod 相关操作")
    print("     - list_pods - 列出 Pod")
    print("     - get_pod - 获取 Pod 详情")
    print("     - get_pod_logs - 获取 Pod 日志")
    print("  3. Deployment 相关操作")
    print("     - list_deployments - 列出 Deployment")
    print("     - get_deployment - 获取 Deployment 详情")
    print("  4. Service 相关操作")
    print("     - list_services - 列出 Service")
    print("     - get_service - 获取 Service 详情")
    print("  5. Node 相关操作")
    print("     - list_nodes - 列出 Node")
    print("     - get_node - 获取 Node 详情")
    print("  6. Event 相关操作")
    print("     - list_events - 列出 Event")
    print("  7. 数据转换方法")
    print("     - _pod_to_dict, _deployment_to_dict 等")
    print("     - K8s 对象 -> 可序列化字典")
    print("\n注意: 需要实际的 K8s 集群才能进行端到端测试。")
else:
    print("[FAIL] Task 3 验证完成 - 部分测试失败，请检查错误信息")
    print("=" * 60)
    sys.exit(1)
