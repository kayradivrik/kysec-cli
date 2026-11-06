"""
SecAI sade web arayuzu sunucusu.

- Sadece 127.0.0.1 uzerinde dinler.
- Her baslatmada rastgele bir erisim token'i uretir; tum /api istekleri
  'X-SecAI-Token' basligiyla bu token'i gondermek zorundadir (CSRF / yabanci
  sitelerden localhost'a istek atilmasina karsi).
- Web arayuzu sistem komutu CALISTIRMAZ; AI'nin onerdigi komutlar sadece gosterilir.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlparse

from secai import __version__
from secai.config import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_TTS_VOICE,
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
    clear_chat_history,
    create_session,
    delete_memory,
    delete_session,
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
    collect_security_checkup,
    extract_memory_actions,
    extract_saved_notes,
    strip_internal_blocks,
)
from secai.core.image import generate_image_data, list_generated_images
from secai.core.intel import format_intel_report
from secai.core.llm import OllamaConnectionError, stream_chat, stream_generate
from secai.core.skills import get_active_skill, list_all_skills, set_active_skill
from secai.core.voice import (
    VOICE_PROFILES,
    synthesize_speech_bytes,
    transcribe_voice,
    transcribe_voice_bytes,
)

STATIC_DIR = Path(__file__).parent / "static"
WEB_SESSION = "web"
MAX_BODY = 64 * 1024


def make_handler(token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"secai-web/{__version__}"

        def log_message(self, fmt, *args):  # sessiz log
            return

        # ---------- yardimcilar ----------
        def _send_json(self, data, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            return secrets.compare_digest(self.headers.get("X-SecAI-Token", ""), token)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return {}
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
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

        # ---------- GET ----------
        def _host_ok(self) -> bool:
            # DNS rebinding korumasi: sadece localhost Host basliklarini kabul et
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

            if path == "/api/status":
                info = get_active_llm_info()
                settings = load_settings()
                active_skill = get_active_skill()
                import getpass
                return self._send_json(
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

            if path == "/api/models":
                info = get_active_llm_info()
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
                return self._send_json(
                    {
                        "active_provider": info["provider"],
                        "active_model": info["model"],
                        "ollama_models": ollama_models or ["gemma3:4b", "qwen2.5-coder:7b"],
                        "gemini_models": ["gemini-2.5-flash", "gemini-3-flash-preview"],
                        "has_gemini_key": bool(info["api_key"]),
                    }
                )

            if path == "/api/skills":
                return self._send_json(list_all_skills())

            if path == "/api/images":
                return self._send_json(list_generated_images())

            if path == "/api/baseline/diff":
                diff = compare_with_baseline()
                return self._send_json(diff)

            if path == "/api/sessions":
                try:
                    autotitle_unnamed_sessions()
                except Exception:
                    pass
                s_list = list_sessions()
                if not s_list:
                    create_session(WEB_SESSION, "Genel Sohbet")
                    s_list = list_sessions()
                return self._send_json(s_list)

            if path == "/api/history":
                query_sess = urlparse(self.path).query
                sess_id = WEB_SESSION
                if "session=" in query_sess:
                    sess_id = query_sess.split("session=")[1].split("&")[0].strip() or WEB_SESSION
                return self._send_json(get_chat_history(session_id=sess_id, limit=60))

            if path == "/api/memories":
                return self._send_json(list_memories())

            if path == "/api/profile":
                return self._send_json({"profile": get_user_profile() or ""})

            if path == "/api/notes":
                rows = list_notes()
                return self._send_json(
                    [
                        {"id": r["id"], "title": r["title"], "category": r["category"],
                         "tags": r["tags"], "created_at": r["created_at"]}
                        for r in rows
                    ]
                )

            if path.startswith("/api/notes/"):
                if path.endswith("/pdf"):
                    parts = path.strip("/").split("/")
                    if len(parts) >= 3 and parts[2].isdigit():
                        note_id = int(parts[2])
                        from secai.core.pdf_report import generate_note_pdf_report
                        try:
                            pdf_path = generate_note_pdf_report(note_id)
                            pdf_data = pdf_path.read_bytes()
                            self.send_response(200)
                            self.send_header("Content-Type", "application/pdf")
                            self.send_header("Content-Disposition", f'inline; filename="{pdf_path.name}"')
                            self.send_header("Content-Length", str(len(pdf_data)))
                            self.end_headers()
                            self.wfile.write(pdf_data)
                            return
                        except Exception as e:
                            return self._send_json({"error": str(e)}, 500)

                raw_id = path.rsplit("/", 1)[-1]
                if not raw_id.isdigit():
                    return self._send_json({"error": "gecersiz id"}, 400)
                note = get_note(int(raw_id))
                if not note:
                    return self._send_json({"error": "bulunamadi"}, 404)
                return self._send_json(dict(note))

            if path.startswith("/api/sessions/") and path.endswith("/pdf"):
                parts = path.strip("/").split("/")
                if len(parts) >= 3:
                    s_id = parts[2]
                    from secai.core.pdf_report import generate_session_pdf_report
                    try:
                        pdf_path = generate_session_pdf_report(s_id)
                        pdf_data = pdf_path.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/pdf")
                        self.send_header("Content-Disposition", f'inline; filename="{pdf_path.name}"')
                        self.send_header("Content-Length", str(len(pdf_data)))
                        self.end_headers()
                        self.wfile.write(pdf_data)
                        return
                    except Exception as e:
                        return self._send_json({"error": str(e)}, 500)

            if path == "/api/score":
                return self._send_json(calculate_hardening_score())

            return self._send_json({"error": "bulunamadi"}, 404)

        # ---------- POST ----------
        def do_POST(self):
            path = urlparse(self.path).path
            if not self._host_ok() or not self._authorized():
                return self._send_json({"error": "yetkisiz"}, 401)

            if path == "/api/clear":
                data = self._read_json()
                s_id = data.get("session", WEB_SESSION)
                clear_chat_history(session_id=s_id)
                return self._send_json({"ok": True})

            if path == "/api/sessions/new":
                data = self._read_json()
                s_id = data.get("id") or f"chat_{secrets.token_hex(4)}"
                title = data.get("title") or "Yeni Sohbet"
                create_session(s_id, title)
                return self._send_json({"id": s_id, "title": title})

            if path.startswith("/api/sessions/delete"):
                data = self._read_json()
                s_id = data.get("id", "")
                if s_id:
                    delete_session(s_id)
                return self._send_json({"ok": True})

            if path in ("/api/sessions/rename", "/api/session/rename"):
                data = self._read_json()
                s_id = data.get("id") or data.get("session_id", "")
                title = data.get("title", "").strip()
                if not s_id or not title:
                    return self._send_json({"error": "id ve title zorunludur"}, 400)
                ok = update_session_title(s_id, title)
                return self._send_json({"ok": ok, "id": s_id, "title": title})

            if path == "/api/sessions/autotitle":
                data = self._read_json()
                s_id = data.get("id") or data.get("session_id", "")
                if not s_id:
                    return self._send_json({"error": "id zorunludur"}, 400)
                new_title = auto_title_session(s_id)
                return self._send_json({"ok": bool(new_title), "id": s_id, "title": new_title})

            if path.startswith("/api/memories/delete"):
                data = self._read_json()
                key = data.get("key", "")
                if key:
                    delete_memory(key)
                return self._send_json({"ok": True})

            if path == "/api/profile":
                data = self._read_json()
                info = data.get("profile", "").strip()
                if info:
                    set_user_profile(info)
                return self._send_json({"ok": True, "profile": get_user_profile() or ""})

            if path == "/api/intel":
                data = self._read_json()
                query = data.get("query", "").strip()
                report = format_intel_report(query)
                return self._send_json({"report": report})

            if path == "/api/baseline/take":
                data = self._read_json()
                label = data.get("label", "web-snap")
                rec = save_baseline(label)
                return self._send_json(rec)

            if path == "/api/skill/set":
                data = self._read_json()
                name = data.get("name")
                chosen = set_active_skill(name)
                return self._send_json({"active": chosen["name"] if chosen else None})

            if path == "/api/image/generate":
                data = self._read_json()
                prompt = data.get("prompt", "").strip()
                if not prompt:
                    return self._send_json({"error": "prompt bos olamaz"}, 400)
                res = generate_image_data(prompt)
                if not res:
                    return self._send_json({"error": "gorsel olusturulamadi"}, 500)
                return self._send_json({"ok": True, **res})

            if path == "/api/model/set":
                data = self._read_json()
                provider = data.get("provider")
                model = data.get("model")
                settings = load_settings()
                if provider:
                    settings["provider"] = provider
                if model:
                    if provider == "gemini":
                        settings["gemini_model"] = model
                    else:
                        settings["ollama_model"] = model
                save_settings(settings)
                return self._send_json({"ok": True, "active": get_active_llm_info()})

            if path == "/api/voice/settings":
                data = self._read_json()
                settings = load_settings()
                if "voice" in data:
                    settings["tts_voice"] = data["voice"]
                if "enabled" in data:
                    settings["tts_enabled"] = bool(data["enabled"])
                save_settings(settings)
                return self._send_json(
                    {
                        "ok": True,
                        "tts_voice": settings.get("tts_voice", DEFAULT_TTS_VOICE),
                        "tts_enabled": bool(settings.get("tts_enabled", False)),
                    }
                )

            if path == "/api/tts":
                data = self._read_json()
                text = data.get("text", "")
                audio_bytes = synthesize_speech_bytes(text)
                if not audio_bytes:
                    return self._send_json({"error": "ses uretilemedi"}, 500)
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(audio_bytes)))
                self.end_headers()
                self.wfile.write(audio_bytes)
                return

            if path == "/api/stt":
                data = self._read_json()
                b64_audio = data.get("audio", "")
                mime_type = data.get("mime_type", "audio/webm")
                if not b64_audio:
                    return self._send_json({"error": "ses verisi bos"}, 400)
                try:
                    import base64
                    raw_bytes = base64.b64decode(b64_audio.split(",")[-1])
                    text = transcribe_voice_bytes(raw_bytes, mime_type=mime_type)
                    return self._send_json({"transcript": text})
                except Exception as e:
                    return self._send_json({"error": str(e)}, 500)

            if path == "/api/chat":
                data = self._read_json()
                message = str(data.get("message", "")).strip()
                s_id = str(data.get("session", WEB_SESSION)).strip() or WEB_SESSION
                if not message:
                    return self._send_json({"error": "mesaj bos"}, 400)
                return self._stream_chat(message, s_id)

            return self._send_json({"error": "bulunamadi"}, 404)

        def _stream_chat(self, message: str, session_id: str) -> None:
            add_chat_message(session_id=session_id, role="user", content=message)
            try:
                auto_title_session(session_id)
            except Exception:
                pass

            # Slash komutlarini aninda karsila (Ajan / Beceri / Model)
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

            # ChatGPT Memory gibi bellek kaydetme/silme
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

            # Dogal dille "not ekle" istegi geldiyse deftere kaydet
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

    return Handler


def run_web_server(port: int = 8765, open_browser: bool = True) -> None:
    token = secrets.token_urlsafe(24)
    handler = make_handler(token)

    # Port cakismasi onleme (allow_reuse_address ve otomatik bosta port arama)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = None
    target_port = port
    for p in range(port, port + 10):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), handler)
            target_port = p
            break
        except OSError as e:
            if e.errno in (98, 48):  # EADDRINUSE
                continue
            raise

    if not httpd:
        print(f"[!] 127.0.0.1 üzerinde {port}-{port+9} aralığındaki portlar dolu.")
        return

    url = f"http://127.0.0.1:{target_port}/"
    print(f"[+] SecAI web arayuzu: {url}  (durdurmak icin Ctrl+C)")

    if open_browser:
        try:
            import webbrowser

            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Web arayuzu durduruldu.")
    finally:
        httpd.server_close()
