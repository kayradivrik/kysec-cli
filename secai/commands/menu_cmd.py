"""SecAI Ana Terminal Arayüzü ve Ajan Orkestratörü.

Bu modül, kullanıcı etkileşimini, readline geçmişini, akış yanıtlarını
ve çok adımlı otonom SecOps ajan döngüsünü koordine eder.
Tüm alt komutlar `dispatcher` ve ilgili `handlers` modüllerine delege edilir.
"""

from pathlib import Path
from rich.console import Console

from secai.commands.dispatcher import CommandDispatcher
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
    stream_markdown_from_generator,
)
from secai.commands.handlers.voice_handler import (
    interactive_push_to_talk,
    interactive_voice_loop,
    manage_voice_settings,
)
from secai.commands.ui import (
    PIXEL_LOGO_LINES,
    SLASH_COMMANDS,
    render_prompt_frame_and_input,
    render_top_banner,
    save_readline_history,
    setup_readline,
    show_shortcuts,
)
from secai.config import load_settings
from secai.core.baseline import compare_with_baseline, calculate_hardening_score, format_baseline_diff_report, format_hardening_report
from secai.core.database import (
    add_chat_message,
    add_note,
    auto_title_session,
    delete_memory,
    delete_note,
    export_note_markdown,
    get_chat_history,
    save_memory,
    update_note,
)
from secai.core.executor import (
    expand_file_references,
    extract_intel_queries,
    extract_memory_actions,
    extract_note_actions,
    extract_saved_notes,
    extract_secops_actions,
    extract_shell_commands,
    extract_web_searches,
    prompt_and_execute,
    strip_internal_blocks,
)
from secai.core.intel import format_intel_report
from secai.core.llm import OllamaConnectionError, stream_chat
from secai.core.voice import speak_text
from secai.core.web import format_web_results

console = Console()

# Geriye dönük uyumluluk için aliaslar:
_stream_markdown_from_generator = stream_markdown_from_generator
_setup_readline = setup_readline
_save_readline_history = save_readline_history


def _stream_reply(messages: list[dict]) -> str:
    """Aktif LLM motorundan gelen yanıtı ekranda Markdown paneli olarak canlı akıtır."""
    gen = stream_chat(messages=messages)
    return stream_markdown_from_generator(gen)


