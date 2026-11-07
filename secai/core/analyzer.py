"""SecAI Güvenli Dosya & Sistem Komutu Analiz Modülü.

Büyük log dosyalarını ilk ve son kritik bloklara bölen (chunking) güvenli mekanizma ve
sistem komutlarını alt süreçte (subprocess) çalıştırıp analiz için hazırlayan katman.
"""

import os
from pathlib import Path
import subprocess
from typing import Optional, Tuple

from secai.core.prompts import COMMAND_ANALYSIS_TEMPLATE, FILE_ANALYSIS_TEMPLATE


def format_bytes(size: int) -> str:
    """Bayt boyutunu insan okunabilir formata dönüştürür."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def safe_chunk_content(
    text: str,
    max_chars: int = 36000,
    head_chars: int = 14000,
    tail_chars: int = 20000,
) -> str:
    """
    Büyük log/çıktı metinlerini güvenli bir şekilde ilk (başlık/konfigürasyon)
    ve son (güncel hatalar/saldırılar) blokları alarak böler (chunking).
    """
    total_len = len(text)
    if total_len <= max_chars:
        return text

    head = text[:head_chars]
    tail = text[-tail_chars:]
    skipped_chars = total_len - (head_chars + tail_chars)
    skipped_lines = text[head_chars:-tail_chars].count("\n")

    separator = (
        f"\n\n[... DİKKAT: Dosya çok büyük ({format_bytes(total_len)} / {total_len} karakter). "
        f"Kritik başlangıç ({format_bytes(head_chars)}) ve en güncel son ({format_bytes(tail_chars)}) "
        f"blokları alındı. Ortadaki {skipped_chars} karakter (~{skipped_lines} satır) atlandı ...]\n\n"
    )
    return f"{head}{separator}{tail}"


def read_and_prepare_file_for_analysis(file_path_str: str) -> Tuple[bool, str]:
    """
    Verilen dosya yolunu doğrular, okur, chunking uygular ve analiz promptunu oluşturur.
    Başarılıysa (True, hazir_prompt), hata durumunda (False, hata_mesaji) döner.
    """
    raw_path = file_path_str.strip().strip("'\"")
    if not raw_path:
        return False, "Dosya yolu belirtilmedi. Örnek: `/analyze auth.log`"

    path = Path(raw_path).expanduser().resolve()

    if not path.exists():
        return False, f"Dosya bulunamadı: [cyan]{path}[/cyan]"

    if path.is_dir():
        return False, f"Belirtilen yol bir dizindir, dosya değildir: [cyan]{path}[/cyan]"

    try:
        file_stat = path.stat()
        file_size = file_stat.st_size
    except OSError as err:
        return False, f"Dosya bilgileri okunamadı ({path}): {err}"

    try:
        # Metin dosyalarını utf-8 (replace ile hatasız) oku
        content = path.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        return False, f"Yetki hatası: [cyan]{path}[/cyan] dosyasını okumak için okuma izniniz yok (sudo gerekebilir)."
    except OSError as err:
        return False, f"Dosya okunurken sistem hatası oluştu ({path}): {err}"

    if not content.strip():
        return False, f"Dosya boş: [cyan]{path}[/cyan]"

    chunked = safe_chunk_content(content)
    formatted_prompt = FILE_ANALYSIS_TEMPLATE.format(
        file_path=str(path),
        file_size=format_bytes(file_size),
        content=chunked,
    )
    return True, formatted_prompt


def run_command_for_analysis(cmd_str: str, timeout: int = 30) -> Tuple[bool, str]:
    """
    Verilen kabuk komutunu güvenli alt süreçte (subprocess) çalıştırır, çıktıyı yakalar
    ve analiz promptunu oluşturur.
    """
    clean_cmd = cmd_str.strip()
    if not clean_cmd:
        return False, "Çalıştırılacak komut belirtilmedi. Örnek: `/run ss -tulnp`"

    try:
        proc = subprocess.run(
            clean_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined_output = proc.stdout
        if proc.stderr:
            if combined_output:
                combined_output += f"\n[STDERR]:\n{proc.stderr}"
            else:
                combined_output = proc.stderr

        if not combined_output.strip():
            combined_output = "[Komut başarıyla çalıştı ancak çıktı üretmedi (0 bayt).]"

        chunked = safe_chunk_content(combined_output)
        formatted_prompt = COMMAND_ANALYSIS_TEMPLATE.format(
            command=clean_cmd,
            exit_code=proc.returncode,
            output=chunked,
        )
        return True, formatted_prompt

    except subprocess.TimeoutExpired:
        return False, f"Komut zaman aşımına uğradı ({timeout} saniye): `{clean_cmd}`"
    except PermissionError:
        return False, f"Komutu çalıştırma izni yok: `{clean_cmd}`"
    except Exception as exc:
        return False, f"Komut çalıştırılırken hata: {exc}"

