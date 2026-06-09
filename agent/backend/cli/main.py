"""
CLI 命令行入口
提供交互式对话、健康监测、轮询控制、异常分析等功能
与 GUI 功能完全同步
"""

import sys
import time
import json
from typing import Optional, Dict, Any, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich.markdown import Markdown

from config import get_settings
from agents.agent import get_agent
from agents.engine import (
    get_analysis_engine,
    quick_health_check,
    full_analysis,
)
from tools.base import ToolResult
from agents.scheduler import get_polling_scheduler
from agents.llm_client import get_llm_client
from agents.anomaly_analyzer import get_anomaly_analyzer
from agents.analysis_store import get_analysis_store
from api.schemas import RootCauseAnalysis, RecoveryPlan

console = Console()
app = typer.Typer(
    name="ops-agent",
    help="微服务运维智能体（与 GUI 功能同步）",
    add_completion=False,
    no_args_is_help=True,
)


def _get_status_color(status: str) -> str:
    """根据状态返回颜色"""
    color_map = {
        "normal": "green",
        "warning": "yellow",
        "critical": "red",
        "error": "red",
        "ok": "green",
    }
    return color_map.get(status, "white")


def _format_tool_name(tool_name: str) -> str:
    """格式化工具名称为用户友好的描述"""
    tool_descriptions = {
        "get_cluster_status": "查询集群状态",
        "list_pods": "列出 Pod",
        "get_pod_detail": "获取 Pod 详情",
        "get_pod_logs": "获取 Pod 日志",
        "list_deployments": "列出 Deployment",
        "list_services": "列出 Service",
        "list_nodes": "列出节点",
        "list_events": "列出事件",
        "echo": "回显测试",
        "calculator": "计算器",
    }
    return tool_descriptions.get(tool_name, tool_name)


def _on_tool_call(tool_name: str, arguments: Dict[str, Any]):
    """工具调用开始时的回调"""
    desc = _format_tool_name(tool_name)
    arg_str = ", ".join(f"{k}={v}" for k, v in arguments.items() if v)
    if arg_str:
        console.print(f"[dim]🔍 {desc}... ({arg_str})[/dim]")
    else:
        console.print(f"[dim]🔍 {desc}...[/dim]")


def _on_tool_result(tool_name: str, arguments: Dict[str, Any], result: ToolResult):
    """工具执行完成后的回调"""
    desc = _format_tool_name(tool_name)
    if result.success:
        console.print(f"[dim]✓ {desc} 完成[/dim]")
    else:
        error_msg = result.error or "未知错误"
        console.print(f"[dim]✗ {desc} 失败: {error_msg}[/dim]")


def _display_banner():
    """显示欢迎横幅"""
    banner = Text()
    banner.append("╔══════════════════════════════════════════════╗\n", style="cyan")
    banner.append("║     🤖 微服务运维智能体 (Ops Agent)          ║\n", style="cyan bold")
    banner.append("║     版本: 0.1.0                              ║\n", style="cyan")
    banner.append("╚══════════════════════════════════════════════╝\n", style="cyan")
    console.print(banner)


@app.command()
def chat(
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="单次消息模式：发送消息后退出"
    ),
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-n", help="Kubernetes 命名空间"
    ),
):
    """
    与运维智能体进行交互式对话

    使用示例:
      ops-agent chat                    # 启动交互式对话
      ops-agent chat -m "集群状态如何？" # 发送单次消息
    """
    _display_banner()

    if message:
        _chat_single(message, namespace)
    else:
        _chat_interactive(namespace)


