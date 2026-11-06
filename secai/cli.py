import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from secai import __version__
from secai.config import get_system_info

app = typer.Typer(
    name="secai",
    help="SecOps CLI Asistanı & Vaka Defteri (Local LLM + Casebook)",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Versiyon bilgisini gösterir ve çıkar."
    ),
):
    """SecOps CLI Asistanı & Vaka Defteri."""
    if version:
        console.print(f"[bold cyan]secai[/bold cyan] v{__version__}")
        raise typer.Exit()


@app.command("status")
def status():
    """Sistem, veri dizini ve yapılandırma durumunu gösterir."""
    info = get_system_info()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Anahtar", style="bold cyan")
    table.add_column("Değer", style="white")

    table.add_row("Versiyon", __version__)
    table.add_row("İşletim Sistemi", info["os"])
    table.add_row("Python Sürümü", info["python"])
    table.add_row("Veri Dizini", info["data_dir"])
    table.add_row("Veritabanı Yolu", info["db_path"])

    console.print(
        Panel(
            table,
            title="[bold green]SecAI Sistem Durumu[/bold green]",
            border_style="green",
            expand=False,
        )
    )


if __name__ == "__main__":
    app()

