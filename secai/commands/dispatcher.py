"""SecAI Komut Yönlendiricisi (Command Dispatcher).

Kullanıcının terminalden girdiği /slash komutlarını, özel anahtar yapılarını ve
SecOps kısayollarını ilgili işleyicilere (handlers) temizce yönlendirir.
"""

from typing import Any, Callable, Dict, Optional
import uuid
from rich.console import Console
from rich.prompt import Prompt

from secai.commands.handlers.config_handler import (
    configure_api_key,
    manage_image_interactive,
    manage_infomy_interactive,
    manage_skills_interactive,
    switch_model_interactive,
)
from secai.commands.handlers.intel_handler import (
    interactive_abuse,
    interactive_intel,
    interactive_vt,
)
from secai.commands.handlers.note_handler import (
    interactive_add_note,
    interactive_edit_note,
    interactive_list_and_read,
    interactive_restore_backup,
)
from secai.commands.handlers.secops_handler import (
    generate_session_report,
    interactive_audit,
    interactive_baseline,
    interactive_diff,
    interactive_hardening_score,
    interactive_security_checkup,
)
from secai.commands.handlers.voice_handler import (
    interactive_push_to_talk,
    interactive_voice_loop,
    manage_voice_settings,
)
from secai.commands.ui import render_top_banner, show_shortcuts
from secai.core.database import (
    add_note,
    backup_database,
    clear_chat_history,
    create_session,
    delete_memory,
    list_memories,
    list_sessions,
    update_session_title,
)

console = Console()


