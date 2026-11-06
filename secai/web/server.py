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
from secai.config import get_active_llm_info
from secai.core.baseline import calculate_hardening_score
from secai.core.database import (
    add_chat_message,
    add_note,
    clear_chat_history,
    get_chat_history,
    get_note,
    list_notes,
)
from secai.core.executor import extract_saved_notes, strip_internal_blocks
from secai.core.llm import OllamaConnectionError, stream_chat

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
                return self._send_json(
                    {"version": __version__, "provider": info["provider_label"], "model": info["model"]}
                )

            if path == "/api/history":
                return self._send_json(get_chat_history(session_id=WEB_SESSION, limit=40))

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
                raw_id = path.rsplit("/", 1)[-1]
                if not raw_id.isdigit():
                    return self._send_json({"error": "gecersiz id"}, 400)
                note = get_note(int(raw_id))
                if not note:
                    return self._send_json({"error": "bulunamadi"}, 404)
                return self._send_json(dict(note))

            if path == "/api/score":
                return self._send_json(calculate_hardening_score())

            return self._send_json({"error": "bulunamadi"}, 404)

        # ---------- POST ----------
        def do_POST(self):
            path = urlparse(self.path).path
            if not self._host_ok() or not self._authorized():
                return self._send_json({"error": "yetkisiz"}, 401)

            if path == "/api/clear":
                clear_chat_history(session_id=WEB_SESSION)
                return self._send_json({"ok": True})

            if path == "/api/chat":
                data = self._read_json()
                message = str(data.get("message", "")).strip()
                if not message:
                    return self._send_json({"error": "mesaj bos"}, 400)
                return self._stream_chat(message)

            return self._send_json({"error": "bulunamadi"}, 404)

        def _stream_chat(self, message: str) -> None:
            add_chat_message(session_id=WEB_SESSION, role="user", content=message)
            history = get_chat_history(session_id=WEB_SESSION, limit=40)

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
                session_id=WEB_SESSION,
                role="assistant",
                content=strip_internal_blocks(reply) or reply,
            )

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
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(token))
    url = f"http://127.0.0.1:{port}/"
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
