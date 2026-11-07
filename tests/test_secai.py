import os
from pathlib import Path
import tempfile
import unittest
from typer.testing import CliRunner

TEST_DIR = tempfile.mkdtemp(prefix="secai_test_")
os.environ["SECAI_DATA_DIR"] = TEST_DIR

from secai.cli import app  # noqa: E402
from secai.core.baseline import (  # noqa: E402
    calculate_hardening_score,
    compare_with_baseline,
    format_baseline_diff_report,
    format_hardening_report,
    save_baseline,
)
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
from secai.core.intel import (  # noqa: E402
    extract_iocs,
    format_intel_report,
    is_public_ipv4,
)
from secai.core.skills import (  # noqa: E402
    create_custom_skill,
    get_active_skill,
    list_all_skills,
    set_active_skill,
)
from secai.core.voice import (  # noqa: E402
    VOICE_PROFILES,
    clean_text_for_speech,
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

        # Test extract_note_actions with "id: all"
        from secai.core.database import clear_all_notes
        from secai.core.executor import extract_note_actions

        sample_reply = "Notlari siliyorum:\n```delete-note\nid: all\n```"
        acts = extract_note_actions(sample_reply)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["action"], "delete-note")
        self.assertEqual(acts[0]["id"], "all")

        # Test clear_all_notes
        deleted = clear_all_notes()
        self.assertGreaterEqual(deleted, 1)
        self.assertEqual(len(list_notes()), 0)

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

    def test_ioc_extraction_and_shodan_intel(self):
        self.assertFalse(is_public_ipv4("127.0.0.1"))
        self.assertFalse(is_public_ipv4("192.168.1.15"))
        self.assertFalse(is_public_ipv4("10.0.0.5"))
        self.assertTrue(is_public_ipv4("1.1.1.1"))

        sample_log = (
            "Failed password for root from 185.220.101.45 port 44322 ssh2 "
            "local 192.168.1.10 CVE-2024-6387 "
            "sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        iocs = extract_iocs(sample_log)
        self.assertEqual(iocs["ips"], ["185.220.101.45"])
        self.assertEqual(iocs["cves"], ["CVE-2024-6387"])
        self.assertEqual(
            iocs["sha256"],
            ["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
        )

        report = format_intel_report(sample_log, max_ips=1)
        self.assertIn("185.220.101.45", report)
        self.assertIn("CVE-2024-6387", report)

    def test_baseline_snapshot_diff_and_hardening_score(self):
        record = save_baseline(label="unit-test-clean")
        self.assertGreater(record["id"], 0)
        self.assertIn("ports", record["snapshot"])

        diff = compare_with_baseline()
        self.assertTrue(diff["has_baseline"])
        diff_md = format_baseline_diff_report(diff)
        self.assertIn("Baseline", diff_md)

        score_res = calculate_hardening_score()
        self.assertGreaterEqual(score_res["score"], 0)
        self.assertLessEqual(score_res["score"], 100)
        self.assertGreater(len(score_res["checks"]), 0)
        score_md = format_hardening_report(score_res)
        self.assertIn("100", score_md)

    def test_voice_speech_cleaner(self):
        self.assertIn("tr-TR-AhmetNeural", VOICE_PROFILES)
        raw_md = (
            "### Port Analizi\n"
            "| Port | Durum |\n| :--- | :--- |\n| 1080 | Acik |\n"
            "**127.0.0.1** uzerinde `secai` guvenli calisiyor.\n"
            "```bash\nss -tulnp\n```"
        )
        cleaned = clean_text_for_speech(raw_md)
        self.assertIn("localhost", cleaned)
        self.assertIn("Sekay", cleaned)
        self.assertNotIn("ss -tulnp", cleaned)

    def test_web_server_endpoints(self):
        from http.server import HTTPServer
        import json
        import threading
        import urllib.request
        from secai.web.server import make_handler

        token = "test-token-xyz"
        server = HTTPServer(("127.0.0.1", 0), make_handler(token))
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def req(path, method="GET", data=None):
            url = f"http://127.0.0.1:{port}{path}"
            headers = {"X-SecAI-Token": token}
            body = json.dumps(data).encode("utf-8") if data else None
            r = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(r) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))

        status, data = req("/api/status")
        self.assertEqual(status, 200)
        self.assertIn("version", data)

        status, skills = req("/api/skills")
        self.assertEqual(status, 200)
        self.assertIsInstance(skills, list)

        status, diff = req("/api/baseline/diff")
        self.assertEqual(status, 200)
        self.assertIn("baseline_label", diff)

        status, score = req("/api/score")
        self.assertEqual(status, 200)
        self.assertIn("score", score)

        # Test /api/profile endpoint and user profile memory
        from secai.core.database import get_memory_context, get_user_profile, set_user_profile

        set_user_profile("Siber guvenlik uzmani ve arastirmaci.")
        self.assertEqual(get_user_profile(), "Siber guvenlik uzmani ve arastirmaci.")
        mem_ctx = get_memory_context()
        self.assertIn("arastirmaci", mem_ctx)

        status, prof_res = req("/api/profile")
        self.assertEqual(status, 200)
        self.assertEqual(prof_res["profile"], "Siber guvenlik uzmani ve arastirmaci.")

        status, post_prof = req("/api/profile", method="POST", data={"profile": "Guncel Profil Bilgisi"})
        self.assertEqual(status, 200)
        self.assertEqual(post_prof["profile"], "Guncel Profil Bilgisi")

        # Test /api/images endpoint and core image helpers
        from secai.core.image import _slugify, get_images_dir, list_generated_images

        self.assertEqual(_slugify("Hacker Cyberpunk Shield 4K!"), "hacker_cyberpunk_shield_4k")
        self.assertTrue(get_images_dir().exists())
        status, img_list = req("/api/images")
        self.assertEqual(status, 200)
        self.assertIsInstance(img_list, list)

        # Test session title determination, update, and /api/sessions/rename
        from secai.core.database import auto_title_session, create_session, determine_chat_title, update_session_title

        self.assertEqual(determine_chat_title("evcil hayvan ve kedi kopek bakimi"), "Evcil Hayvan & Bakım")
        self.assertEqual(determine_chat_title("Sistemimdeki açık portları ve servisleri listele"), "Açık Port Analizi")
        self.assertEqual(determine_chat_title("CIS Linux güvenlik puanını hesapla"), "CIS Güvenlik Skoru")

        test_s_id = "test_rename_sess"
        create_session(test_s_id, "Yeni Sohbet")
        self.assertTrue(update_session_title(test_s_id, "Yeni Özel Başlık"))
        add_chat_message(test_s_id, "user", "iptables ile port engelleme")
        auto_title_session(test_s_id)
        status, rename_res = req("/api/sessions/rename", method="POST", data={"id": test_s_id, "title": "Manuel Başlık"})
        self.assertEqual(status, 200)
        self.assertEqual(rename_res["title"], "Manuel Başlık")

        # Test Corporate PDF Report generation
        from secai.core.pdf_report import generate_note_pdf_report
        pdf_n_id = add_note(title="Denetim Bulgusu", content="## Acik Portlar\n| Port | Servis |\n| 22 | SSH |\n```bash\nnmap -sV localhost\n```\n- Kritik zafiyet yok.", category="secops", tags="audit")
        pdf_file = generate_note_pdf_report(pdf_n_id)
        self.assertTrue(pdf_file.exists())
        self.assertGreater(pdf_file.stat().st_size, 500)

        # Test /api/notes/<id>/pdf endpoint
        req_pdf = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/api/notes/{pdf_n_id}/pdf", headers={"X-SecAI-Token": token})
        with urllib.request.urlopen(req_pdf) as resp_pdf:
            self.assertEqual(resp_pdf.status, 200)
            self.assertEqual(resp_pdf.headers.get("Content-Type"), "application/pdf")
            self.assertGreater(len(resp_pdf.read()), 500)

        # Test /api/models with new provider fields
        status, models_res = req("/api/models")
        self.assertEqual(status, 200)
        self.assertIn("groq_models", models_res)
        self.assertIn("deepseek_models", models_res)
        self.assertIn("openrouter_models", models_res)

        # Test /api/settings/keys GET & POST
        status, keys_post = req("/api/settings/keys", method="POST", data={"groq_api_key": "gsk_test123", "virustotal_api_key": "vt_test123"})
        self.assertEqual(status, 200)
        status, keys_get = req("/api/settings/keys")
        self.assertEqual(status, 200)
        self.assertEqual(keys_get["groq_api_key"], "gsk_test123")
        self.assertEqual(keys_get["virustotal_api_key"], "vt_test123")

        server.shutdown()
        server.server_close()

    def test_multi_provider_llm_config(self):
        from secai.config import get_active_llm_info, save_settings

        save_settings({"provider": "groq", "groq_api_key": "gsk_unit_test", "groq_model": "openai/gpt-oss-120b"})
        info = get_active_llm_info()
        self.assertEqual(info["provider"], "groq")
        self.assertEqual(info["model"], "openai/gpt-oss-120b")
        self.assertEqual(info["api_key"], "gsk_unit_test")

        save_settings({"provider": "deepseek", "deepseek_api_key": "sk_ds_test", "deepseek_model": "deepseek-reasoner"})
        info_ds = get_active_llm_info()
        self.assertEqual(info_ds["provider"], "deepseek")
        self.assertEqual(info_ds["model"], "deepseek-reasoner")

        save_settings({"provider": "openrouter", "openrouter_api_key": "sk-or-test", "openrouter_model": "meta-llama/llama-3.3-70b-instruct:free"})
        info_or = get_active_llm_info()
        self.assertEqual(info_or["provider"], "openrouter")

    def test_threat_intel_virustotal_and_abuseipdb(self):
        from unittest.mock import MagicMock, patch
        from secai.core.intel import enrich_abuseipdb, enrich_virustotal

        # Without keys, returns None safely
        self.assertIsNone(enrich_virustotal("8.8.8.8", api_key=""))
        self.assertIsNone(enrich_abuseipdb("8.8.8.8", api_key=""))

        # With mock response for VT
        mock_vt_resp = MagicMock()
        mock_vt_resp.status_code = 200
        mock_vt_resp.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 5, "suspicious": 1, "undetected": 10, "harmless": 60},
                    "reputation": -15,
                }
            }
        }
        with patch("requests.get", return_value=mock_vt_resp):
            res = enrich_virustotal("1.2.3.4", api_key="mock_vt_key")
            self.assertIsNotNone(res)
            self.assertEqual(res["malicious"], 5)
            self.assertTrue(res["is_dangerous"])

        # With mock response for AbuseIPDB
        mock_abuse_resp = MagicMock()
        mock_abuse_resp.status_code = 200
        mock_abuse_resp.json.return_value = {
            "data": {
                "abuseConfidenceScore": 85,
                "totalReports": 42,
                "countryCode": "RU",
                "isp": "Evil ISP",
                "isWhitelisted": False,
                "lastReportedAt": "2026-11-06T10:00:00Z",
            }
        }
        with patch("requests.get", return_value=mock_abuse_resp):
            res = enrich_abuseipdb("185.220.101.5", api_key="mock_abuse_key")
            self.assertIsNotNone(res)
            self.assertEqual(res["abuse_score"], 85)
            self.assertEqual(res["risk"], "KRITIK")

    def test_command_dispatcher_and_web_router(self):
        from secai.commands.dispatcher import CommandDispatcher
        from secai.web.router import Router

        # Test Web Router registration and match
        router = Router()

        @router.get("/api/test/{item_id}/info")
        def dummy_get(handler, item_id: str):
            return f"item_{item_id}"

        fn, params = router.match("GET", "/api/test/42/info")
        self.assertIsNotNone(fn)
        self.assertEqual(params.get("item_id"), "42")
        self.assertEqual(fn(None, **params), "item_42")

        # Non-matching route returns None
        fn_miss, _ = router.match("GET", "/api/nonexistent")
        self.assertIsNone(fn_miss)

        # Test CommandDispatcher
        dispatcher = CommandDispatcher()
        state = {"session": "test_sess", "should_exit": False}

        # Clear command handled
        handled = dispatcher.dispatch("/clear", state)
        self.assertTrue(handled)

        # Exit command sets flag
        dispatcher.dispatch("/exit", state)
        self.assertTrue(state["should_exit"])

        # Non-command returns False for natural dialogue
        handled_dialogue = dispatcher.dispatch("selam nasilsin", state)
        self.assertFalse(handled_dialogue)


if __name__ == "__main__":
    unittest.main()
