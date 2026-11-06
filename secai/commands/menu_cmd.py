import os
from pathlib import Path
import shutil
import sys
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

try:
    import readline
except ImportError:
    readline = None  # type: ignore

from secai import __version__
from secai.commands.note_cmd import note_list, note_show
from secai.config import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OLLAMA_MODEL,
    get_active_llm_info,
    get_data_dir,
    get_user_host_cwd,
    load_settings,
    save_settings,
)
from secai.core.baseline import (
    calculate_hardening_score,
    compare_with_baseline,
    format_baseline_diff_report,
    format_hardening_report,
    save_baseline,
)
from secai.core.database import (
    VALID_CATEGORIES,
    add_chat_message,
    add_note,
    backup_database,
    clear_chat_history,
    delete_note,
    export_note_markdown,
    get_chat_history,
    get_note,
    list_backups,
    restore_database,
    update_note,
)
from secai.core.executor import (
    collect_security_checkup,
    expand_file_references,
    extract_intel_queries,
    extract_note_actions,
    extract_saved_notes,
    extract_secops_actions,
    extract_shell_commands,
    extract_web_searches,
    prompt_and_execute,
    strip_internal_blocks,
)
from secai.core.intel import extract_iocs, format_intel_report
from secai.core.llm import OllamaConnectionError, check_ollama, stream_chat, stream_generate
from secai.core.skills import (
    create_custom_skill,
    get_active_skill,
    list_all_skills,
    set_active_skill,
)
from secai.core.voice import (
    VOICE_PROFILES,
    record_voice_input,
    speak_text,
    transcribe_voice,
)
from secai.core.web import format_web_results

console = Console()

SLASH_COMMANDS = [
    "/v",
    "/voice",
    "/talk",
    "/ses",
    "/tts",
    "/api",
    "/model",
    "/models",
    "/skills",
    "/skill",
    "/intel",
    "/baseline",
    "/diff",
    "/score",
    "/harden",
    "/notes",
    "/add",
    "/edit",
    "/save",
    "/report",
    "/audit",
    "/check",
    "/backup",
    "/restore",
    "/status",
    "/clear",
    "/help",
    "/exit",
]

PIXEL_LOGO_LINES = [
    ("  ▄▄████▄▄  ", "#00e5ff"),
    (" ██▀    ▀██ ", "#00b8ff"),
    (" ▀██▄▄      ", "#3b82f6"),
    ("    ▀▀██▄▄  ", "#6366f1"),
    (" ██▄    ▄██ ", "#8b5cf6"),
    ("  ▀▀████▀▀  ", "#a855f7"),
]


def _setup_readline() -> Path:
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


def _save_readline_history(history_file: Path) -> None:
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
        # Readline non-printing escape isaretleyicileri (\001 ve \002) sayesinde
        # ok tuslari ve backspace > isaretini asla bozmaz
        prompt_str = "\001\033[1;36m\002> \001\033[0m\002"
        return input(prompt_str).strip()

    return console.input("[bold cyan]> [/bold cyan]").strip()


def show_shortcuts() -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("cmd", style="bold cyan")
    table.add_column("desc", style="white")

    table.add_row("/v veya /talk", "Bas-Konus: Mikrofondan sesli emir ver, SecAI sesli ve yazili yanitlasin")
    table.add_row("/voice", "Canli Sesli Diyalog (Telsiz Modu): Karsilikli kesintisiz sesli sohbet")
    table.add_row("/ses veya /tts", "Ses ayarlarini yonet (Ahmet/Emel ses secimi, yazili sohbette ses ac/kapat)")
    table.add_row("/api", "Gemini API Token ekle veya degistir (veya dogrudan AIza... yapistir)")
    table.add_row("/model", "Aktif modeli degistir (Gemini 3 Flash / Pro / Yerel Ollama)")
    table.add_row("/skills", "SecOps yeteneklerini (recon, hardening, detection, ctf) sec veya yeni skill ekle")
    table.add_row("/intel <ip/log>", "Shodan InternetDB & GeoIP ile IP/CVE/Hash tehdit istihbarati sorgula")
    table.add_row("/baseline", "Sistemin temiz referans goruntusunu (portlar, servisler, SHA256) al")
    table.add_row("/diff", "Mevcut sistemi son baseline ile karsilastir (arka kapi / degisim tespiti)")
    table.add_row("/score", "Deterministik CIS Linux Guvenlik & Sikilastirma Puanini (0-100) hesapla")
    table.add_row("/check", "Bilgisayarin anlik guvenlik taramasini yap ve AI ile analiz et")
    table.add_row("/report", "Mevcut oturumdaki bulgulardan resmi Siber Guvenlik Raporu (.md) uret")
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


