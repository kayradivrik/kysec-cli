from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from typing import Optional

from secai.core.database import get_connection, init_db

CRITICAL_FILES = (
    "/etc/passwd",
    "/etc/group",
    "/etc/hosts",
    "/etc/resolv.conf",
    "/etc/ssh/sshd_config",
    "/etc/crontab",
)


def _run_quiet(cmd: str) -> str:
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=10,
        )
        return ((res.stdout or "") + (res.stderr or "")).strip()
    except Exception:
        return ""


def _hash_file(filepath: str) -> Optional[str]:
    p = Path(filepath)
    if not p.exists() or not p.is_file():
        return None
    try:
        h = hashlib.sha256()
        h.update(p.read_bytes())
        return h.hexdigest()
    except Exception:
        return None


def collect_system_snapshot() -> dict:
    """
    Sistemin anlik dinlenen portlarini, calisan systemd servislerini, cron gorevlerini
    ve kritik sistem dosyalarinin SHA256 kriptografik ozetlerini toplar.
    """
    is_windows = platform.system().lower().startswith("win")
    ports: set[str] = set()
    services: set[str] = set()
    file_hashes: dict[str, str] = {}

    if is_windows:
        out = _run_quiet("netstat -ano")
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0].upper() in ("TCP", "UDP"):
                ports.add(f"{parts[0].lower()} {parts[1]}")
    else:
        ss_out = _run_quiet("ss -tuln")
        for line in ss_out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 5:
                proto = parts[0].lower()
                local_addr = parts[4]
                ports.add(f"{proto} {local_addr}")

        svc_out = _run_quiet(
            "systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null"
        )
        for line in svc_out.splitlines():
            parts = line.split()
            if parts and parts[0].endswith(".service"):
                services.add(parts[0])

        for fpath in CRITICAL_FILES:
            digest = _hash_file(fpath)
            if digest:
                file_hashes[fpath] = digest

    cron_raw = _run_quiet("crontab -l 2>/dev/null || true")
    cron_lines = [
        line.strip()
        for line in cron_raw.splitlines()
        if line.strip() and not line.strip().startswith("#") and "no crontab" not in line.lower()
    ]

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ports": sorted(ports),
        "services": sorted(services),
        "file_hashes": file_hashes,
        "cron": cron_lines,
    }


