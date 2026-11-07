"""SecOps guvenlik checkup, baseline drift, audit ve CIS skor komut isleyicileri."""

from pathlib import Path
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.prompt import Confirm, Prompt

from secai.config import get_active_llm_info
from secai.core.baseline import (
    calculate_hardening_score,
    compare_with_baseline,
    format_baseline_diff_report,
    format_hardening_report,
    save_baseline,
)
from secai.core.database import add_note, export_note_markdown, get_chat_history
from secai.core.executor import collect_security_checkup, strip_internal_blocks
from secai.core.intel import extract_iocs, format_intel_report
from secai.core.llm import OllamaConnectionError, stream_generate

console = Console()


def stream_markdown_from_generator(gen) -> str:
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
        analysis = stream_markdown_from_generator(gen)
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
            stream_markdown_from_generator(gen)
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
            stream_markdown_from_generator(gen)
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
        analysis = stream_markdown_from_generator(gen)
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
        report_md = stream_markdown_from_generator(gen)
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
        from secai.core.pdf_report import generate_note_pdf_report
        try:
            pdf_path = generate_note_pdf_report(nid)
            console.print(
                f"[bold green][+][/bold green] Rapor Vaka Defterine kaydedildi (#{nid}).\n"
                f"    • [bold cyan]Kurumsal PDF Raporu:[/bold cyan] [bold green]{pdf_path}[/bold green]\n"
                f"    • [dim]Markdown:[/dim] [cyan]{md_path}[/cyan]\n"
            )
            import shutil, subprocess
            if shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", str(pdf_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            console.print(
                f"[bold green][+][/bold green] Rapor Vaka Defterine kaydedildi (#{nid}) ve Markdown olarak disa aktarildi:\n"
                f"    [cyan]{md_path}[/cyan] (PDF Hatasi: {e})\n"
            )