def _chat_single(message: str, namespace: Optional[str] = None):
    """单次消息对话模式"""
    console.print(f"\n[cyan]发送消息:[/cyan] {message}")

    try:
        settings = get_settings()

        if settings.llm_configured:
            agent = get_agent()
            console.print("")
            response = agent.chat(
                message,
                on_tool_call=_on_tool_call,
                on_tool_result=_on_tool_result,
            )
            reply = response.content if response else "无响应"
        else:
            engine = get_analysis_engine(use_llm=False)
            result = engine.quick_check(namespace=namespace)
            reply = result.get("summary", "快速检查完成")

        console.print(Panel.fit(
            Text(reply, style="green"),
            title="Agent 回复",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        raise typer.Exit(code=1)


def _chat_interactive(namespace: Optional[str] = None):
    """交互式对话模式"""
    console.print("\n[cyan]欢迎使用交互式对话模式！[/cyan]")
    console.print("[dim]输入 'quit' 或 'exit' 退出，输入 'help' 查看帮助[/dim]\n")

    if namespace:
        console.print(f"[blue]目标命名空间:[/blue] {namespace}\n")

    settings = get_settings()
    use_llm = settings.llm_configured

    if use_llm:
        try:
            agent = get_agent()
            console.print("[green]✓ LLM 对话模式已启用[/green]\n")
        except Exception as e:
            console.print(f"[yellow]⚠ LLM 初始化失败，使用内置分析模式: {e}[/yellow]\n")
            use_llm = False

    while True:
        try:
            user_input = Prompt.ask("[bold green]你[/bold green]").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                console.print("[cyan]再见！👋[/cyan]")
                break

            if user_input.lower() == 'help':
                _display_chat_help()
                continue

            if not user_input:
                continue

            start_time = time.time()

            if use_llm:
                agent = get_agent()
                console.print("")
                response = agent.chat(
                    user_input,
                    on_tool_call=_on_tool_call,
                    on_tool_result=_on_tool_result,
                )
                reply = response.content if response else "无响应"
                elapsed = time.time() - start_time
            else:
                with console.status("[bold cyan]Agent 正在思考...[/bold cyan]", spinner="dots"):
                    engine = get_analysis_engine(use_llm=False)
                    result = engine.quick_check(namespace=namespace)
                    reply = result.get("summary", "快速检查完成")
                    elapsed = time.time() - start_time

            response_text = Text(reply, style="green")
            console.print(Panel.fit(
                response_text,
                title=f"[bold cyan]Agent[/bold cyan] ({elapsed:.2f}s)",
                border_style="cyan"
            ))

        except KeyboardInterrupt:
            console.print("\n\n[cyan]用户中断，再见！[/cyan]")
            break
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


def _display_chat_help():
    """显示对话帮助"""
    help_text = """
[bold cyan]可用命令:[/bold cyan]
  [green]普通问题[/green]    - 直接输入，Agent 会根据上下文回答
  [green]quit/exit[/green]   - 退出对话
  [green]help[/green]        - 显示此帮助

[bold cyan]示例问题:[/bold cyan]
  - "集群状态如何？"
  - "查看 default 命名空间的 Pod"
  - "获取 nginx Pod 的最近日志"
  - "检查服务的 CPU 使用率"
"""
    console.print(Panel(help_text, title="对话帮助", border_style="blue"))


@app.command()
def monitor(
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-n", help="指定命名空间"
    ),
    deep_analysis: bool = typer.Option(
        False, "--deep", "-d", help="执行深度分析"
    ),
):
    """
    立即执行一次健康监测

    使用示例:
      ops-agent monitor                    # 检查所有命名空间
      ops-agent monitor -n default         # 检查指定命名空间
      ops-agent monitor -n default -d      # 深度分析
    """
    _display_banner()
    console.print(f"\n[cyan]执行健康监测...[/cyan]")
    if namespace:
        console.print(f"[blue]命名空间:[/blue] {namespace}")
    if deep_analysis:
        console.print("[yellow]深度分析模式[/yellow]")

    try:
        with console.status("[bold cyan]正在收集集群状态...[/bold cyan]", spinner="dots"):
            if deep_analysis:
                result_obj = full_analysis(namespace=namespace)
                result = result_obj.to_dict()
            else:
                result = quick_health_check(namespace=namespace)

        _display_monitor_result(result, deep_analysis)

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


def _display_monitor_result(result: Dict[str, Any], deep_analysis: bool):
    """显示监测结果"""
    status = result.get("status", "unknown")
    status_color = _get_status_color(status)

    summary = result.get("summary", "")
    summary_panel = Panel(
        Text(summary, style=status_color),
        title=f"[bold]监测结果: [{status_color}]{status.upper()}[/bold]",
        border_style=status_color
    )
    console.print(summary_panel)

    anomalies = result.get("anomalies", [])
    if anomalies:
        table = Table(title="异常详情", border_style="yellow")
        table.add_column("类型", style="cyan")
        table.add_column("资源", style="magenta")
        table.add_column("描述", style="white")
        table.add_column("严重程度", style="red")

        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            severity_color = _get_status_color(severity)
            table.add_row(
                anomaly.get("type", "unknown"),
                anomaly.get("target", anomaly.get("resource", "-")),
                anomaly.get("description", anomaly.get("message", "")),
                f"[{severity_color}]{severity}[/]"
            )

        console.print(table)

    if deep_analysis and hasattr(result, 'analysis'):
        console.print(Panel(
            Text(str(result.analysis), style="cyan"),
            title="深度分析",
            border_style="blue"
        ))


@app.command()
def status():
    """
    查看轮询调度器状态
    """
    _display_banner()

    try:
        settings = get_settings()
        scheduler = get_polling_scheduler(
            interval_minutes=settings.polling_interval_minutes
        )
        status_info = scheduler.get_status()

        table = Table(title="轮询调度器状态", border_style="cyan")
        table.add_column("属性", style="cyan")
        table.add_column("值", style="white")

        is_running = status_info.get("is_running", False)
        running_color = "green" if is_running else "red"
        running_text = "[green]运行中[/green]" if is_running else "[red]已停止[/red]"

        table.add_row("运行状态", running_text)
        table.add_row("轮询间隔", f"{status_info.get('interval_minutes', 'N/A')} 分钟")
        table.add_row("历史记录数", str(status_info.get('history_count', 0)))
        table.add_row("最大历史记录", str(status_info.get('max_history', 100)))

        if status_info.get("next_run"):
            table.add_row("下次运行", str(status_info["next_run"]))
        if status_info.get("last_run"):
            table.add_row("上次运行", str(status_info["last_run"]))

        console.print(table)

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@app.command()
def polling_start(
    interval_minutes: int = typer.Option(
        5, "--interval", "-i", help="轮询间隔（分钟）"
    ),
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-n", help="指定命名空间（为空则检查所有）"
    ),
    deep_analysis: bool = typer.Option(
        False, "--deep", "-d", help="启用深度分析"
    ),
):
    """
    启动定时轮询

    使用示例:
      ops-agent polling-start -i 5         # 每 5 分钟轮询一次
      ops-agent polling-start -n default   # 只检查指定命名空间
    """
    _display_banner()

    try:
        settings = get_settings()
        scheduler = get_polling_scheduler(
            interval_minutes=interval_minutes,
            max_history=100,
        )

        if scheduler.is_running():
            console.print("[yellow]轮询调度器已在运行[/yellow]")
            return

        scheduler.start(
            interval_minutes=interval_minutes,
            namespace=namespace,
            deep_analysis=deep_analysis,
        )

        console.print(f"[green]✓ 轮询调度器已启动[/green]")
        console.print(f"  间隔: {interval_minutes} 分钟")
        if namespace:
            console.print(f"  命名空间: {namespace}")
        if deep_analysis:
            console.print(f"  深度分析: 已启用")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@app.command()