def save_baseline(label: str = "default") -> dict:
    """Anlik sistem goruntusunu alir ve SQLite veritabanina kaydeder."""
    init_db()
    snap = collect_system_snapshot()
    now = snap["timestamp"]

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO baselines (label, snapshot_json, created_at)
            VALUES (?, ?, ?)
            """,
            (label.strip() or "default", json.dumps(snap, ensure_ascii=False), now),
        )
        baseline_id = cursor.lastrowid

    return {
        "id": baseline_id,
        "label": label,
        "created_at": now,
        "snapshot": snap,
    }


def get_latest_baseline() -> Optional[dict]:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM baselines ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "label": row["label"],
            "created_at": row["created_at"],
            "snapshot": json.loads(row["snapshot_json"]),
        }


def compare_with_baseline() -> dict:
    """
    Son kaydedilen baseline ile sistemin su anki canli durumunu karsilastirir
    (yeni acilan portlar, kapanan portlar, yeni baslayan servisler, degisen kritik dosyalar).
    """
    base_record = get_latest_baseline()
    if not base_record:
        return {"has_baseline": False}

    old = base_record["snapshot"]
    cur = collect_system_snapshot()

    old_ports = set(old.get("ports", []))
    cur_ports = set(cur.get("ports", []))

    old_services = set(old.get("services", []))
    cur_services = set(cur.get("services", []))

    old_hashes = old.get("file_hashes", {})
    cur_hashes = cur.get("file_hashes", {})

    modified_files: list[str] = []
    for fpath, old_digest in old_hashes.items():
        new_digest = cur_hashes.get(fpath)
        if new_digest and new_digest != old_digest:
            modified_files.append(fpath)

    old_cron = set(old.get("cron", []))
    cur_cron = set(cur.get("cron", []))

    new_ports = sorted(cur_ports - old_ports)
    closed_ports = sorted(old_ports - cur_ports)
    new_services = sorted(cur_services - old_services)
    stopped_services = sorted(old_services - cur_services)
    new_cron = sorted(cur_cron - old_cron)

    has_drift = bool(new_ports or closed_ports or new_services or stopped_services or modified_files or new_cron)

    return {
        "has_baseline": True,
        "baseline_id": base_record["id"],
        "baseline_label": base_record["label"],
        "baseline_time": base_record["created_at"],
        "current_time": cur["timestamp"],
        "has_drift": has_drift,
        "new_ports": new_ports,
        "closed_ports": closed_ports,
        "new_services": new_services,
        "stopped_services": stopped_services,
        "modified_files": modified_files,
        "new_cron": new_cron,
    }


def format_baseline_diff_report(diff: dict) -> str:
    if not diff.get("has_baseline"):
        return (
            "[Baseline Karsilastirmasi]: Henuz alinmis bir sistem referans kaydi (baseline) bulunamadi. "
            "Once `/baseline` komutuyla temiz sistem goruntusu alin."
        )

    lines = [
        f"### Sistem Baseline & Anomali (Drift) Analizi",
        f"- **Referans Kayit:** #{diff['baseline_id']} (`{diff['baseline_label']}` — {diff['baseline_time']})",
        f"- **Kontrol Zamani:** {diff['current_time']}",
        "",
    ]

    if not diff["has_drift"]:
        lines.append(
            "**Durum: TEMIZ (Sifir Sapma)** — Referans kayittan bu yana yeni acilan port, yeni servis, cron degisikligi veya kritik dosya degisimi tespit edilmedi."
        )
        return "\n".join(lines)

    lines.append("| Kategori | Degisim Tipi | Tespit Edilen Detaylar |")
    lines.append("| :--- | :--- | :--- |")

    for p in diff["new_ports"]:
        lines.append(f"| **Ag / Port** | YENI ACILAN PORT (DIKKAT) | `{p}` |")
    for p in diff["closed_ports"]:
        lines.append(f"| Ag / Port | Kapanan Port | `{p}` |")
    for s in diff["new_services"]:
        lines.append(f"| **Systemd Servis** | YENI BASLAYAN SERVIS | `{s}` |")
    for s in diff["stopped_services"]:
        lines.append(f"| Systemd Servis | Duran Servis | `{s}` |")
    for f in diff["modified_files"]:
        lines.append(f"| **Dosya Butunlugu (SHA256)** | DEGISEN KRITIK DOSYA | `{f}` |")
    for c in diff["new_cron"]:
        lines.append(f"| **Zamanlanmis Gorev** | YENI CRON GOREVI | `{c}` |")

    return "\n".join(lines)


def calculate_hardening_score() -> dict:
    """
    Deterministik CIS-benzeri Linux guvenlik denetimi yapar ve 0-100 arasi
    gercek bir Guvenlik Sikilastirma Puani (Security Score) hesaplar.
    """
    checks: list[dict] = []
    score = 0
    max_score = 100

    # 1. Firewall kontrolu (20 Puan)
    fw_out = _run_quiet("systemctl is-active ufw firewalld nftables iptables 2>/dev/null || true")
    fw_active = "active" in fw_out.splitlines()
    if fw_active:
        score += 20
        checks.append({
            "name": "Guvenlik Duvari (Firewall)",
            "status": "PASS",
            "points": "20/20",
            "current": "Aktif",
            "remediation": "Guvenlik duvari servisi aktif.",
        })
    else:
        checks.append({
            "name": "Guvenlik Duvari (Firewall)",
            "status": "FAIL",
            "points": "0/20",
            "current": "Kapali (Pasif)",
            "remediation": "`sudo pacman -S ufw && sudo ufw default deny incoming && sudo ufw enable`",
        })

    # 2. ASLR (Address Space Layout Randomization) (15 Puan)
    aslr = _run_quiet("sysctl -n kernel.randomize_va_space 2>/dev/null").strip()
    if aslr == "2":
        score += 15
        checks.append({
            "name": "Bellek Rastgelelestirme (ASLR)",
            "status": "PASS",
            "points": "15/15",
            "current": "2 (Tam Koruma)",
            "remediation": "Tam ASLR aktif.",
        })
    else:
        checks.append({
            "name": "Bellek Rastgelelestirme (ASLR)",
            "status": "FAIL",
            "points": "0/15",
            "current": aslr or "Bilinmiyor",
            "remediation": "`sudo sysctl -w kernel.randomize_va_space=2`",
        })

    # 3. Kernel Pointer Restriction (10 Puan)
    kptr = _run_quiet("sysctl -n kernel.kptr_restrict 2>/dev/null").strip()
    if kptr in ("1", "2"):
        score += 10
        checks.append({
            "name": "Kernel Pointer Gizleme (kptr_restrict)",
            "status": "PASS",
            "points": "10/10",
            "current": kptr,
            "remediation": "Kernel bellek adresleri gizleniyor.",
        })
    else:
        checks.append({
            "name": "Kernel Pointer Gizleme (kptr_restrict)",
            "status": "WARN",
            "points": "0/10",
            "current": kptr or "0",
            "remediation": "`sudo sysctl -w kernel.kptr_restrict=2`",
        })

    # 4. Kernel Dmesg Restriction (10 Puan)
    dmesg = _run_quiet("sysctl -n kernel.dmesg_restrict 2>/dev/null").strip()
    if dmesg == "1":
        score += 10
        checks.append({
            "name": "Kernel Log Kisitlamasi (dmesg_restrict)",
            "status": "PASS",
            "points": "10/10",
            "current": "1 (Kisitli)",
            "remediation": "Yetkisiz kullanicilar dmesg okuyamaz.",
        })
    else:
        checks.append({
            "name": "Kernel Log Kisitlamasi (dmesg_restrict)",
            "status": "WARN",
            "points": "0/10",
            "current": dmesg or "0",
            "remediation": "`sudo sysctl -w kernel.dmesg_restrict=1`",
        })

    # 5. TCP SYN Cookies (SYN Flood Korumasi) (10 Puan)
    syncookies = _run_quiet("sysctl -n net.ipv4.tcp_syncookies 2>/dev/null").strip()
    if syncookies == "1":
        score += 10
        checks.append({
            "name": "TCP SYN Flood Korumasi (tcp_syncookies)",
            "status": "PASS",
            "points": "10/10",
            "current": "1 (Aktif)",
            "remediation": "SYN flood korumasi aktif.",
        })
    else:
        checks.append({
            "name": "TCP SYN Flood Korumasi (tcp_syncookies)",
            "status": "FAIL",
            "points": "0/10",
            "current": syncookies or "0",
            "remediation": "`sudo sysctl -w net.ipv4.tcp_syncookies=1`",
        })

    # 6. ICMP Redirect Engelleme (MITM Korumasi) (10 Puan)
    icmp_red = _run_quiet("sysctl -n net.ipv4.conf.all.accept_redirects 2>/dev/null").strip()
    if icmp_red == "0":
        score += 10
        checks.append({
            "name": "ICMP Redirect Engeli (MITM Korumasi)",
            "status": "PASS",
            "points": "10/10",
            "current": "0 (Kapali)",
            "remediation": "Sahte yonlendirme paketleri reddediliyor.",
        })
    else:
        checks.append({
            "name": "ICMP Redirect Engeli (MITM Korumasi)",
            "status": "WARN",
            "points": "0/10",
            "current": icmp_red or "1",
            "remediation": "`sudo sysctl -w net.ipv4.conf.all.accept_redirects=0`",
        })

    # 7. SSH Servis & Root Giris Kontrolu (15 Puan)
    sshd_active = _run_quiet("systemctl is-active sshd ssh 2>/dev/null || true")
    if "active" not in sshd_active.splitlines():
        score += 15
        checks.append({
            "name": "SSH Daemon (Uzaktan Giris)",
            "status": "PASS",
            "points": "15/15",
            "current": "Kapali (Saldiri Yuzeyi Yok)",
            "remediation": "SSH servisi kapali, disaridan brute-force yapilamaz.",
        })
    else:
        sshd_cfg = Path("/etc/ssh/sshd_config")
        root_disabled = False
        if sshd_cfg.exists():
            try:
                cfg_text = sshd_cfg.read_text(encoding="utf-8", errors="ignore")
                for line in cfg_text.splitlines():
                    clean = line.strip().lower()
                    if clean.startswith("permitrootlogin") and ("no" in clean or "prohibit-password" in clean):
                        root_disabled = True
            except Exception:
                pass
        if root_disabled:
            score += 15
            checks.append({
                "name": "SSH Root Giris Korumasi",
                "status": "PASS",
                "points": "15/15",
                "current": "PermitRootLogin no",
                "remediation": "SSH uzerinden dogrudan root girisi kapali.",
            })
        else:
            score += 5
            checks.append({
                "name": "SSH Root Giris Korumasi",
                "status": "WARN",
                "points": "5/15",
                "current": "SSH Aktif",
                "remediation": "`/etc/ssh/sshd_config` icinde `PermitRootLogin no` ayarlayin.",
            })

    # 8. Tum Aga (0.0.0.0 / *) Acik TCP Portlarin Analizi (10 Puan)
    ss_tcp = _run_quiet("ss -tln")
    exposed_tcp: list[str] = []
    for line in ss_tcp.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4:
            local = parts[3]
            if local.startswith("0.0.0.0:") or local.startswith("*:"):
                port_num = local.rsplit(":", 1)[-1]
                exposed_tcp.append(port_num)

    exposed_unique = sorted(set(exposed_tcp))
    if not exposed_unique:
        score += 10
        checks.append({
            "name": "Dis Aga Acik TCP Portlar (0.0.0.0)",
            "status": "PASS",
            "points": "10/10",
            "current": "Yok (Sadece localhost)",
            "remediation": "Dis aga acik dinlenen TCP portu yok.",
        })
    elif len(exposed_unique) <= 2:
        score += 5
        checks.append({
            "name": "Dis Aga Acik TCP Portlar (0.0.0.0)",
            "status": "WARN",
            "points": "5/10",
            "current": f"Portlar: {', '.join(exposed_unique)}",
            "remediation": "Bu portlarin sadece `127.0.0.1` dinlemesi veya UFW ile sinirlanmasi onerilir.",
        })
    else:
        checks.append({
            "name": "Dis Aga Acik TCP Portlar (0.0.0.0)",
            "status": "WARN",
            "points": "0/10",
            "current": f"Portlar: {', '.join(exposed_unique)}",
            "remediation": "Cok sayida port yerel aga acik; UFW ile gelen baglantilari kisitlayin.",
        })

    grade = "A (Guclu)" if score >= 85 else "B (Iyi - Gelistirilebilir)" if score >= 70 else "C (Orta Risk)" if score >= 50 else "D (Zayif - Sikilastirma Gerekli)"

    return {
        "score": score,
        "max_score": max_score,
        "grade": grade,
        "checks": checks,
    }


def format_hardening_report(result: dict) -> str:
    lines = [
        f"### Sistem Guvenlik & Sikilastirma (Hardening) Skoru: **{result['score']} / {result['max_score']}** — Seviye: **{result['grade']}**",
        "",
        "| Kontrol Kalemi | Durum | Puan | Mevcut Deger | Oneri / Cozum Komutu |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for c in result["checks"]:
        lines.append(
            f"| **{c['name']}** | `{c['status']}` | {c['points']} | {c['current']} | {c['remediation']} |"
        )
    return "\n".join(lines)

