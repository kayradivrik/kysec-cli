"""Sesli komut, push-to-talk ve canli telsiz diyalog isleyicileri."""

from typing import Callable, Optional
from rich.console import Console
from rich.prompt import Prompt

from secai.commands.ui import render_top_banner
from secai.config import load_settings, save_settings
from secai.core.voice import (
    VOICE_PROFILES,
    record_voice_input,
    transcribe_voice,
)

console = Console()


def manage_voice_settings(inline_arg: str = "", on_voice_loop: Optional[Callable[[], None]] = None) -> None:
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
        if on_voice_loop:
            on_voice_loop()
        else:
            interactive_voice_loop(session="default")


def interactive_push_to_talk(session: str = "default", agent_turn_fn: Optional[Callable] = None) -> str:
    """Tek seferlik Bas-Konus (mikrofonu dinler, metne cevirir, yanitlar ve sesli konusur)."""
    wav_path = record_voice_input()
    if not wav_path:
        return ""
    transcript = transcribe_voice(wav_path)
    if not transcript:
        console.print("[yellow][!] Konusma anlasilamadi, tekrar deneyin.[/yellow]\n")
        return ""

    console.print(f"\n[bold cyan][Sen (Sesli)]:[/bold cyan] [bold white]{transcript}[/bold white]")
    if agent_turn_fn is not None:
        return agent_turn_fn(transcript, session=session, force_speak=True)
    from secai.commands.menu_cmd import _run_agent_turn
    return _run_agent_turn(transcript, session=session, force_speak=True)


def interactive_voice_loop(session: str = "default", agent_turn_fn: Optional[Callable] = None) -> None:
    """Karsilikli kesintisiz Canli Sesli Diyalog (Telsiz) Modu."""
    console.print(
        "\n[bold cyan][*] CANLI SESLI DIYALOG (TELSIZ) MODU AKTIF[/bold cyan]\n"
        "[dim]Konusup ENTER'a basin, SecAI hem ekranda gosterecek hem de sesli yanitlayacaktir. Cikmak icin 'q' yazin.[/dim]"
    )
    while True:
        interactive_push_to_talk(session=session, agent_turn_fn=agent_turn_fn)
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