def configure_api_key(inline_key: str = "") -> None:
    if inline_key:
        key = inline_key.strip()
    else:
        console.print(
            "\n[dim]Google AI Studio (https://aistudio.google.com/apikey) uzerinden ucretsiz alabilirsiniz.[/dim]"
        )
        key = Prompt.ask("[bold cyan]Gemini API Key[/bold cyan]").strip()

    if not key:
        console.print("[yellow][!] Islem iptal edildi.[/yellow]\n")
        return

    save_settings(
        {
            "gemini_api_key": key,
            "provider": "gemini",
            "gemini_model": DEFAULT_GEMINI_MODEL,
        }
    )
    render_top_banner()
    console.print(
        f"[bold green][+][/bold green] Gemini API anahtari kaydedildi ve [bold cyan]{DEFAULT_GEMINI_MODEL}[/bold cyan] aktif edildi.\n"
    )


def switch_model_interactive() -> None:
    s = load_settings()
    has_key = bool(s.get("gemini_api_key", "").strip())
    active_info = get_active_llm_info()
    active_model_name = active_info["model"]
    active_provider = active_info["provider"]

    ollama_state = check_ollama()
    local_models = ollama_state.get("models", []) or [DEFAULT_OLLAMA_MODEL]

    console.print("\n[bold white]Model / Motor Secimi (Kurulu Modeller Otomatik Listelenir)[/bold white]")
    g1_mark = " [bold green][AKTIF][/bold green]" if active_provider == "gemini" and active_model_name == "gemini-3-flash-preview" else ""
    g2_mark = " [bold green][AKTIF][/bold green]" if active_provider == "gemini" and active_model_name == "gemini-3.1-pro-preview" else ""

    console.print(
        f"  [cyan]1[/cyan]  gemini-3-flash-preview   [dim](Google Gemini 3 Flash - Bulut / Cok Hizli {'[Hazir]' if has_key else '[Key Gerekli]'})[/dim]{g1_mark}\n"
        f"  [cyan]2[/cyan]  gemini-3.1-pro-preview   [dim](Google Gemini 3.1 Pro - Bulut / Derin Analiz {'[Hazir]' if has_key else '[Key Gerekli]'})[/dim]{g2_mark}"
    )
    choices = ["1", "2", "i", "0"]
    for idx, m_name in enumerate(local_models, start=3):
        key_str = str(idx)
        choices.append(key_str)
        l_mark = " [bold green][AKTIF][/bold green]" if active_provider == "ollama" and active_model_name == m_name else ""
        console.print(f"  [cyan]{key_str}[/cyan]  {m_name:<24} [dim](Local Ollama - %100 Yerel / GPU)[/dim]{l_mark}")

    console.print(
        "  [cyan]i[/cyan]  Yeni yerel model indir (orn: gemma3:4b, qwen2.5-coder:3b)\n"
        "  [cyan]0[/cyan]  Iptal\n"
    )

    choice = Prompt.ask("Secim", choices=choices, default="1" if has_key else "3")
    if choice == "0":
        return

    if choice == "i":
        new_model = Prompt.ask(
            "Indirilecek Ollama modeli",
            default="gemma3:4b",
        ).strip()
        if new_model:
            prompt_and_execute(f"ollama pull {new_model}")
            save_settings({"provider": "ollama", "ollama_model": new_model})
            render_top_banner()
            console.print(f"[bold green][+][/bold green] '{new_model}' indirildi ve aktif model yapildi.\n")
        return

    if choice in ("1", "2"):
        target_model = "gemini-3-flash-preview" if choice == "1" else "gemini-3.1-pro-preview"
        if not has_key:
            configure_api_key()
            save_settings({"provider": "gemini", "gemini_model": target_model})
        else:
            save_settings({"provider": "gemini", "gemini_model": target_model})
            render_top_banner()
            console.print(f"[bold green][+][/bold green] Aktif model: [cyan]{target_model}[/cyan]\n")
    else:
        picked_local = local_models[int(choice) - 3]
        save_settings({"provider": "ollama", "ollama_model": picked_local})
        render_top_banner()
        console.print(f"[bold green][+][/bold green] Aktif model: [cyan]{picked_local} (Local Ollama)[/cyan]\n")


