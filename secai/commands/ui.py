"""SecAI Terminal UI, Banner, Prompt cercevesi ve Readline yonetimi."""

import os
from pathlib import Path
import shutil
import sys
from rich.console import Console
from rich.table import Table
from rich.text import Text

try:
    import readline
except ImportError:
    readline = None  # type: ignore

from secai import __version__
from secai.config import get_active_llm_info, get_data_dir, get_user_host_cwd, load_settings
from secai.core.skills import get_active_skill

console = Console()

SLASH_COMMANDS = [
    "/new",
    "/yeni",
    "/chats",
    "/chat",
    "/rename",
    "/title",
    "/baslik",
    "/sessions",
    "/memory",
    "/bellek",
    "/infomy",
    "/myinfo",
    "/kimim",
    "/image",
    "/img",
    "/ciz",
    "/gorsel",
    "/vt",
    "/virustotal",
    "/abuse",
    "/abuseipdb",
    "/agent",
    "/agents",
    "/ajan",
    "/skills",
    "/skill",
    "/yetenek",
    "/check",
    "/intel",
    "/baseline",
    "/diff",
    "/score",
    "/harden",
    "/notes",
    "/list",
    "/defter",
    "/add",
    "/edit",
    "/backup",
    "/restore",
    "/status",
    "/report",
    "/save",
    "/clear",
    "/v",
    "/talk",
    "/voice",
    "/ses",
    "/tts",
    "/web",
    "/help",
    "/exit",
    "/q",
    "/?",
    "/model",
    "/models",
    "/motor",
    "/smart",
    "/smartmode",
    "/analyze",
    "/run",
    "/api",
    "/key",
]

PIXEL_LOGO_LINES = [
    ("   ▄▄▄▄▄    ", "#38bdf8"),
    (" ▄██▀▀▀▀██▄ ", "#60a5fa"),
    (" ██ ▄██▄ ██ ", "#818cf8"),
    (" ██▄    ▄██ ", "#8b5cf6"),
    ("  ▀▀████▀▀  ", "#a855f7"),
]


def setup_readline() -> Path:
    history_file = get_data_dir() / "command_history"
    if readline is None:
        return history_file

    if history_file.exists():
        try:
            readline.read_history_file(str(history_file))
        except Exception:
            pass

    readline.set_history_length(500)

    def completer(text: str, state: int):
        options = [c for c in SLASH_COMMANDS if c.startswith(text.lower())]
        if state < len(options):
            return options[state]
        return None

    try:
        readline.parse_and_bind("tab: complete")
        readline.set_completer(completer)
        readline.set_completer_delims(" \t\n")
    except Exception:
        pass

    return history_file


def save_readline_history(history_file: Path) -> None:
    if readline is None:
        return
    try:
        readline.write_history_file(str(history_file))
        if os.name == "posix" and history_file.exists():
            history_file.chmod(0o600)
    except Exception:
        pass


def render_top_banner() -> None:
    """Ekranı temizler ve Antigravity CLI tarzı üst başlığı çizer."""
    console.clear()
    llm_info = get_active_llm_info()
    settings = load_settings()
    active_skill = get_active_skill()
    skill_badge = f"  [skill: {active_skill['name']}]" if active_skill else ""
    tts_badge = "  [ses: aktif]" if settings.get("tts_enabled") else ""
    user_host, cwd_short = get_user_host_cwd()

    logo_text = Text()
    for idx, (line, color) in enumerate(PIXEL_LOGO_LINES):
        logo_text.append(line, style=f"bold {color}")
        if idx < len(PIXEL_LOGO_LINES) - 1:
            logo_text.append("\n")

    info_text = Text()
    info_text.append(f"SecAI CLI {__version__}\n", style="bold #38bdf8")
    info_text.append(f"{user_host} ({llm_info['provider_label']})\n", style="dim white")
    info_text.append(f"{llm_info['model']}{skill_badge}{tts_badge}\n", style="dim white")
    info_text.append(f"{cwd_short}", style="dim white")

    header_grid = Table.grid(padding=(0, 2))
    header_grid.add_column()
    header_grid.add_column()
    header_grid.add_row(logo_text, info_text)

    console.print()
    console.print(header_grid)
    console.print()


