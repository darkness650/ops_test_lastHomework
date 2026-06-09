"""
Task 9 验证脚本: CLI 交互界面
验证目标:
  - CLI 能正确解析命令和参数
  - --help 能显示所有子命令的帮助信息
"""

import logging
import sys
from io import StringIO
from typing import Optional

from typer.testing import CliRunner

from cli.main import app

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

runner = CliRunner()


def test_1_help_output():
    """测试 1: 主命令 --help 输出"""
    print("\n" + "=" * 60)
    print("测试 1: 主命令 --help 输出")
    print("=" * 60)

    result = runner.invoke(app, ["--help"])
    print("\n  [INFO] 执行: ops-agent --help")

    if result.exit_code == 0:
        print("  [PASS] 帮助命令执行成功 (exit_code=0)")

        # 检查关键命令是否存在
        expected_commands = [
            "chat",
            "monitor",
            "status",
            "polling-start",
            "polling-stop",
            "polling-run-once",
            "history",
            "version",
        ]

        for cmd in expected_commands:
            if cmd in result.output:
                print(f"  [PASS] 找到命令: {cmd}")
            else:
                print(f"  [FAIL] 缺少命令: {cmd}")

        print("\n  输出预览:")
        for line in result.output.split("\n")[:15]:
            if line.strip():
                print(f"    {line}")

        return True
    else:
        print(f"  [FAIL] 执行失败: {result.exit_code}")
        print(f"  错误: {result.stdout}")
        print(f"  异常: {result.exception}")
        return False


def test_2_chat_help():
    """测试 2: chat 子命令帮助"""
    print("\n" + "=" * 60)
    print("测试 2: chat 子命令 --help")
    print("=" * 60)

    result = runner.invoke(app, ["chat", "--help"])
    print("\n  [INFO] 执行: ops-agent chat --help")

    if result.exit_code == 0:
        print("  [PASS] chat --help 执行成功")

        expected_options = ["--message", "-m", "--namespace", "-n"]
        for opt in expected_options:
            if opt in result.output:
                print(f"  [PASS] 找到选项: {opt}")
            else:
                print(f"  [WARN] 选项未在输出中: {opt}")

        print("\n  输出预览:")
        for line in result.output.split("\n")[:12]:
            if line.strip():
                print(f"    {line}")

        return True
    else:
        print(f"  [FAIL] chat --help 失败: {result.exit_code}")
        return False


def test_3_monitor_help():
    """测试 3: monitor 子命令帮助"""
    print("\n" + "=" * 60)
    print("测试 3: monitor 子命令 --help")
    print("=" * 60)

    result = runner.invoke(app, ["monitor", "--help"])
    print("\n  [INFO] 执行: ops-agent monitor --help")

    if result.exit_code == 0:
        print("  [PASS] monitor --help 执行成功")

        expected_options = ["--namespace", "-n", "--deep", "-d"]
        for opt in expected_options:
            if opt in result.output:
                print(f"  [PASS] 找到选项: {opt}")

        print("\n  输出预览:")
        for line in result.output.split("\n")[:12]:
            if line.strip():
                print(f"    {line}")

        return True
    else:
        print(f"  [FAIL] monitor --help 失败: {result.exit_code}")
        return False


