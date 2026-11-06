import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding

from secai.config import DEFAULT_MODEL
from secai.core.database import (
    add_chat_message,
    add_note,
    clear_chat_history,
    get_chat_history,
)
from secai.core.executor import extract_shell_commands, prompt_and_execute
from secai.core.llm import OllamaConnectionError, stream_chat

console = Console()


def _stream_and_print_reply(messages: list[dict], model: str) -> str:
    reply_chunks: list[str] = []
    gen = stream_chat(messages=messages, model=model)
    with console.status("[cyan][*] model dusunuyor...[/cyan]", spinner="dots"):
        first_token = next(gen, None)

    if first_token:
        reply_chunks.append(first_token)
        console.print()
        with Live(
            Padding(Markdown("".join(reply_chunks), code_theme="monokai"), (0, 1)),
            console=console,
            refresh_per_second=14,
        ) as live:
            for token in gen:
                reply_chunks.append(token)
                live.update(Padding(Markdown("".join(reply_chunks), code_theme="monokai"), (0, 1)))
        console.print()

    return "".join(reply_chunks).strip()


def chat_command(
    session: str = typer.Option("default", "--session", "-s", help="Oturum adi"),
    clear: bool = typer.Option(False, "--clear", help="Oturum gecmisini sifirla"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Ollama modeli"),
):
    """Yerel model ile hafizali ve e/h komut onayli terminal sohbeti."""
    if clear:
        deleted = clear_chat_history(session_id=session)
        console.print(f"[yellow][*][/yellow] '{session}' oturumundan {deleted} mesaj silindi.")

    history = get_chat_history(session_id=session, limit=20)
    console.print(
        f"\n[bold cyan][*][/bold cyan] model: {model} | hafiza: {len(history)} mesaj\n"
        "[dim]Cikis: q | Hafizayi sil: /clear | Son yaniti deftere kaydet: /save <baslik>[/dim]"
    )

    last_assistant_reply = ""

    while True:
        try:
            user_input = console.input("\n[bold cyan]sen>[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "exit", "quit", "q", "0"):
            break

        if user_input.lower() == "/clear":
            clear_chat_history(session_id=session)
            console.print("[bold green][+][/bold green] Sohbet hafizasi temizlendi.")
            continue

        if user_input.lower().startswith("/save"):
            title = user_input[5:].strip() or f"chat-{session}"
            if not last_assistant_reply:
                console.print("[yellow][!][/yellow] Henuz kaydedilecek bir yanit yok.")
                continue
            note_id = add_note(
                title=title,
                content=last_assistant_reply,
                category="secops",
                tags=f"chat,{session}",
            )
            console.print(f"[bold green][+][/bold green] Deftere kaydedildi (#{note_id} - {title})")
            continue

        add_chat_message(session_id=session, role="user", content=user_input)
        current_messages = get_chat_history(session_id=session, limit=20)

        try:
            last_assistant_reply = _stream_and_print_reply(current_messages, model)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow][!] Yanit durduruldu.[/yellow]")
            continue
        except OllamaConnectionError as err:
            console.print(f"\n[bold red][-][/bold red] {err}")
            continue

        if last_assistant_reply:
            add_chat_message(
                session_id=session, role="assistant", content=last_assistant_reply
            )

            # Yanit icinde bash/sh komutu varsa kullaniciya e/h diye sor
            commands = extract_shell_commands(last_assistant_reply)
            for cmd in commands:
                cmd_output = prompt_and_execute(cmd)
                if cmd_output is not None:
                    trimmed_out = cmd_output[:16000]
                    add_chat_message(
                        session_id=session,
                        role="user",
                        content=(
                            f"[Komut Ciktisi ('{cmd}')]:\n{trimmed_out}\n\n"
                            "Yukaridaki komut ciktisina gore kullanicinin sorusunu kisaca yanitla (tekrar bash komutu yazma)."
                        ),
                    )
                    try:
                        updated_messages = get_chat_history(session_id=session, limit=20)
                        summary_reply = _stream_and_print_reply(updated_messages, model)
                        if summary_reply:
                            last_assistant_reply = summary_reply
                            add_chat_message(
                                session_id=session,
                                role="assistant",
                                content=summary_reply,
                            )
                    except (KeyboardInterrupt, EOFError, OllamaConnectionError):
                        pass