def polling_stop():
    """
    停止定时轮询
    """
    _display_banner()

    try:
        settings = get_settings()
        scheduler = get_polling_scheduler(
            interval_minutes=settings.polling_interval_minutes
        )

        if not scheduler.is_running():
            console.print("[yellow]轮询调度器未在运行[/yellow]")
            return

        scheduler.stop()
        console.print("[green]✓ 轮询调度器已停止[/green]")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@app.command()
def polling_run_once(
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-n", help="指定命名空间"
    ),
    deep_analysis: bool = typer.Option(
        False, "--deep", "-d", help="启用深度分析"
    ),
):
    """
    立即执行一次轮询

    使用示例:
      ops-agent polling-run-once
      ops-agent polling-run-once -n default -d
    """
    _display_banner()
    console.print("\n[cyan]执行单次轮询...[/cyan]")

    try:
        settings = get_settings()
        scheduler = get_polling_scheduler(
            interval_minutes=settings.polling_interval_minutes
        )

        with console.status("[bold cyan]正在执行轮询...[/bold cyan]", spinner="dots"):
            result = scheduler.run_once(namespace=namespace, deep_analysis=deep_analysis)

        if not result:
            console.print("[yellow]⚠ 轮询执行完成但未获取到结果[/yellow]")
            return

        status = result.get("status", "unknown")
        status_color = _get_status_color(status)
        console.print(f"[green]✓ 轮询完成[/green]")
        console.print(f"  状态: [{status_color}]{status}[/]")
        console.print(f"  异常数: {result.get('anomaly_count', 0)}")
        console.print(f"  耗时: {result.get('duration_ms', 0):.2f}ms")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="显示最近 N 条记录"),
    clear: bool = typer.Option(False, "--clear", "-c", help="清空历史记录"),
):
    """
    查看轮询历史记录

    使用示例:
      ops-agent history            # 显示最近 10 条
      ops-agent history -l 20      # 显示最近 20 条
      ops-agent history --clear    # 清空历史记录
    """
    _display_banner()

    try:
        settings = get_settings()
        scheduler = get_polling_scheduler(
            interval_minutes=settings.polling_interval_minutes
        )

        if clear:
            scheduler.clear_history()
            console.print("[green]✓ 历史记录已清空[/green]")
            return

        result = scheduler.get_history(limit=limit)
        records = result.get("records", [])

        if not records:
            console.print("[yellow]暂无历史记录[/yellow]")
            return

        console.print(f"[cyan]最近 {len(records)} 条记录:[/cyan]\n")

        table = Table(title="轮询历史", border_style="cyan")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("时间", style="magenta")
        table.add_column("状态", style="white")
        table.add_column("异常数", style="yellow", justify="right")
        table.add_column("耗时", style="white", justify="right")

        for i, record in enumerate(records, 1):
            status = record.get("status", "unknown")
            status_color = _get_status_color(status)
            table.add_row(
                str(i),
                record.get("timestamp", "-"),
                f"[{status_color}]{status}[/]",
                str(record.get("anomaly_count", 0)),
                f"{record.get('duration_ms', 0):.2f}ms"
            )

        console.print(table)

        status_counts: Dict[str, int] = {}
        for record in records:
            status = record.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        stats_text = "\n".join([
            f"  [{_get_status_color(s)}]{s}: {c}[/]"
            for s, c in status_counts.items()
        ])
        console.print(f"\n[bold]统计:[/bold]\n{stats_text}")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@app.command()
