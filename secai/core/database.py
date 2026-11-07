import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from secai.config import get_backup_dir, get_db_path, get_export_dir

VALID_CATEGORIES = ("secops", "audit", "ctf", "project", "idea", "research", "general")
VALID_STATUSES = ("open", "closed", "archived")


@contextmanager
def get_connection():
    db_path = get_db_path()
    is_new = not db_path.exists()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    if is_new and os.name == "posix":
        db_path.chmod(0o600)

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                status TEXT NOT NULL DEFAULT 'open',
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                entry_type TEXT NOT NULL DEFAULT 'note',
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL DEFAULT 'default',
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                fact TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'auto',
                created_at TEXT NOT NULL
            );
            """
        )


def backup_database(target_dir: Optional[Path] = None) -> Path:
    init_db()
    dest_dir = target_dir.expanduser().resolve() if target_dir else get_backup_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = dest_dir / f"casebook_backup_{timestamp}.db"

    with get_connection() as src_conn:
        dest_conn = sqlite3.connect(backup_path)
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()

    if os.name == "posix":
        backup_path.chmod(0o600)

    return backup_path


def list_backups() -> list[Path]:
    b_dir = get_backup_dir()
    if not b_dir.exists():
        return []
    return sorted(b_dir.glob("casebook_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)


def restore_database(backup_file: Path) -> Path:
    target_backup = backup_file.expanduser().resolve()
    if not target_backup.exists() or not target_backup.is_file():
        raise ValueError(f"Yedek dosyasi bulunamadi: {target_backup}")

    db_path = get_db_path()
    src_conn = sqlite3.connect(target_backup)
    dest_conn = sqlite3.connect(db_path)
    try:
        src_conn.backup(dest_conn)
    finally:
        src_conn.close()
        dest_conn.close()

    if os.name == "posix":
        db_path.chmod(0o600)

    return db_path


def add_note(
    title: str,
    content: str,
    category: str = "general",
    tags: str = "",
) -> int:
    init_db()
    clean_category = category.lower().strip()
    if clean_category not in VALID_CATEGORIES:
        clean_category = "general"

    clean_tags = ",".join(t.strip() for t in tags.split(",") if t.strip())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO notes (title, category, content, tags, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title.strip(), clean_category, content.strip(), clean_tags, now),
        )
        return cursor.lastrowid


def update_note(
    note_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    append: bool = False,
) -> bool:
    init_db()
    existing = get_note(note_id)
    if not existing:
        return False

    new_title = title.strip() if title is not None and title.strip() else existing["title"]
    new_category = (
        category.lower().strip()
        if category is not None and category.lower().strip() in VALID_CATEGORIES
        else existing["category"]
    )
    new_tags = (
        ",".join(t.strip() for t in tags.split(",") if t.strip())
        if tags is not None
        else existing["tags"]
    )

    if content is not None and content.strip():
        if append:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_content = f"{existing['content']}\n\n---\n**[Ek - {stamp}]:**\n{content.strip()}"
        else:
            new_content = content.strip()
    else:
        new_content = existing["content"]

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE notes
            SET title = ?, category = ?, content = ?, tags = ?
            WHERE id = ?
            """,
            (new_title, new_category, new_content, new_tags, note_id),
        )
        return cursor.rowcount > 0


def list_notes(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search_query: Optional[str] = None,
) -> list[sqlite3.Row]:
    init_db()
    query = "SELECT * FROM notes WHERE 1=1"
    params: list[str] = []

    if category:
        query += " AND category = ?"
        params.append(category.lower().strip())
    if tag:
        query += " AND (',' || tags || ',') LIKE ?"
        params.append(f"%,{tag.strip()},%")
    if search_query:
        query += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        pattern = f"%{search_query.strip()}%"
        params.extend([pattern, pattern, pattern])

    query += " ORDER BY id DESC"

    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def get_note(note_id: int) -> Optional[sqlite3.Row]:
    init_db()
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()


def delete_note(note_id: int) -> bool:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cursor.rowcount > 0


def clear_all_notes() -> int:
    """Vaka Defterindeki tüm notları siler ve silinen kayıt sayısını döner."""
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM notes")
        return cursor.rowcount