def render_prompt_frame_and_input() -> str:
    """İnce çizgili > giriş alanını ve alt kısayol çubuğunu readline uyumlu olarak çizer."""
    llm_info = get_active_llm_info()
    term_width = shutil.get_terminal_size((80, 24)).columns
    line_str = "─" * term_width

    left_hint = " ? kisayollar   /v sesli konus   /ses ayar   /model   /notes   /check"
    right_model = f"{llm_info['model']} "
    spaces = max(1, term_width - len(left_hint) - len(right_model))
    footer = f"[dim]{left_hint}{' ' * spaces}{right_model}[/dim]"

    console.print(f"[#0e4f6e]{line_str}[/#0e4f6e]")
    console.print(footer)
    console.print(f"[#0e4f6e]{line_str}[/#0e4f6e]")

    if sys.stdout.isatty() and readline is not None:
        prompt_str = "\001\033[1;36m\002> \001\033[0m\002"
        return input(prompt_str).strip()

    return console.input("[bold cyan]> [/bold cyan]").strip()


def show_shortcuts() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("cmd", style="bold cyan")
    table.add_column("desc", style="white")

    table.add_row("/new", "ChatGPT gibi yepyeni bir sohbet oturumu baslat")
    table.add_row("/chats", "Gecmis sohbet oturumlarini listele (/chat <id> ile gecis yap)")
    table.add_row("/memory", "SecAI'nin senin hakkinda ogrendigi kalici kisisel bellekleri goster")
    table.add_row("/infomy", "Kim olduğunu, rolünü ve tercihlerini kaydet (/infomy ile güncelle)")
    table.add_row("/image <prompt>", "Yerel AI Görsel Stüdyosu ile siber güvenlik / konsept görseli üret")
    table.add_row("/web", "Sade React Web Arayuzunu baslat (127.0.0.1:8765)")
    table.add_row("/v veya /talk", "Bas-Konus: Mikrofondan sesli emir ver, SecAI sesli ve yazili yanitlasin")
    table.add_row("/voice", "Canli Sesli Diyalog (Telsiz Modu): Karsilikli kesintisiz sesli sohbet")
    table.add_row("/ses veya /tts", "Ses ayarlarini yonet (Ahmet/Emel ses secimi, yazili sohbette ses ac/kapat)")
    table.add_row("/api", "API Anahtarlarını yönet (Groq, DeepSeek, Gemini, OpenRouter, VT, Abuse)")
    table.add_row("/model", "Aktif AI Motorunu değiştir (Groq 500t/s, DeepSeek R1, Gemini, Ollama)")
    table.add_row("/smart", "Smart Mode: Karmaşık tersine mühendislik / exploit analizlerinde akıllı model önerici")
    table.add_row("/analyze <dosya/komut>", "Dosyayı güvenli chunking ile oku veya çıktıyı kıdemli analist promptuyla incele")
    table.add_row("/run <komut>", "Sistem komutunu alt süreçte çalıştır ve sonucunu güvenlik analisti gözüyle analiz et")
    table.add_row("/skills", "SecOps yeteneklerini (recon, hardening, detection, ctf) sec veya yeni skill ekle")
    table.add_row("/intel <ip/log>", "Shodan InternetDB & GeoIP ile IP/CVE/Hash tehdit istihbarati sorgula")
    table.add_row("/vt <hedef>", "VirusTotal v3 ile IP, Domain veya Hash (MD5/SHA256) güvenlik taraması")
    table.add_row("/abuse <ip>", "AbuseIPDB v2 ile IP kötü niyetlilik ve saldırı itibar kontrolü")
    table.add_row("/baseline", "Sistemin temiz referans goruntusunu (portlar, servisler, SHA256) al")
    table.add_row("/diff", "Mevcut sistemi son baseline ile karsilastir (arka kapi / degisim tespiti)")
    table.add_row("/score", "Deterministik CIS Linux Guvenlik & Sikilastirma Puanini (0-100) hesapla")
    table.add_row("/check", "Bilgisayarin anlik guvenlik taramasini yap ve AI ile analiz et")
    table.add_row("/report", "Mevcut oturumdaki bulgulardan resmi Kurumsal PDF Raporu (.pdf) ve (.md) uret")
    table.add_row("@dosya", "Sohbet icinde herhangi bir dosyayi okutmak icin basina @ koyun (orn: @/etc/hosts)")
    table.add_row("/notes", "Vaka & Proje defterindeki kayitlari listele ve oku")
    table.add_row("/add", "Deftere yeni vaka, bulgu veya kisisel proje ekle")
    table.add_row("/edit", "Mevcut bir notun/projenin uzerine ekleme yap veya duzenle")
    table.add_row("/save <baslik>", "Son AI yanitini Vaka Defterine kaydet")
    table.add_row("/audit <dosya>", "Bir log veya kaynak kod dosyasini (otomatik Shodan IOC ile) analiz et")
    table.add_row("/backup", "Veritabaninin yedegini al")
    table.add_row("/restore", "Kayitli bir yedekten veritabanini geri yukle")
    table.add_row("/clear", "Ekrani ve sohbet hafizasini temizle")
    table.add_row("q / /exit", "Cikis")

    console.print()
    console.print(table)
    console.print()