def version():
    """
    显示版本信息
    """
    console.print(Panel.fit(
        Text("微服务运维智能体 v0.1.0\n\nCopyright 2024 Ops Agent Team", style="cyan"),
        title="版本信息",
        border_style="cyan"
    ))


# ============================================================
# 异常分析命令组（与 GUI Dashboard 同步）
# ============================================================
anomaly_app = typer.Typer(
    name="anomaly",
    help="异常分析相关命令",
    add_completion=False,
    no_args_is_help=True,
)
app.add_typer(anomaly_app, name="anomaly")


def _get_anomaly_id_by_index(namespace: Optional[str] = None, index: int = 1) -> Optional[str]:
    """
    根据索引获取异常 ID
    
    Args:
        namespace: 命名空间
        index: 异常索引（从 1 开始）
        
    Returns:
        Optional[str]: 异常 ID
    """
    try:
        result = quick_health_check(namespace=namespace)
        anomalies = result.get("anomalies", [])
        
        if not anomalies:
            console.print("[yellow]当前没有异常[/yellow]")
            return None
        
        if index < 1 or index > len(anomalies):
            console.print(f"[red]索引超出范围，当前共有 {len(anomalies)} 个异常[/red]")
            return None
        
        anomaly = anomalies[index - 1]
        return anomaly.get("id")
    except Exception as e:
        console.print(f"[red]获取异常 ID 失败: {e}[/red]")
        return None


def _get_analysis_status_color(status: str) -> str:
    """根据分析状态返回颜色"""
    color_map = {
        "pending": "gray",
        "analyzing": "blue",
        "completed": "green",
        "failed": "red",
    }
    return color_map.get(status, "white")


def _get_risk_color(risk: str) -> str:
    """根据风险等级返回颜色"""
    color_map = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
    }
    return color_map.get(risk, "white")


