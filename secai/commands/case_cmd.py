import sys
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from secai.core.database import (
    VALID_CATEGORIES,
    VALID_STATUSES,
    add_case_entry,
    create_case,
    get_case_with_entries,
    list_cases,
    update_case_status,
)

case_app = typer.Typer(
    help="Vaka ve proje takibi.",
    no_args_is_help=False,
)
console = Console()


@case_app.command("new")
def case_new(
    title: str = typer.Argument(..., help="Baslik"),
    category: str = typer.Option("general", "--category", "-c", help=f"Kategori ({', '.join(VALID_CATEGORIES)})"),
    tags: str = typer.Option("", "--tags", "-t", help="Etiketler"),
):
    """Yeni vaka veya proje acar."""
    try:
        case_id = create_case(title=title, category=category, tags=tags)
        console.print(f"[bold green][+][/bold green] Vaka olusturuldu (#{case_id}) - {title} [{category}]")
    except ValueError as err:
        console.print(f"[bold red][-][/bold red] {err}")
        raise typer.Exit(code=1)


@case_app.command("list")
def case_list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Kategori filtresi"),
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Durum filtresi"),
):
    """Vakalari ve projeleri listeler."""
    rows = list_cases(category=category, status=status_filter)

    if not rows:
        console.print("[yellow][!][/yellow] Kayit bulunamadi.")
        return

    table = Table(border_style="dim")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Baslik", style="white")
    table.add_column("Kategori", style="yellow")
    table.add_column("Durum", style="green")
    table.add_column("Kayit", justify="center", style="magenta")
    table.add_column("Etiketler", style="dim")
    table.add_column("Tarih", style="dim")

    for r in rows:
        status_color = "green" if r["status"] == "open" else "dim"
        table.add_row(
            f"#{r['id']}",
            r["title"],
            r["category"],
            f"[{status_color}]{r['status']}[/{status_color}]",
            str(r["entry_count"]),
            r["tags"] or "-",
            r["created_at"],
        )

    console.print(table)


@case_app.command("add")
def case_add_entry(
    case_id: int = typer.Argument(..., help="Vaka ID"),
    content: Optional[str] = typer.Argument(None, help="Icerik"),
    entry_type: str = typer.Option("note", "--type", "-t", help="Tur (note, finding, command, todo)"),
):
    """Vakaya yeni bulgu veya adim ekler."""
    final_content = content
    if not final_content:
        if not sys.stdin.isatty():
            final_content = sys.stdin.read()
        else:
            console.print("[bold red][-][/bold red] Icerik belirtilmedi.")
            raise typer.Exit(code=1)

    try:
        entry_id = add_case_entry(case_id=case_id, content=final_content, entry_type=entry_type)
        console.print(f"[bold green][+][/bold green] #{case_id} altina kayit eklendi (#{entry_id}).")
    except ValueError as err:
        console.print(f"[bold red][-][/bold red] {err}")
        raise typer.Exit(code=1)


@case_app.command("show")
def case_show(
    case_id: int = typer.Argument(..., help="Vaka ID"),
):
    """Vaka detaylarini ve alt kayitlarini gosterir."""
    case_row, entries = get_case_with_entries(case_id)
    if not case_row:
        console.print(f"[bold red][-][/bold red] #{case_id} bulunamadi.")
        raise typer.Exit(code=1)

    console.print(
        f"\n[bold cyan]#{case_row['id']} {case_row['title']}[/bold cyan] "
        f"({case_row['category']} | {case_row['status']} | {case_row['tags'] or '-'})"
    )

    if not entries:
        console.print("[dim]Alt kayit yok.[/dim]")
        return

    for idx, entry in enumerate(entries, start=1):
        console.print(
            Panel(
                Markdown(entry["content"]),
                title=f"#{idx} [{entry['entry_type']}]",
                subtitle=entry["created_at"],
                border_style="dim",
            )
        )


@case_app.command("status")
def case_status(
    case_id: int = typer.Argument(..., help="Vaka ID"),
    new_status: str = typer.Argument(..., help=f"Durum ({', '.join(VALID_STATUSES)})"),
):
    """Vaka durumunu gunceller."""
    try:
        updated = update_case_status(case_id=case_id, new_status=new_status)
        if not updated:
            console.print(f"[bold red][-][/bold red] #{case_id} bulunamadi.")
            raise typer.Exit(code=1)
        console.print(f"[bold green][+][/bold green] #{case_id} durumu '{new_status}' yapildi.")
    except ValueError as err:
        console.print(f"[bold red][-][/bold red] {err}")
        raise typer.Exit(code=1)
