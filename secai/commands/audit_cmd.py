from pathlib import Path
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding

from secai.config import DEFAULT_MODEL
from secai.core.database import add_note
from secai.core.intel import extract_iocs, format_intel_report
from secai.core.llm import OllamaConnectionError, stream_generate

console = Console()


def audit_command(
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Analiz edilecek dosya"),
    save_title: Optional[str] = typer.Option(None, "--save", "-s", help="Ciktiyi belirtilen baslikla kaydet"),
    category: str = typer.Option("secops", "--category", "-c", help="Kategori"),
    tags: str = typer.Option("audit", "--tags", "-t", help="Etiketler"),
    custom_prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Ozel analiz talimati"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Ollama modeli"),
):
    """Log, komut ciktisi (pipe) veya kaynak kodu analiz eder."""
    raw_input = ""
    source_label = "stdin"

    if file:
        target = file.expanduser().resolve()
        if not target.exists() or not target.is_file():
            console.print(f"[bold red][-][/bold red] Dosya bulunamadi: {target}")
            raise typer.Exit(code=1)
        raw_input = target.read_text(encoding="utf-8", errors="replace")
        source_label = str(target.name)
    elif not sys.stdin.isatty():
        raw_input = sys.stdin.read()
    else:
        console.print(
            "[bold red][-][/bold red] Veri girilmedi.\n"
            "Kullanim: journalctl -n 20 | secai audit  veya  secai audit -f dosya.log"
        )
        raise typer.Exit(code=1)

    if not raw_input.strip():
        console.print("[bold red][-][/bold red] Gelen veri bos.")
        raise typer.Exit(code=1)

    instruction = (
        custom_prompt
        or "Asagidaki log, komut ciktisi veya kod blogunu guvenlik acisindan analiz et:"
    )

    iocs = extract_iocs(raw_input)
    intel_block = ""
    if iocs["ips"] or iocs["cves"] or iocs["sha256"]:
        console.print(
            f"[bold cyan][*][/bold cyan] IOC tespit edildi ({len(iocs['ips'])} dis IP, {len(iocs['cves'])} CVE) — Shodan InternetDB sorgulaniyor..."
        )
        intel_md = format_intel_report(raw_input, max_ips=6)
        console.print(Padding(Markdown(intel_md, code_theme="monokai"), (0, 1)))
        console.print()
        intel_block = f"\n\n[OTOMATIK SHODAN & IOC TEHDIT ISTIHBARATI]:\n{intel_md}"

    full_prompt = f"{instruction}\n\n```\n{raw_input.strip()}\n```{intel_block}"

    console.print(
        f"[bold cyan][*][/bold cyan] kaynak: {source_label} | model: {model} | satir: {len(raw_input.splitlines())}\n"
    )

    collected_chunks: list[str] = []
    try:
        gen = stream_generate(prompt=full_prompt, model=model)
        with console.status("[cyan][*] analiz ediliyor...[/cyan]", spinner="dots"):
            first_token = next(gen, None)

        if first_token:
            collected_chunks.append(first_token)
            with Live(
                Padding(Markdown("".join(collected_chunks), code_theme="monokai"), (0, 1)),
                console=console,
                refresh_per_second=14,
            ) as live:
                for token in gen:
                    collected_chunks.append(token)
                    live.update(
                        Padding(Markdown("".join(collected_chunks), code_theme="monokai"), (0, 1))
                    )
            console.print()
    except OllamaConnectionError as err:
        console.print(f"\n[bold red][-][/bold red] {err}")
        raise typer.Exit(code=1)

    final_analysis = "".join(collected_chunks).strip()

    if save_title and final_analysis:
        note_id = add_note(
            title=save_title,
            content=final_analysis,
            category=category,
            tags=tags,
        )
        console.print(
            f"[bold green][+][/bold green] Rapor kaydedildi (#{note_id}: {save_title})"
        )