@anomaly_app.command("list")
def anomaly_list(
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-n", help="指定命名空间"
    ),
):
    """
    查看当前异常列表（与 GUI Dashboard 同步）

    使用示例:
      ops-agent anomaly list              # 查看所有命名空间的异常
      ops-agent anomaly list -n default   # 查看指定命名空间的异常
    """
    _display_banner()
    console.print(f"\n[cyan]获取异常列表...[/cyan]")
    if namespace:
        console.print(f"[blue]命名空间:[/blue] {namespace}")

    try:
        result = quick_health_check(namespace=namespace)
        anomalies = result.get("anomalies", [])

        if not anomalies:
            console.print("[green]✓ 当前没有异常，集群状态正常[/green]")
            return

        analysis_store = get_analysis_store()
        analyzer = get_anomaly_analyzer()

        console.print(f"\n[green]✓ 共发现 {len(anomalies)} 个异常[/green]\n")

        table = Table(title="当前异常列表", border_style="cyan")
        table.add_column("#", style="cyan", justify="right", width=4)
        table.add_column("异常 ID", style="magenta", width=36)
        table.add_column("类型", style="yellow", width=20)
        table.add_column("资源", style="blue", width=25)
        table.add_column("严重程度", style="red", width=10)
        table.add_column("分析状态", style="white", width=12)
        table.add_column("描述", style="white")

        for i, anomaly in enumerate(anomalies, 1):
            anomaly_id = anomaly.get("id", "-")
            severity = anomaly.get("severity", "medium")
            severity_color = _get_status_color(severity)

            # 获取分析状态
            analysis_status = "未分析"
            try:
                stored_status = analysis_store.get_status(anomaly_id)
                if stored_status:
                    analysis_status = stored_status
                    status_color = _get_analysis_status_color(stored_status)
                elif analyzer and analyzer.is_analyzing(anomaly_id):
                    analysis_status = "分析中"
                    status_color = "blue"
                else:
                    status_color = "gray"
            except Exception:
                status_color = "gray"

            table.add_row(
                str(i),
                anomaly_id[:8] + "..." if len(anomaly_id) > 8 else anomaly_id,
                anomaly.get("type", "unknown"),
                anomaly.get("target", "-"),
                f"[{severity_color}]{severity}[/]",
                f"[{status_color}]{analysis_status}[/]",
                anomaly.get("description", "")[:50] + ("..." if len(anomaly.get("description", "")) > 50 else ""),
            )

        console.print(table)

        # 显示统计信息
        severity_counts: Dict[str, int] = {}
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        stats_parts = []
        for sev, count in severity_counts.items():
            color = _get_status_color(sev)
            stats_parts.append(f"[{color}]{sev}: {count}[/]")
        if stats_parts:
            console.print(f"\n[bold]严重程度统计:[/bold] {', '.join(stats_parts)}")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@anomaly_app.command("analyze")