def manage_skills_interactive(inline_arg: str = "") -> None:
    arg = inline_arg.strip().lower()
    if arg == "add" or arg == "ekle":
        console.print("\n[bold cyan][*] Yeni Skill Olustur[/bold cyan]")
        name = Prompt.ask("Skill adi (orn: web-pentest)").strip()
        if not name:
            return
        desc = Prompt.ask("Kisa aciklama").strip()
        instr = Prompt.ask("Modele verilecek uzmanlik talimati (prompt)").strip()
        if not instr:
            return
        path = create_custom_skill(name=name, description=desc, instructions=instr)
        set_active_skill(path.stem)
        render_top_banner()
        console.print(f"[bold green][+][/bold green] Yeni skill kaydedildi ve aktif edildi: [cyan]{path.stem}[/cyan]\n")
        return

    if arg and arg not in ("list", "liste"):
        try:
            chosen = set_active_skill(arg)
            render_top_banner()
            if chosen:
                console.print(f"[bold green][+][/bold green] Aktif skill: [cyan]{chosen['name']}[/cyan] ({chosen['description']})\n")
            else:
                console.print("[bold green][+][/bold green] Skill modu kapatildi (standart mod).\n")
            return
        except ValueError as err:
            console.print(f"[bold red][-][/bold red] {err}\n")

    skills = list_all_skills()
    active = get_active_skill()
    active_name = active["name"] if active else ""

    console.print("\n[bold white]SecAI Yetenekleri (Skills)[/bold white]")
    for idx, s in enumerate(skills, start=1):
        mark = " [bold green][AKTIF][/bold green]" if s["name"] == active_name else ""
        console.print(f"  [cyan]{idx}[/cyan]  [bold white]{s['name']}[/bold white] — [dim]{s['description']}[/dim]{mark}")
    console.print("  [cyan]y[/cyan]  Yeni ozel skill ekle (+)")
    console.print("  [cyan]0[/cyan]  Skill modunu kapat (Standart Mod)\n")

    choice = Prompt.ask("Secim (iptal icin Enter)", default="").strip().lower()
    if not choice:
        return
    if choice == "0":
        set_active_skill(None)
        render_top_banner()
        console.print("[bold green][+][/bold green] Skill modu kapatildi.\n")
    elif choice == "y":
        manage_skills_interactive("add")
    elif choice.isdigit() and 1 <= int(choice) <= len(skills):
        picked = skills[int(choice) - 1]
        set_active_skill(picked["name"])
        render_top_banner()
        console.print(f"[bold green][+][/bold green] Aktif skill: [cyan]{picked['name']}[/cyan]\n")


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


def _stream_markdown_from_generator(gen) -> str:
    """Generator'dan gelen metni canli, renklendirilmis Markdown paneli olarak ekrana akitir."""
    chunks: list[str] = []
    with console.status("[cyan][*] dusunuyor...[/cyan]", spinner="dots"):
        first_token = next(gen, None)

    if not first_token:
        return ""

    chunks.append(first_token)
    console.print()
    with Live(
        Padding(Markdown(strip_internal_blocks("".join(chunks)), code_theme="monokai"), (0, 1)),
        console=console,
        refresh_per_second=14,
    ) as live:
        for token in gen:
            chunks.append(token)
            visible_md = strip_internal_blocks("".join(chunks))
            live.update(Padding(Markdown(visible_md, code_theme="monokai"), (0, 1)))
    console.print()
    return "".join(chunks).strip()


def interactive_security_checkup(require_confirm: bool = True) -> None:
    telemetry = collect_security_checkup(require_confirm=require_confirm)
    if not telemetry:
        return

    score_data = calculate_hardening_score()
    score_md = format_hardening_report(score_data)
    console.print()
    console.print(Padding(Markdown(score_md, code_theme="monokai"), (0, 1)))
    console.print()

    llm_info = get_active_llm_info()
    console.print(f"[bold cyan][*][/bold cyan] model: {llm_info['model']} ile detayli sistem guvenlik analizi yapiliyor...")

    prompt = (
        "Asagida kullanicinin bilgisayarindan toplanan deterministik CIS Guvenlik Skoru tablosu ve anlik sistem guvenlik telemetrisi "
        "(dinlenen portlar, surecler, ag arayuzleri, komsu cihazlar, guvenlik duvari durumu, son hata/SSH loglari) yer almaktadir.\n"
        "Lutfen analizi yarida kesmeden eksiksiz olarak su basliklarla yaz:\n"
        "1. **Risk Seviyesi ve Nedenleri:** Sistemin neden bu risk seviyesinde (DUSUK/ORTA/YUKSEK) oldugunu somut bulgularla (hangi portlar dis aga acik, hangi sysctl parametreleri eksik) madde madde acikla.\n"
        "2. **Acik Portlar ve Servis Analizi (Markdown Tablosu):** `127.0.0.1` (yerel/guvenli) ile `0.0.0.0` / `*` (tum yerel aga acik) portlari ayirarak tablo halinde goster.\n"
        "3. **Uygulanabilir Sikilastirma (Hardening) Komutlari:** Tespit edilen WARN/FAIL maddelerini ve acik port risklerini kapatmak icin dogrudan uygulanabilir Arch Linux komutlarini ```bash bloklari icinde ver.\n\n"
        f"{score_md}\n\n{telemetry}"
    )

    try:
        gen = stream_generate(prompt=prompt)
        analysis = _stream_markdown_from_generator(gen)
    except OllamaConnectionError as err:
        console.print(f"\n[bold red][-][/bold red] {err}\n")
        return

    full_report = f"{score_md}\n\n---\n\n{analysis}" if analysis else score_md

    if full_report and Confirm.ask("Bu sistem guvenlik raporunu Vaka Defterine kaydet?", default=True):
        save_title = Prompt.ask("Baslik", default="Sistem Guvenlik Check-up Raporu")
        note_id = add_note(
            title=save_title,
            content=full_report,
            category="secops",
            tags="checkup,hardening",
        )
        console.print(f"[bold green][+][/bold green] Kaydedildi (#{note_id})\n")


