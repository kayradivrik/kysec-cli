import getpass
import json
import os
import platform
import socket
from pathlib import Path
import typer

APP_NAME = "secai"
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("SECAI_MODEL", "qwen2.5-coder:7b")
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"


def get_data_dir() -> Path:
    custom_dir = os.environ.get("SECAI_DATA_DIR")
    if custom_dir:
        data_dir = Path(custom_dir).expanduser().resolve()
    else:
        data_dir = Path(typer.get_app_dir(APP_NAME))

    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            data_dir.chmod(0o700)

    return data_dir


def get_db_path() -> Path:
    return get_data_dir() / "casebook.db"


def get_settings_path() -> Path:
    return get_data_dir() / "settings.json"


def get_backup_dir() -> Path:
    backup_dir = get_data_dir() / "backups"
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            backup_dir.chmod(0o700)
    return backup_dir


def get_export_dir() -> Path:
    export_dir = get_data_dir() / "exports"
    if not export_dir.exists():
        export_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            export_dir.chmod(0o700)
    return export_dir


def load_settings() -> dict:
    path = get_settings_path()
    defaults = {
        "provider": "ollama",
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "gemini_model": DEFAULT_GEMINI_MODEL,
        "ollama_model": DEFAULT_OLLAMA_MODEL,
        "ollama_url": DEFAULT_OLLAMA_URL,
    }
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            defaults.update(saved)
        except Exception:
            pass

    # Eski 2.5 model adlari kaldiysa otomatik gemini-3-flash-preview'a yukselt
    if defaults.get("gemini_model") in ("gemini-2.5-flash", "gemini-2.5-pro"):
        defaults["gemini_model"] = DEFAULT_GEMINI_MODEL

    if os.environ.get("GEMINI_API_KEY") and not defaults.get("gemini_api_key"):
        defaults["gemini_api_key"] = os.environ["GEMINI_API_KEY"]

    return defaults


def save_settings(new_settings: dict) -> None:
    current = load_settings()
    current.update(new_settings)
    path = get_settings_path()
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    if os.name == "posix":
        path.chmod(0o600)


def get_active_llm_info() -> dict:
    s = load_settings()
    has_key = bool(s.get("gemini_api_key", "").strip())
    provider = s.get("provider", "ollama")

    if provider == "gemini" and has_key:
        return {
            "provider": "gemini",
            "provider_label": "Google Gemini API",
            "model": s.get("gemini_model", DEFAULT_GEMINI_MODEL),
            "api_key": s["gemini_api_key"].strip(),
            "ollama_url": s.get("ollama_url", DEFAULT_OLLAMA_URL),
        }
    return {
        "provider": "ollama",
        "provider_label": "Local Ollama",
        "model": s.get("ollama_model", DEFAULT_OLLAMA_MODEL),
        "api_key": s.get("gemini_api_key", "").strip(),
        "ollama_url": s.get("ollama_url", DEFAULT_OLLAMA_URL),
    }


def get_user_host_cwd() -> tuple[str, str]:
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    try:
        host = socket.gethostname()
    except Exception:
        host = "localhost"

    cwd = str(Path.cwd())
    home = str(Path.home())
    if cwd == home:
        cwd_short = "~"
    elif cwd.startswith(home + os.sep):
        cwd_short = "~" + cwd[len(home):]
    else:
        cwd_short = cwd

    return f"{user}@{host}", cwd_short


def get_system_info() -> dict:
    llm_info = get_active_llm_info()
    return {
        "os": f"{platform.system()} ({platform.release()})",
        "python": platform.python_version(),
        "data_dir": str(get_data_dir()),
        "db_path": str(get_db_path()),
        "backup_dir": str(get_backup_dir()),
        "provider": llm_info["provider_label"],
        "ollama_url": llm_info["ollama_url"],
        "model": llm_info["model"],
    }


DEFAULT_MODEL = DEFAULT_OLLAMA_MODEL
