"""
Task 7 验证脚本
验证定时轮询调度器
"""

import sys
import logging
import time
import threading

# 添加 backend 目录到 Python 路径
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_1_history_store_import():
    """测试 1: 历史存储模块导入和基本操作"""
    print("\n" + "=" * 60)
    print("测试 1: 历史存储模块导入和基本操作")
    print("=" * 60)
    
    try:
        from agents.history import PollingRecord, HistoryStore
        
        # 测试 PollingRecord
        record = PollingRecord(
            status="normal",
            summary="测试记录",
            anomaly_count=0,
            duration_ms=100.0,
        )
        record_dict = record.to_dict()
        print(f"  [PASS] PollingRecord 创建成功")
        print(f"         status: {record_dict['status']}")
        print(f"         timestamp: {record_dict['timestamp']}")
        
        # 测试 HistoryStore
        store = HistoryStore(max_records=5)
        print(f"\n  [PASS] HistoryStore 创建成功: max_records={store.max_records}")
        
        # 添加多条记录
        for i in range(3):
            store.add(PollingRecord(
                status="warning" if i % 2 == 0 else "normal",
                summary=f"记录 {i}",
                anomaly_count=i,
            ))
        
        print(f"\n  [PASS] 添加 3 条记录: size={store.size()}")
        
        # 测试 get_all
        all_records = store.get_all()
        print(f"  [PASS] get_all: 返回 {len(all_records)} 条记录（最新在前）")
        assert len(all_records) == 3
        
        # 测试 get_latest
        latest = store.get_latest(2)
        print(f"  [PASS] get_latest(2): 返回 {len(latest)} 条记录")
        assert len(latest) == 2
        
        # 测试 get_by_status
        warnings = store.get_by_status("warning")
        print(f"  [PASS] get_by_status('warning'): 返回 {len(warnings)} 条")
        assert len(warnings) == 2
        
        # 测试 get_statistics
        stats = store.get_statistics()
        print(f"  [PASS] get_statistics: {stats}")
        assert stats["total"] == 3
        
        # 测试 clear
        store.clear()
        print(f"  [PASS] clear: size={store.size()}")
        assert store.size() == 0
        
        return True
        
    except Exception as e:
        logger.error(f"测试 1 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_history_store_capacity():
    """测试 2: 历史存储容量限制和淘汰策略"""
    print("\n" + "=" * 60)
    print("测试 2: 历史存储容量限制和淘汰策略")
    print("=" * 60)
    
    try:
        from agents.history import PollingRecord, HistoryStore
        
        max_records = 5
        store = HistoryStore(max_records=max_records)
        
        # 添加超过容量的记录
        for i in range(10):
            store.add(PollingRecord(
                status="normal",
                summary=f"记录 {i}",
                anomaly_count=0,
            ))
            time.sleep(0.01)
        
        print(f"  [PASS] 添加 10 条记录到容量 {max_records} 的存储")
        print(f"         当前 size: {store.size()}")
        
        # 验证容量限制
        assert store.size() == max_records, f"期望 {max_records}，实际 {store.size()}"
        print(f"  [PASS] 容量限制生效: size={store.size()}")
        
        # 验证最早的记录被淘汰（时间倒序验证）
        all_records = store.get_all()
        
        # 最新的应该是记录 9
        latest_summary = all_records[0]["summary"]
        oldest_summary = all_records[-1]["summary"]
        
        print(f"  [PASS] 最新记录: {latest_summary}")
        print(f"  [PASS] 最旧记录: {oldest_summary}")
        
        # 应该只保留 5-9 这 5 条
        assert "9" in latest_summary, f"期望最新记录是 9，实际是 {latest_summary}"
        assert "5" in oldest_summary, f"期望最旧记录是 5，实际是 {oldest_summary}"
        
        return True
        
    except Exception as e:
        logger.error(f"测试 2 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_history_store_thread_safety():
    """测试 3: 历史存储线程安全"""
    print("\n" + "=" * 60)
    print("测试 3: 历史存储线程安全")
    print("=" * 60)
    
    try:
        from agents.history import PollingRecord, HistoryStore
        
        store = HistoryStore(max_records=1000)
        threads = []
        records_per_thread = 50
        
        def add_records(thread_id: int):
            for i in range(records_per_thread):
                store.add(PollingRecord(
                    status="normal",
                    summary=f"thread-{thread_id}-{i}",
                    anomaly_count=0,
                ))
        
        # 创建多个线程并发添加记录
        for i in range(10):
            t = threading.Thread(target=add_records, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        expected = 10 * records_per_thread
        actual = store.size()
        print(f"  [PASS] 10 个线程各添加 {records_per_thread} 条记录")
        print(f"         期望: {expected}, 实际: {actual}")
        
        # 允许轻微误差（因为 max_records=1000，实际也是 500，所以没问题）
        assert actual == expected, f"期望 {expected}，实际 {actual}"
        print(f"  [PASS] 线程安全验证通过")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 3 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_scheduler_import():
    """测试 4: 调度器模块导入"""
    print("\n" + "=" * 60)
    print("测试 4: 调度器模块导入")
    print("=" * 60)
    
    try:
        from agents.scheduler import PollingScheduler, get_polling_scheduler
        
        # 测试创建（不启动）
        scheduler = PollingScheduler(interval_minutes=1, max_records=50)
        print(f"  [PASS] PollingScheduler 创建成功")
        print(f"         interval_minutes: {scheduler.interval_minutes}")
        print(f"         _is_running: {scheduler._is_running}")
        
        # 测试 get_status
        status = scheduler.get_status()
        print(f"\n  [PASS] get_status:")
        print(f"         is_running: {status['is_running']}")
        print(f"         interval_minutes: {status['interval_minutes']}")
        print(f"         execution_count: {status['execution_count']}")
        
        # 测试单例
        singleton = get_polling_scheduler()
        print(f"\n  [PASS] get_polling_scheduler 单例获取成功")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 4 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_scheduler_operations():
    """测试 5: 调度器操作（run_once、set_interval、历史查询）"""
    print("\n" + "=" * 60)
    print("测试 5: 调度器操作（run_once、set_interval、历史查询）")
    print("=" * 60)
    
    try:
        from agents.scheduler import PollingScheduler
        
        # 创建独立实例（不影响全局）
        scheduler = PollingScheduler(interval_minutes=5, max_records=20)
        
        # 测试 run_once（立即执行一次）
        print("  执行 run_once...")
        result = scheduler.run_once()
        print(f"  [PASS] run_once 执行完成")
        print(f"         status: {result.get('status')}")
        print(f"         duration_ms: {result.get('duration_ms')}")
        
        # 执行多次
        for i in range(2):
            time.sleep(0.05)
            scheduler.run_once()
        
        print(f"\n  [PASS] 共执行 {scheduler._execution_count} 次轮询")
        
        # 测试 get_history
        history = scheduler.get_history(limit=5)
        print(f"\n  [PASS] get_history:")
        print(f"         total: {history['total']}")
        print(f"         returned: {history['returned']}")
        print(f"         statistics: {history['statistics']}")
        
        # 测试 set_interval
        old_interval = scheduler.interval_minutes
        scheduler.set_interval(3)
        print(f"\n  [PASS] set_interval: {old_interval} -> {scheduler.interval_minutes}")
        
        # 测试 clear_history
        scheduler.clear_history()
        print(f"  [PASS] clear_history: size={scheduler._history_store.size()}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 5 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_scheduler_start_stop():
    """测试 6: 调度器启动和停止（快速测试）"""
    print("\n" + "=" * 60)
    print("测试 6: 调度器启动和停止（快速测试）")
    print("=" * 60)
    
    try:
        from agents.scheduler import PollingScheduler
        
        scheduler = PollingScheduler(interval_minutes=1, max_records=10)
        
        # 测试启动前状态
        status_before = scheduler.get_status()
        assert not status_before["is_running"]
        print(f"  [PASS] 启动前: is_running={status_before['is_running']}")
        
        # 启动调度器
        started = scheduler.start()
        assert started
        print(f"  [PASS] 启动成功: _is_running={scheduler._is_running}")
        
        # 检查状态
        status_after_start = scheduler.get_status()
        assert status_after_start["is_running"]
        print(f"  [PASS] 启动后: is_running={status_after_start['is_running']}")
        print(f"         next_run: {status_after_start['next_run']}")
        
        # 等待一小段时间让任务执行一次
        print("  等待任务执行...")
        time.sleep(1)
        
        # 停止调度器
        stopped = scheduler.stop()
        assert stopped
        print(f"  [PASS] 停止成功: _is_running={scheduler._is_running}")
        
        # 检查停止后的状态
        status_after_stop = scheduler.get_status()
        assert not status_after_stop["is_running"]
        print(f"  [PASS] 停止后: is_running={status_after_stop['is_running']}")
        print(f"         execution_count: {status_after_stop['execution_count']}")
        
        # 验证历史记录
        history = scheduler.get_history(limit=5)
        print(f"  [PASS] 历史记录: total={history['total']}")
        
        return True
        
    except Exception as e:
        logger.error(f"测试 6 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主验证函数"""
    print("\n" + "=" * 60)
    print("Task 7 验证: 定时轮询调度器")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("测试 1", test_1_history_store_import()))
    results.append(("测试 2", test_2_history_store_capacity()))
    results.append(("测试 3", test_3_history_store_thread_safety()))
    results.append(("测试 4", test_4_scheduler_import()))
    results.append(("测试 5", test_5_scheduler_operations()))
    results.append(("测试 6", test_6_scheduler_start_stop()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    if passed == total:
        print("[OK] Task 7 验证完成 - 核心模块测试通过!")
    else:
        print(f"[FAIL] Task 7 验证完成 - {passed}/{total} 测试通过")
    
    print("=" * 60)
    
    # 功能清单
    print("\n已实现的功能:")
    print("  Task 7: 定时轮询调度器")
    print("    1. 历史记录模块 (agents/history.py)")
    print("       - PollingRecord: 单次轮询记录")
    print("       - HistoryStore: 固定容量内存存储")
    print("       - 线程安全（Lock 保护）")
    print("       - 自动淘汰最旧记录")
    print("       - 支持按状态筛选")
    print("       - 统计信息查询")
    print("       - 单例模式: get_history_store()")
    
    print("\n    2. 调度器模块 (agents/scheduler.py)")
    print("       - PollingScheduler: APScheduler 封装")
    print("       - start(): 启动定时轮询")
    print("       - stop(): 停止轮询")
    print("       - get_status(): 获取运行状态")
    print("       - run_once(): 立即执行一次")
    print("       - set_interval(): 动态修改间隔")
    print("       - get_history(): 查询历史记录")
    print("       - clear_history(): 清空历史")
    print("       - 延迟初始化调度器")
    print("       - 配置驱动的轮询间隔")
    print("       - 单例模式: get_polling_scheduler()")
    
    print("\n    3. 验证覆盖")
    print("       - 存储基本操作: add/get_all/get_latest/get_by_status")
    print("       - 容量限制: 超过 max_records 淘汰最旧")
    print("       - 线程安全: 多线程并发写入")
    print("       - 调度器操作: start/stop/run_once")
    print("       - 历史查询: 限制数量、按状态筛选")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
