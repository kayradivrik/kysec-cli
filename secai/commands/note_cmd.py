from pathlib import Path
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from secai.core.database import (
    VALID_CATEGORIES,
    add_note,
    delete_note,
    export_note_markdown,
    get_note,
    list_notes,
    update_note,
)

note_app = typer.Typer(
    help="Vaka ve proje notlari.",
    no_args_is_help=False,
)
console = Console()


@note_app.command("add")
def note_add(
    title: str = typer.Argument(..., help="Baslik"),
    content: Optional[str] = typer.Argument(None, help="Icerik (veya stdin pipe)"),
    category: str = typer.Option("general", "--category", "-c", help=f"Kategori ({', '.join(VALID_CATEGORIES)})"),
    tags: str = typer.Option("", "--tags", "-t", help="Etiketler (virgulle ayrilmis)"),
):
    """Yeni not veya proje kaydi ekler."""
    final_content = content
    if not final_content:
        if not sys.stdin.isatty():
            final_content = sys.stdin.read()
        else:
            console.print("[bold red][-][/bold red] Icerik girilmedi.")
            raise typer.Exit(code=1)

    if not final_content or not final_content.strip():
        console.print("[bold red][-][/bold red] Bos icerik kaydedilemez.")
        raise typer.Exit(code=1)

    note_id = add_note(title=title, content=final_content, category=category, tags=tags)
    console.print(f"[bold green][+][/bold green] Kaydedildi (#{note_id}) - {title} [{category}]")


@note_app.command("edit")
def note_edit(
    note_id: int = typer.Argument(..., help="Duzenlenecek Not ID"),
    content: Optional[str] = typer.Argument(None, help="Yeni veya eklenecek icerik"),
    title: Optional[str] = typer.Option(None, "--title", help="Yeni baslik"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Yeni kategori"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Yeni etiketler"),
    append: bool = typer.Option(
        True,
        "--append/--replace",
        help="Mevcut icerigin sonuna ekle (--append) veya tamamen degistir (--replace)",
    ),
):
    """Mevcut bir notun uzerine ekleme yapar veya gunceller."""
    final_content = content
    if not final_content and not sys.stdin.isatty():
        final_content = sys.stdin.read()

    ok = update_note(
        note_id=note_id,
        title=title,
        content=final_content,
        category=category,
        tags=tags,
        append=append,
    )
    if not ok:
        console.print(f"[bold red][-][/bold red] #{note_id} bulunamadi.")
        raise typer.Exit(code=1)
    console.print(f"[bold green][+][/bold green] #{note_id} guncellendi.")


@note_app.command("list")
def note_list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Kategori filtresi"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Etiket filtresi"),
    query: Optional[str] = typer.Option(None, "--search", "-q", help="Kelime arama"),
):
    """Kayitli notlari ve projeleri listeler."""
    rows = list_notes(category=category, tag=tag, search_query=query)

    if not rows:
        console.print("[yellow][!][/yellow] Kayit bulunamadi.")
        return

    table = Table(border_style="dim")
    table.add_column("ID", style="cyan", justify="right", no_wrap=True)
    table.add_column("Baslik", style="white", min_width=24)
    table.add_column("Kategori", style="yellow", no_wrap=True)
    table.add_column("Etiketler", style="magenta")
    table.add_column("Tarih", style="dim", no_wrap=True)

    for r in rows:
        table.add_row(
            f"#{r['id']}",
            r["title"],
            r["category"],
            r["tags"] or "-",
            r["created_at"],
        )

    console.print(table)


@note_app.command("show")
def note_show(
    note_id: int = typer.Argument(..., help="Not ID"),
):
    """Not icerigini gosterir."""
    note = get_note(note_id)
    if not note:
        console.print(f"[bold red][-][/bold red] #{note_id} bulunamadi.")
        raise typer.Exit(code=1)

    meta = f"Kategori: {note['category']} | Etiketler: {note['tags'] or '-'} | Tarih: {note['created_at']}"
    console.print(
        Panel(
            Markdown(note["content"]),
            title=f"#{note['id']} {note['title']}",
            subtitle=meta,
            border_style="dim",
        )
    )


@note_app.command("export")
def note_export(
    note_id: int = typer.Argument(..., help="Not ID"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Dosya yolu (.md)"),
):
    """Notu Markdown (.md) dosyasina aktarir."""
    try:
        export_path = export_note_markdown(note_id=note_id, output_path=output)
        console.print(f"[bold green][+][/bold green] Disa aktarildi: {export_path}")
    except ValueError as err:
        console.print(f"[bold red][-][/bold red] {err}")
        raise typer.Exit(code=1)


@note_app.command("delete")
def note_delete(
    note_id: int = typer.Argument(..., help="Not ID"),
):
    """Notu siler."""
    deleted = delete_note(note_id)
    if not deleted:
        console.print(f"[bold red][-][/bold red] #{note_id} bulunamadi.")
        raise typer.Exit(code=1)
    console.print(f"[bold green][+][/bold green] #{note_id} silindi.")