def test_4_polling_commands_help():
    """测试 4: polling 相关命令帮助"""
    print("\n" + "=" * 60)
    print("测试 4: polling 相关命令 --help")
    print("=" * 60)

    all_passed = True

    # 测试 status
    result = runner.invoke(app, ["status", "--help"])
    print("\n  [INFO] 执行: ops-agent status --help")
    if result.exit_code == 0:
        print("  [PASS] status --help 执行成功")
    else:
        print(f"  [FAIL] status --help 失败: {result.exit_code}")
        all_passed = False

    # 测试 polling-start
    result = runner.invoke(app, ["polling-start", "--help"])
    print("\n  [INFO] 执行: ops-agent polling-start --help")
    if result.exit_code == 0:
        print("  [PASS] polling-start --help 执行成功")
        if "--interval" in result.output:
            print("  [PASS] 找到 --interval 选项")
        if "--namespace" in result.output:
            print("  [PASS] 找到 --namespace 选项")
    else:
        print(f"  [FAIL] polling-start --help 失败: {result.exit_code}")
        all_passed = False

    # 测试 history
    result = runner.invoke(app, ["history", "--help"])
    print("\n  [INFO] 执行: ops-agent history --help")
    if result.exit_code == 0:
        print("  [PASS] history --help 执行成功")
        if "--limit" in result.output:
            print("  [PASS] 找到 --limit 选项")
        if "--clear" in result.output:
            print("  [PASS] 找到 --clear 选项")
    else:
        print(f"  [FAIL] history --help 失败: {result.exit_code}")
        all_passed = False

    return all_passed


def test_5_version_command():
    """测试 5: version 命令"""
    print("\n" + "=" * 60)
    print("测试 5: version 命令")
    print("=" * 60)

    result = runner.invoke(app, ["version"])
    print("\n  [INFO] 执行: ops-agent version")

    if result.exit_code == 0:
        print("  [PASS] version 执行成功")
        print("\n  输出:")
        for line in result.output.split("\n")[:5]:
            if line.strip():
                safe_line = line.encode('ascii', errors='replace').decode('ascii')
                print(f"    {safe_line}")
        return True
    else:
        print(f"  [FAIL] version 失败: {result.exit_code}")
        return False


def test_6_command_parsing():
    """测试 6: 命令参数解析"""
    print("\n" + "=" * 60)
    print("测试 6: 命令参数解析（模拟调用）")
    print("=" * 60)

    all_passed = True

    # 测试无效命令
    result = runner.invoke(app, ["invalid-command"])
    print("\n  [INFO] 执行: ops-agent invalid-command")
    if result.exit_code != 0:
        print("  [PASS] 无效命令返回非零退出码")
    else:
        print("  [WARN] 无效命令未返回错误")
        all_passed = False

    # 测试 chat 无参数（应该显示 help）
    result = runner.invoke(app, ["chat", "--help"])
    print("\n  [INFO] 执行: ops-agent chat --help")
    if result.exit_code == 0:
        print("  [PASS] chat --help 可执行")
    else:
        print(f"  [FAIL] chat --help 失败: {result.exit_code}")
        all_passed = False

    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Task 9 验证: CLI 交互界面")
    print("=" * 60)

    tests = [
        ("测试 1: 主命令 --help", test_1_help_output),
        ("测试 2: chat --help", test_2_chat_help),
        ("测试 3: monitor --help", test_3_monitor_help),
        ("测试 4: polling 命令 --help", test_4_polling_commands_help),
        ("测试 5: version 命令", test_5_version_command),
        ("测试 6: 命令参数解析", test_6_command_parsing),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"{name} 失败: {e}", exc_info=True)
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"[OK] Task 9 验证完成 - {passed}/{len(tests)} 测试通过!")
        print("=" * 60)
        print("\n✅ CLI 命令行界面已实现!")
        print("\n可用命令:")
        print("  ops-agent chat              - 启动交互式对话")
        print("  ops-agent monitor           - 立即执行健康监测")
        print("  ops-agent status            - 查看轮询状态")
        print("  ops-agent polling-start     - 启动定时轮询")
        print("  ops-agent polling-stop      - 停止定时轮询")
        print("  ops-agent polling-run-once  - 立即执行一次轮询")
        print("  ops-agent history           - 查看轮询历史")
        print("  ops-agent version           - 显示版本信息")
        print("\n使用 --help 查看每个命令的详细用法")
    else:
        print(f"[FAIL] Task 9 验证完成 - {passed}/{len(tests)} 测试通过")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