def export_note_markdown(note_id: int, output_path: Optional[Path] = None) -> Path:
    note = get_note(note_id)
    if not note:
        raise ValueError(f"#{note_id} numarali kayit bulunamadi.")

    if output_path:
        target = output_path.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", note["title"].lower()).strip("_")
        target = get_export_dir() / f"note_{note['id']}_{slug or 'export'}.md"

    md_content = (
        f"# {note['title']}\n\n"
        f"- ID: #{note['id']}\n"
        f"- Kategori: {note['category']}\n"
        f"- Etiketler: {note['tags'] or '-'}\n"
        f"- Tarih: {note['created_at']}\n\n"
        f"---\n\n"
        f"{note['content']}\n"
    )
    target.write_text(md_content, encoding="utf-8")
    return target


def get_casebook_context(user_query: str = "", limit: int = 15) -> str:
    """
    Sohbet modelinin kullanicinin Vaka & Proje Defterinden haberdar olmasi icin
    kayitli notlarin ve vakalarin ozetini (veya soruda gecen #ID detayini) uretir.
    """
    init_db()
    all_notes = list_notes()
    all_cases = list_cases()

    if not all_notes and not all_cases:
        return ""

    low_q = user_query.lower()
    is_asking_notes = any(
        kw in low_q
        for kw in ("not", "defter", "vaka", "kayıt", "kayit", "rapor", "hafıza", "hafiza", "proje", "listele", "geçmiş", "gecmis")
    ) or bool(re.search(r"(?:#|not\s+|id\s+)(\d+)", low_q))

    # Semantik / Anahtar Kelime RAG Eşleştiricisi
    query_terms = [
        t for t in re.findall(r"\b\w{3,}\b", low_q)
        if t not in ("nedir", "nasil", "nasıl", "var", "mi", "mı", "mu", "mü", "ile", "icin", "için", "not", "notlar", "bana", "sunu", "bunu", "hakkinda", "hakkında")
    ]
    scored_notes = []
    if query_terms and all_notes:
        for n in all_notes:
            haystack = f"{n['title']} {n['tags']} {n['content']}".lower()
            score = sum(haystack.count(term) for term in query_terms)
            if score > 0:
                scored_notes.append((score, n))
        scored_notes.sort(key=lambda x: x[0], reverse=True)

    # Eğer kullanıcı defteri sormuyorsa ve soruyla alakalı hiçbir not bulunamadıysa bağlamı kirletme
    if not is_asking_notes and not scored_notes:
        return ""

    lines: list[str] = ["[KULLANICININ VAKA & PROJE DEFTERI (SQLite)]:"]
    notes = all_notes[:limit]
    cases = all_cases[:limit]

    if is_asking_notes and notes:
        lines.append("Kayitli Notlar / Raporlar:")
        for n in notes:
            short_body = n["content"].replace("\n", " ")[:250]
            lines.append(
                f"  - Not #{n['id']} ({n['created_at']}): '{n['title']}' [kategori: {n['category']}, etiket: {n['tags'] or '-'}] -> {short_body}"
            )

    if is_asking_notes and cases:
        lines.append("Cok Adimli Vakalar / Projeler:")
        for c in cases:
            lines.append(
                f"  - Vaka #{c['id']}: '{c['title']}' [kategori: {c['category']}, durum: {c['status']}, kayit: {c['entry_count']}]"
            )

    # Eger kullanici belirli bir #ID sorduysa (orn: #2 veya not 2), o notun tam metnini ekle
    mentioned_ids = {int(m) for m in re.findall(r"(?:#|not\s+|id\s+)(\d+)", low_q)}
    for mid in mentioned_ids:
        detail = get_note(mid)
        if detail:
            lines.append(f"\n[Not #{mid} Tam Icerigi ('{detail['title']}')]:\n{detail['content'][:1500]}")

    # Soruyla en alakalı eşleşen notlar varsa tam metinlerini ekle
    for _, rel_n in scored_notes[:3]:
        if rel_n["id"] not in mentioned_ids:
            lines.append(
                f"\n[Soruyla En Alakalı Not #{rel_n['id']} ('{rel_n['title']}')]:\n{rel_n['content'][:1200]}"
            )

    return "\n".join(lines)