def interactive_intel(inline_target: str = "") -> None:
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


def interactive_baseline(label: str = "default") -> None:
    clean_label = label.strip() or "default"
    console.print(f"\n[bold cyan][*][/bold cyan] Sistem referans goruntusu (baseline: '{clean_label}') aliniyor...")
    record = save_baseline(label=clean_label)
    snap = record["snapshot"]
    console.print(
        f"[bold green][+][/bold green] Baseline #{record['id']} kaydedildi ({record['created_at']})\n"
        f"    Dinlenen Port: [cyan]{len(snap['ports'])}[/cyan] | "
        f"Aktif Servis: [cyan]{len(snap['services'])}[/cyan] | "
        f"SHA256 Dosya: [cyan]{len(snap['file_hashes'])}[/cyan]\n"
    )


def interactive_diff(analyze_with_ai: bool = False) -> None:
    console.print("\n[bold cyan][*][/bold cyan] Mevcut sistem durumu son baseline ile karsilastiriliyor...")
    diff = compare_with_baseline()
    report_md = format_baseline_diff_report(diff)
    console.print()
    console.print(Padding(Markdown(report_md, code_theme="monokai"), (0, 1)))
    console.print()

    if analyze_with_ai and diff.get("has_baseline") and diff.get("has_drift"):
        prompt = (
            "Asagida sistemin temiz baseline kaydi ile su anki durumu arasindaki farklar (drift/anomali) yer almaktadir.\n"
            "Yeni acilan portlari, servisleri veya degisen dosyalari guvenlik acisindan degerlendir:\n\n"
            f"{report_md}"
        )
        try:
            gen = stream_generate(prompt=prompt)
            _stream_markdown_from_generator(gen)
        except OllamaConnectionError as err:
            console.print(f"\n[bold red][-][/bold red] {err}\n")


def interactive_hardening_score(analyze_with_ai: bool = False) -> None:
    console.print("\n[bold cyan][*][/bold cyan] Deterministik CIS Linux Guvenlik & Sikilastirma denetimi yapiliyor...")
    res = calculate_hardening_score()
    report_md = format_hardening_report(res)
    console.print()
    console.print(Padding(Markdown(report_md, code_theme="monokai"), (0, 1)))
    console.print()

    if analyze_with_ai:
        prompt = (
            "Asagida kullanicinin sisteminden alinan deterministik CIS Guvenlik ve Sikilastirma (Hardening) tablosu yer almaktadir.\n"
            "Basarisiz (FAIL/WARN) olan maddeleri nasil kapatabilecegini kisa ve uygulanabilir komutlarla acikla:\n\n"
            f"{report_md}"
        )
        try:
            gen = stream_generate(prompt=prompt)
            _stream_markdown_from_generator(gen)
        except OllamaConnectionError as err:
            console.print(f"\n[bold red][-][/bold red] {err}\n")


def interactive_audit(inline_target: str = "") -> None:
    source = inline_target.strip()
    if not source:
        source = Prompt.ask("\nAnaliz edilecek dosya yolu veya log metni").strip()
    if not source:
        return

    potential_file = Path(source).expanduser()
    if potential_file.exists() and potential_file.is_file():
        raw_input = potential_file.read_text(encoding="utf-8", errors="replace")
        label = potential_file.name
    else:
        raw_input = source
        label = "manuel-giris"

    llm_info = get_active_llm_info()
    console.print(f"\n[bold cyan][*][/bold cyan] kaynak: {label} | model: {llm_info['model']}")

    iocs = extract_iocs(raw_input)
    intel_block = ""
    if iocs["ips"] or iocs["cves"] or iocs["sha256"]:
        console.print(
            f"[bold cyan][*][/bold cyan] IOC tespit edildi ({len(iocs['ips'])} dis IP, {len(iocs['cves'])} CVE) — Shodan InternetDB sorgulaniyor..."
        )
        intel_md = format_intel_report(raw_input, max_ips=6)
        console.print()
        console.print(Padding(Markdown(intel_md, code_theme="monokai"), (0, 1)))
        intel_block = f"\n\n[OTOMATIK SHODAN & IOC TEHDIT ISTIHBARATI]:\n{intel_md}"

    prompt = (
        "Asagidaki log, komut ciktisi veya kod blogunu guvenlik acisindan analiz et:\n\n"
        f"```\n{raw_input}\n```{intel_block}"
    )
    try:
        gen = stream_generate(prompt=prompt)
        analysis = _stream_markdown_from_generator(gen)
    except OllamaConnectionError as err:
        console.print(f"\n[bold red][-][/bold red] {err}\n")
        return

    if analysis and Confirm.ask("Sonucu deftere kaydet?", default=True):
        save_title = Prompt.ask("Baslik", default=f"audit-{label}")
        note_id = add_note(
            title=save_title,
            content=analysis,
            category="secops",
            tags="audit",
        )
        console.print(f"[bold green][+][/bold green] Kaydedildi (#{note_id})\n")


