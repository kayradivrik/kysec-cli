import os
import re
from pathlib import Path
from typing import Optional

from secai.config import get_data_dir, load_settings, save_settings

BUILTIN_SKILLS: dict[str, dict[str, str]] = {
    "recon": {
        "name": "recon",
        "description": "Ag, port ve servis kesif uzmani (ss, nmap, ip, dns analizi)",
        "instructions": (
            "AKTIF SKILL [recon - Ag & Kesif Uzmani]:\n"
            "Kullaniciya ag kesfi, acik port analizi, servis versiyon tespiti ve yerel ag haritalama konularinda "
            "adim adim rehberlik et. Gerekli oldugunda ss, ip, nmap, dig, curl gibi araclari ```bash blogu icinde oner."
        ),
    },
    "hardening": {
        "name": "hardening",
        "description": "Linux & Arch sistem sikilastirma uzmani (SSH, firewall, SUID, sysctl)",
        "instructions": (
            "AKTIF SKILL [hardening - Sistem Sikilastirma Uzmani]:\n"
            "Sistemi CIS ve SecOps standartlarina gore denetle. SUID bitleri, sshd_config, ufw/nftables/iptables, "
            "acik servisler ve dosya izinlerindeki zafiyetleri bulup dogrudan sikilastirma komutlarini ver."
        ),
    },
    "detection": {
        "name": "detection",
        "description": "YARA, Sigma ve Fail2ban/iptables kural yazici (Blue Team)",
        "instructions": (
            "AKTIF SKILL [detection - Kural & Tespit Uzmani]:\n"
            "Kullanicinin verdigi log, saldiri senaryosu veya zararli davranis icin dogrudan calisabilir "
            "Sigma kurali, YARA kurali veya Fail2ban/iptables engelleme kurali uret."
        ),
    },
    "ctf": {
        "name": "ctf",
        "description": "CTF cozumu ve Linux Privilege Escalation (GTFOBins, SUID, Cron) asistani",
        "instructions": (
            "AKTIF SKILL [ctf - CTF & Privesc Uzmani]:\n"
            "CTF senaryolarinda enumeration, web zafiyetleri ve Linux yetki yukseltme (sudo -l, SUID, capabilities, "
            "cronjobs, GTFOBins) tekniklerini pratik komutlarla goster."
        ),
    },
}


def get_skills_dir() -> Path:
    s_dir = get_data_dir() / "skills"
    if not s_dir.exists():
        s_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            s_dir.chmod(0o700)
    return s_dir


def ensure_builtin_skills() -> None:
    s_dir = get_skills_dir()
    for key, data in BUILTIN_SKILLS.items():
        path = s_dir / f"{key}.md"
        if not path.exists():
            content = (
                f"# {data['name']}\n"
                f"Aciklama: {data['description']}\n\n"
                f"{data['instructions']}\n"
            )
            path.write_text(content, encoding="utf-8")


def list_all_skills() -> list[dict[str, str]]:
    ensure_builtin_skills()
    s_dir = get_skills_dir()
    skills: list[dict[str, str]] = []

    for md_file in sorted(s_dir.glob("*.md")):
        name = md_file.stem.lower()
        raw = md_file.read_text(encoding="utf-8", errors="replace").strip()
        desc = "Ozel kullanici yetenegi"
        body_lines: list[str] = []

        for line in raw.splitlines():
            if line.lower().startswith("aciklama:") or line.lower().startswith("description:"):
                desc = line.split(":", 1)[1].strip()
            elif not line.startswith("# "):
                body_lines.append(line)

        skills.append(
            {
                "name": name,
                "description": desc,
                "instructions": "\n".join(body_lines).strip(),
                "path": str(md_file),
            }
        )
    return skills


def get_skill(name: str) -> Optional[dict[str, str]]:
    clean = name.lower().strip()
    for s in list_all_skills():
        if s["name"] == clean:
            return s
    return None


def create_custom_skill(name: str, description: str, instructions: str) -> Path:
    ensure_builtin_skills()
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower().strip()).strip("-")
    if not slug:
        raise ValueError("Gecersiz skill adi.")

    path = get_skills_dir() / f"{slug}.md"
    content = (
        f"# {slug}\n"
        f"Aciklama: {description.strip()}\n\n"
        f"AKTIF SKILL [{slug}]:\n"
        f"{instructions.strip()}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def get_active_skill() -> Optional[dict[str, str]]:
    settings = load_settings()
    active_name = settings.get("active_skill", "").strip()
    if not active_name:
        return None
    return get_skill(active_name)


def set_active_skill(name: Optional[str]) -> Optional[dict[str, str]]:
    if not name or name.lower().strip() in ("none", "off", "kapat", "sifirla", "0"):
        save_settings({"active_skill": ""})
        return None

    skill = get_skill(name)
    if not skill:
        raise ValueError(f"'{name}' adinda bir skill bulunamadi.")

    save_settings({"active_skill": skill["name"]})
    return skill

