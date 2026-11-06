import asyncio
import base64
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
from typing import Optional
import requests
from rich.console import Console

from secai.config import DEFAULT_GEMINI_MODEL, DEFAULT_TTS_VOICE, load_settings
from secai.core.executor import strip_internal_blocks

console = Console()

VOICE_PROFILES = {
    "tr-TR-AhmetNeural": "Ahmet (Erkek — Tok Siber Asistan Sesi)",
    "tr-TR-EmelNeural": "Emel (Kadin — Net Siber Asistan Sesi)",
}


def clean_text_for_speech(markdown_text: str, max_chars: int = 950) -> str:
    """
    Markdown yanitindaki kod bloklarini, ham tablo cizgilerini ve isaretleri temizleyerek
    dogal ve akici bir Turkce seslendirme metni uretir.
    """
    text = strip_internal_blocks(markdown_text)

    # Bash / kod bloklarini seslendirmede bogmamak icin cikar
    has_code = bool(re.search(r"```.*?```", text, flags=re.DOTALL))
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)

    # Markdown tablo ayirici satirlarini (| :--- |) ve ham tablo satirlarini ayikla
    non_table_lines: list[str] = []
    table_row_summaries: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            if re.match(r"^\|[\s:\-\|]+\|$", stripped):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|") if c.strip()]
            if len(cells) >= 2 and len(table_row_summaries) < 5:
                table_row_summaries.append(", ".join(cells[:3]))
            continue
        non_table_lines.append(stripped)

    if non_table_lines:
        body = " ".join(non_table_lines)
    else:
        body = ". ".join(table_row_summaries)

    # Markdown linklerini [metin](url) -> metin yap
    body = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", body)
    # Baslik, kalinlik, kod tirnagi ve madde isaretlerini temizle
    body = re.sub(r"[#*`_~>]+", " ", body)
    body = re.sub(r"\b127\.0\.0\.1\b", "localhost", body)
    body = re.sub(r"\b0\.0\.0\.0\b", "tüm ağ", body)
    body = re.sub(r"\bsecai\b", "Sekay", body, flags=re.IGNORECASE)
    body = re.sub(r"\s+", " ", body).strip()

    if not body and has_code:
        return "İlgili komutu ekrana hazırladım, onaylarsan çalıştırabilirim."

    if len(body) > max_chars:
        cut = body[:max_chars]
        last_dot = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
        if last_dot > 200:
            body = cut[: last_dot + 1]
        else:
            body = cut + "..."

    return body