def create_case(title: str, category: str = "general", tags: str = "") -> int:
    init_db()
    clean_category = category.lower().strip()
    if clean_category not in VALID_CATEGORIES:
        raise ValueError(
            f"Gecersiz kategori: '{category}'. Gecerli olanlar: {', '.join(VALID_CATEGORIES)}"
        )

    clean_tags = ",".join(t.strip() for t in tags.split(",") if t.strip())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cases (title, category, status, tags, created_at)
            VALUES (?, ?, 'open', ?, ?)
            """,
            (title.strip(), clean_category, clean_tags, now),
        )
        return cursor.lastrowid


def list_cases(
    category: Optional[str] = None, status: Optional[str] = None
) -> list[sqlite3.Row]:
    init_db()
    query = """
        SELECT c.*, COUNT(e.id) AS entry_count
        FROM cases c
        LEFT JOIN entries e ON c.id = e.case_id
        WHERE 1=1
    """
    params: list[str] = []

    if category:
        query += " AND c.category = ?"
        params.append(category.lower().strip())
    if status:
        query += " AND c.status = ?"
        params.append(status.lower().strip())

    query += " GROUP BY c.id ORDER BY c.id DESC"

    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def update_case_status(case_id: int, new_status: str) -> bool:
    init_db()
    clean_status = new_status.lower().strip()
    if clean_status not in VALID_STATUSES:
        raise ValueError(
            f"Gecersiz durum: '{new_status}'. Gecerli olanlar: {', '.join(VALID_STATUSES)}"
        )

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE cases SET status = ? WHERE id = ?",
            (clean_status, case_id),
        )
        return cursor.rowcount > 0


def add_case_entry(case_id: int, content: str, entry_type: str = "note") -> int:
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        case_row = conn.execute(
            "SELECT id FROM cases WHERE id = ?", (case_id,)
        ).fetchone()
        if not case_row:
            raise ValueError(f"#{case_id} numarali vaka/proje bulunamadi.")

        cursor = conn.execute(
            """
            INSERT INTO entries (case_id, entry_type, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (case_id, entry_type.strip().lower(), content.strip(), now),
        )
        return cursor.lastrowid


def get_case_with_entries(
    case_id: int,
) -> tuple[Optional[sqlite3.Row], list[sqlite3.Row]]:
    init_db()
    with get_connection() as conn:
        case_row = conn.execute(
            "SELECT * FROM cases WHERE id = ?", (case_id,)
        ).fetchone()
        if not case_row:
            return None, []
        entries = conn.execute(
            "SELECT * FROM entries WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
        return case_row, entries


def add_chat_message(session_id: str, role: str, content: str) -> int:
    init_db()
    clean_session = session_id.strip() or "default"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chat_history (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (clean_session, role.strip(), content, now),
        )
        msg_id = cursor.lastrowid

        # Oturum tablosunda yoksa olustur veya updated_at guncelle
        first_line = content.strip().splitlines()[0][:45] if content.strip() else "Yeni Sohbet"
        conn.execute(
            """
            INSERT INTO sessions (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (clean_session, first_line, now, now),
        )
        return msg_id


def get_chat_history(session_id: str = "default", limit: int = 100) -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at FROM (
                SELECT id, role, content, created_at
                FROM chat_history
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (session_id.strip(), limit),
        ).fetchall()
        return [
            {"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
            for r in rows
        ]


def clear_chat_history(session_id: str = "default") -> int:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM chat_history WHERE session_id = ?", (session_id.strip(),)
        )
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id.strip(),))
        return cursor.rowcount


def list_sessions() -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COUNT(c.id) AS msg_count
            FROM sessions s
            LEFT JOIN chat_history c ON s.id = c.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "msg_count": r["msg_count"],
            }
            for r in rows
        ]


def create_session(session_id: str, title: str = "Yeni Sohbet") -> str:
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET title = excluded.title
            """,
            (session_id.strip(), title.strip() or "Yeni Sohbet", now, now),
        )
        return session_id.strip()


def delete_session(session_id: str) -> bool:
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id.strip(),))
        c = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id.strip(),))
        return c.rowcount > 0