class CommandDispatcher:
    """Terminal slash komutlarını dinamik ve genişletilebilir biçimde işleyen yönlendirici."""

    def __init__(self, agent_turn_fn: Optional[Callable] = None):
        self.agent_turn_fn = agent_turn_fn

    def dispatch(self, user_input: str, state: Dict[str, Any]) -> bool:
        """
        Kullanıcı girdisini analiz eder.
        Eğer komut bir /slash komutu ise işletir ve True döner.
        Eğer normal sohbet mesajı ise False döner.
        """
        raw = user_input.strip()
        low = raw.lower()
        session = state.get("session", "default")

        # 1. Doğrudan yapıştırılan API anahtarlarını algıla
        if (
            (raw.startswith("AIza") or raw.startswith("AQ.") or raw.startswith("gsk_") or raw.startswith("sk-"))
            and len(raw.split()) == 1
            and len(raw) >= 20
        ):
            configure_api_key(inline_key=raw)
            return True

        # 2. Çıkış komutları
        if low in ("q", "quit", "exit", "/exit", "/q", "cikis", "çıkış"):
            state["should_exit"] = True
            return True

        # 3. Yardım ve kısayollar
        if low in ("?", "/help", "help", "yardim", "yardım", "menu", "menü"):
            show_shortcuts()
            return True

        # 4. Sohbet & Oturum Yönetimi
        if low in ("/clear", "clear", "temizle"):
            clear_chat_history(session_id=session)
            render_top_banner()
            console.print(f"[bold green][+][/bold green] '{session}' sohbet geçmişi temizlendi.\n")
            return True

        if low in ("/new", "/yeni", "new", "yeni"):
            new_id = f"chat_{uuid.uuid4().hex[:6]}"
            state["session"] = new_id
            create_session(new_id, "Yeni Sohbet")
            render_top_banner()
            console.print(f"[bold green][+][/bold green] Yeni sohbet oturumu başlatıldı: [cyan]{new_id}[/cyan]\n")
            return True

        if low in ("/chats", "/sessions", "chats", "sohbetler"):
            s_list = list_sessions()
            console.print("\n[bold white]Kayıtlı Sohbet Oturumları[/bold white]")
            for s_item in s_list:
                cur_mark = " [bold green][AKTİF][/bold green]" if s_item["id"] == session else ""
                console.print(
                    f"  • [cyan]{s_item['id']:<14}[/cyan] '{s_item['title']}' "
                    f"({s_item['msg_count']} mesaj, {s_item['updated_at']}){cur_mark}"
                )
            console.print("\n[dim]Geçiş yapmak için: /chat <id> | Başlık değiştirmek için: /rename <yeni isim>[/dim]\n")
            return True

        if low in ("/rename", "/title", "/baslik", "rename", "title", "baslik") or low.startswith(
            ("/rename ", "/title ", "/baslik ", "rename ", "title ", "baslik ")
        ):
            parts = raw.split(maxsplit=1)
            new_title = parts[1].strip() if len(parts) > 1 else ""
            if not new_title:
                new_title = Prompt.ask("\n[bold cyan]Yeni Sohbet Başlığı[/bold cyan]").strip()
            if new_title:
                update_session_title(session, new_title)
                console.print(f"\n[bold green]✓ Sohbet başlığı güncellendi:[/bold green] [cyan]{new_title}[/cyan]\n")
            return True

        if low.startswith("/chat ") or low.startswith("chat "):
            target_sess = raw.split(maxsplit=1)[1].strip()
            if target_sess:
                state["session"] = target_sess
                create_session(target_sess, target_sess)
                render_top_banner()
                console.print(f"[bold green][+][/bold green] Oturuma geçildi: [cyan]{target_sess}[/cyan]\n")
            return True

        # 5. Kimlik Hafızası & Profil
        if low in ("/infomy", "/myinfo", "infomy", "myinfo", "/kimim", "kimim") or low.startswith(
            ("/infomy ", "/myinfo ", "infomy ", "myinfo ", "/kimim ", "kimim ")
        ):
            parts = raw.split(maxsplit=1)
            arg = parts[1].strip() if len(parts) > 1 else ""
            manage_infomy_interactive(inline_info=arg)
            return True

        # 6. Görsel Üretim
        if low in ("/image", "/img", "/ciz", "/gorsel", "/görsel", "image", "img", "ciz", "gorsel", "görsel") or low.startswith(
            ("/image ", "/img ", "/ciz ", "/gorsel ", "/görsel ", "image ", "img ", "ciz ", "gorsel ", "görsel ")
        ):
            parts = raw.split(maxsplit=1)
            arg = parts[1].strip() if len(parts) > 1 else ""
            manage_image_interactive(prompt=arg)
            return True

        # 7. ChatGPT Tarzı Kalıcı Bellek (Memory)
        if low in ("/memory", "/bellek", "memory", "bellek"):
            mems = list_memories()
            if not mems:
                console.print("\n[dim]SecAI tarafından henüz kaydedilmiş kişisel bir bellek yok.[/dim]\n")
            else:
                console.print("\n[bold magenta]SecAI Kalıcı Profil & Bellek (ChatGPT Memory):[/bold magenta]")
                for m in mems:
                    console.print(f"  • [cyan]{m['key']}:[/cyan] {m['fact']} [dim]({m['created_at']})[/dim]")
                console.print("\n[dim]Bellekten silmek için: /forget <anahtar>[/dim]\n")
            return True

        if low.startswith("/forget ") or low.startswith("forget "):
            k = raw.split(maxsplit=1)[1].strip()
            if delete_memory(k):
                console.print(f"[bold green][+][/bold green] '{k}' bellekten silindi.\n")
            else:
                console.print(f"[yellow][!] '{k}' anahtarlı bellek bulunamadı.[/yellow]\n")
            return True

        # 8. Ses ve Konuşma Modları
        if low in ("/v", "/talk", "talk", "konus", "konuş", "dinle"):
            reply = interactive_push_to_talk(session=session, agent_turn_fn=self.agent_turn_fn)
            if reply:
                state["last_assistant_reply"] = reply
            return True

        if low in ("/voice", "voice", "telsiz", "sesli mod", "sesli sohbet"):
            interactive_voice_loop(session=session, agent_turn_fn=self.agent_turn_fn)
            return True

        if low in ("/ses", "/tts", "ses", "tts") or low.startswith("/ses ") or low.startswith("/tts "):
            parts = raw.split(maxsplit=1)
            arg = parts[1] if len(parts) > 1 else ""
            manage_voice_settings(
                inline_arg=arg,
                on_voice_loop=lambda: interactive_voice_loop(session=session, agent_turn_fn=self.agent_turn_fn),
            )
            return True

        # 9. Web Arayüzü Başlatıcı
        if low in ("/web", "web", "gui"):
            from secai.web.server import run_web_server

            console.print("\n[bold cyan][*][/bold cyan] Web arayüzü başlatılıyor...")
            run_web_server(port=8765, open_browser=True)
            return True

        # 10. API & Model & Yetenek Yapılandırması
        if low in ("api", "key", "/api", "/key") or low.startswith("/api ") or low.startswith("/key ") or low.startswith("api "):
            parts = raw.split(maxsplit=1)
            inline_key = parts[1] if len(parts) > 1 else ""
            configure_api_key(inline_key=inline_key)
            return True

        if low in ("/model", "/models", "model", "models", "motor"):
            switch_model_interactive()
            return True

        if low in ("/agent", "/agents", "agent", "agents", "/ajan", "ajan", "/skills", "/skill", "skills", "skill", "yetenek") or low.startswith(
            ("/agent ", "agent ", "/ajan ", "ajan ", "/skill ", "skill ")
        ):
            parts = raw.split(maxsplit=1)
            arg = parts[1] if len(parts) > 1 else ""
            manage_skills_interactive(inline_arg=arg)
            return True

        # 11. Tehdit İstihbaratı (Shodan, VT, Abuse)
        if low.startswith("/intel") or low.startswith("intel "):
            parts = raw.split(maxsplit=1)
            target = parts[1] if len(parts) > 1 else ""
            interactive_intel(inline_target=target)
            return True

        if low in ("/vt", "/virustotal") or low.startswith(("/vt ", "/virustotal ")):
            parts = raw.split(maxsplit=1)
            target = parts[1] if len(parts) > 1 else ""
            interactive_vt(inline_target=target)
            return True

        if low in ("/abuse", "/abuseipdb") or low.startswith(("/abuse ", "/abuseipdb ")):
            parts = raw.split(maxsplit=1)
            ip = parts[1] if len(parts) > 1 else ""
            interactive_abuse(inline_ip=ip)
            return True

        # 12. SecOps, Hardening & Checkup
        if low in ("/check",):
            interactive_security_checkup(require_confirm=True)
            return True

        if low.startswith("/baseline") or low == "baseline":
            parts = raw.split(maxsplit=1)
            lbl = parts[1] if len(parts) > 1 else "default"
            interactive_baseline(label=lbl)
            return True

        if low in ("/diff", "diff"):
            interactive_diff(analyze_with_ai=True)
            return True

        if low in ("/score", "/harden", "score", "harden"):
            interactive_hardening_score(analyze_with_ai=False)
            return True

        if low.startswith("/audit"):
            parts = raw.split(maxsplit=1)
            target = parts[1] if len(parts) > 1 else ""
            interactive_audit(inline_target=target)
            return True

        # 12b. Güvenli Dosya & Çıktı Analizi (/analyze)
        if low == "/analyze" or low.startswith("/analyze "):
            parts = raw.split(maxsplit=1)
            target = parts[1].strip() if len(parts) > 1 else ""
            if not target:
                console.print("\n[yellow][!][/yellow] Kullanım: [cyan]/analyze <dosya_yolu_veya_komut>[/cyan]")
                console.print("[dim]Örnek: /analyze auth.log veya /analyze nmap_output.txt[/dim]\n")
                return True

            from pathlib import Path
            from secai.core.analyzer import read_and_prepare_file_for_analysis, run_command_for_analysis

            target_path = Path(target).expanduser()
            if target_path.exists() and not target_path.is_dir():
                ok, prompt_or_err = read_and_prepare_file_for_analysis(target)
                if not ok:
                    console.print(f"\n[bold red][-][/bold red] {prompt_or_err}\n")
                    return True
                console.print(f"\n[bold cyan][*][/bold cyan] Dosya analiz ediliyor: [cyan]{target_path}[/cyan]\n")
                if self.agent_turn_fn:
                    self.agent_turn_fn(prompt_or_err, session=session)
                return True

            ok_cmd, cmd_prompt_or_err = run_command_for_analysis(target)
            if ok_cmd:
                console.print(f"\n[bold cyan][*][/bold cyan] Komut çalıştırıldı ve çıktısı analiz ediliyor: [cyan]{target}[/cyan]\n")
                if self.agent_turn_fn:
                    self.agent_turn_fn(cmd_prompt_or_err, session=session)
                return True
            else:
                console.print(f"\n[bold red][-][/bold red] Dosya bulunamadı veya komut çalıştırılamadı: [cyan]{target}[/cyan]")
                console.print(f"[dim]{cmd_prompt_or_err}[/dim]\n")
                return True

        # 12c. Doğrudan Komut Çalıştırıp Analiz Etme (/run)
        if low == "/run" or low.startswith("/run "):
            parts = raw.split(maxsplit=1)
            cmd = parts[1].strip() if len(parts) > 1 else ""
            if not cmd:
                console.print("\n[yellow][!][/yellow] Kullanım: [cyan]/run <sistem_komutu>[/cyan]")
                console.print("[dim]Örnek: /run ss -tulnp veya /run netstat -tulpn[/dim]\n")
                return True

            from secai.core.analyzer import run_command_for_analysis

            console.print(f"\n[bold cyan][*][/bold cyan] Komut alt süreçte çalıştırılıyor: [cyan]{cmd}[/cyan]\n")
            ok_cmd, cmd_prompt_or_err = run_command_for_analysis(cmd)
            if not ok_cmd:
                console.print(f"\n[bold red][-][/bold red] {cmd_prompt_or_err}\n")
                return True

            if self.agent_turn_fn:
                self.agent_turn_fn(cmd_prompt_or_err, session=session)
            return True

        # 12d. Smart Mode (Akıllı Model Yönlendirici)
        if low in ("/smart", "/smartmode") or low.startswith(("/smart ", "/smartmode ")):
            from secai.core.smart_router import is_smart_mode_enabled, set_smart_mode
            parts = raw.split(maxsplit=1)
            sub = parts[1].strip().lower() if len(parts) > 1 else ""
            if sub in ("on", "ac", "aç", "aktif", "enable", "1"):
                set_smart_mode(True)
                console.print("\n[bold green][+][/bold green] Smart Mode (Akıllı Model Yönlendirici) [bold green]AKTİF[/bold green].\n")
                return True
            if sub in ("off", "kapat", "pasif", "disable", "0"):
                set_smart_mode(False)
                console.print("\n[bold yellow][!][/bold yellow] Smart Mode (Akıllı Model Yönlendirici) [yellow]PASİF[/yellow].\n")
                return True

            current_status = is_smart_mode_enabled()
            status_text = "[bold green]AÇIK (AKTİF)[/bold green]" if current_status else "[bold red]KAPALI (PASİF)[/bold red]"
            console.print(f"\n[bold cyan]⚡ Smart Mode (Akıllı Model Yönlendirici):[/bold cyan] {status_text}")
            console.print("[dim]Karmaşık analizlerde (tersine mühendislik, exploit) bulut/büyük modellere geçiş önerir.[/dim]")
            console.print("[dim]Açıp kapatmak için: /smart on veya /smart off[/dim]\n")
            return True

        if low in ("/report", "rapor", "rapor cikar", "rapor oluştur"):
            generate_session_report(session=session)
            return True

        # 13. Vaka Defteri & Yedekleme
        if (
            low in ("/notes", "/list", "/defter", "notları sil", "notlari sil", "tüm notları sil", "tum notlari sil", "defteri temizle")
            or low.startswith(("/notes ", "/list ", "/defter "))
        ):
            parts = raw.split(maxsplit=1)
            sub = parts[1].strip().lower() if len(parts) > 1 else ""
            if sub in ("clear", "sil", "temizle", "all") or low in ("notları sil", "notlari sil", "tüm notları sil", "tum notlari sil", "defteri temizle"):
                from rich.prompt import Confirm
                from secai.core.database import clear_all_notes

                if Confirm.ask("Vaka Defterindeki TÜM notlar silinsin mi?", default=False):
                    cnt = clear_all_notes()
                    console.print(f"\n[bold green][+][/bold green] Vaka Defterindeki tüm notlar silindi ({cnt} adet).\n")
                return True
            interactive_list_and_read()
            return True

        if low in ("/add",):
            interactive_add_note()
            return True

        if low in ("/edit",):
            interactive_edit_note()
            return True

        if low in ("/backup",):
            b_path = backup_database()
            console.print(f"\n[bold green][+][/bold green] Yedek alındı: {b_path}\n")
            return True

        if low in ("/restore",):
            interactive_restore_backup()
            return True

        if low in ("/status", "durum") and state.get("status_callback"):
            console.print()
            state["status_callback"]()
            console.print()
            return True

        if low.startswith("/save"):
            title = raw[5:].strip() or f"not-{session}"
            last_reply = state.get("last_assistant_reply", "")
            if not last_reply:
                console.print("\n[yellow][!][/yellow] Henüz kaydedilecek bir yanıt yok.\n")
                return True
            note_id = add_note(
                title=title,
                content=last_reply,
                category="secops",
                tags="chat",
            )
            console.print(f"\n[bold green][+][/bold green] Deftere kaydedildi (#{note_id} - {title})\n")
            return True

        # Eşleşen /slash komutu yok; normal mesaj olarak ajana ilet
        return False