def generate_session_report(session: str = "default") -> None:
    history = get_chat_history(session_id=session, limit=40)
    if not history:
        console.print("\n[yellow][!][/yellow] Rapor olusturmak icin henuz yeterli oturum verisi yok.\n")
        return

    console.print("\n[bold cyan][*][/bold cyan] Oturum verilerinden resmi SecOps raporu hazirlaniyor...")
    transcript = "\n\n".join(f"[{m['role'].upper()}]:\n{m['content']}" for m in history)
    prompt = (
        "Asagidaki SecOps oturum gecmisini ve bulgularini kullanarak profesyonel, resmi bir "
        "**Siber Guvenlik Degerlendirme ve Vaka Raporu** hazirla.\n"
        "Raporda su bolumler yer alsin:\n"
        "1. Yonetici Ozeti\n"
        "2. Incelenen Sistem ve Kapsam\n"
        "3. Tespit Edilen Bulgular & Acik Portlar (Tablo halinde)\n"
        "4. Risk Degerlendirmesi\n"
        "5. Sikilastirma (Hardening) ve Cozum Onerileri\n\n"
        f"OTURUM VERILERI:\n{transcript[:16000]}"
    )

    try:
        gen = stream_generate(prompt=prompt)
        report_md = _stream_markdown_from_generator(gen)
    except OllamaConnectionError as err:
        console.print(f"\n[bold red][-][/bold red] {err}\n")
        return

    if report_md:
        nid = add_note(
            title="SecOps Degerlendirme Raporu",
            content=report_md,
            category="secops",
            tags="report,secops",
        )
        md_path = export_note_markdown(nid)
        console.print(
            f"[bold green][+][/bold green] Rapor Vaka Defterine kaydedildi (#{nid}) ve Markdown olarak disa aktarildi:\n"
            f"    [cyan]{md_path}[/cyan]\n"
        )


def _stream_reply(messages: list[dict]) -> str:
    gen = stream_chat(messages=messages)
    return _stream_markdown_from_generator(gen)


def manage_voice_settings(inline_arg: str = "") -> None:
    s = load_settings()
    arg = inline_arg.strip().lower()
    if arg in ("on", "ac", "aç", "aktif", "1"):
        save_settings({"tts_enabled": True})
        render_top_banner()
        console.print("[bold green][+][/bold green] Sesli yanit modu acildi (Tum yanitlar seslendirilecek).\n")
        return
    if arg in ("off", "kapat", "pasif", "0"):
        save_settings({"tts_enabled": False})
        render_top_banner()
        console.print("[bold green][+][/bold green] Sesli yanit modu kapatildi.\n")
        return
    if arg in ("ahmet", "erkek"):
        save_settings({"tts_voice": "tr-TR-AhmetNeural"})
        console.print("[bold green][+][/bold green] Asistan sesi: [cyan]Ahmet (Erkek)[/cyan]\n")
        return
    if arg in ("emel", "kadin", "kadın"):
        save_settings({"tts_voice": "tr-TR-EmelNeural"})
        console.print("[bold green][+][/bold green] Asistan sesi: [cyan]Emel (Kadin)[/cyan]\n")
        return

    tts_on = bool(s.get("tts_enabled", False))
    cur_voice = s.get("tts_voice", "tr-TR-AhmetNeural")

    console.print("\n[bold white]SecAI Ses & Konusma Ayarlari[/bold white]")
    status_str = "[bold green]ACIK[/bold green]" if tts_on else "[dim]KAPALI[/dim]"
    console.print(f"  [cyan]1[/cyan]  Yazili Sohbette Sesli Yanit (Su an: {status_str})")
    for idx, (v_id, v_desc) in enumerate(VOICE_PROFILES.items(), start=2):
        mark = " [bold green][AKTIF][/bold green]" if cur_voice == v_id else ""
        console.print(f"  [cyan]{idx}[/cyan]  {v_desc}{mark}")
    console.print("  [cyan]4[/cyan]  Canli Sesli Diyalog (Telsiz Modu — /voice) Baslat")
    console.print("  [cyan]0[/cyan]  Iptal\n")

    choice = Prompt.ask("Secim", choices=["1", "2", "3", "4", "0"], default="0")
    if choice == "1":
        save_settings({"tts_enabled": not tts_on})
        render_top_banner()
        new_lbl = "ACILDI" if not tts_on else "KAPATILDI"
        console.print(f"[bold green][+][/bold green] Sesli yanit modu {new_lbl}.\n")
    elif choice == "2":
        save_settings({"tts_voice": "tr-TR-AhmetNeural"})
        console.print("[bold green][+][/bold green] Asistan sesi: [cyan]Ahmet (Erkek)[/cyan]\n")
    elif choice == "3":
        save_settings({"tts_voice": "tr-TR-EmelNeural"})
        console.print("[bold green][+][/bold green] Asistan sesi: [cyan]Emel (Kadin)[/cyan]\n")
    elif choice == "4":
        interactive_voice_loop(session="default")