SESSION_TITLE_PATTERNS = [
    (r"(?i)(ku[sş]|papa[gğ]an|kedi|k[oö]pek|evcil|veteriner)", "Evcil Hayvan & Bakım"),
    (r"(?i)(a[cç][ıi]k\s+port|port\s+analiz|portlar|dinleyen\s+servis)", "Açık Port Analizi"),
    (r"(?i)(cis|hardening|s[ıi]k[ıi]la[sş]t[ıi]rma|g[uü]venlik\s+skor)", "CIS Güvenlik Skoru"),
    (r"(?i)(baseline|sapma|referans|snapshot)", "Sistem Baseline & Sapma"),
    (r"(?i)(firewall|iptables|ufw|nftables)", "Güvenlik Duvarı (Firewall)"),
    (r"(?i)(nmap|a[gğ]\s+tara|ke[sş]if|recon)", "Recon & Ağ Taraması"),
    (r"(?i)(auth|journal|syslog|g[uü]nl[uü]k|systemd\s+log)", "Sistem Log Analizi"),
    (r"(?i)(brute|fail2ban|hydra|parola\s+sald[ıi]r)", "Brute-Force & Koruma"),
    (r"(?i)(ctf|privilege|yetki\s+y[uü]kselt|suid|gtfobins)", "CTF & Yetki Yükseltme"),
    (r"(?i)(socket|soket|tcp|udp|a[gğ]\s+program)", "Soket Programlama"),
    (r"(?i)(python|script|kodlama|algoritma)", "Python & Kodlama"),
    (r"(?i)(g[oö]rsel|resim|[cç]iz|image|wallpaper)", "Görsel Üretimi"),
    (r"(?i)(kimlik|infomy|profil|ben\s+kimim)", "Profil & Kimlik Hafızası"),
    (r"(?i)(shodan|virustotal|abuseipdb|ioc|tehdit)", "Tehdit İstihbaratı"),
    (r"(?i)(ssh|anahtar|key|yetkilendirme)", "SSH & Güvenlik"),
    (r"(?i)(docker|container|podman|k8s)", "Konteyner Güvenliği"),
    (r"(?i)(vaka|casebook|olay\s+m[uü]dahale)", "Vaka Defteri"),
]

SESSION_TITLE_STOPS = {
    "bana", "bir", "bu", "şu", "o", "ve", "ile", "için", "hakkında", "nasıl", "nedir",
    "ne", "nerede", "kim", "hangi", "sence", "lütfen", "yardım", "et", "eder", "misin",
    "mısın", "musun", "müsün", "yap", "yapabilir", "misiniz", "istiyorum", "alacağım",
    "yarın", "bugün", "merhaba", "selam", "hey", "günaydın", "iyi", "akşamlar", "teşekkürler",
    "sağol", "nasılsın", "naber", "acaba", "şöyle", "böyle", "diye", "gibi", "kadar", "ona",
    "aylık", "var", "yok", "olur", "mu", "mü", "mı", "mi", "daha", "en", "çok", "az"
}


def determine_chat_title(message: str) -> str:
    """Kullanıcının mesajını analiz ederek anlamlı ve özgün bir sohbet başlığı belirler."""
    raw = message.strip()
    if not raw:
        return "Yeni Sohbet"

    if raw.startswith(("/image", "/img", "/ciz", "/gorsel", "/görsel")):
        p = raw.split(maxsplit=1)[1] if " " in raw else ""
        return f"🎨 {p[:22].strip().title()}" if p else "🎨 Görsel Üretimi"
    if raw.startswith(("/infomy", "/myinfo", "/kimim")):
        return "👤 Kimlik Tanımlama"
    if raw.startswith(("/agent", "/ajan")):
        p = raw.split(maxsplit=1)[1] if " " in raw else ""
        return f"🕵️ Ajan: {p.title()}" if p else "🕵️ Ajan Seçimi"

    for pat, label in SESSION_TITLE_PATTERNS:
        if re.search(pat, raw):
            return label

    cleaned = re.sub(r"[^\w\s]", " ", raw)
    words = cleaned.split()
    meaningful = [w for w in words if w.lower() not in SESSION_TITLE_STOPS and len(w) > 2]
    if meaningful:
        title = " ".join(meaningful[:3]).title()
        if len(title) > 28:
            title = title[:28].rsplit(" ", 1)[0]
        return title or "Yeni Sohbet"

    fallback = " ".join(words[:3]).title()
    return fallback[:28] or "Yeni Sohbet"


