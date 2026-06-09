"""
Task 4 和 Task 5 验证脚本
验证日志工具（Task 4）和 Prometheus 工具（Task 5）的核心功能
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


def test_1_k8s_logs_tool_import():
    """测试 1: K8s 日志工具导入和 Schema 生成"""
    print("\n" + "=" * 60)
    print("测试 1: K8s 日志工具导入和 Schema 生成")
    print("=" * 60)
    
    try:
        from tools.logs import K8sLogsTool
        from tools.base import ToolRegistry
        
        # 测试工具创建
        tool = K8sLogsTool()
        print(f"  [PASS] K8sLogsTool 创建成功: {tool.name}")
        
        # 测试参数定义
        print(f"         工具描述: {tool.description[:80]}...")
        print(f"         参数数量: {len(tool.parameters)}")
        
        # 打印参数信息
        for param in tool.parameters:
            req = "(必需)" if param.required else "(可选)"
            print(f"           - {param.name}: {param.type} {req}")
        
        # 测试 OpenAI Schema 生成
        registry = ToolRegistry()
        registry.register_class(K8sLogsTool)
        
        schemas = registry.get_openai_functions()
        if schemas:
            print(f"\n  [PASS] OpenAI Function Schema 生成成功")
            print(f"         Schema: {json.dumps(schemas[0], ensure_ascii=False, indent=2)[:400]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 1 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_es_logs_tool_import():
    """测试 2: ElasticSearch 日志工具导入和 Schema 生成"""
    print("\n" + "=" * 60)
    print("测试 2: ElasticSearch 日志工具导入和 Schema 生成")
    print("=" * 60)
    
    try:
        from tools.logs import ElasticSearchLogsTool
        from tools.base import ToolRegistry
        
        # 测试工具创建
        tool = ElasticSearchLogsTool()
        print(f"  [PASS] ElasticSearchLogsTool 创建成功: {tool.name}")
        
        # 测试参数定义
        print(f"         工具描述: {tool.description[:80]}...")
        print(f"         参数数量: {len(tool.parameters)}")
        
        # 测试 _build_query 方法
        print("\n  测试查询 DSL 构建...")
        query = tool._build_query(
            namespace="default",
            pod_name="nginx",
            container=None,
            keyword="error",
            start_time=None,
            end_time=None,
            last_minutes=15,
        )
        
        print(f"  [PASS] 查询 DSL 构建成功")
        print(f"         Query: {json.dumps(query, ensure_ascii=False, indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 2 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_prometheus_client_import():
    """测试 3: Prometheus 客户端导入和延迟初始化"""
    print("\n" + "=" * 60)
    print("测试 3: Prometheus 客户端导入和延迟初始化")
    print("=" * 60)
    
    try:
        from tools.prometheus import PrometheusClient, get_prometheus_client
        
        # 测试创建（延迟初始化）
        client = PrometheusClient(base_url="http://localhost:9090")
        print(f"  [PASS] PrometheusClient 创建成功")
        print(f"         base_url: {client.base_url}")
        print(f"         _initialized: {client._initialized} (延迟初始化)")
        
        # 测试单例
        singleton = get_prometheus_client()
        print(f"\n  [PASS] Prometheus 客户端单例获取成功")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 3 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_prometheus_tools_import():
    """测试 4: Prometheus 工具导入和 Schema 生成"""
    print("\n" + "=" * 60)
    print("测试 4: Prometheus 工具导入和 Schema 生成")
    print("=" * 60)
    
    try:
        from tools.prometheus import PrometheusQueryTool, ClusterMetricsTool
        from tools.base import ToolRegistry
        
        # 测试 PrometheusQueryTool
        tool1 = PrometheusQueryTool()
        print(f"  [PASS] PrometheusQueryTool 创建成功: {tool1.name}")
        print(f"         参数数量: {len(tool1.parameters)}")
        
        # 测试 ClusterMetricsTool
        tool2 = ClusterMetricsTool()
        print(f"  [PASS] ClusterMetricsTool 创建成功: {tool2.name}")
        print(f"         参数数量: {len(tool2.parameters)}")
        
        # 测试 Schema 生成
        registry = ToolRegistry()
        registry.register_class(PrometheusQueryTool)
        registry.register_class(ClusterMetricsTool)
        
        schemas = registry.get_openai_functions()
        print(f"\n  [PASS] 注册了 {len(schemas)} 个 Prometheus 工具")
        
        for schema in schemas:
            func_name = schema["function"]["name"]
            print(f"         - {func_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 4 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_tools_execution_simulated():
    """测试 5: 模拟工具执行（无实际连接）"""
    print("\n" + "=" * 60)
    print("测试 5: 模拟工具执行（未配置服务时的失败处理）")
    print("=" * 60)
    
    all_passed = True
    
    # 1. 测试 K8s 日志工具（无 K8s 集群时）
    try:
        from tools.logs import K8sLogsTool
        tool = K8sLogsTool()
        result = tool.execute(pod_name="test-pod", namespace="default")
        print(f"  [PASS] K8s 日志工具执行返回格式正确")
        print(f"         success: {result.success}")
        print(f"         message: {result.message[:60]}...")
    except Exception as e:
        logger.error(f"K8s 日志工具测试失败: {e}")
        all_passed = False
    
    # 2. 测试 Prometheus 工具（无 Prometheus 时）
    try:
        from tools.prometheus import PrometheusQueryTool
        tool = PrometheusQueryTool()
        result = tool.execute(
            query='sum(container_cpu_usage_seconds_total)'
        )
        print(f"\n  [PASS] Prometheus 工具执行返回格式正确")
        print(f"         success: {result.success}")
        print(f"         message: {result.message}")
    except Exception as e:
        logger.error(f"Prometheus 工具测试失败: {e}")
        all_passed = False
    
    return all_passed


def main():
    """主验证函数"""
    print("\n" + "=" * 60)
    print("Task 4 & Task 5 验证: 日志工具 + Prometheus 工具")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("测试 1", test_1_k8s_logs_tool_import()))
    results.append(("测试 2", test_2_es_logs_tool_import()))
    results.append(("测试 3", test_3_prometheus_client_import()))
    results.append(("测试 4", test_4_prometheus_tools_import()))
    results.append(("测试 5", test_5_tools_execution_simulated()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    if passed == total:
        print("[OK] Task 4 & Task 5 验证完成 - 核心模块测试通过!")
    else:
        print(f"[FAIL] Task 4 & Task 5 验证完成 - {passed}/{total} 测试通过")
    
    print("=" * 60)
    
    # 功能清单
    print("\n已实现的功能:")
    print("  Task 4: 日志查询工具")
    print("    1. K8sLogsTool - Pod 日志查询")
    print("       - 支持 tail_lines、since_seconds 两种方式")
    print("       - 支持 previous（上一个容器日志）")
    print("       - 支持 keyword_filter 关键词过滤")
    print("       - 日志截断保护（最大 50000 字符）")
    print("    2. ElasticSearchLogsTool - ES 日志查询")
    print("       - 支持按 namespace、pod、container 筛选")
    print("       - 支持关键词全文搜索")
    print("       - 支持时间范围查询")
    print("       - 智能 DSL 构建")
    print("    3. 注册函数 register_logs_tools()")
    
    print("\n  Task 5: Prometheus 指标工具")
    print("    1. PrometheusClient - Prometheus API 客户端")
    print("       - 支持 query（即时查询）")
    print("       - 支持 query_range（范围查询）")
    print("       - 延迟初始化（lazy init）")
    print("       - 单例模式 get_prometheus_client()")
    print("    2. PrometheusQueryTool - 自定义 PromQL 查询")
    print("       - 支持 instant 和 range 两种查询类型")
    print("       - 结果处理和格式化")
    print("    3. ClusterMetricsTool - 集群指标概览")
    print("       - 内置常用 PromQL 查询")
    print("       - 自动获取 CPU、内存、节点、Pod 指标")
    print("       - 无需手动写 PromQL")
    print("    4. 注册函数 register_prometheus_tools()")
    
    print("\n注意: 需要实际的 K8s 集群、ES 和 Prometheus 服务才能进行端到端测试。")
    print("      工具在未配置服务时会返回友好的错误信息。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