def anomaly_analyze(
    anomaly_id: Optional[str] = typer.Option(
        None, "--id", "-i", help="异常 ID（与 GUI 中的异常 ID 一致）"
    ),
    index: int = typer.Option(
        1, "--index", "-n", help="异常索引（从 1 开始，用于快速选择列表中的第 N 个异常）"
    ),
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-ns", help="命名空间（使用索引时需要）"
    ),
    wait: bool = typer.Option(
        False, "--wait", "-w", help="等待分析完成（默认只触发不等待）"
    ),
    timeout: int = typer.Option(
        120, "--timeout", "-t", help="等待超时时间（秒）"
    ),
):
    """
    查看异常分析详情（与 GUI 异常分析弹窗同步）

    使用示例:
      ops-agent anomaly analyze -i <异常ID>        # 查看指定异常的分析
      ops-agent anomaly analyze -n 1 -ns default   # 查看第 1 个异常的分析
      ops-agent anomaly analyze -i <ID> -w         # 等待分析完成后显示结果
    """
    _display_banner()

    # 获取异常 ID
    target_id = anomaly_id
    if not target_id:
        target_id = _get_anomaly_id_by_index(namespace=namespace, index=index)
        if not target_id:
            raise typer.Exit(code=1)

    console.print(f"\n[cyan]查看异常分析:[/cyan] {target_id}")

    try:
        analysis_store = get_analysis_store()
        analyzer = get_anomaly_analyzer()

        # 检查是否正在分析
        is_analyzing = analyzer and analyzer.is_analyzing(target_id)
        if is_analyzing:
            console.print("[blue]该异常正在分析中...[/blue]")
            if not wait:
                console.print("[yellow]使用 --wait 参数等待分析完成[/yellow]")
            else:
                console.print(f"[cyan]等待分析完成（最长 {timeout} 秒）...[/cyan]")

        # 如果需要等待
        if wait:
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                is_analyzing = analyzer and analyzer.is_analyzing(target_id)
                if not is_analyzing:
                    break
                time.sleep(2)

        # 获取分析结果
        analysis = analysis_store.get_analysis(target_id)

        if not analysis:
            if is_analyzing:
                console.print("[yellow]⚠ 异常正在分析中，尚未完成[/yellow]")
                console.print("[dim]可使用 --wait 参数等待分析完成[/dim]")
            else:
                console.print("[yellow]⚠ 该异常暂无分析记录[/yellow]")
                console.print("\n[cyan]提示: 您可以使用以下命令触发分析:[/cyan]")
                console.print(f"  ops-agent anomaly trigger -i {target_id}")
            return

        # 显示分析结果
        status = analysis.get("status", "unknown")
        status_color = _get_analysis_status_color(status)

        console.print("")
        console.print(Panel(
            Text(f"状态: [{status_color}]{status.upper()}[/]\n创建时间: {analysis.get('created_at', '-')}\n完成时间: {analysis.get('completed_at', '-')}"),
            title="[bold]分析概览[/bold]",
            border_style=status_color
        ))

        # 如果分析失败
        if status == "failed":
            error_msg = analysis.get("error_message", "未知错误")
            console.print(Panel(
                Text(error_msg, style="red"),
                title="[bold]分析失败[/bold]",
                border_style="red"
            ))
            return

        # 如果分析完成
        if status == "completed":
            # 显示根因分析
            root_cause = analysis.get("root_cause")
            if root_cause:
                console.print("\n[bold cyan]━━━ 根因分析 ━━━[/bold cyan]")

                category = root_cause.get("category", "其他")
                confidence = root_cause.get("confidence", 0.0)
                confidence_type = "success" if confidence >= 0.8 else "warning" if confidence >= 0.5 else "info"
                confidence_color = "green" if confidence >= 0.8 else "yellow" if confidence >= 0.5 else "cyan"

                console.print(f"\n[bold]分类:[/bold] {category}")
                console.print(f"[bold]置信度:[/bold] [{confidence_color}]{(confidence * 100):.0f}%[/]")

                analysis_text = root_cause.get("analysis", "")
                if analysis_text:
                    console.print(f"\n[bold]分析:[/bold]")
                    console.print(Panel(analysis_text, border_style="cyan"))

                evidence = root_cause.get("evidence", [])
                if evidence:
                    console.print(f"\n[bold]证据 ({len(evidence)} 条):[/bold]")
                    for i, ev in enumerate(evidence, 1):
                        ev_text = ev if isinstance(ev, str) else json.dumps(ev, ensure_ascii=False)
                        console.print(f"  {i}. {ev_text}")

            # 显示恢复计划
            recovery_plan = analysis.get("recovery_plan")
            if recovery_plan:
                console.print("\n[bold cyan]━━━ 故障恢复建议 ━━━[/bold cyan]")

                steps = recovery_plan.get("steps", [])
                if steps:
                    console.print(f"\n[bold]恢复步骤 ({len(steps)} 步):[/bold]")
                    for step in steps:
                        order = step.get("order", "?")
                        action = step.get("action", "")
                        risk = step.get("risk", "low")
                        risk_color = _get_risk_color(risk)
                        desc = step.get("description", "")
                        validation = step.get("validation", "")

                        console.print(f"\n[bold]步骤 {order}:[/bold] {action} [{risk_color}]{risk}[/]")
                        if desc:
                            console.print(f"  {desc}")
                        if validation:
                            console.print(f"  [dim]验证: {validation}[/dim]")

                precautions = recovery_plan.get("precautions", [])
                if precautions:
                    console.print(f"\n[bold]注意事项:[/bold]")
                    for i, p in enumerate(precautions, 1):
                        console.print(f"  {i}. {p}")

                estimated_time = recovery_plan.get("estimated_time")
                if estimated_time:
                    console.print(f"\n[bold]预计恢复时间:[/bold] {estimated_time}")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@anomaly_app.command("trigger")