def _run_agent_turn(user_input: str, session: str = "default", force_speak: bool = False) -> str:
    """
    Kullanici mesajini alir, AI yanitini akitir, çok adimli ajan dongusunu (notlar, web arama,
    Shodan intel, SecOps motorlari ve bash komutlari) calistirir ve seslendirme aktifse konusur.
    """
    should_speak = force_speak or bool(load_settings().get("tts_enabled", False))
    expanded_input = expand_file_references(user_input)
    add_chat_message(session_id=session, role="user", content=expanded_input)
    current_messages = get_chat_history(session_id=session, limit=40)

    try:
        last_assistant_reply = _stream_reply(current_messages)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow][!] Durduruldu.[/yellow]\n")
        return ""
    except OllamaConnectionError as err:
        console.print(f"\n[bold red][-][/bold red] {err}\n")
        return ""

    final_reply = last_assistant_reply
    step_count = 0
    while last_assistant_reply and step_count < 3:
        step_count += 1
        final_reply = last_assistant_reply
        clean_reply_for_history = strip_internal_blocks(last_assistant_reply)
        add_chat_message(
            session_id=session,
            role="assistant",
            content=clean_reply_for_history or last_assistant_reply,
        )

        # Dogal dille not kaydetme istegi varsa otomatik veritabanina kaydet
        auto_notes = extract_saved_notes(last_assistant_reply)
        for an in auto_notes:
            nid = add_note(
                title=an["title"],
                content=an["content"],
                category=an["category"],
                tags=an["tags"],
            )
            console.print(
                f"[bold green][+][/bold green] Deftere kaydedildi (#{nid} — {an['title']} [{an['category']}])\n"
            )

        # Dogal dille not guncelleme / silme / markdown disa aktarma
        for act in extract_note_actions(last_assistant_reply):
            nid = int(act["id"])
            if act["action"] == "update-note" and act["content"]:
                if update_note(note_id=nid, content=act["content"], append=True):
                    console.print(f"[bold green][+][/bold green] Not #{nid} guncellendi.\n")
            elif act["action"] == "delete-note":
                if delete_note(nid):
                    console.print(f"[bold green][+][/bold green] Not #{nid} silindi.\n")
            elif act["action"] == "export-note":
                try:
                    md_path = export_note_markdown(nid)
                    console.print(f"[bold green][+][/bold green] Markdown rapor hazir: {md_path}\n")
                except ValueError:
                    pass

        # Otomatik Canli Web Aramasi
        web_queries = extract_web_searches(last_assistant_reply)
        if web_queries:
            wq = web_queries[0]
            console.print(f"[bold cyan][*][/bold cyan] Web'de araniyor: [white]{wq}[/white]")
            web_report = format_web_results(wq, max_results=6)
            add_chat_message(
                session_id=session,
                role="user",
                content=(
                    f"{web_report}\n\n"
                    "Yukaridaki canli web arama sonuclarini kullanarak kullanicinin sorusunu detayli ve kaynak linkleriyle yanitla (tekrar web-search blogu yazma)."
                ),
            )
            try:
                updated_messages = get_chat_history(session_id=session, limit=40)
                last_assistant_reply = _stream_reply(updated_messages)
                continue
            except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                break

        # Otomatik Shodan InternetDB & GeoIP Tehdit Istihbarati Sorgusu
        intel_queries = extract_intel_queries(last_assistant_reply)
        if intel_queries:
            iq = "\n".join(intel_queries)
            console.print("[bold cyan][*][/bold cyan] Shodan InternetDB & GeoIP tehdit istihbarati sorgulaniyor...")
            intel_report = format_intel_report(iq, max_ips=8)
            add_chat_message(
                session_id=session,
                role="user",
                content=(
                    f"{intel_report}\n\n"
                    "Yukaridaki gercek Shodan InternetDB ve GeoIP istihbarat sonuclarini kullanarak kullaniciya detayli bir tehdit analizi sun (tekrar intel-lookup blogu yazma)."
                ),
            )
            try:
                updated_messages = get_chat_history(session_id=session, limit=40)
                last_assistant_reply = _stream_reply(updated_messages)
                continue
            except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                break

        # Otomatik SecOps Motorlari (baseline, diff, score)
        secops_acts = extract_secops_actions(last_assistant_reply)
        if secops_acts:
            act = secops_acts[0]
            if act == "baseline":
                interactive_baseline("default")
                break
            elif act == "diff":
                diff_data = compare_with_baseline()
                diff_md = format_baseline_diff_report(diff_data)
                console.print(Padding(Markdown(diff_md, code_theme="monokai"), (0, 1)))
                add_chat_message(
                    session_id=session,
                    role="user",
                    content=(
                        f"{diff_md}\n\n"
                        "Yukaridaki sistem baseline karsilastirma (drift) raporunu degerlendir ve varsa anomalileri acikla (tekrar secops-action blogu yazma)."
                    ),
                )
            elif act in ("score", "harden"):
                score_data = calculate_hardening_score()
                score_md = format_hardening_report(score_data)
                console.print(Padding(Markdown(score_md, code_theme="monokai"), (0, 1)))
                add_chat_message(
                    session_id=session,
                    role="user",
                    content=(
                        f"{score_md}\n\n"
                        "Yukaridaki deterministik CIS guvenlik skoru tablosundaki eksikleri (FAIL/WARN) nasil kapatabilecegimizi ozetle (tekrar secops-action blogu yazma)."
                    ),
                )
            try:
                updated_messages = get_chat_history(session_id=session, limit=40)
                last_assistant_reply = _stream_reply(updated_messages)
                continue
            except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                break

        commands = extract_shell_commands(last_assistant_reply)
        if not commands:
            if should_speak and last_assistant_reply:
                speak_text(last_assistant_reply)
            break

        if should_speak and last_assistant_reply:
            speak_text(last_assistant_reply)

        next_reply = ""
        for cmd in commands:
            cmd_output = prompt_and_execute(cmd)
            if cmd_output is not None:
                trimmed_out = cmd_output[:16000]
                add_chat_message(
                    session_id=session,
                    role="user",
                    content=(
                        f"[Komut Ciktisi ('{cmd}')]:\n{trimmed_out}\n\n"
                        "Yukaridaki komut ciktisini analiz et. Eger komut hata verdiyse veya islemi tamamlamak icin 2. bir komut gerekiyorsa yeni ```bash blogu ver; islem tamamlandiysa sonucu tablo/maddelerle ozetle."
                    ),
                )
                try:
                    updated_messages = get_chat_history(session_id=session, limit=40)
                    next_reply = _stream_reply(updated_messages)
                except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                    next_reply = ""
        last_assistant_reply = next_reply

    return final_reply