def update_session_title(session_id: str, title: str) -> bool:
    """Sohbet oturumunun başlığını günceller."""
    init_db()
    clean_title = title.strip() or "Yeni Sohbet"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        c = conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (clean_title, now, session_id.strip()),
        )
        return c.rowcount > 0


def auto_title_session(session_id: str) -> Optional[str]:
    """Bir oturumun ilk kullanıcı mesajını okuyup başlığı otomatik olarak günceller."""
    init_db()
    with get_connection() as conn:
        first_msg = conn.execute(
            "SELECT content FROM chat_history WHERE session_id = ? AND role = 'user' ORDER BY id ASC LIMIT 1",
            (session_id.strip(),),
        ).fetchone()
        if not first_msg or not first_msg["content"]:
            return None

        new_title = determine_chat_title(first_msg["content"])
        if new_title:
            update_session_title(session_id, new_title)
            return new_title
    return None


def autotitle_unnamed_sessions() -> int:
    """Başlığı henüz 'Yeni Sohbet' olan veya boş kalmış tüm geçmiş sohbetleri otomatik isimlendirir."""
    init_db()
    with get_connection() as conn:
        unnamed = conn.execute(
            "SELECT id FROM sessions WHERE title = 'Yeni Sohbet' OR title IS NULL OR title = ''"
        ).fetchall()
        count = 0
        for row in unnamed:
            res = auto_title_session(row["id"])
            if res and res != "Yeni Sohbet":
                count += 1
        return count


# ---------- KISISEL PROFIL & BELLEK (ChatGPT Memory Tarzi) ----------

def set_user_profile(info: str) -> bool:
    """Kullanicinin kim oldugunu, tercihlerini ve tanitimini kalici hafizaya yazar."""
    return save_memory(key="kullanici_kimlik", fact=info.strip(), source="user_profile")


def get_user_profile() -> Optional[str]:
    """Kullanicinin kaydedilmis ozel kimlik ve profil bilgisini dondurur."""
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT fact FROM memories WHERE key = 'kullanici_kimlik'").fetchone()
        return row["fact"] if row else None


def save_memory(key: str, fact: str, source: str = "auto") -> bool:
    init_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO memories (key, fact, source, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET fact = excluded.fact, created_at = excluded.created_at
            """,
            (key.strip().lower(), fact.strip(), source, now),
        )
        return True


def delete_memory(key: str) -> bool:
    init_db()
    with get_connection() as conn:
        c = conn.execute("DELETE FROM memories WHERE key = ? OR id = ?", (key.strip().lower(), key.strip()))
        return c.rowcount > 0


def list_memories() -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM memories ORDER BY id ASC").fetchall()
        return [
            {"id": r["id"], "key": r["key"], "fact": r["fact"], "source": r["source"], "created_at": r["created_at"]}
            for r in rows
        ]


def get_memory_context() -> str:
    """ChatGPT Memory gibi kullanici hakkinda ogrenilen profil/bellek bilgilerini dondurur."""
    mems = list_memories()
    if not mems:
        return ""
    lines = ["[KULLANICI PROFILI VE HATIRLANAN BILGILER (KALICI BELLEK)]:"]
    for m in mems:
        if m["key"] == "kullanici_kimlik":
            lines.insert(1, f"  ★ KULLANICI KİMLİK TANIMI (/infomy): {m['fact']}")
        else:
            lines.append(f"  • {m['fact']} (anahtar: {m['key']})")
    lines.append("Bu bilgileri dogal olarak hatirla ve kullanicinin kimligine/tercihlerine uygun cevap ver.")
    return "\n".join(lines)