def anomaly_trigger(
    anomaly_id: Optional[str] = typer.Option(
        None, "--id", "-i", help="异常 ID"
    ),
    index: int = typer.Option(
        1, "--index", "-n", help="异常索引（从 1 开始）"
    ),
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-ns", help="命名空间（使用索引时需要）"
    ),
    wait: bool = typer.Option(
        False, "--wait", "-w", help="等待分析完成"
    ),
    timeout: int = typer.Option(
        120, "--timeout", "-t", help="等待超时时间（秒）"
    ),
):
    """
    手动触发异常分析（与 GUI"触发分析/重新分析"按钮同步）

    使用示例:
      ops-agent anomaly trigger -i <异常ID>        # 触发指定异常的分析
      ops-agent anomaly trigger -n 1 -ns default   # 触发第 1 个异常的分析
      ops-agent anomaly trigger -i <ID> -w         # 触发并等待完成
    """
    _display_banner()

    # 获取异常 ID
    target_id = anomaly_id
    if not target_id:
        target_id = _get_anomaly_id_by_index(namespace=namespace, index=index)
        if not target_id:
            raise typer.Exit(code=1)

    console.print(f"\n[cyan]触发异常分析:[/cyan] {target_id}")

    try:
        analyzer = get_anomaly_analyzer()

        if not analyzer:
            console.print("[red]✗ 异常分析器未初始化[/red]")
            raise typer.Exit(code=1)

        # 检查是否正在分析
        if analyzer.is_analyzing(target_id):
            console.print("[yellow]⚠ 该异常正在分析中，请等待完成后再重试[/yellow]")
            raise typer.Exit(code=0)

        # 触发分析
        success = analyzer.analyze_anomaly_async(anomaly_id=target_id)

        if not success:
            console.print("[red]✗ 触发分析失败[/red]")
            raise typer.Exit(code=1)

        console.print("[green]✓ 分析任务已提交，正在后台执行...[/green]")

        if wait:
            console.print(f"[cyan]等待分析完成（最长 {timeout} 秒）...[/cyan]")
            start_wait = time.time()

            while time.time() - start_wait < timeout:
                if not analyzer.is_analyzing(target_id):
                    break
                console.print(".", end="", flush=True)
                time.sleep(2)

            console.print("")

            # 显示分析结果
            analysis_store = get_analysis_store()
            analysis = analysis_store.get_analysis(target_id)

            if analysis:
                status = analysis.get("status", "unknown")
                if status == "completed":
                    console.print("[green]✓ 分析完成[/green]")
                    console.print(f"\n[cyan]使用以下命令查看详细结果:[/cyan]")
                    console.print(f"  ops-agent anomaly analyze -i {target_id}")
                elif status == "failed":
                    console.print(f"[red]✗ 分析失败: {analysis.get('error_message', '未知错误')}[/red]")
            else:
                console.print("[yellow]⚠ 分析完成但未获取到结果[/yellow]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@anomaly_app.command("status")
def anomaly_status(
    anomaly_id: Optional[str] = typer.Option(
        None, "--id", "-i", help="异常 ID"
    ),
    index: int = typer.Option(
        1, "--index", "-n", help="异常索引（从 1 开始）"
    ),
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-ns", help="命名空间（使用索引时需要）"
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w", help="持续监视状态变化"
    ),
):
    """
    查看异常分析状态（与 GUI 轮询状态同步）

    使用示例:
      ops-agent anomaly status -i <异常ID>     # 查看指定异常的分析状态
      ops-agent anomaly status -n 1 -ns default  # 查看第 1 个异常的状态
      ops-agent anomaly status -i <ID> -w        # 持续监视状态变化
    """
    _display_banner()

    # 获取异常 ID
    target_id = anomaly_id
    if not target_id:
        target_id = _get_anomaly_id_by_index(namespace=namespace, index=index)
        if not target_id:
            raise typer.Exit(code=1)

    console.print(f"\n[cyan]查看分析状态:[/cyan] {target_id}")

    try:
        analysis_store = get_analysis_store()
        analyzer = get_anomaly_analyzer()

        def show_status():
            is_analyzing = analyzer and analyzer.is_analyzing(target_id)
            stored_status = analysis_store.get_status(target_id)

            console.print(f"\n[bold]异常 ID:[/bold] {target_id}")
            console.print(f"[bold]分析中:[/bold] {is_analyzing}")
            console.print(f"[bold]存储状态:[/bold] {stored_status or '无记录'}")

            # 显示统计信息
            try:
                stats = analysis_store.get_statistics()
                console.print(f"\n[bold]分析器统计:[/bold]")
                console.print(f"  总记录数: {stats.get('total', 0)}")
                console.print(f"  已完成: {stats.get('completed', 0)}")
                console.print(f"  分析中: {stats.get('analyzing', 0)}")
                console.print(f"  待分析: {stats.get('pending', 0)}")
                console.print(f"  失败: {stats.get('failed', 0)}")
            except Exception:
                pass

        if watch:
            console.print("[cyan]持续监视中（按 Ctrl+C 退出）...[/cyan]")
            try:
                while True:
                    show_status()
                    time.sleep(3)
            except KeyboardInterrupt:
                console.print("\n[cyan]已停止监视[/cyan]")
        else:
            show_status()

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


# ============================================================
# 健康分析器命令组
# ============================================================
health_app = typer.Typer(
    name="health",
    help="健康分析器相关命令",
    add_completion=False,
    no_args_is_help=True,
)
app.add_typer(health_app, name="health")