def interactive_push_to_talk(session: str = "default") -> str:
    """Tek seferlik Bas-Konus (mikrofonu dinler, metne cevirir, yanitlar ve sesli konusur)."""
    wav_path = record_voice_input()
    if not wav_path:
        return ""
    transcript = transcribe_voice(wav_path)
    if not transcript:
        console.print("[yellow][!] Konusma anlasilamadi, tekrar deneyin.[/yellow]\n")
        return ""

    console.print(f"\n[bold cyan][Sen (Sesli)]:[/bold cyan] [bold white]{transcript}[/bold white]")
    return _run_agent_turn(transcript, session=session, force_speak=True)


def interactive_voice_loop(session: str = "default") -> None:
    """Karsilikli kesintisiz Canli Sesli Diyalog (Telsiz) Modu."""
    console.print(
        "\n[bold cyan][*] CANLI SESLI DIYALOG (TELSIZ) MODU AKTIF[/bold cyan]\n"
        "[dim]Konusup ENTER'a basin, SecAI hem ekranda gosterecek hem de sesli yanitlayacaktir. Cikmak icin 'q' yazin.[/dim]"
    )
    while True:
        reply = interactive_push_to_talk(session=session)
        try:
            cont = console.input(
                "\n[bold cyan][Sesli Diyalog][/bold cyan] Yeni soz icin [bold white]ENTER[/bold white]'a basin [dim](Cikis icin 'q')[/dim]: "
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim][*] Sesli diyalog modundan cikildi.[/dim]\n")
            break
        if cont in ("q", "quit", "exit", "cikis", "çıkış"):
            console.print("[dim][*] Sesli diyalog modundan cikildi.[/dim]\n")
            break
    let_unused = reply
    _ = let_unused


