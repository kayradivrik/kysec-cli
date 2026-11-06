import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from rich.console import Console

console = Console()

DANGEROUS_PATTERNS = (
    r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
    r"\bchmod\s+-R\s+777\s+/\b",
    r":\(\)\s*\{\s*:\|:&\s*\};:",
)


def expand_file_references(user_text: str) -> str:
    """
    Kullanici mesajindaki @dosya_yolu ifadelerini bulur ve dosya icerigini mesaja ekler.
    Orn: '@README.md bunu ozetle' veya '@/etc/hosts kontrol et'
    """
    matches = re.findall(r"@([^\s]+)", user_text)
    if not matches:
        return user_text

    attachments: list[str] = []
    for raw_path in matches:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if candidate.exists() and candidate.is_file():
            try:
                content = candidate.read_text(encoding="utf-8", errors="replace")[:12000]
                console.print(f"[cyan][*] Dosya okundu:[/cyan] {candidate}")
                attachments.append(f"\n\n[DOSYA ICERIGI ('{candidate}')]:\n```\n{content}\n```")
            except Exception as exc:
                console.print(f"[yellow][!] Dosya okunamadi ({candidate}): {exc}[/yellow]")

    if not attachments:
        return user_text
    return user_text + "".join(attachments)


def extract_shell_commands(markdown_text: str) -> list[str]:
    """Model yanitindaki ```bash, ```sh veya ```shell bloklarindan komutlari cikarir."""
    pattern = re.compile(r"```(?:bash|sh|shell)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(markdown_text)

    commands: list[str] = []
    for block in matches:
        lines = [
            line.rstrip()
            for line in block.strip().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            continue
        if len(lines) == 1:
            commands.append(lines[0].strip())
        else:
            commands.append("\n".join(lines))
    return commands


def strip_internal_blocks(markdown_text: str) -> str:
    """Ekranda kullaniciya gosterilmemesi gereken arka plan not, web arama ve secops bloklarini temizler."""
    cleaned = re.sub(
        r"```(?:save-note|update-note|delete-note|export-note|web-search|intel-lookup|secops-action)\s*\n.*?(?:```|$)",
        "",
        markdown_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return cleaned.strip()


def extract_intel_queries(markdown_text: str) -> list[str]:
    """Model yanitindaki ```intel-lookup bloklarindan hedef IP veya log metnini ayiklar."""
    pattern = re.compile(r"```intel-lookup\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
    targets: list[str] = []
    for block in pattern.findall(markdown_text):
        clean = block.strip()
        if clean:
            targets.append(clean)
    return targets


def extract_secops_actions(markdown_text: str) -> list[str]:
    """Model yanitindaki ```secops-action bloklarindan (baseline, diff, score) komutlarini ayiklar."""
    pattern = re.compile(r"```secops-action\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
    actions: list[str] = []
    for block in pattern.findall(markdown_text):
        for line in block.strip().splitlines():
            act = line.strip().lower()
            if act in ("baseline", "diff", "score", "harden"):
                actions.append(act)
    return actions


def extract_web_searches(markdown_text: str) -> list[str]:
    """Model yanitindaki ```web-search bloklarindan sorgulari ayiklar."""
    pattern = re.compile(r"```web-search\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
    queries: list[str] = []
    for block in pattern.findall(markdown_text):
        for line in block.strip().splitlines():
            clean = line.strip()
            if not clean:
                continue
            if clean.lower().startswith("sorgu:") or clean.lower().startswith("query:"):
                q = clean.split(":", 1)[1].strip()
                if q:
                    queries.append(q)
            else:
                queries.append(clean)
    return queries


def extract_note_actions(markdown_text: str) -> list[dict[str, str]]:
    """Model yanitindaki update-note, delete-note ve export-note bloklarini ayiklar."""
    actions: list[dict[str, str]] = []

    for action_type in ("update-note", "delete-note", "export-note"):
        pat = re.compile(rf"```{action_type}\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
        for block in pat.findall(markdown_text):
            note_id = ""
            content_lines: list[str] = []
            in_content = False
            for line in block.strip().splitlines():
                low = line.lower().strip()
                if not in_content and low.startswith("id:"):
                    note_id = line.split(":", 1)[1].strip().lstrip("#")
                elif not in_content and low.startswith("icerik:"):
                    in_content = True
                    rest = line.split(":", 1)[1].strip()
                    if rest:
                        content_lines.append(rest)
                else:
                    in_content = True
                    content_lines.append(line)
            if note_id.isdigit():
                actions.append(
                    {
                        "action": action_type,
                        "id": note_id,
                        "content": "\n".join(content_lines).strip(),
                    }
                )
    return actions


def extract_saved_notes(markdown_text: str) -> list[dict[str, str]]:
    """Model yanitindaki ```save-note bloklarini ayiklar."""
    pattern = re.compile(r"```save-note\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(markdown_text)
    notes: list[dict[str, str]] = []

    for block in matches:
        title = "Otomatik Not"
        category = "general"
        tags = ""
        content_lines: list[str] = []
        in_content = False

        for line in block.strip().splitlines():
            low = line.lower().strip()
            if not in_content and low.startswith("baslik:"):
                title = line.split(":", 1)[1].strip()
            elif not in_content and low.startswith("kategori:"):
                category = line.split(":", 1)[1].strip()
            elif not in_content and low.startswith("etiketler:"):
                tags = line.split(":", 1)[1].strip()
            elif not in_content and low.startswith("icerik:"):
                in_content = True
                rest = line.split(":", 1)[1].strip()
                if rest:
                    content_lines.append(rest)
            else:
                in_content = True
                content_lines.append(line)

        body = "\n".join(content_lines).strip()
        if body:
            notes.append(
                {
                    "title": title,
                    "category": category,
                    "tags": tags,
                    "content": body,
                }
            )
    return notes


def is_dangerous_command(cmd: str) -> bool:
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return True
    return False


def prompt_and_execute(cmd: str) -> str | None:
    """
    Kullanicidan e/h onayi alir. 'e' verilirse komutu canli cikti akisiyla (ve sudo destegiyle)
    calistirir ve uretilen ciktiyi dondurur.
    """
    console.print()
    if is_dangerous_command(cmd):
        console.print("[bold red][!] DIKKAT: Bu komut sistem dosyalarina zarar verebilir![/bold red]")

    display_cmd = cmd if "\n" not in cmd else f"\n{cmd}\n"
    try:
        ans = console.input(
            f"[bold yellow][?][/bold yellow] Komut calistirilsin mi: [bold white]{display_cmd}[/bold white] [cyan]\\[e/h][/cyan]: "
        ).strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim][*] Iptal edildi.[/dim]")
        return None

    if ans not in ("e", "evet", "y", "yes"):
        console.print("[dim][*] Komut atlandi.[/dim]")
        return None

    console.print(f"[cyan][*] Calistiriliyor...[/cyan]\n")
    captured_chunks: list[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=None,  # sudo sifre girisi icin terminal stdin'ini miras alir
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        assert proc.stdout is not None
        fd = proc.stdout.fileno()

        while True:
            chunk = os.read(fd, 1024)
            if not chunk:
                break
            text_chunk = chunk.decode("utf-8", errors="replace")
            captured_chunks.append(text_chunk)
            sys.stdout.write(text_chunk)
            sys.stdout.flush()

        return_code = proc.wait(timeout=180)
        full_output = "".join(captured_chunks).strip()

        if not full_output:
            console.print("[dim](Komut tamamlandi, cikti uretmedi)[/dim]")

        if return_code == 0:
            console.print(f"\n[bold green][+][/bold green] Komut tamamlandi (kod: 0)")
        else:
            console.print(f"\n[bold red][-][/bold red] Komut hata kodu dondurdu (kod: {return_code})")

        return full_output or f"(exit code: {return_code})"
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:
            pass
        console.print("\n[yellow][!] Komut kullanici tarafindan durduruldu.[/yellow]")
        return "".join(captured_chunks).strip() or None
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        console.print("[bold red][-][/bold red] Komut zaman asimina ugradi (180sn).")
        return None
    except Exception as exc:
        console.print(f"[bold red][-][/bold red] Calistirma hatasi: {exc}")
        return None


def collect_security_checkup(require_confirm: bool = True) -> str | None:
    """
    Sistemin anlik guvenlik durumunu (dinlenen portlar, ag arayuzleri, firewall,
    son hata/SSH loglari ve kaynak tuketen surecler) toplar.
    """
    if require_confirm:
        try:
            ans = console.input(
                "\n[bold yellow][?][/bold yellow] Sistem guvenlik taramasi (portlar, ag, firewall, son loglar) baslatilsin mi? [cyan]\\[e/h][/cyan]: "
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return None

        if ans not in ("e", "evet", "y", "yes"):
            console.print("[dim][*] Tarama iptal edildi.[/dim]\n")
            return None

    is_windows = platform.system().lower().startswith("win")
    if is_windows:
        checks = [
            ("Ag Arayuzleri (ipconfig)", "ipconfig"),
            ("Dinlenen Portlar (netstat)", "netstat -ano"),
            ("Guvenlik Duvari Durumu", "netsh advfirewall show allprofiles state"),
        ]
    else:
        checks = [
            ("Ag Arayuzleri (ip -br a)", "ip -br a"),
            ("Dinlenen Portlar ve Surecler (ss -tulnp)", "ss -tulnp 2>/dev/null || ss -tuln"),
            ("ARP / Yerel Ag Komsulari (ip neigh)", "ip neigh"),
            (
                "Guvenlik Duvari Servis Durumu",
                "systemctl is-active ufw firewalld iptables nftables 2>/dev/null || true",
            ),
            (
                "Son SSH ve Yetki Loglari",
                "journalctl -u sshd -n 15 --no-pager 2>/dev/null || journalctl -p err -n 15 --no-pager 2>/dev/null || true",
            ),
            (
                "En Cok CPU/Bellek Tuketen Surecler",
                "ps aux --sort=-%cpu | head -n 8",
            ),
        ]

    sections: list[str] = []
    console.print("\n[cyan][*] Sistem telemetrisi toplaniyor...[/cyan]")
    for label, cmd in checks:
        try:
            res = subprocess.run(
                cmd,
                shell=True,
                text=True,
                capture_output=True,
                timeout=15,
            )
            out = ((res.stdout or "") + (res.stderr or "")).strip()
        except Exception as exc:
            out = f"Hata: {exc}"
        sections.append(f"### {label} (`{cmd}`)\n```\n{out or '(bos)'}\n```")

    return "\n\n".join(sections)
