from pathlib import Path
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from secai import __version__
from secai.commands.audit_cmd import audit_command
from secai.commands.case_cmd import case_app, case_list
from secai.commands.chat_cmd import chat_command
from secai.commands.menu_cmd import (
    configure_api_key,
    interactive_baseline,
    interactive_diff,
    interactive_hardening_score,
    interactive_intel,
    interactive_restore_backup,
    interactive_security_checkup,
    interactive_voice_loop,
    manage_skills_interactive,
    run_interactive_menu,
)
from secai.commands.note_cmd import note_add, note_app, note_list, note_show
from secai.config import DEFAULT_MODEL, get_system_info
from secai.core.database import backup_database, init_db, restore_database
from secai.core.llm import check_ollama

app = typer.Typer(
    name="secai",
    help="SecOps CLI & Vaka Defteri",
    add_completion=False,
    invoke_without_command=True,
)

app.add_typer(note_app, name="note")
app.add_typer(case_app, name="case")
app.command("audit")(audit_command)
app.command("chat")(chat_command)
app.command("list", help="Kayitli notlari ve projeleri listeler.")(note_list)
app.command("show", help="Belirtilen ID'li notu gosterir.")(note_show)
app.command("add", help="Yeni not veya proje ekler.")(note_add)

console = Console()


@app.command("api")
def set_api(
    key: Optional[str] = typer.Argument(None, help="Google Gemini API Key"),
):
    """Gemini API anahtarini kaydeder ve Gemini modelini aktif eder."""
    configure_api_key(inline_key=key or "")


@app.command("skill")
def skill_cmd(
    name: Optional[str] = typer.Argument(None, help="Aktif edilecek skill adi (recon, hardening, detection, ctf, add, off)"),
):
    """SecOps yeteneklerini (skills) listeler, aktif eder veya yeni skill ekler."""
    manage_skills_interactive(inline_arg=name or "")


@app.command("check")
def check_system(
    yes: bool = typer.Option(False, "--yes", "-y", help="Onay sormadan taramayi baslat"),
):
    """Sistemin anlik guvenlik taramasini (portlar, ag, firewall, loglar) yapar ve AI ile analiz eder."""
    interactive_security_checkup(require_confirm=not yes)


@app.command("intel")
def intel_cmd(
    target: Optional[str] = typer.Argument(None, help="Sorgulanacak dis IP adresi veya log dosyasi"),
):
    """Shodan InternetDB ve GeoIP ile IP/CVE/Hash tehdit istihbarati sorgular."""
    interactive_intel(inline_target=target or "")


@app.command("baseline")
def baseline_cmd(
    label: str = typer.Argument("default", help="Baseline etiketi"),
):
    """Sistemin temiz referans kaydini (portlar, servisler, SHA256) alir."""
    interactive_baseline(label=label)


@app.command("diff")
def diff_cmd(
    ai: bool = typer.Option(False, "--ai", help="Sapmalari AI ile analiz et"),
):
    """Mevcut sistem durumunu son baseline ile karsilastirir (drift/anomali tespiti)."""
    interactive_diff(analyze_with_ai=ai)


@app.command("score")
def score_cmd(
    ai: bool = typer.Option(False, "--ai", help="Skor tablosunu AI ile degerlendir"),
):
    """Deterministik CIS Linux Guvenlik ve Sikilastirma Puanini (0-100) hesaplar."""
    interactive_hardening_score(analyze_with_ai=ai)


@app.command("voice")
def voice_cmd():
    """Canli Sesli Diyalog (Telsiz) modunu baslatir."""
    interactive_voice_loop(session="default")


@app.command("restore")
def restore(
    backup_file: Optional[Path] = typer.Argument(None, help="Geri yuklenecek .db yedek dosyasi"),
):
    """Kayitli bir yedekten veritabanini geri yukler."""
    if backup_file:
        try:
            path = restore_database(backup_file)
            console.print(f"[bold green][+][/bold green] Veritabani geri yuklendi: {path}")
        except ValueError as err:
            console.print(f"[bold red][-][/bold red] {err}")
            raise typer.Exit(code=1)
    else:
        interactive_restore_backup()


@case_app.callback(invoke_without_command=True)
def case_default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        case_list(category=None, status_filter=None)


@note_app.callback(invoke_without_command=True)
def note_default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        note_list(category=None, tag=None, query=None)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Versiyon"),
    case_flag: bool = typer.Option(False, "--case", help="Vaka listesi"),
    note_flag: bool = typer.Option(False, "--note", help="Not listesi"),
):
    if version:
        console.print(f"secai v{__version__}")
        raise typer.Exit()

    if case_flag:
        case_list(category=None, status_filter=None)
        raise typer.Exit()

    if note_flag:
        note_list(category=None, tag=None, query=None)
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        if not sys.stdin.isatty():
            audit_command(
                file=None,
                save_title=None,
                category="secops",
                tags="audit",
                custom_prompt=None,
                model=DEFAULT_MODEL,
            )
            raise typer.Exit()

        run_interactive_menu(status_callback=status)


@app.command("status")
def status():
    """Sistem, veritabani ve aktif LLM durumunu gosterir."""
    init_db()
    info = get_system_info()
    llm_state = check_ollama(base_url=info["ollama_url"])

    ollama_str = "[green]aktif[/green]" if llm_state["online"] else "[red]kapali[/red]"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="cyan")
    table.add_column("val", style="white")

    table.add_row("versiyon", __version__)
    table.add_row("sistem", info["os"])
    table.add_row("python", info["python"])
    table.add_row("veritabani", info["db_path"])
    table.add_row("yedekler", info["backup_dir"])
    table.add_row("aktif motor", info["provider"])
    table.add_row("aktif model", f"[green]{info['model']}[/green]")
    table.add_row("yerel ollama", ollama_str)

    console.print(table)


@app.command("backup")
def backup(
    target_dir: Optional[Path] = typer.Option(None, "--dir", "-d", help="Hedef klasor"),
):
    """Veritabanini yedekler."""
    backup_file = backup_database(target_dir=target_dir)
    console.print(f"[bold green][+][/bold green] Yedek alindi: {backup_file}")


if __name__ == "__main__":
    app()