def run_interactive_menu(status_callback=None) -> None:
    """Antigravity CLI tarzı tam ekran temiz çalışma alanı."""
    session = "default"
    last_assistant_reply = ""
    history_file = _setup_readline()
    render_top_banner()

    try:
        while True:
            try:
                user_input = render_prompt_frame_and_input()
            except (KeyboardInterrupt, EOFError):
                console.print()
                break

            if not user_input:
                continue

            low = user_input.lower().strip()

            # Kullanici dogrudan AIza... veya AQ.... ile baslayan Gemini API anahtarini yapistirdiysa otomatik tani
            if (user_input.startswith("AIza") or user_input.startswith("AQ.")) and len(user_input.split()) == 1 and len(user_input) >= 30:
                configure_api_key(inline_key=user_input)
                continue

            if low in ("q", "quit", "exit", "/exit", "/q", "cikis", "çıkış"):
                break

            if low in ("?", "/help", "help", "yardim", "yardım", "menu", "menü"):
                show_shortcuts()
                continue

            if low in ("/clear", "clear", "temizle"):
                clear_chat_history(session_id=session)
                render_top_banner()
                continue

            if low in ("/v", "/talk", "talk", "konus", "konuş", "dinle"):
                reply = interactive_push_to_talk(session=session)
                if reply:
                    last_assistant_reply = reply
                continue

            if low in ("/voice", "voice", "telsiz", "sesli mod", "sesli sohbet"):
                interactive_voice_loop(session=session)
                continue

            if low in ("/ses", "/tts", "ses", "tts") or low.startswith("/ses ") or low.startswith("/tts "):
                parts = user_input.split(maxsplit=1)
                arg = parts[1] if len(parts) > 1 else ""
                manage_voice_settings(inline_arg=arg)
                continue

            if low in ("api", "key", "/api", "/key") or low.startswith("/api ") or low.startswith("/key ") or low.startswith("api "):
                parts = user_input.split(maxsplit=1)
                inline_key = parts[1] if len(parts) > 1 else ""
                configure_api_key(inline_key=inline_key)
                continue

            if low in ("/model", "/models", "model", "models", "motor"):
                switch_model_interactive()
                continue

            if low in ("/skills", "/skill", "skills", "skill", "yetenek") or low.startswith("/skill ") or low.startswith("skill "):
                parts = user_input.split(maxsplit=1)
                arg = parts[1] if len(parts) > 1 else ""
                manage_skills_interactive(inline_arg=arg)
                continue

            if low in ("/check",):
                interactive_security_checkup(require_confirm=True)
                continue

            if low.startswith("/intel") or low.startswith("intel "):
                parts = user_input.split(maxsplit=1)
                target = parts[1] if len(parts) > 1 else ""
                interactive_intel(inline_target=target)
                continue

            if low.startswith("/baseline") or low == "baseline":
                parts = user_input.split(maxsplit=1)
                lbl = parts[1] if len(parts) > 1 else "default"
                interactive_baseline(label=lbl)
                continue

            if low in ("/diff", "diff"):
                interactive_diff(analyze_with_ai=True)
                continue

            if low in ("/score", "/harden", "score", "harden"):
                interactive_hardening_score(analyze_with_ai=False)
                continue

            if low in ("/notes", "/list", "/defter"):
                interactive_list_and_read()
                continue

            if low in ("/add",):
                interactive_add_note()
                continue

            if low in ("/edit",):
                interactive_edit_note()
                continue

            if low in ("/backup",):
                b_path = backup_database()
                console.print(f"\n[bold green][+][/bold green] Yedek alindi: {b_path}\n")
                continue

            if low in ("/restore",):
                interactive_restore_backup()
                continue

            if low in ("/status", "durum") and status_callback:
                console.print()
                status_callback()
                console.print()
                continue

            if low in ("/report", "rapor", "rapor cikar", "rapor oluştur"):
                generate_session_report(session=session)
                continue

            if low.startswith("/audit"):
                parts = user_input.split(maxsplit=1)
                target = parts[1] if len(parts) > 1 else ""
                interactive_audit(inline_target=target)
                continue

            if low.startswith("/save"):
                title = user_input[5:].strip() or f"not-{session}"
                if not last_assistant_reply:
                    console.print("\n[yellow][!][/yellow] Henuz kaydedilecek bir yanit yok.\n")
                    continue
                note_id = add_note(
                    title=title,
                    content=last_assistant_reply,
                    category="secops",
                    tags="chat",
                )
                console.print(f"\n[bold green][+][/bold green] Deftere kaydedildi (#{note_id} - {title})\n")
                continue

            last_assistant_reply = _run_agent_turn(user_input, session=session, force_speak=False)
    finally:
        _save_readline_history(history_file)