def _run_agent_turn(user_input: str, session: str = "default", force_speak: bool = False) -> str:
    """
    Kullanıcı mesajını alır, AI yanıtını akıtır, çok adımlı ajan döngüsünü (notlar, web arama,
    Shodan intel, SecOps motorları ve bash komutları) çalıştırır ve seslendirme aktifse konuşur.
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

        # 1. Doğal dille not kaydetme isteği varsa otomatik veritabanına kaydet
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

        # 2. Doğal dille not güncelleme / silme / markdown dışa aktarma
        for act in extract_note_actions(last_assistant_reply):
            nid = int(act["id"])
            if act["action"] == "update-note" and act["content"]:
                if update_note(note_id=nid, content=act["content"], append=True):
                    console.print(f"[bold green][+][/bold green] Not #{nid} güncellendi.\n")
            elif act["action"] == "delete-note":
                if delete_note(nid):
                    console.print(f"[bold green][+][/bold green] Not #{nid} silindi.\n")
            elif act["action"] == "export-note":
                try:
                    md_path = export_note_markdown(nid)
                    console.print(f"[bold green][+][/bold green] Markdown rapor hazır: {md_path}\n")
                except ValueError:
                    pass

        # 3. ChatGPT Memory Tarzı Kalıcı Profil & Bellek İşlemleri
        for m_act in extract_memory_actions(last_assistant_reply):
            if m_act["action"] == "remember":
                save_memory(key=m_act["key"], fact=m_act["fact"])
                console.print(f"[bold magenta][🧠 Bellek Kaydedildi][/bold magenta] {m_act['fact']}\n")
            elif m_act["action"] == "forget":
                if delete_memory(m_act["key"]):
                    console.print(f"[bold magenta][🧠 Bellekten Silindi][/bold magenta] '{m_act['key']}'\n")

        # 4. Otomatik Canlı Web Araması
        web_queries = extract_web_searches(last_assistant_reply)
        if web_queries:
            wq = web_queries[0]
            console.print(f"[bold cyan][*][/bold cyan] Web'de aranıyor: [white]{wq}[/white]")
            web_report = format_web_results(wq, max_results=6)
            add_chat_message(
                session_id=session,
                role="user",
                content=(
                    f"{web_report}\n\n"
                    "Yukarıdaki canlı web arama sonuçlarını kullanarak kullanıcının sorusunu detaylı ve kaynak linkleriyle yanıtla (tekrar web-search bloğu yazma)."
                ),
            )
            try:
                updated_messages = get_chat_history(session_id=session, limit=40)
                last_assistant_reply = _stream_reply(updated_messages)
                continue
            except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                break

        # 5. Otomatik Shodan InternetDB & GeoIP Tehdit İstihbaratı Sorgusu
        intel_queries = extract_intel_queries(last_assistant_reply)
        if intel_queries:
            iq = "\n".join(intel_queries)
            console.print("[bold cyan][*][/bold cyan] Shodan InternetDB & GeoIP tehdit istihbaratı sorgulanıyor...")
            intel_report = format_intel_report(iq, max_ips=8)
            add_chat_message(
                session_id=session,
                role="user",
                content=(
                    f"{intel_report}\n\n"
                    "Yukarıdaki gerçek Shodan InternetDB ve GeoIP istihbarat sonuçlarını kullanarak kullanıcıya detaylı bir tehdit analizi sun (tekrar intel-lookup bloğu yazma)."
                ),
            )
            try:
                updated_messages = get_chat_history(session_id=session, limit=40)
                last_assistant_reply = _stream_reply(updated_messages)
                continue
            except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                break

        # 6. Otomatik SecOps Motorları (baseline, diff, score)
        secops_acts = extract_secops_actions(last_assistant_reply)
        if secops_acts:
            act = secops_acts[0]
            if act == "baseline":
                interactive_baseline("default")
                break
            elif act == "diff":
                diff_data = compare_with_baseline()
                diff_md = format_baseline_diff_report(diff_data)
                from rich.padding import Padding
                from rich.markdown import Markdown

                console.print(Padding(Markdown(diff_md, code_theme="monokai"), (0, 1)))
                add_chat_message(
                    session_id=session,
                    role="user",
                    content=(
                        f"{diff_md}\n\n"
                        "Yukarıdaki sistem baseline karşılaştırma (drift) raporunu değerlendir ve varsa anomalileri açıkla (tekrar secops-action bloğu yazma)."
                    ),
                )
            elif act in ("score", "harden"):
                score_data = calculate_hardening_score()
                score_md = format_hardening_report(score_data)
                from rich.padding import Padding
                from rich.markdown import Markdown

                console.print(Padding(Markdown(score_md, code_theme="monokai"), (0, 1)))
                add_chat_message(
                    session_id=session,
                    role="user",
                    content=(
                        f"{score_md}\n\n"
                        "Yukarıdaki deterministik CIS güvenlik skoru tablosundaki eksikleri (FAIL/WARN) nasıl kapatabileceğimizi özetle (tekrar secops-action bloğu yazma)."
                    ),
                )
            try:
                updated_messages = get_chat_history(session_id=session, limit=40)
                last_assistant_reply = _stream_reply(updated_messages)
                continue
            except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                break

        # 7. Sistem Bash Komutları Çalıştırma
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
                        f"[Komut Çıktısı ('{cmd}')]:\n{trimmed_out}\n\n"
                        "Yukarıdaki komut çıktısını analiz et. Eğer komut hata verdiyse veya işlemi tamamlamak için 2. bir komut gerekiyorsa yeni ```bash bloğu ver; işlem tamamlandıysa sonucu tablo/maddelerle özetle."
                    ),
                )
                try:
                    updated_messages = get_chat_history(session_id=session, limit=40)
                    next_reply = _stream_reply(updated_messages)
                except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                    next_reply = ""
        last_assistant_reply = next_reply

    return final_reply


def run_interactive_menu(status_callback=None) -> None:
    """Antigravity CLI tarzı tam ekran temiz çalışma alanı ana döngüsü."""
    dispatcher = CommandDispatcher(agent_turn_fn=_run_agent_turn)
    history_file = setup_readline()
    render_top_banner()

    state = {
        "session": "default",
        "last_assistant_reply": "",
        "status_callback": status_callback,
        "should_exit": False,
    }

    try:
        while True:
            try:
                user_input = render_prompt_frame_and_input()
            except (KeyboardInterrupt, EOFError):
                console.print()
                break

            if not user_input:
                continue

            # Komutu Dispatcher'a ilet
            handled = dispatcher.dispatch(user_input, state)
            if state["should_exit"]:
                break
            if handled:
                continue

            # Normal mesaj: Çok adımlı ajanı tetikle
            session = state["session"]
            state["last_assistant_reply"] = _run_agent_turn(user_input, session=session, force_speak=False)
            try:
                auto_title_session(session)
            except Exception:
                pass
    finally:
        save_readline_history(history_file)
