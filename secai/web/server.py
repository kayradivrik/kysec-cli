"""SecAI sade web arayüzü sunucusu.

- Sadece 127.0.0.1 üzerinde dinler.
- Her başlatmada rastgele bir erişim token'ı üretir; tüm /api istekleri
  'X-SecAI-Token' başlığıyla bu token'ı göndermek zorundadır (CSRF koruması).
- Web arayüzü doğrudan sistem komutu ÇALIŞTIRMAZ; öneriler sunulur.
- REST API uç noktaları `Router` dekoratörleri ile modüler olarak yönetilir.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlparse

from secai import __version__
from secai.config import (
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_TTS_VOICE,
    DEEPSEEK_MODELS,
    GROQ_MODELS,
    OPENROUTER_MODELS,
    get_active_llm_info,
    load_settings,
    save_settings,
)
from secai.core.baseline import (
    calculate_hardening_score,
    compare_with_baseline,
    format_baseline_diff_report,
    save_baseline,
)
from secai.core.database import (
    add_chat_message,
    add_note,
    auto_title_session,
    autotitle_unnamed_sessions,
    clear_all_notes,
    clear_chat_history,
    create_session,
    delete_memory,
    delete_note,
    delete_session,
    export_note_markdown,
    get_chat_history,
    get_note,
    get_user_profile,
    list_memories,
    list_notes,
    list_sessions,
    save_memory,
    set_user_profile,
    update_session_title,
)
from secai.core.executor import (
    extract_abuse_lookups,
    extract_memory_actions,
    extract_note_actions,
    extract_saved_notes,
    extract_vt_lookups,
    strip_internal_blocks,
)
from secai.core.image import generate_image_data, list_generated_images
from secai.core.intel import (
    enrich_abuseipdb,
    enrich_virustotal,
    format_abuse_report,
    format_intel_report,
    format_vt_report,
)
from secai.core.llm import OllamaConnectionError, stream_chat
from secai.core.pdf_report import generate_note_pdf_report, generate_session_pdf_report
from secai.core.skills import get_active_skill, list_all_skills, set_active_skill
from secai.core.voice import synthesize_speech_bytes, transcribe_voice_bytes
from secai.web.router import Router

STATIC_DIR = Path(__file__).parent / "static"
WEB_SESSION = "web"
MAX_BODY = 64 * 1024

api = Router()


# ============================================================================
# GET API Uç Noktaları
# ============================================================================


@api.get("/api/status")
def handle_get_status(handler, **kwargs):
    import getpass

    info = get_active_llm_info()
    settings = load_settings()
    active_skill = get_active_skill()
    return handler._send_json(
        {
            "version": __version__,
            "user": getpass.getuser(),
            "provider": info["provider_label"],
            "model": info["model"],
            "active_skill": active_skill["name"] if active_skill else None,
            "tts_voice": settings.get("tts_voice", DEFAULT_TTS_VOICE),
            "tts_enabled": bool(settings.get("tts_enabled", False)),
        }
    )


@api.get("/api/models")
def handle_get_models(handler, **kwargs):
    info = get_active_llm_info()
    settings = load_settings()
    ollama_models = []
    try:
        import urllib.request

        req = urllib.request.Request(f"{info['ollama_url']}/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8"))
                ollama_models = [m["name"] for m in data.get("models", [])]
    except Exception:
        pass

    return handler._send_json(
        {
            "active_provider": info["provider"],
            "active_model": info["model"],
            "active_label": info.get("provider_label", info["provider"]),
            "ollama_models": ollama_models or ["qwen2.5-coder:7b", "gemma3:4b"],
            "groq_models": GROQ_MODELS,
            "deepseek_models": DEEPSEEK_MODELS,
            "gemini_models": ["gemini-3-flash-preview", "gemini-3.1-pro-preview"],
            "openrouter_models": OPENROUTER_MODELS,
            "has_groq_key": bool(settings.get("groq_api_key")),
            "has_deepseek_key": bool(settings.get("deepseek_api_key")),
            "has_gemini_key": bool(settings.get("gemini_api_key")),
            "has_openrouter_key": bool(settings.get("openrouter_api_key")),
            "has_vt_key": bool(settings.get("virustotal_api_key")),
            "has_abuse_key": bool(settings.get("abuseipdb_api_key")),
        }
    )


@api.get("/api/skills")
def handle_get_skills(handler, **kwargs):
    return handler._send_json(list_all_skills())


@api.get("/api/images")
def handle_get_images(handler, **kwargs):
    return handler._send_json(list_generated_images())


@api.get("/api/baseline/diff")
def handle_get_baseline_diff(handler, **kwargs):
    return handler._send_json(compare_with_baseline())


@api.get("/api/sessions")
def handle_get_sessions(handler, **kwargs):
    try:
        autotitle_unnamed_sessions()
    except Exception:
        pass
    s_list = list_sessions()
    if not s_list:
        create_session(WEB_SESSION, "Genel Sohbet")
        s_list = list_sessions()
    return handler._send_json(s_list)


@api.get("/api/history")
def handle_get_history(handler, **kwargs):
    query_sess = urlparse(handler.path).query
    sess_id = WEB_SESSION
    if "session=" in query_sess:
        sess_id = query_sess.split("session=")[1].split("&")[0].strip() or WEB_SESSION
    return handler._send_json(get_chat_history(session_id=sess_id, limit=60))


@api.get("/api/memories")
def handle_get_memories(handler, **kwargs):
    return handler._send_json(list_memories())


@api.get("/api/profile")
def handle_get_profile(handler, **kwargs):
    return handler._send_json({"profile": get_user_profile() or ""})


@api.get("/api/settings/keys")
def handle_get_settings_keys(handler, **kwargs):
    s = load_settings()
    return handler._send_json(
        {
            "groq_api_key": s.get("groq_api_key", ""),
            "deepseek_api_key": s.get("deepseek_api_key", ""),
            "gemini_api_key": s.get("gemini_api_key", ""),
            "openrouter_api_key": s.get("openrouter_api_key", ""),
            "virustotal_api_key": s.get("virustotal_api_key", ""),
            "abuseipdb_api_key": s.get("abuseipdb_api_key", ""),
        }
    )


@api.get("/api/notes")
def handle_get_notes(handler, **kwargs):
    rows = list_notes()
    return handler._send_json(
        [
            {
                "id": r["id"],
                "title": r["title"],
                "category": r["category"],
                "tags": r["tags"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    )


@api.get("/api/notes/{id}/pdf")
def handle_get_note_pdf(handler, id: str, **kwargs):
    if not id.isdigit():
        return handler._send_json({"error": "gecersiz id"}, 400)
    try:
        pdf_path = generate_note_pdf_report(int(id))
        pdf_data = pdf_path.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/pdf")
        handler.send_header("Content-Disposition", f'inline; filename="{pdf_path.name}"')
        handler.send_header("Content-Length", str(len(pdf_data)))
        handler.end_headers()
        handler.wfile.write(pdf_data)
    except Exception as e:
        return handler._send_json({"error": str(e)}, 500)


@api.get("/api/notes/{id}")
def handle_get_note_detail(handler, id: str, **kwargs):
    if not id.isdigit():
        return handler._send_json({"error": "gecersiz id"}, 400)
    note = get_note(int(id))
    if not note:
        return handler._send_json({"error": "bulunamadi"}, 404)
    return handler._send_json(dict(note))


@api.get("/api/sessions/{id}/pdf")
def handle_get_session_pdf(handler, id: str, **kwargs):
    try:
        pdf_path = generate_session_pdf_report(id)
        pdf_data = pdf_path.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/pdf")
        handler.send_header("Content-Disposition", f'inline; filename="{pdf_path.name}"')
        handler.send_header("Content-Length", str(len(pdf_data)))
        handler.end_headers()
        handler.wfile.write(pdf_data)
    except Exception as e:
        return handler._send_json({"error": str(e)}, 500)


@api.get("/api/score")
def handle_get_score(handler, **kwargs):
    return handler._send_json(calculate_hardening_score())


# ============================================================================
# POST API Uç Noktaları
# ============================================================================


@api.post("/api/clear")
def handle_post_clear(handler, **kwargs):
    data = handler._read_json()
    s_id = data.get("session", WEB_SESSION)
    clear_chat_history(session_id=s_id)
    return handler._send_json({"ok": True})


@api.post("/api/sessions/new")
def handle_post_session_new(handler, **kwargs):
    data = handler._read_json()
    s_id = data.get("id") or f"chat_{secrets.token_hex(4)}"
    title = data.get("title") or "Yeni Sohbet"
    create_session(s_id, title)
    return handler._send_json({"id": s_id, "title": title})


@api.post("/api/sessions/delete")
def handle_post_session_delete(handler, **kwargs):
    data = handler._read_json()
    s_id = data.get("id")
    if s_id:
        delete_session(s_id)
    return handler._send_json({"ok": True})


@api.post("/api/sessions/rename")
def handle_post_session_rename(handler, **kwargs):
    data = handler._read_json()
    s_id = data.get("id")
    title = data.get("title", "").strip()
    if not s_id or not title:
        return handler._send_json({"error": "id ve title zorunludur"}, 400)
    if update_session_title(s_id, title):
        return handler._send_json({"ok": True, "id": s_id, "title": title})
    return handler._send_json({"error": "oturum bulunamadi"}, 404)


@api.post("/api/memories/delete")
def handle_post_memories_delete(handler, **kwargs):
    data = handler._read_json()
    key = data.get("key")
    if key:
        delete_memory(key)
    return handler._send_json({"ok": True})


@api.post("/api/profile")
def handle_post_profile(handler, **kwargs):
    data = handler._read_json()
    info = data.get("profile", "").strip()
    if info:
        set_user_profile(info)
    return handler._send_json({"ok": True, "profile": get_user_profile() or ""})


@api.post("/api/intel")
def handle_post_intel(handler, **kwargs):
    data = handler._read_json()
    query = data.get("query", "").strip()
    report = format_intel_report(query)
    return handler._send_json({"report": report})


@api.post("/api/intel/vt")
def handle_post_intel_vt(handler, **kwargs):
    data = handler._read_json()
    target = data.get("target", "").strip()
    res = enrich_virustotal(target)
    if not res:
        return handler._send_json(
            {"error": "VirusTotal sorgulanamadı veya kayıt bulunamadı (API anahtarınızı kontrol edin)."}, 400
        )
    return handler._send_json({"ok": True, "data": res})


@api.post("/api/intel/abuse")
def handle_post_intel_abuse(handler, **kwargs):
    data = handler._read_json()
    ip = data.get("ip", "").strip()
    res = enrich_abuseipdb(ip)
    if not res:
        return handler._send_json(
            {"error": "AbuseIPDB sorgulanamadı veya geçersiz IP (API anahtarınızı kontrol edin)."}, 400
        )
    return handler._send_json({"ok": True, "data": res})


@api.post("/api/settings/keys")
def handle_post_settings_keys(handler, **kwargs):
    data = handler._read_json()
    to_save = {}
    for k in (
        "groq_api_key",
        "deepseek_api_key",
        "gemini_api_key",
        "openrouter_api_key",
        "virustotal_api_key",
        "abuseipdb_api_key",
    ):
        if k in data and data[k] is not None:
            to_save[k] = data[k].strip()
    if to_save:
        save_settings(to_save)
    return handler._send_json({"ok": True})


@api.post("/api/baseline/take")
def handle_post_baseline_take(handler, **kwargs):
    data = handler._read_json()
    label = data.get("label", "web-snap")
    rec = save_baseline(label)
    return handler._send_json(rec)


@api.post("/api/skill/set")
def handle_post_skill_set(handler, **kwargs):
    data = handler._read_json()
    name = data.get("name")
    chosen = set_active_skill(name)
    return handler._send_json({"active": chosen["name"] if chosen else None})


@api.post("/api/image/generate")
def handle_post_image_generate(handler, **kwargs):
    data = handler._read_json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return handler._send_json({"error": "prompt bos olamaz"}, 400)
    res = generate_image_data(prompt)
    if not res:
        return handler._send_json({"error": "gorsel olusturulamadi"}, 500)
    return handler._send_json({"ok": True, **res})


@api.post("/api/model/set")
def handle_post_model_set(handler, **kwargs):
    data = handler._read_json()
    provider = data.get("provider")
    model = data.get("model")
    settings = load_settings()
    if provider:
        settings["provider"] = provider
    if model:
        if provider == "gemini":
            settings["gemini_model"] = model
        elif provider == "groq":
            settings["groq_model"] = model
        elif provider == "deepseek":
            settings["deepseek_model"] = model
        elif provider == "openrouter":
            settings["openrouter_model"] = model
        else:
            settings["ollama_model"] = model
    save_settings(settings)
    return handler._send_json({"ok": True, "active": get_active_llm_info()})


@api.post("/api/voice/settings")
def handle_post_voice_settings(handler, **kwargs):
    data = handler._read_json()
    settings = load_settings()
    if "voice" in data:
        settings["tts_voice"] = data["voice"]
    if "enabled" in data:
        settings["tts_enabled"] = bool(data["enabled"])
    save_settings(settings)
    return handler._send_json(
        {
            "ok": True,
            "tts_voice": settings.get("tts_voice", DEFAULT_TTS_VOICE),
            "tts_enabled": bool(settings.get("tts_enabled", False)),
        }
    )


@api.post("/api/tts")
def handle_post_tts(handler, **kwargs):
    data = handler._read_json()
    text = data.get("text", "")
    audio_bytes = synthesize_speech_bytes(text)
    if not audio_bytes:
        return handler._send_json({"error": "ses uretilemedi"}, 500)
    handler.send_response(200)
    handler.send_header("Content-Type", "audio/mpeg")
    handler.send_header("Content-Length", str(len(audio_bytes)))
    handler.end_headers()
    handler.wfile.write(audio_bytes)


@api.post("/api/stt")
def handle_post_stt(handler, **kwargs):
    data = handler._read_json()
    b64_audio = data.get("audio", "")
    mime_type = data.get("mime_type", "audio/webm")
    if not b64_audio:
        return handler._send_json({"error": "ses verisi bos"}, 400)
    try:
        import base64

        raw_bytes = base64.b64decode(b64_audio.split(",")[-1])
        text = transcribe_voice_bytes(raw_bytes, mime_type=mime_type)
        return handler._send_json({"transcript": text})
    except Exception as e:
        return handler._send_json({"error": str(e)}, 500)


@api.post("/api/notes")
def handle_post_notes(handler, **kwargs):
    data = handler._read_json()
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    category = data.get("category", "project")
    tags = data.get("tags", "")
    if not title or not content:
        return handler._send_json({"error": "title ve content zorunlu"}, 400)
    nid = add_note(title=title, content=content, category=category, tags=tags)
    return handler._send_json({"id": nid, "title": title})


@api.post("/api/notes/{id}/delete")
def handle_post_note_delete(handler, id: str, **kwargs):
    if not id.isdigit():
        return handler._send_json({"error": "gecersiz id"}, 400)
    delete_note(int(id))
    return handler._send_json({"ok": True})


@api.post("/api/notes/{id}/markdown")
def handle_post_note_markdown(handler, id: str, **kwargs):
    if not id.isdigit():
        return handler._send_json({"error": "gecersiz id"}, 400)
    try:
        md_path = export_note_markdown(int(id))
        return handler._send_json({"path": str(md_path)})
    except Exception as e:
        return handler._send_json({"error": str(e)}, 400)


@api.post("/api/chat")
def handle_post_chat(handler, **kwargs):
    data = handler._read_json()
    message = str(data.get("message", "")).strip()
    s_id = str(data.get("session", WEB_SESSION)).strip() or WEB_SESSION
    if not message:
        return handler._send_json({"error": "mesaj bos"}, 400)
    return handler._stream_chat(message, s_id)


# ============================================================================
# HTTP İstek İşleyici Fabrikası
# ============================================================================


def make_handler(token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"SecAI/{__version__}"

        def log_message(self, format, *args):
            pass

        def _authorized(self) -> bool:
            return self.headers.get("X-SecAI-Token") == token

        def _send_json(self, data, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length > MAX_BODY:
                    return {}
                raw = self.rfile.read(length).decode("utf-8")
                return json.loads(raw) if raw else {}
            except Exception:
                return {}

        def _serve_static(self, name: str, ctype: str) -> None:
            path = STATIC_DIR / name
            if not path.exists():
                self.send_error(404)
                return
            content = path.read_text(encoding="utf-8")
            if name == "index.html":
                content = content.replace("__SECAI_TOKEN__", token)
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").split(":")[0].lower()
            return host in ("127.0.0.1", "localhost")

        def do_GET(self):
            if not self._host_ok():
                return self.send_error(403)
            path = urlparse(self.path).path

            if path in ("/", "/index.html"):
                return self._serve_static("index.html", "text/html")
            if path == "/app.js":
                return self._serve_static("app.js", "text/javascript")
            if path == "/style.css":
                return self._serve_static("style.css", "text/css")

            if not path.startswith("/api/"):
                return self.send_error(404)
            if not self._authorized():
                return self._send_json({"error": "yetkisiz"}, 401)

            fn, params = api.match("GET", path)
            if fn:
                return fn(self, **params)

            return self._send_json({"error": "bulunamadi"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            if not self._host_ok() or not self._authorized():
                return self._send_json({"error": "yetkisiz"}, 401)

            fn, params = api.match("POST", path)
            if fn:
                return fn(self, **params)

            return self._send_json({"error": "bulunamadi"}, 404)

        def _stream_chat(self, message: str, session_id: str) -> None:
            add_chat_message(session_id=session_id, role="user", content=message)
            try:
                auto_title_session(session_id)
            except Exception:
                pass

            # Slash komutlarını öncelikli karşıla
            raw_cmd = message.strip()
            if raw_cmd.startswith(("/agent", "/ajan", "/skill", "/skills")):
                parts = raw_cmd.split(maxsplit=1)
                arg = parts[1].strip().lower() if len(parts) > 1 else ""
                if arg:
                    if arg in ("default", "standart", "none", "sifirla", "sıfırla", "genel"):
                        set_active_skill(None)
                        reply = "🎯 **Aktif Ajan:** `Standart / Genel Siber Asistan` moduna geçildi."
                    else:
                        chosen = set_active_skill(arg)
                        if chosen:
                            reply = (
                                f"🕵️ **Aktif Ajan Seçildi:** `{chosen['name']}`\n\n"
                                f"**Uzmanlık:** {chosen.get('description', '')}\n\n"
                                f"Ajan talimatları sisteme yüklendi. Artık bu uzmanlık profiliyle çalışıyoruz."
                            )
                        else:
                            all_s = list_all_skills()
                            names = ", ".join(f"`{s['name']}`" for s in all_s)
                            reply = f"❌ `{arg}` isimli ajan bulunamadı.\n\nKullanılabilir Ajanlar: {names} veya `standart`."
                else:
                    active = get_active_skill()
                    all_s = list_all_skills()
                    lines = [
                        "### 🕵️ SecAI Ajanları & Uzmanlık Modları\n",
                        f"**Mevcut Aktif Ajan:** `{active['name'] if active else 'Standart / Genel'}`\n",
                        "| Ajan | Uzmanlık Alanı | Komut |",
                        "| :--- | :--- | :--- |",
                        "| `standart` | Genel Linux ve SecOps Danışmanı | `/agent standart` |",
                    ]
                    for s in all_s:
                        lines.append(f"| `{s['name']}` | {s.get('description', '')} | `/agent {s['name']}` |")
                    lines.append(
                        "\n_İpucu: Sağ üstteki **'Ajan'** butonundan veya sol menüdeki **'Ajanlar'** sekmesinden tek tıkla değiştirebilirsiniz._"
                    )
                    reply = "\n".join(lines)

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(reply.encode("utf-8"))
                add_chat_message(session_id=session_id, role="assistant", content=reply)
                return

            if raw_cmd.startswith(("/image", "/img", "/ciz", "/gorsel", "/görsel")):
                parts = raw_cmd.split(maxsplit=1)
                prompt = parts[1].strip() if len(parts) > 1 else ""
                if not prompt:
                    reply = (
                        "🎨 **SecAI Image Studio**\n\n"
                        "Görsel oluşturmak için komutun yanına bir prompt yazın:\n"
                        "Örnek: `/image neon siber güvenlik kalkanı, dijital sanat`"
                    )
                else:
                    res = generate_image_data(prompt)
                    if res:
                        reply = (
                            f"🎨 **Görsel Başarıyla Oluşturuldu!**\n\n"
                            f"**Prompt:** {prompt}\n\n"
                            f"**Kayıt Yolu:** `{res['path']}`\n\n"
                            f"![{prompt}]({res['b64']})"
                        )
                    else:
                        reply = "❌ Görsel oluşturulamadı. Lütfen tekrar deneyin."

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(reply.encode("utf-8"))
                add_chat_message(session_id=session_id, role="assistant", content=reply)
                return

            if raw_cmd.startswith(("/infomy", "/myinfo", "/kimim")):
                parts = raw_cmd.split(maxsplit=1)
                info = parts[1].strip() if len(parts) > 1 else ""
                if info:
                    set_user_profile(info)
                    reply = (
                        f"👤 **SecAI Kimlik Hafızası Güncellendi (/infomy):**\n\n"
                        f"> {info}\n\n"
                        f"Artık tüm sohbetlerde ve oturumlarda bu profil bilgine göre sana hitap edeceğim ve tercihlerini daima hatırlayacağım!"
                    )
                else:
                    existing = get_user_profile()
                    if existing:
                        reply = (
                            f"👤 **SecAI Tarafından Tanınan Kimlik Bilginiz (/infomy):**\n\n"
                            f"> {existing}\n\n"
                            f"_Profilinizi güncellemek için: `/infomy <yeni bilgileriniz>` yazabilirsiniz._"
                        )
                    else:
                        reply = (
                            f"👤 **Henüz Bir Kimlik Profili Tanımlanmamış:**\n\n"
                            f"SecAI'ın sizi tam olarak tanıması için kendinizle ilgili bilgileri şu komutla yazabilirsiniz:\n"
                            f"```text\n/infomy Adım Kayra, siber güvenlik araştırmacısıyım. Arch Linux ve Python kullanıyorum.\n```"
                        )

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(reply.encode("utf-8"))
                add_chat_message(session_id=session_id, role="assistant", content=reply)
                return

            history = get_chat_history(session_id=session_id, limit=60)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            chunks: list[str] = []
            try:
                for token_text in stream_chat(messages=history):
                    chunks.append(token_text)
                    self.wfile.write(token_text.encode("utf-8"))
                    self.wfile.flush()
            except OllamaConnectionError as err:
                self.wfile.write(f"\n\n**Hata:** {err}".encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError):
                return

            reply = "".join(chunks).strip()
            if not reply:
                return

            add_chat_message(
                session_id=session_id,
                role="assistant",
                content=strip_internal_blocks(reply) or reply,
            )

            for m_act in extract_memory_actions(reply):
                if m_act["action"] == "remember":
                    save_memory(key=m_act["key"], fact=m_act["fact"])
                    try:
                        self.wfile.write(f"\n\n_🧠 Belleğe kaydedildi: {m_act['fact']}_".encode("utf-8"))
                        self.wfile.flush()
                    except Exception:
                        pass
                elif m_act["action"] == "forget":
                    delete_memory(m_act["key"])

            # Doğal dille not silme / güncelleme
            for act in extract_note_actions(reply):
                target_id = act.get("id", "").strip().lower()
                if act["action"] == "delete-note":
                    if target_id in ("all", "tum", "tüm", "hepsi", "*"):
                        del_cnt = clear_all_notes()
                        try:
                            self.wfile.write(f"\n\n_🗑️ Defterdeki tüm notlar silindi ({del_cnt} adet)_\n".encode("utf-8"))
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            pass
                    elif target_id.isdigit():
                        nid = int(target_id)
                        if delete_note(nid):
                            try:
                                self.wfile.write(f"\n\n_🗑️ Not #{nid} silindi_\n".encode("utf-8"))
                                self.wfile.flush()
                            except (BrokenPipeError, ConnectionResetError):
                                pass

            saved = []
            for n in extract_saved_notes(reply):
                nid = add_note(title=n["title"], content=n["content"], category=n["category"], tags=n["tags"])
                saved.append(f"#{nid} {n['title']}")
            if saved:
                try:
                    self.wfile.write(f"\n\n_Deftere kaydedildi: {', '.join(saved)}_".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            for vt_tgt in extract_vt_lookups(reply):
                vt_rep = format_vt_report(vt_tgt)
                try:
                    self.wfile.write(f"\n\n{vt_rep}\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            for ab_ip in extract_abuse_lookups(reply):
                ab_rep = format_abuse_report(ab_ip)
                try:
                    self.wfile.write(f"\n\n{ab_rep}\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

    return Handler


def run_web_server(port: int = 8765, open_browser: bool = True) -> None:
    token = secrets.token_urlsafe(24)
    handler = make_handler(token)

    ThreadingHTTPServer.allow_reuse_address = True
    httpd = None
    target_port = port
    for p in range(port, port + 10):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), handler)
            target_port = p
            break
        except OSError as e:
            if e.errno in (98, 48):
                continue
            raise

    if not httpd:
        print(f"[!] 127.0.0.1 üzerinde {port}-{port+9} aralığındaki portlar dolu.")
        return

    url = f"http://127.0.0.1:{target_port}/"
    print(f"[+] SecAI web arayüzü: {url}  (durdurmak için Ctrl+C)")

    if open_browser:
        try:
            import webbrowser

            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Web arayüzü durduruldu.")
    finally:
        httpd.server_close()
