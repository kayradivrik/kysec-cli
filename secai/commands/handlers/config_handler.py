"""Model, API anahtarlari, kullanici profili, yetenekler ve gorsel yonetimi."""

import shutil
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from secai.commands.ui import render_top_banner
from secai.config import (
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    DEEPSEEK_MODELS,
    GROQ_MODELS,
    OPENROUTER_MODELS,
    get_active_llm_info,
    load_settings,
    save_settings,
)
from secai.core.database import get_user_profile, set_user_profile
from secai.core.executor import prompt_and_execute
from secai.core.image import generate_image
from secai.core.llm import check_ollama
from secai.core.skills import (
    create_custom_skill,
    get_active_skill,
    list_all_skills,
    set_active_skill,
)

console = Console()


def configure_api_key(inline_key: str = "") -> None:
    raw = inline_key.strip()
    parts = raw.split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    val = parts[1].strip() if len(parts) > 1 else ""

    if sub in ("vt", "virustotal") and val:
        save_settings({"virustotal_api_key": val})
        console.print("\n[bold green][+][/bold green] VirusTotal API anahtarı kaydedildi.\n")
        return

    if sub in ("abuse", "abuseipdb") and val:
        save_settings({"abuseipdb_api_key": val})
        console.print("\n[bold green][+][/bold green] AbuseIPDB API anahtarı kaydedildi.\n")
        return

    if sub in ("groq", "gsk") and val:
        save_settings({"groq_api_key": val, "provider": "groq", "groq_model": DEFAULT_GROQ_MODEL})
        render_top_banner()
        console.print(f"\n[bold green][+][/bold green] Groq API anahtarı kaydedildi ve [cyan]{DEFAULT_GROQ_MODEL}[/cyan] (500 tok/sn) aktif edildi!\n")
        return

    if sub in ("deepseek", "r1") and val:
        save_settings({"deepseek_api_key": val, "provider": "deepseek", "deepseek_model": DEFAULT_DEEPSEEK_MODEL})
        render_top_banner()
        console.print(f"\n[bold green][+][/bold green] DeepSeek API anahtarı kaydedildi ve [cyan]{DEFAULT_DEEPSEEK_MODEL} (R1 Akıl Yürütme)[/cyan] aktif edildi!\n")
        return

    if sub in ("openrouter",) and val:
        save_settings({"openrouter_api_key": val, "provider": "openrouter", "openrouter_model": DEFAULT_OPENROUTER_MODEL})
        render_top_banner()
        console.print(f"\n[bold green][+][/bold green] OpenRouter API anahtarı kaydedildi ve [cyan]{DEFAULT_OPENROUTER_MODEL}[/cyan] aktif edildi!\n")
        return

    # Doğrudan anahtar yapıştırıldıysa otomatik tanı:
    if raw.startswith("gsk_"):
        save_settings({"groq_api_key": raw, "provider": "groq", "groq_model": DEFAULT_GROQ_MODEL})
        render_top_banner()
        console.print(f"\n[bold green][+][/bold green] Groq API anahtarı algılandı ve [cyan]{DEFAULT_GROQ_MODEL}[/cyan] (500 tok/sn) aktif edildi!\n")
        return

    if raw.startswith("sk-or-"):
        save_settings({"openrouter_api_key": raw, "provider": "openrouter", "openrouter_model": DEFAULT_OPENROUTER_MODEL})
        render_top_banner()
        console.print(f"\n[bold green][+][/bold green] OpenRouter API anahtarı algılandı ve [cyan]{DEFAULT_OPENROUTER_MODEL}[/cyan] aktif edildi!\n")
        return

    if raw.startswith("AIza"):
        save_settings({"gemini_api_key": raw, "provider": "gemini", "gemini_model": DEFAULT_GEMINI_MODEL})
        render_top_banner()
        console.print(f"\n[bold green][+][/bold green] Gemini API anahtarı kaydedildi ve [cyan]{DEFAULT_GEMINI_MODEL}[/cyan] aktif edildi.\n")
        return

    if raw.startswith("sk-"):
        save_settings({"deepseek_api_key": raw, "provider": "deepseek", "deepseek_model": DEFAULT_DEEPSEEK_MODEL})
        render_top_banner()
        console.print(f"\n[bold green][+][/bold green] DeepSeek API anahtarı algılandı ve [cyan]{DEFAULT_DEEPSEEK_MODEL} (R1 Akıl Yürütme)[/cyan] aktif edildi!\n")
        return

    console.print(
        Panel(
            "[bold white]SecAI Evrensel API & Model Sağlayıcıları[/bold white]\n\n"
            "  [cyan]1[/cyan]  ⚡ Groq API Key       [dim](Ücretsiz, 500 tok/sn GPT-OSS 120B & Qwen 27B - console.groq.com)[/dim]\n"
            "  [cyan]2[/cyan]  🧠 DeepSeek API Key   [dim](DeepSeek R1 Derin Düşünce & V3 - platform.deepseek.com)[/dim]\n"
            "  [cyan]3[/cyan]  🌐 Google Gemini Key  [dim](Gemini 3 Flash & Pro - aistudio.google.com)[/dim]\n"
            "  [cyan]4[/cyan]  🧭 OpenRouter Key     [dim](Tüm Ücretsiz Modeller :free - openrouter.ai)[/dim]\n"
            "  [cyan]5[/cyan]  🛡️ VirusTotal API Key [dim](70+ Antivirüs ile Hash & IP Tarama - virustotal.com)[/dim]\n"
            "  [cyan]6[/cyan]  ⚡ AbuseIPDB API Key  [dim](IP İtibar & Saldırı Raporlama - abuseipdb.com)[/dim]\n"
            "  [cyan]0[/cyan]  İptal\n\n"
            "[dim]İpucu: Anahtarı doğrudan '/api gsk_...' veya '/api AIza...' şeklinde yapıştırabilirsiniz.[/dim]",
            title="🔑 API Anahtarları",
            border_style="cyan",
        )
    )
    ch = Prompt.ask("Seçim", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")
    if ch == "0":
        return
    if ch == "1":
        k = Prompt.ask("[bold cyan]Groq API Key (gsk_...)[/bold cyan]").strip()
        if k:
            save_settings({"groq_api_key": k, "provider": "groq", "groq_model": DEFAULT_GROQ_MODEL})
            render_top_banner()
            console.print(f"\n[bold green][+][/bold green] Groq aktif edildi: [cyan]{DEFAULT_GROQ_MODEL}[/cyan]\n")
    elif ch == "2":
        k = Prompt.ask("[bold cyan]DeepSeek API Key (sk-...)[/bold cyan]").strip()
        if k:
            save_settings({"deepseek_api_key": k, "provider": "deepseek", "deepseek_model": DEFAULT_DEEPSEEK_MODEL})
            render_top_banner()
            console.print(f"\n[bold green][+][/bold green] DeepSeek R1 aktif edildi: [cyan]{DEFAULT_DEEPSEEK_MODEL}[/cyan]\n")
    elif ch == "3":
        k = Prompt.ask("[bold cyan]Gemini API Key[/bold cyan]").strip()
        if k:
            save_settings({"gemini_api_key": k, "provider": "gemini", "gemini_model": DEFAULT_GEMINI_MODEL})
            render_top_banner()
            console.print(f"\n[bold green][+][/bold green] Gemini aktif edildi: [cyan]{DEFAULT_GEMINI_MODEL}[/cyan]\n")
    elif ch == "4":
        k = Prompt.ask("[bold cyan]OpenRouter API Key (sk-or-...)[/bold cyan]").strip()
        if k:
            save_settings({"openrouter_api_key": k, "provider": "openrouter", "openrouter_model": DEFAULT_OPENROUTER_MODEL})
            render_top_banner()
            console.print(f"\n[bold green][+][/bold green] OpenRouter aktif edildi: [cyan]{DEFAULT_OPENROUTER_MODEL}[/cyan]\n")
    elif ch == "5":
        k = Prompt.ask("[bold cyan]VirusTotal API Key[/bold cyan]").strip()
        if k:
            save_settings({"virustotal_api_key": k})
            console.print("\n[bold green][+][/bold green] VirusTotal API anahtarı kaydedildi.\n")
    elif ch == "6":
        k = Prompt.ask("[bold cyan]AbuseIPDB API Key[/bold cyan]").strip()
        if k:
            save_settings({"abuseipdb_api_key": k})
            console.print("\n[bold green][+][/bold green] AbuseIPDB API anahtarı kaydedildi.\n")


def switch_model_interactive() -> None:
    s = load_settings()
    active_info = get_active_llm_info()
    active_model_name = active_info["model"]
    active_provider = active_info["provider"]

    has_gemini = bool(s.get("gemini_api_key", "").strip())
    has_groq = bool(s.get("groq_api_key", "").strip())
    has_deepseek = bool(s.get("deepseek_api_key", "").strip())
    has_openrouter = bool(s.get("openrouter_api_key", "").strip())

    ollama_state = check_ollama()
    local_models = ollama_state.get("models", []) or [DEFAULT_OLLAMA_MODEL]

    console.print("\n[bold white]🧠 Model & Yapay Zeka Motoru Seçimi[/bold white]\n")

    # Group 1: Local RTX 4050
    console.print("[bold green]── 🖥️ YEREL GPU (RTX 4050 / Ollama - Çevrimdışı & Kotasız) ──[/bold green]")
    model_map = {}
    idx = 1
    for m in local_models:
        cur = " [bold green][AKTİF][/bold green]" if active_provider == "ollama" and active_model_name == m else ""
        console.print(f"  [cyan]{idx:<2}[/cyan] {m:<30} [dim](%100 Yerel / 40+ tok/sn)[/dim]{cur}")
        model_map[str(idx)] = ("ollama", m)
        idx += 1

    # Group 2: Groq Ultra Fast
    console.print(f"\n[bold cyan]── ⚡ GROQ LPU (Ultra Hızlı - 500 tok/sn {'[Key Var]' if has_groq else '[Key Gerekli]'}) ──[/bold cyan]")
    for m in GROQ_MODELS:
        cur = " [bold green][AKTİF][/bold green]" if active_provider == "groq" and active_model_name == m else ""
        console.print(f"  [cyan]{idx:<2}[/cyan] {m:<30} [dim](Groq / LPU Cloud)[/dim]{cur}")
        model_map[str(idx)] = ("groq", m)
        idx += 1

    # Group 3: DeepSeek R1 Reasoning
    console.print(f"\n[bold magenta]── 🧠 DEEPSEEK REASONING (Derin Akıl Yürütme & V3 {'[Key Var]' if has_deepseek else '[Key Gerekli]'}) ──[/bold magenta]")
    for m in DEEPSEEK_MODELS:
        cur = " [bold green][AKTİF][/bold green]" if active_provider == "deepseek" and active_model_name == m else ""
        label = "R1 Akıl Yürütme (Thinking Chain)" if "reasoner" in m else "V3 Genel & Kod"
        console.print(f"  [cyan]{idx:<2}[/cyan] {m:<30} [dim]({label})[/dim]{cur}")
        model_map[str(idx)] = ("deepseek", m)
        idx += 1

    # Group 4: Google Gemini
    console.print(f"\n[bold blue]── 🌐 GOOGLE GEMINI (Bulut LLM {'[Key Var]' if has_gemini else '[Key Gerekli]'}) ──[/bold blue]")
    for m in ("gemini-3-flash-preview", "gemini-3.1-pro-preview"):
        cur = " [bold green][AKTİF][/bold green]" if active_provider == "gemini" and active_model_name == m else ""
        console.print(f"  [cyan]{idx:<2}[/cyan] {m:<30} [dim](Google AI Studio)[/dim]{cur}")
        model_map[str(idx)] = ("gemini", m)
        idx += 1

    # Group 5: OpenRouter
    console.print(f"\n[bold yellow]── 🧭 OPENROUTER (Evrensel Ücretsiz Modeller {'[Key Var]' if has_openrouter else '[Key Gerekli]'}) ──[/bold yellow]")
    for m in OPENROUTER_MODELS:
        cur = " [bold green][AKTİF][/bold green]" if active_provider == "openrouter" and active_model_name == m else ""
        console.print(f"  [cyan]{idx:<2}[/cyan] {m:<30} [dim](Ücretsiz Açık Kaynak)[/dim]{cur}")
        model_map[str(idx)] = ("openrouter", m)
        idx += 1

    console.print("\n  [cyan]i[/cyan]  Yeni yerel Ollama modeli indir (örn: qwen2.5-coder:3b)")
    console.print("  [cyan]0[/cyan]  İptal\n")

    choices = list(model_map.keys()) + ["i", "0"]
    choice = Prompt.ask("Seçiminiz", choices=choices, default="1")
    if choice == "0":
        return

    if choice == "i":
        new_model = Prompt.ask("İndirilecek Ollama modeli", default="qwen2.5-coder:3b").strip()
        if new_model:
            prompt_and_execute(f"ollama pull {new_model}")
            save_settings({"provider": "ollama", "ollama_model": new_model})
            render_top_banner()
            console.print(f"[bold green][+][/bold green] '{new_model}' indirildi ve aktif model yapıldı.\n")
        return

    prov, mod = model_map[choice]
    # Key kontrolü
    if prov == "groq" and not has_groq:
        console.print("\n[yellow][!] Groq API anahtarı gerekli.[/yellow]")
        configure_api_key("groq")
    elif prov == "deepseek" and not has_deepseek:
        console.print("\n[yellow][!] DeepSeek API anahtarı gerekli.[/yellow]")
        configure_api_key("deepseek")
    elif prov == "gemini" and not has_gemini:
        console.print("\n[yellow][!] Gemini API anahtarı gerekli.[/yellow]")
        configure_api_key("gemini")
    elif prov == "openrouter" and not has_openrouter:
        console.print("\n[yellow][!] OpenRouter API anahtarı gerekli.[/yellow]")
        configure_api_key("openrouter")

    save_settings({"provider": prov, f"{prov}_model" if prov != "ollama" else "ollama_model": mod})
    render_top_banner()
    console.print(f"\n[bold green][+][/bold green] Aktif Yapay Zeka Motoru: [cyan]{mod} ({prov.upper()})[/cyan]\n")


def manage_infomy_interactive(inline_info: str = "") -> None:
    """Kullanicinin kim oldugunu, profilini ve ozel tercihlerini kaydeder veya gosterir."""
    if inline_info:
        set_user_profile(inline_info)
        console.print(
            Panel(
                f"[bold green]✓ Profil Bilgin Başarıyla Kaydedildi![/bold green]\n\n"
                f"[cyan]{inline_info}[/cyan]\n\n"
                f"[dim]SecAI artık tüm sohbetlerde ve komutlarda senin kim olduğunu, hedeflerini ve tercihlerini tam olarak hatırlayacak.[/dim]",
                title="👤 SecAI Kimlik Hafızası (/infomy)",
                border_style="green",
            )
        )
        return

    existing = get_user_profile()
    if existing:
        console.print(
            Panel(
                f"[bold cyan]Kayıtlı Kimlik Profilin:[/bold cyan]\n\n"
                f"[white]{existing}[/white]\n\n"
                f"[dim]Profilini güncellemek için yeni bilgiyi yazabilir ya da aynı bırakmak için boş geçebilirsiniz.[/dim]",
                title="👤 SecAI Kimlik Hafızası (/infomy)",
                border_style="cyan",
            )
        )
        new_info = Prompt.ask("\n[bold cyan]Yeni profil bilgin[/bold cyan] (değiştirmemek için Enter)", default="")
        if new_info.strip():
            set_user_profile(new_info.strip())
            console.print("\n[bold green][+][/bold green] Kimlik profilin güncellendi!\n")
    else:
        console.print(
            Panel(
                "[bold cyan]SecAI seni tanısın![/bold cyan]\n\n"
                "Kendinle ilgili dilediğin bilgileri gir (adın, rolün, uzmanlık alanın, kullandığın teknolojiler, hedeflerin).\n\n"
                "[dim]Örnek: 'Adım Kayra, siber güvenlik ve ağ analizi araştırmacısıyım. Arch Linux ve Python kullanıyorum. Hedefim OSCP sertifikası almak.'[/dim]",
                title="👤 SecAI Kimlik Tanımlama (/infomy)",
                border_style="cyan",
            )
        )
        info = Prompt.ask("[bold cyan]Profil Bilgin[/bold cyan]")
        if info.strip():
            set_user_profile(info.strip())
            console.print("\n[bold green][+][/bold green] Kimlik profilin kaydedildi! SecAI artık seni tanıyor.\n")


def manage_image_interactive(prompt: str = "") -> None:
    """Yapay zeka ile görsel üretir ve yerel diskte saklar."""
    if not prompt:
        prompt = Prompt.ask("\n[bold cyan]🎨 Oluşturulacak Görsel Promptu[/bold cyan]").strip()
        if not prompt:
            return

    console.print()
    with console.status("[bold magenta]🎨 Görsel oluşturuluyor (Stable Diffusion / Horde)...[/bold magenta]", spinner="dots"):
        img_path = generate_image(prompt)

    if not img_path or not img_path.exists():
        console.print("[bold red][!] Görsel oluşturulamadı. Lütfen tekrar deneyin.[/bold red]\n")
        return

    size_kb = max(1, img_path.stat().st_size // 1024)
    console.print(
        Panel(
            f"[bold green]✓ Görsel Başarıyla Üretildi![/bold green]\n\n"
            f"[bold]Prompt:[/bold] [italic]{prompt}[/italic]\n"
            f"[bold]Dosya Yolu:[/bold] [cyan]{img_path}[/cyan]\n"
            f"[bold]Boyut:[/bold] {size_kb} KB\n\n"
            f"[dim]İpucu: Görseli açmak için sistem görüntüleyicisi tetikleniyor...[/dim]",
            title="🎨 SecAI Image Studio (/image)",
            border_style="magenta",
        )
    )

    if shutil.which("xdg-open"):
        try:
            subprocess.Popen(["xdg-open", str(img_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


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

