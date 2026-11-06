import ipaddress
import re
import requests

IPV4_CANDIDATE_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
MD5_RE = re.compile(r"\b[a-fA-F0-9]{32}\b")

HIGH_RISK_PORTS = {21, 22, 23, 445, 1080, 1433, 3306, 3389, 4444, 5432, 5900, 6379, 8080, 9200, 27017}
SUSPICIOUS_TAGS = {"tor", "scanner", "compromised", "malware", "botnet", "c2", "proxy", "vpn", "honeypot"}


def is_public_ipv4(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return (
            isinstance(addr, ipaddress.IPv4Address)
            and addr.is_global
            and not addr.is_private
            and not addr.is_loopback
            and not addr.is_multicast
            and not addr.is_link_local
            and not addr.is_reserved
        )
    except ValueError:
        return False


def extract_iocs(text: str) -> dict[str, list[str]]:
    """Metin, log veya komut ciktisindan dis IP'leri, CVE kodlarini ve hash'leri cikarir."""
    public_ips: list[str] = []
    seen_ips: set[str] = set()
    for match in IPV4_CANDIDATE_RE.findall(text):
        if match not in seen_ips and is_public_ipv4(match):
            seen_ips.add(match)
            public_ips.append(match)

    cves = sorted({m.upper() for m in CVE_RE.findall(text)})
    sha256s = sorted({m.lower() for m in SHA256_RE.findall(text)})

    # 64 karakterlik SHA256 icindeki alt dizileri MD5 sanmamak icin filtrele
    text_without_sha256 = SHA256_RE.sub("", text)
    md5s = sorted({m.lower() for m in MD5_RE.findall(text_without_sha256)})

    return {
        "ips": public_ips,
        "cves": cves,
        "sha256": sha256s,
        "md5": md5s,
    }


def enrich_ip_intel(ip: str) -> dict:
    """
    Shodan InternetDB (anahtarsiz) ve IP-API uzerinden bir dis IP adresinin
    acik portlarini, bilinen CVE zafiyetlerini, etiketlerini ve ASN/Ulke bilgisini sorgular.
    """
    info = {
        "ip": ip,
        "country": "-",
        "asn": "-",
        "isp": "-",
        "ports": [],
        "vulns": [],
        "hostnames": [],
        "tags": [],
        "risk": "DUSUK",
    }

    # 1. Shodan InternetDB sorgusu
    try:
        resp = requests.get(f"https://internetdb.shodan.io/{ip}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            info["ports"] = data.get("ports", []) or []
            info["vulns"] = data.get("vulns", []) or []
            info["hostnames"] = data.get("hostnames", []) or []
            info["tags"] = data.get("tags", []) or []
    except requests.RequestException:
        pass

    # 2. GeoIP / ASN sorgusu
    try:
        geo_resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,country,isp,as",
            timeout=4,
        )
        if geo_resp.status_code == 200:
            gdata = geo_resp.json()
            if gdata.get("status") == "success":
                info["country"] = gdata.get("country") or "-"
                info["isp"] = gdata.get("isp") or "-"
                info["asn"] = gdata.get("as") or "-"
    except requests.RequestException:
        pass

    # Risk skorlama
    vulns = info["vulns"]
    tags_lower = {t.lower() for t in info["tags"]}
    hosts_joined = " ".join(info["hostnames"]).lower()
    ports_set = set(info["ports"])

    if (
        len(vulns) >= 3
        or (tags_lower & {"compromised", "malware", "botnet", "c2", "tor"})
        or "tor-exit" in hosts_joined
    ):
        info["risk"] = "KRITIK"
    elif (
        vulns
        or (tags_lower & SUSPICIOUS_TAGS)
        or any(k in hosts_joined for k in ("scanner", "proxy", "vpn", "tor"))
        or len(ports_set & HIGH_RISK_PORTS) >= 2
    ):
        info["risk"] = "YUKSEK"
    elif ports_set:
        info["risk"] = "ORTA"

    return info


def format_intel_report(text_or_ip: str, max_ips: int = 8) -> str:
    """
    Metindeki veya dogrudan verilen IP/log icindeki IOC'leri ayiklar, Shodan InternetDB ile
    zenginlestirir ve Markdown tablosu olarak dondurur.
    """
    iocs = extract_iocs(text_or_ip)
    ips = iocs["ips"][:max_ips]
    cves = iocs["cves"]
    sha256s = iocs["sha256"]
    md5s = iocs["md5"]

    if not ips and not cves and not sha256s and not md5s:
        return "[IOC & Tehdit Istihbarati]: Metinde herhangi bir dis (public) IPv4 adresi, CVE kodu veya dosya hash'i tespit edilmedi."

    lines: list[str] = ["### Tehdit Istihbarati & IOC Analizi (Shodan InternetDB)"]

    if ips:
        lines.append("")
        lines.append("| IP Adresi | Ulke / ASN | Acik Portlar (Shodan) | CVE / Etiketler / Host | Risk |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for ip in ips:
            intel = enrich_ip_intel(ip)
            loc_asn = f"{intel['country']} ({intel['asn'][:28]})" if intel["asn"] != "-" else intel["country"]
            ports_str = ", ".join(str(p) for p in intel["ports"][:10]) or "Yok"
            if len(intel["ports"]) > 10:
                ports_str += f" (+{len(intel['ports']) - 10})"

            details: list[str] = []
            if intel["vulns"]:
                details.append("CVE: " + ", ".join(intel["vulns"][:4]))
                if len(intel["vulns"]) > 4:
                    details[-1] += f" (+{len(intel['vulns']) - 4})"
            if intel["tags"]:
                details.append("Tag: " + ", ".join(intel["tags"]))
            if intel["hostnames"]:
                details.append("Host: " + intel["hostnames"][0])
            detail_str = " / ".join(details) if details else "Temiz / Bilinmiyor"

            lines.append(
                f"| `{ip}` | {loc_asn} | `{ports_str}` | {detail_str} | **{intel['risk']}** |"
            )

    if cves:
        lines.append(f"\n- **Tespit Edilen CVE Kodlari:** {', '.join(f'`{c}`' for c in cves)}")
    if sha256s:
        lines.append(f"- **SHA256 Hash ({len(sha256s)}):** {', '.join(f'`{h[:16]}...`' for h in sha256s[:5])}")
    if md5s:
        lines.append(f"- **MD5 Hash ({len(md5s)}):** {', '.join(f'`{h}`' for h in md5s[:5])}")

    return "\n".join(lines)
