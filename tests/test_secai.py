import os
from pathlib import Path
import tempfile
import unittest
from typer.testing import CliRunner

TEST_DIR = tempfile.mkdtemp(prefix="secai_test_")
os.environ["SECAI_DATA_DIR"] = TEST_DIR

from secai.cli import app  # noqa: E402
from secai.core.database import (  # noqa: E402
    add_chat_message,
    add_note,
    backup_database,
    clear_chat_history,
    create_case,
    export_note_markdown,
    get_casebook_context,
    get_chat_history,
    get_note,
    list_backups,
    list_notes,
    restore_database,
    update_note,
)
from secai.core.executor import (  # noqa: E402
    collect_security_checkup,
    extract_shell_commands,
    is_dangerous_command,
)
from secai.core.skills import (  # noqa: E402
    create_custom_skill,
    get_active_skill,
    list_all_skills,
    set_active_skill,
)


class SecAITestSuite(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_note_crud_edit_and_export(self):
        note_id = add_note(
            title="Test Guvenlik Notu",
            content="## Risk: Yuksek\nTest icerigi.",
            category="secops",
            tags="test,ssh",
        )
        self.assertGreater(note_id, 0)

        # Append test
        updated = update_note(note_id, content="Ek bulgu: Port 2222", append=True)
        self.assertTrue(updated)

        note = get_note(note_id)
        self.assertIsNotNone(note)
        self.assertIn("Port 2222", note["content"])

        # Casebook context injection test
        ctx = get_casebook_context(user_query=f"#{note_id} numarali notta ne var?")
        self.assertIn("Test Guvenlik Notu", ctx)
        self.assertIn("Port 2222", ctx)

        results = list_notes(category="secops", search_query="Yuksek")
        self.assertTrue(any(r["id"] == note_id for r in results))

        md_path = export_note_markdown(note_id)
        self.assertTrue(md_path.exists())
        self.assertIn("Test Guvenlik Notu", md_path.read_text(encoding="utf-8"))

    def test_chat_history_memory(self):
        clear_chat_history("test_session")
        add_chat_message("test_session", "user", "Merhaba, iptables kurali nedir?")
        add_chat_message("test_session", "assistant", "iptables -A INPUT -s 1.2.3.4 -j DROP")

        history = get_chat_history("test_session")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_cli_commands_backup_and_restore(self):
        res_add = self.runner.invoke(
            app,
            ["note", "add", "Proje Fikri", "Otonom analiz modulu", "-c", "project", "-t", "ai"],
        )
        self.assertEqual(res_add.exit_code, 0)

        backup_file = backup_database()
        self.assertTrue(Path(backup_file).exists())
        self.assertGreaterEqual(len(list_backups()), 1)

        restored_db = restore_database(backup_file)
        self.assertTrue(restored_db.exists())

        res_list = self.runner.invoke(app, ["note", "list", "-c", "project"])
        self.assertEqual(res_list.exit_code, 0)
        self.assertIn("Proje Fikri", res_list.stdout)

        case_id = create_case("CTF Test", category="ctf", tags="linux")
        self.assertGreater(case_id, 0)

    def test_command_extraction_safety_and_checkup(self):
        reply = "Acik portlari gormek icin:\n```bash\nss -tuln\n```"
        cmds = extract_shell_commands(reply)
        self.assertEqual(cmds, ["ss -tuln"])
        self.assertFalse(is_dangerous_command("ss -tuln"))
        self.assertTrue(is_dangerous_command("rm -rf /tmp/test"))

        telemetry = collect_security_checkup(require_confirm=False)
        self.assertIsNotNone(telemetry)
        self.assertIn("```", telemetry)

    def test_skills_system(self):
        skills = list_all_skills()
        names = [s["name"] for s in skills]
        self.assertIn("recon", names)
        self.assertIn("hardening", names)

        custom_path = create_custom_skill(
            name="web-audit",
            description="OWASP Top 10 web analiz uzmani",
            instructions="Web uygulamalarinda SQLi, XSS ve IDOR ara.",
        )
        self.assertTrue(custom_path.exists())

        set_active_skill("web-audit")
        active = get_active_skill()
        self.assertIsNotNone(active)
        self.assertEqual(active["name"], "web-audit")
        set_active_skill(None)
        self.assertIsNone(get_active_skill())


if __name__ == "__main__":
    unittest.main()
