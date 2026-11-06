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
    notes = list_notes()[:limit]
    cases = list_cases()[:limit]

    if not notes and not cases:
        return "Kullanicinin Vaka & Proje Defterinde henuz kayit yok."

    lines: list[str] = ["[KULLANICININ VAKA & PROJE DEFTERI (SQLite)]:"]
    if notes:
        lines.append("Kayitli Notlar / Raporlar:")
        for n in notes:
            short_body = n["content"].replace("\n", " ")[:400]
            lines.append(
                f"  - Not #{n['id']} ({n['created_at']}): '{n['title']}' [kategori: {n['category']}, etiket: {n['tags'] or '-'}] -> Icerik Ozeti: {short_body}"
            )

    if cases:
        lines.append("Cok Adimli Vakalar / Projeler:")
        for c in cases:
            lines.append(
                f"  - Vaka #{c['id']}: '{c['title']}' [kategori: {c['category']}, durum: {c['status']}, kayit: {c['entry_count']}]"
            )

    # Eger kullanici belirli bir #ID sorduysa (orn: #2 veya not 2), o notun tam metnini ekle
    mentioned_ids = {int(m) for m in re.findall(r"(?:#|not\s+|id\s+)(\d+)", user_query.lower())}
    for mid in mentioned_ids:
        detail = get_note(mid)
        if detail:
            lines.append(f"\n[Not #{mid} Tam Icerigi ('{detail['title']}')]:\n{detail['content'][:1500]}")

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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chat_history (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id.strip(), role.strip(), content, now),
        )
        return cursor.lastrowid


def get_chat_history(session_id: str = "default", limit: int = 40) -> list[dict]:
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
        return cursor.rowcount