@health_app.command("status")
def health_status():
    """
    查看健康分析器状态（与 GUI 分析器状态同步）

    使用示例:
      ops-agent health status
    """
    _display_banner()
    console.print("\n[cyan]获取健康分析器状态...[/cyan]")

    try:
        analyzer = get_anomaly_analyzer()
        analysis_store = get_analysis_store()

        table = Table(title="健康分析器状态", border_style="cyan")
        table.add_column("属性", style="cyan")
        table.add_column("值", style="white")

        # 分析器状态
        is_running = analyzer and analyzer.is_running()
        running_color = "green" if is_running else "red"
        running_text = "[green]运行中[/green]" if is_running else "[red]已停止[/red]"

        # LLM 配置状态
        settings = get_settings()
        llm_available = settings.llm_configured
        llm_color = "green" if llm_available else "yellow"
        llm_text = "[green]已配置[/green]" if llm_available else "[yellow]未配置[/yellow]"

        table.add_row("分析器状态", running_text)
        table.add_row("LLM 配置", llm_text)
        table.add_row("最大并发数", str(analyzer.max_workers) if analyzer else "N/A")
        table.add_row("轮询间隔", f"{analyzer.poll_interval_seconds}s" if analyzer else "N/A")

        console.print(table)

        # 统计信息
        try:
            stats = analysis_store.get_statistics()
            stats_table = Table(title="分析记录统计", border_style="magenta")
            stats_table.add_column("状态", style="cyan")
            stats_table.add_column("数量", style="white", justify="right")

            stats_table.add_row("总记录数", str(stats.get('total', 0)))
            stats_table.add_row("[green]已完成[/green]", str(stats.get('completed', 0)))
            stats_table.add_row("[blue]分析中[/blue]", str(stats.get('analyzing', 0)))
            stats_table.add_row("[yellow]待分析[/yellow]", str(stats.get('pending', 0)))
            stats_table.add_row("[red]失败[/red]", str(stats.get('failed', 0)))

            console.print(stats_table)
        except Exception as e:
            console.print(f"[yellow]获取统计信息失败: {e}[/yellow]")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


@health_app.command("list")
def health_list(
    limit: int = typer.Option(20, "--limit", "-l", help="显示最近 N 条记录"),
    status_filter: str = typer.Option(
        "", "--status", "-s", help="按状态过滤 (pending/analyzing/completed/failed)"
    ),
):
    """
    查看异常分析记录列表（与 GUI 历史分析记录同步）

    使用示例:
      ops-agent health list                 # 查看最近 20 条记录
      ops-agent health list -l 50           # 查看最近 50 条记录
      ops-agent health list -s completed    # 只查看已完成的分析
    """
    _display_banner()
    console.print(f"\n[cyan]获取分析记录列表...[/cyan]")

    try:
        analysis_store = get_analysis_store()
        analyzer = get_anomaly_analyzer()

        # 获取所有记录
        all_records = analysis_store.get_pending_analysis(limit=limit)

        # 如果没有待分析记录，尝试获取已完成的
        if not all_records:
            # 简单方式：尝试查询所有状态
            all_records = []
            with analysis_store._get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT anomaly_id, status, created_at, completed_at
                       FROM anomaly_analysis
                       ORDER BY created_at DESC
                       LIMIT ?''',
                    (limit,)
                )
                for row in cursor.fetchall():
                    all_records.append({
                        'anomaly_id': row[0],
                        'status': row[1],
                        'created_at': row[2],
                        'completed_at': row[3],
                    })

        # 过滤状态
        if status_filter:
            all_records = [r for r in all_records if r.get('status') == status_filter]

        if not all_records:
            console.print("[yellow]暂无分析记录[/yellow]")
            return

        console.print(f"\n[green]✓ 共 {len(all_records)} 条记录[/green]\n")

        table = Table(title="异常分析记录", border_style="cyan")
        table.add_column("#", style="cyan", justify="right", width=4)
        table.add_column("异常 ID", style="magenta", width=36)
        table.add_column("状态", style="white", width=12)
        table.add_column("创建时间", style="blue", width=20)
        table.add_column("完成时间", style="green", width=20)

        for i, record in enumerate(all_records, 1):
            status = record.get("status", "unknown")
            status_color = _get_analysis_status_color(status)

            table.add_row(
                str(i),
                record.get("anomaly_id", "-"),
                f"[{status_color}]{status}[/]",
                str(record.get("created_at", "-")),
                str(record.get("completed_at", "-")),
            )

        console.print(table)

        # 统计信息
        status_counts: Dict[str, int] = {}
        for record in all_records:
            status = record.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        if status_counts:
            stats_parts = []
            for s, c in status_counts.items():
                color = _get_analysis_status_color(s)
                stats_parts.append(f"[{color}]{s}: {c}[/]")
            console.print(f"\n[bold]状态统计:[/bold] {', '.join(stats_parts)}")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(code=1)


def main():
    """CLI 主入口"""
    app()


if __name__ == "__main__":
    main()
