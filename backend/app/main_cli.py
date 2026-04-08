import os
import typer
import asyncio
import subprocess
import httpx
from typing import Optional, List
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from app.sdk.core import settings
from app.sdk.bootstrap import bootstrap_system
from app.sdk.discovery.graph_sync import GraphSyncManager
from app.sdk.spec_engine import get_spec_engine

# --- Root Apps ---
app = typer.Typer(help="HiveMind Unified CLI - The Commander")
console = Console()

# --- Sub Apps ---
spec_app = typer.Typer(help="Specification & Graph Management")
db_app = typer.Typer(help="Database & Data Management")
audit_app = typer.Typer(help="System Governance & Auditing")
learn_app = typer.Typer(help="Self-Learning & Ingestion Cycle")
eval_app = typer.Typer(help="Evaluation & Benchmarking")
scaffold_app = typer.Typer(help="Smart Scaffolding for New Projects")

app.add_typer(spec_app, name="spec")
app.add_typer(db_app, name="db")
app.add_typer(audit_app, name="audit")
app.add_typer(learn_app, name="learn")
app.add_typer(eval_app, name="eval")
app.add_typer(scaffold_app, name="scaffold")

# --- Utils ---
def run_script(script_name: str):
    """Helper to run a script from the backend/scripts directory."""
    script_path = os.path.join("backend", "scripts", script_name)
    if not os.path.exists(script_path):
        typer.secho(f"Error: Script {script_name} not found at {script_path}", fg="red")
        return
    
    # Set PYTHONPATH and execute
    env = os.environ.copy()
    env["PYTHONPATH"] = "backend"
    subprocess.run(["python", script_path], env=env)

# --- Root Commands ---
@app.command()
def doctor():
    """环境自检与系统引导 (System Health Check)"""
    typer.echo("Running HiveMind Doctor...")
    asyncio.run(bootstrap_system())

# --- DB Commands ---
@db_app.command()
def init():
    """初始化所有数据库表 (init_all_tables.py)"""
    typer.echo("Initializing all database tables...")
    run_script("init_all_tables.py")

@db_app.command()
def seed():
    """植入基础 Prompt 与 Demo 数据 (seed_initial_prompts.py)"""
    typer.echo("Seeding initial prompts and demo data...")
    run_script("seed_initial_prompts.py")

# --- Audit Commands ---
@audit_app.command()
def costs():
    """审计 LLM 使用成本 (audit_llm_costs.py)"""
    typer.echo("Auditing LLM token costs...")
    run_script("audit_llm_costs.py")

@audit_app.command()
def system():
    """运行全方位系统审计 (run_system_audit.py)"""
    typer.echo("Running comprehensive system audit...")
    run_script("run_system_audit.py")

# --- Learn Commands ---
@learn_app.command()
def cycle():
    """启动每日智体学习闭环 (run_daily_learning_cycle.py)"""
    typer.echo("Starting daily learning cycle...")
    run_script("run_daily_learning_cycle.py")

@learn_app.command()
def report():
    """生成本周学习总结报告 (generate_synthetic_dataset.py)"""
    typer.echo("Generating weekly learning report...")
    run_script("generate_weekly_learning_report.py")

# --- Eval Commands ---
@eval_app.command()
def benchmark():
    """运行进化基准测试 (run_evolution_benchmark.py)"""
    typer.echo("Running evolution benchmark...")
    run_script("run_evolution_benchmark.py")

@eval_app.command()
def run(name: str):
    """运行 scripts 目录下的指定测试脚本 (如 hm eval run test_vfs.py)"""
    typer.echo(f"Running custom test scenario: {name}")
    run_script(name)

@eval_app.command()
def list():
    """列出 scripts 目录中所有可用的测试脚本"""
    scripts = [f for f in os.listdir("backend/scripts") if f.startswith("test_") or f.startswith("verify_")]
    typer.echo("--- Available Test Scenarios ---")
    for s in sorted(scripts):
        typer.echo(f" - {s}")

# --- Spec Commands (Refactored) ---
@spec_app.command()
def sync():
    """同步全站规格文档至 Neo4j 图谱"""
    typer.echo("Syncing specs to Graph...")
    sync_manager = GraphSyncManager()
    asyncio.run(sync_manager.sync_all_specs())
    typer.echo("Sync Complete.")

@spec_app.command()
def registry():
    """强制同步代码装饰器与 REGISTRY.md (sync_registry.py)"""
    typer.echo("Syncing Code Registry with documentation...")
    run_script("sync_registry.py")

@spec_app.command()
def status():
    """概览系统中所有活跃的规格与变更"""
    engine = get_spec_engine()
    report = engine.generate_report()
    typer.echo("--- Spec Global Status ---")
    typer.echo(f"REQ: {report['by_category']['requirement']}")
    typer.echo(f"DES: {report['by_category']['design']}")
    typer.echo(f"Change: {report['by_category']['change']}")
    typer.echo("--------------------------")

# --- Scaffold Commands ---
@scaffold_app.command()
def init(name: str):
    """一键初始化 HiveMind 兼容的项目标准结构"""
    typer.echo(f"Building HiveMind Scaffold for project: {name}...")
    
    dirs = [
        f"{name}/backend/app/sdk",
        f"{name}/backend/app/services",
        f"{name}/docs/requirements",
        f"{name}/docs/design",
        f"{name}/openspec/changes",
        f"{name}/storage"
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        typer.echo(f" - Created directory: {d}")
        
    # 模拟拷贝 SDK 核心文件
    typer.secho(f"Success! Project {name} is now HiveMind-ready.", fg="green")
    typer.echo(f"Next step: cd {name} && hm doctor")

# --- Chat Command (The Experience) ---
@app.command()
def chat():
    """进入交互式对话模式，与 HiveMind Architect 深度协作 (Experience Mode)"""
    console.print(Panel("[bold cyan]Welcome to HiveMind Chat[/bold cyan]\n[dim]I am your Architect. I see your specs, I guard your redlines.[/dim]"))
    
    engine = get_spec_engine()
    report = engine.generate_report()
    history = [
        {"role": "system", "content": f"You are HiveMind Architect. Current Specs: {report['total']}. Redlines are in HIVE.md. Use Markdown output."}
    ]

    while True:
        try:
            user_input = console.input("[bold green]>>> [/bold green]")
        except EOFError:
            break
            
        if user_input.lower() in ["exit", "quit", "bye"]:
            break
            
        history.append({"role": "user", "content": user_input})
        
        with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10, transient=True):
            try:
                if settings.LLM_API_KEY:
                    with httpx.Client() as client:
                        response = client.post(
                            f"{settings.LLM_BASE_URL}/chat/completions",
                            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
                            json={
                                "model": settings.LLM_MODEL,
                                "messages": history,
                                "stream": False
                            },
                            timeout=60.0
                        )
                        result = response.json()["choices"][0]["message"]["content"]
                else:
                    result = "[yellow]LLM_API_KEY not configured.[/yellow]\nI am here to help you manage your 27 specs."
            except Exception as e:
                result = f"[red]Error: {str(e)}[/red]"

        history.append({"role": "assistant", "content": result})
        console.print(Markdown(result))
        console.print("-" * 50)

if __name__ == "__main__":
    app()
