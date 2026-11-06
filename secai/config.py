import os
import platform
from pathlib import Path
import typer

APP_NAME = "secai"


def get_data_dir() -> Path:
    """
    İşletim sistemine uygun veri dizinini döndürür:
    - Linux: ~/.local/share/secai
    - Windows: C:\\Users\\<user>\\AppData\\Roaming\\secai
    """
    # Özel bir dizin ortam değişkeni ile tanımlandıysa onu kullan (test/taşınabilirlik için)
    custom_dir = os.environ.get("SECAI_DATA_DIR")
    if custom_dir:
        data_dir = Path(custom_dir).expanduser().resolve()
    else:
        data_dir = Path(typer.get_app_dir(APP_NAME))

    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        # POSIX (Linux/macOS) sistemlerde sadece dosya sahibine okuma/yazma/çalıştırma izni ver (chmod 700)
        if os.name == "posix":
            data_dir.chmod(0o700)

    return data_dir


def get_db_path() -> Path:
    """SQLite veritabanı dosyasının tam yolunu döndürür."""
    return get_data_dir() / "casebook.db"


def get_system_info() -> dict:
    """Çalışma ortamı bilgilerini döndürür."""
    return {
        "os": f"{platform.system()} ({platform.release()})",
        "python": platform.python_version(),
        "data_dir": str(get_data_dir()),
        "db_path": str(get_db_path()),
    }

