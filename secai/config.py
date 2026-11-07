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
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_DEEPSEEK_MODEL = "deepseek-reasoner"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_TTS_VOICE = "tr-TR-AhmetNeural"

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
]

DEEPSEEK_MODELS = [
    "deepseek-reasoner",
    "deepseek-chat",
]

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
]


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
        "groq_api_key": os.environ.get("GROQ_API_KEY", ""),
        "groq_model": DEFAULT_GROQ_MODEL,
        "deepseek_api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "deepseek_model": DEFAULT_DEEPSEEK_MODEL,
        "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", ""),
        "openrouter_model": DEFAULT_OPENROUTER_MODEL,
        "virustotal_api_key": os.environ.get("VIRUSTOTAL_API_KEY", ""),
        "abuseipdb_api_key": os.environ.get("ABUSEIPDB_API_KEY", ""),
        "ollama_model": DEFAULT_OLLAMA_MODEL,
        "ollama_url": DEFAULT_OLLAMA_URL,
        "tts_enabled": False,
        "tts_voice": DEFAULT_TTS_VOICE,
        "tts_rate": "+8%",
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
    if os.environ.get("GROQ_API_KEY") and not defaults.get("groq_api_key"):
        defaults["groq_api_key"] = os.environ["GROQ_API_KEY"]
    if os.environ.get("DEEPSEEK_API_KEY") and not defaults.get("deepseek_api_key"):
        defaults["deepseek_api_key"] = os.environ["DEEPSEEK_API_KEY"]
    if os.environ.get("OPENROUTER_API_KEY") and not defaults.get("openrouter_api_key"):
        defaults["openrouter_api_key"] = os.environ["OPENROUTER_API_KEY"]

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
    provider = s.get("provider", "ollama")

    gemini_key = s.get("gemini_api_key", "").strip()
    groq_key = s.get("groq_api_key", "").strip()
    deepseek_key = s.get("deepseek_api_key", "").strip()
    openrouter_key = s.get("openrouter_api_key", "").strip()

    if provider == "groq" and groq_key:
        return {
            "provider": "groq",
            "provider_label": "Groq LPU (Ultra Hızlı)",
            "model": s.get("groq_model", DEFAULT_GROQ_MODEL),
            "api_key": groq_key,
            "ollama_url": s.get("ollama_url", DEFAULT_OLLAMA_URL),
        }
    if provider == "deepseek" and deepseek_key:
        return {
            "provider": "deepseek",
            "provider_label": "DeepSeek R1 / V3 Reasoning",
            "model": s.get("deepseek_model", DEFAULT_DEEPSEEK_MODEL),
            "api_key": deepseek_key,
            "ollama_url": s.get("ollama_url", DEFAULT_OLLAMA_URL),
        }
    if provider == "openrouter" and openrouter_key:
        return {
            "provider": "openrouter",
            "provider_label": "OpenRouter Universal",
            "model": s.get("openrouter_model", DEFAULT_OPENROUTER_MODEL),
            "api_key": openrouter_key,
            "ollama_url": s.get("ollama_url", DEFAULT_OLLAMA_URL),
        }
    if provider == "gemini" and gemini_key:
        return {
            "provider": "gemini",
            "provider_label": "Google Gemini API",
            "model": s.get("gemini_model", DEFAULT_GEMINI_MODEL),
            "api_key": gemini_key,
            "ollama_url": s.get("ollama_url", DEFAULT_OLLAMA_URL),
        }

    return {
        "provider": "ollama",
        "provider_label": "Local Ollama (RTX 4050)",
        "model": s.get("ollama_model", DEFAULT_OLLAMA_MODEL),
        "api_key": gemini_key or groq_key or deepseek_key or openrouter_key,
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
