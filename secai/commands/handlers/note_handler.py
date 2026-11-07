"""Not, vaka defteri ve veritabani yedekleme isleyicileri."""

from rich.console import Console
from rich.prompt import Confirm, Prompt

from secai.commands.note_cmd import note_list, note_show
from secai.core.database import (
    VALID_CATEGORIES,
    add_note,
    export_note_markdown,
    get_note,
    list_backups,
    restore_database,
    update_note,
)

console = Console()


def interactive_add_note() -> None:
    console.print("\n[bold cyan][*] Yeni Not / Proje Kaydi[/bold cyan]")
    title = Prompt.ask("Baslik").strip()
    if not title:
        return

    category = Prompt.ask(
        "Kategori",
        choices=list(VALID_CATEGORIES),
        default="project",
    )
    tags = Prompt.ask("Etiketler (opsiyonel)", default="")
    content = Prompt.ask("Icerik").strip()
    if not content:
        return

    note_id = add_note(title=title, content=content, category=category, tags=tags)
    console.print(f"[bold green][+][/bold green] Kaydedildi (#{note_id})\n")


def interactive_edit_note() -> None:
    console.print()
    note_list(category=None, tag=None, query=None)
    choice = Prompt.ask("\nDuzenlenecek Not ID (iptal icin Enter)", default="").strip()
    if not choice.lstrip("#").isdigit():
        return

    note_id = int(choice.lstrip("#"))
    existing = get_note(note_id)
    if not existing:
        console.print(f"[bold red][-][/bold red] #{note_id} bulunamadi.\n")
        return

    console.print(f"\n[cyan][*] Secilen:[/cyan] #{note_id} {existing['title']}")
    mode = Prompt.ask(
        "Islem",
        choices=["ekle", "degistir"],
        default="ekle",
    )
    new_text = Prompt.ask("Yeni icerik / ek").strip()
    if not new_text:
        return

    update_note(note_id=note_id, content=new_text, append=(mode == "ekle"))
    console.print(f"[bold green][+][/bold green] #{note_id} guncellendi.\n")


def interactive_restore_backup() -> None:
    backups = list_backups()
    if not backups:
        console.print("\n[yellow][!][/yellow] Henuz alinmis bir yedek bulunamadi.\n")
        return

    console.print("\n[bold white]Mevcut Veritabani Yedekleri[/bold white]")
    for idx, b in enumerate(backups[:10], start=1):
        console.print(f"  [cyan]{idx}[/cyan]  {b.name}")

    choice = Prompt.ask("\nGeri yuklenecek yedek numarasi (iptal icin Enter)", default="").strip()
    if not choice.isdigit():
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(backups[:10]):
        console.print("[bold red][-][/bold red] Gecersiz secim.\n")
        return

    selected = backups[idx]
    if Confirm.ask(f"'{selected.name}' yedegi geri yuklensin mi?", default=False):
        restore_database(selected)
        console.print(f"[bold green][+][/bold green] Veritabani geri yuklendi: {selected.name}\n")


def interactive_list_and_read() -> None:
    console.print()
    note_list(category=None, tag=None, query=None)

    choice = Prompt.ask(
        "\nDetay okumak icin ID girin (geri donmek icin Enter)",
        default="",
    ).strip()

    if choice.lstrip("#").isdigit():
        note_id = int(choice.lstrip("#"))
        console.print()
        note_show(note_id)
        if Confirm.ask("Markdown (.md) olarak disa aktarilsin mi?", default=False):
            path = export_note_markdown(note_id)
            console.print(f"[bold green][+][/bold green] {path}")
    console.print()

