"""Tehdit istihbarati (Shodan, VirusTotal, AbuseIPDB) komut isleyicileri."""

from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.prompt import Prompt

from secai.config import load_settings
from secai.core.intel import (
    enrich_abuseipdb,
    enrich_virustotal,
    format_intel_report,
)

console = Console()


def interactive_intel(inline_target: str = "") -> None:
    """Shodan InternetDB & GeoIP ile dis IP veya log metnini analiz eder."""
    target = inline_target.strip()
    if not target:
        target = Prompt.ask("\nSorgulanacak dis IP adresi, log metni veya dosya yolu").strip()
    if not target:
        return

    potential_file = Path(target).expanduser()
    if potential_file.exists() and potential_file.is_file():
        raw_text = potential_file.read_text(encoding="utf-8", errors="replace")
    else:
        raw_text = target

    console.print("\n[bold cyan][*][/bold cyan] Shodan InternetDB & GeoIP tehdit istihbarati sorgulaniyor...")
    report_md = format_intel_report(raw_text, max_ips=10)
    console.print()
    console.print(Padding(Markdown(report_md, code_theme="monokai"), (0, 1)))
    console.print()


def interactive_vt(inline_target: str = "") -> None:
    """VirusTotal v3 API uzerinden IP, domain veya hash taramasi yapar."""
    target = inline_target.strip()
    if not target:
        target = Prompt.ask("\n[bold cyan]Sorgulanacak IP, Domain veya SHA256/MD5 Hash[/bold cyan]").strip()
        if not target:
            return

    s = load_settings()
    vt_key = s.get("virustotal_api_key", "").strip()
    if not vt_key:
        console.print("\n[yellow][!] VirusTotal API anahtarı tanımlı değil.[/yellow]")
        console.print("[dim]https://www.virustotal.com/ üzerinden ücretsiz alıp '/api vt <key>' ile ekleyebilirsiniz.[/dim]\n")
        return

    with console.status(f"[bold cyan]🔍 VirusTotal v3 taranıyor: {target}...[/bold cyan]", spinner="dots"):
        res = enrich_virustotal(target)

    if not res:
        console.print(f"[yellow][!] VirusTotal üzerinde '{target}' için kayıt bulunamadı veya API hatası oluştu.[/yellow]\n")
        return

    color = "red" if res["is_dangerous"] else "green"
    badge = "[bold red]🚨 ZARARLI TESPİT EDİLDİ[/bold red]" if res["is_dangerous"] else "[bold green]✓ TEMİZ / GÜVENLİ[/bold green]"
    console.print(
        Panel(
            f"{badge}\n\n"
            f"[bold]Hedef:[/bold] [cyan]{res['target']}[/cyan] ({res['type']})\n"
            f"[bold]Tespit Skoru:[/bold] [{color}]{res['score_label']}[/{color}]\n"
            f"[bold]Zararlı:[/bold] {res['malicious']}  |  [bold]Şüpheli:[/bold] {res['suspicious']}  |  [bold]Temiz/Atlanan:[/bold] {res['harmless'] + res['undetected']}\n"
            f"[bold]Topluluk İtibarı:[/bold] {res['reputation']}\n",
            title="🛡️ VirusTotal v3 Tehdit İstihbaratı",
            border_style=color,
        )
    )


def interactive_abuse(inline_ip: str = "") -> None:
    """AbuseIPDB v2 API uzerinden IP kotu niyetlilik ve saldiri itibarini sorgular."""
    ip = inline_ip.strip()
    if not ip:
        ip = Prompt.ask("\n[bold cyan]Sorgulanacak Dış IPv4 Adresi[/bold cyan]").strip()
        if not ip:
            return

    s = load_settings()
    key = s.get("abuseipdb_api_key", "").strip()
    if not key:
        console.print("\n[yellow][!] AbuseIPDB API anahtarı tanımlı değil.[/yellow]")
        console.print("[dim]https://www.abuseipdb.com/ üzerinden ücretsiz alıp '/api abuse <key>' ile ekleyebilirsiniz.[/dim]\n")
        return

    with console.status(f"[bold cyan]⚡ AbuseIPDB taranıyor: {ip}...[/bold cyan]", spinner="dots"):
        res = enrich_abuseipdb(ip)

    if not res:
        console.print(f"[yellow][!] AbuseIPDB üzerinde '{ip}' için kayıt bulunamadı veya geçersiz IP.[/yellow]\n")
        return

    color = "red" if res["abuse_score"] >= 40 else "yellow" if res["abuse_score"] >= 15 else "green"
    console.print(
        Panel(
            f"[bold]Kötü Niyetlilik Skoru:[/bold] [{color}]%{res['abuse_score']} ({res['risk']})[/{color}]\n\n"
            f"[bold]IP:[/bold] [cyan]{res['ip']}[/cyan]  |  [bold]Ülke:[/bold] {res['country']}  |  [bold]ISP:[/bold] {res['isp']}\n"
            f"[bold]Toplam Şikayet / Rapor:[/bold] {res['total_reports']} adet\n"
            f"[bold]Son Şikayet Tarihi:[/bold] {res['last_reported_at']}\n"
            f"[bold]Beyaz Liste:[/bold] {'Evet' if res['is_whitelisted'] else 'Hayır'}\n",
            title="⚡ AbuseIPDB Saldırı & İtibar Analizi",
            border_style=color,
        )
    )