async def _synthesize_edge_tts(text: str, out_path: str, voice: str, rate: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(out_path)


def synthesize_speech_bytes(markdown_text: str) -> bytes:
    """Metni Edge Neural TTS ile MP3 baytlarina donusturur (Web UI veya API icin)."""
    clean = clean_text_for_speech(markdown_text)
    if not clean:
        return b""

    settings = load_settings()
    voice = settings.get("tts_voice", DEFAULT_TTS_VOICE)
    rate = settings.get("tts_rate", "+8%")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_mp3 = f.name

    try:
        asyncio.run(_synthesize_edge_tts(clean, tmp_mp3, voice=voice, rate=rate))
        p = Path(tmp_mp3)
        if p.exists():
            return p.read_bytes()
        return b""
    except Exception:
        return b""
    finally:
        try:
            Path(tmp_mp3).unlink(missing_ok=True)
        except Exception:
            pass


def _find_audio_player() -> Optional[list[str]]:
    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet"]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
    if shutil.which("paplay"):
        return ["paplay"]
    return None


def speak_text(markdown_text: str) -> None:
    """Metni dogal Turkce Nöral TTS ile seslendirir (Ctrl+C ile susturulabilir)."""
    clean = clean_text_for_speech(markdown_text)
    if not clean:
        return

    settings = load_settings()
    voice = settings.get("tts_voice", DEFAULT_TTS_VOICE)
    rate = settings.get("tts_rate", "+8%")
    player_cmd = _find_audio_player()
    if not player_cmd:
        console.print("[yellow][!] Ses oynatici (mpv veya ffplay) bulunamadi.[/yellow]")
        return

    tmp_mp3 = ""
    proc: Optional[subprocess.Popen] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_mp3 = f.name

        asyncio.run(_synthesize_edge_tts(clean, tmp_mp3, voice=voice, rate=rate))

        console.print(
            "[bold cyan][*] SecAI konusuyor...[/bold cyan] [dim](Susturmak icin Ctrl+C)[/dim]"
        )
        proc = subprocess.Popen(
            player_cmd + [tmp_mp3],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait()
    except KeyboardInterrupt:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        console.print("[dim][*] Seslendirme durduruldu.[/dim]")
    except Exception as exc:
        console.print(f"[yellow][!] Seslendirme hatasi: {exc}[/yellow]")
    finally:
        if tmp_mp3:
            try:
                Path(tmp_mp3).unlink(missing_ok=True)
            except Exception:
                pass


def _build_recorder_command(wav_path: str) -> Optional[list[str]]:
    if shutil.which("pw-record"):
        return ["pw-record", "--rate=16000", "--channels=1", wav_path]
    if shutil.which("arecord"):
        return ["arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", wav_path]
    if shutil.which("ffmpeg"):
        return [
            "ffmpeg",
            "-y",
            "-loglevel",
            "quiet",
            "-f",
            "pulse",
            "-i",
            "default",
            "-ar",
            "16000",
            "-ac",
            "1",
            wav_path,
        ]
    return None


def record_voice_input() -> Optional[Path]:
    """
    Kullanici ENTER tusuna basana kadar mikrofondan 16kHz WAV ses kaydi alir.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = Path(f.name)

    rec_cmd = _build_recorder_command(str(wav_path))
    if not rec_cmd:
        console.print(
            "[bold red][-][/bold red] Mikrofon kayit araci (pw-record, arecord veya ffmpeg) bulunamadi."
        )
        wav_path.unlink(missing_ok=True)
        return None

    proc: Optional[subprocess.Popen] = None
    try:
        proc = subprocess.Popen(
            rec_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        console.input(
            "\n[bold red][●] MIKROFON DINLENIYOR[/bold red] — Konusmayi bitirmek icin [bold cyan]ENTER[/bold cyan] tusuna basin [dim](iptal: Ctrl+C)[/dim]: "
        )
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim][*] Ses kaydi iptal edildi.[/dim]")
        if proc and proc.poll() is None:
            try:
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        wav_path.unlink(missing_ok=True)
        return None

    if proc and proc.poll() is None:
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass

    if not wav_path.exists() or wav_path.stat().st_size < 1024:
        console.print("[yellow][!] Ses algilanamadi.[/yellow]")
        wav_path.unlink(missing_ok=True)
        return None

    return wav_path


def transcribe_voice_bytes(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """
    Ham ses baytlarini Gemini Native Audio STT motoruyla Turkce metne cevirir.
    Web UI veya harici istemcilerden gelen WebM, WAV, OGG, MP3 formatlarini destekler.
    """
    settings = load_settings()
    api_key = settings.get("gemini_api_key", "").strip()
    if not api_key:
        return ""

    if not audio_bytes:
        return ""

    # Tarayici mime-type standardizasyonu
    clean_mime = mime_type.split(";")[0].strip().lower()
    if not clean_mime or clean_mime == "application/octet-stream":
        clean_mime = "audio/webm"

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    model = settings.get("gemini_model", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": clean_mime, "data": audio_b64}},
                    {
                        "text": (
                            "Bu ses kaydinda kullanicinin soyledigi cumleyi hicbir ek aciklama veya yorum yapmadan "
                            "oldugu gibi Turkce metin olarak yaz. "
                            "(Ipucu: Asistanin adi 'secai', siber guvenlik, port, nmap, linux, Arch terimleri geciyor olabilir. "
                            "Eger kayitta hicbir konusma yoksa sadece BOS yaz.)"
                        )
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        transcript = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
        if transcript.upper() in ("BOS", "BOŞ", "YOK", "."):
            return ""
        return transcript
    except Exception as exc:
        console.print(f"[bold red][-][/bold red] Ses cozumleme hatasi: {exc}")
        return ""


def transcribe_voice(wav_path: Path) -> str:
    """
    Kaydedilen WAV dosyasini Gemini 3 Flash Native Audio STT motoruyla Turkce metne cevirir.
    """
    try:
        audio_bytes = wav_path.read_bytes()
    except Exception:
        return ""
    finally:
        wav_path.unlink(missing_ok=True)
    return transcribe_voice_bytes(audio_bytes, mime_type="audio/wav")

