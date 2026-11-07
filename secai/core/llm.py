import json
from pathlib import Path
from typing import Generator, Optional
import requests

from secai.config import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    get_active_llm_info,
    save_settings,
)
from secai.core.database import get_casebook_context, get_memory_context
from secai.core.skills import get_active_skill

AUDIT_SYSTEM_PROMPT = """Sen bir SecOps Analisti ve Zafiyet Arastirmacisisin.
Sana verilen loglari, komut ciktilarini (nmap, journalctl, auth.log vb.) veya kaynak kodlari analiz et.

Kurallar:
1. Net, teknik ve Turkce yanit ver.
2. Analiz yaparken su basliklari kullan:
   - Risk Seviyesi: (DUSUK / ORTA / YUKSEK / KRITIK)
   - Bulgular: Saldiri tipi, supheli IP/kullanicilar, zafiyet detayi.
   - Cozum / Komutlar: Dogrudan uygulanabilir savunma komutlari (iptables, ufw, fail2ban, sshd_config veya kod yamasi).
3. Sadece sana verilen veriyi analiz et, veride olmayan bir seyi uydurma.
"""

CHAT_SYSTEM_PROMPT = """Sen kullanicinin Arch Linux (EndeavourOS) terminalinin icinde calisan 'secai' adinda yetkili bir SecOps, Linux Sorun Giderme ve Sistem Ajanisin.
Yazdigin her ```bash ... ``` kod blogu, kullanici 'e' (evet) dedigi anda gercek terminalde otomatik olarak calistirilir!

KESIN KURALLAR:
1. ASLA "Ben bir yapay zekayim", "Gercek zamanli bilgilere erisemem", "Cihaziniza erisemem" gibi cumleler KURMA!
2. Kullanicinin sistemi **Arch Linux (EndeavourOS)**'tur.
   - Kullanici bir uygulama/paket yuklemek, kaldirmak veya guncellemek istediginde (orn: "bana wireshark kur", "discord yukle", "sistemi guncelle") dogrudan Arch/EndeavourOS paket yoneticisi komutunu (`yay -S <paket>` veya `sudo pacman -S <paket>`) ```bash blogu icinde ver!
   - Kullanici Linux'unda bir sorun yasadiginda (ses, bluetooth, wifi, servis hatasi, pacman veritabani kilidi, disk dolulugu, paket cakismasi vb.) sorunu teshis edecek veya cozecek bash komutunu ```bash blogu icinde ver, ciktisini incele ve adim adim coz!
3. Kullanici sistemle ilgili bir bilgi istediginde, eger o bilgi daha onceki komut ciktilarinda KESIN olarak yoksa ASLA tahmin yurutme; dogrudan o bilgiyi getirecek Linux komutunu ```bash blogu icinde ver:
   - IP adresi veya ag karti -> `ip -br a`
   - Bagli olunan Wi-Fi aginin adi (SSID) (`wlan0` arayuz adidir, ag adi degildir!) -> `nmcli -t -f NAME,TYPE,DEVICE connection show --active`
   - Acik portlar -> `ss -tulnp`
   - Yerel agdaki diger cihazlar -> `ip neigh`
   - Sistem/SSH loglari -> `journalctl -n 25 --no-pager`
3.1. GENEL SOHBET & DUYGU DURUMU:
   - Kullanici dertlestiginde, espri yaptiginda, selam verdiginde veya genel sohbet ettiginde (orn: "hayat acimasiz", "naber", "nasil gidiyor", "sence yapay zeka ne olacak") ASLA alakasiz Linux veya log komutlari (journalctl vb.) VERME! Dogal, samimi, zeki ve insan gibi Turkce sohbet et. Yalnizca kullanici bir sistem/guvenlik/hata sorunu belirttiginde komut oner.
4. Sana `[Komut Ciktisi]` verildiginde, o ciktinin TAMAMINI (ozellikle alt satirlardaki TCP LISTEN portlarini) dikkatle oku:
   - Port, surec veya ag listesi gibi verileri ozetlerken okunakli bir **Markdown Tablosu** (`| Port | Servis | Erisim | Durum / Aciklama |` gibi) ve altina kisa maddeler kullan.
   - Port analizlerinde `127.0.0.1` (sadece bilgisayar icinden erisilebilir, guvenli) ile `0.0.0.0` veya `*` (tum yerel aga acik, orn: proxy, ssh, oyun/dosya paylasim portlari) arasindaki farki mutlaka belirt.
   - Eger calisan komut hata verdiyse (orn: paket bulunamadi, yetki hatasi vb.) veya kullanicinin istegini tamamlamak icin 2. bir komut calistirmak gerekiyorsa yeni ```bash komutunu ver; aksi halde ayni komutu tekrar verme.
5. Kullanici Vaka & Proje Defteri hakkinda soru sorarsa ("notlarimi goster", "defterimde ne var", "projelerim neler", "#3 numarali notla simdiki durumu karsilastir") sana verilen [KULLANICININ VAKA & PROJE DEFTERI] bolumundeki verileri kullanarak guzel bir Markdown tablosu veya maddelerle cevap ver.
6. VAKA & PROJE DEFTERI OTOMATIK YONETIMI (Kullaniciya ASLA '/add' veya '/notes' yaz demeden dogrudan sen yap!):
   - Kullanici "not ekle", "bunu kaydet", "su projeyi deftere yaz", "su bilgiyi not al" dediginde basligi, uygun kategoriyi (`secops`, `project`, `ctf`, `idea`, `research`, `general`) ve etiketleri SEN DUSUNUP belirle ve yanitinin en sonuna su blogu koy:
```save-note
baslik: Senin Belirledigin Kisa Baslik
kategori: project
etiketler: uygun,etiketler
icerik:
Duzenlenmis detayli not veya rapor icerigi...
```
   - Kullanici mevcut bir nota ekleme yapmak veya guncellemek isterse ("#1 numarali notuma sunu ekle"):
```update-note
id: 1
icerik:
Eklenecek yeni detay...
```
   - Kullanici bir veya birkac notu silmek isterse ("#2 numarali notu sil", "not 2'yi sil"):
```delete-note
id: 2
```
   - Kullanici TUM notlari, defteri silmek veya temizlemek isterse ("notlari sil", "defteri temizle", "tum notlarimi sil", "butun notlari sil"):
```delete-note
id: all
```
   - ASLA "notlari silemem", "veritabanina erisemem" veya "kendiniz silin" DEME! Sen bu ```delete-note blogunu verdigin anda sistem arka planda notlari SQLite veritabanindan aninda ve kalici olarak siler!
   - Kullanici bir notu Markdown (.md) dosyasi olarak disa aktarmak isterse ("#3 numarali notu rapor/markdown olarak cikar"):
```export-note
id: 3
```
7. CANLI WEB & CVE ARAMASI:
   - Kullanici guncel bir bilgi, CVE zafiyeti, haber, dokumantasyon veya internette arastirilmasi gereken bir sey sorarsa ("webde ara", "internette arastir", "son CVE'ler neler", "su aracin github sayfasina bak"), ASLA "internete erisemem" deme! Yanitinda sadece su blogu ver (sistem otomatik aramayi yapip sonuclari sana getirecek):
```web-search
sorgu: aranacak anahtar kelimeler
```
8. OTOMATIK TEHDIT ISTIHBARATI (SHODAN, VIRUSTOTAL, ABUSEIPDB) & SECOPS MOTORLARI:
   - Kullanici bir veya birden fazla dis (public) IPv4 adresini Shodan InternetDB uzerinde sorgulamak isterse:
```intel-lookup
185.220.101.45
```
   - Kullanici bir IP, domain veya dosya hash'ini (MD5/SHA256) VirusTotal uzerinde kontrol etmek isterse ("VT'de sorgula", "VirusTotal skoru ne", "bu hash zararli mi"):
```vt-lookup
target: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```
   - Kullanici bir IP'nin kotuye kullanim (abuse/saldiri/tarama) skorunu AbuseIPDB'de sorgulamak isterse ("AbuseIPDB skoru", "bu IP saldirgan mi", "sikayet gecmisi"):
```abuse-lookup
ip: 185.220.101.45
```
   - Kullanici sistemin temiz referans kaydini (baseline) almak isterse ("baseline al", "sistemin su anki goruntusunu kaydet"):
```secops-action
baseline
```
   - Kullanici sistemde son baseline'dan beri degisiklik/anomali (yeni acilan arka kapi portu, yeni servis, degisen `/etc/passwd` veya `/etc/hosts`) olup olmadigini kontrol etmek isterse ("sistemde degisiklik var mi", "baseline ile karsilastir", "anomali kontrolu yap"):
```secops-action
diff
```
   - Kullanici bilgisayarinin guvenlik sikilastirma puanini (0-100 CIS Hardening Score) hesaplamak isterse ("guvenlik puanimi hesapla", "sistemim ne kadar guvenli puanla", "hardening skoru cikar"):
```secops-action
score
```
9. KISISEL PROFIL & BELLEK YONETIMI (ChatGPT Memory):
   - Kullanici kendisi hakkinda onemli bir bilgi, tercih, donanim veya kisisel detay paylastiginda ("benim adim Kayra", "RTX 4050 ekran kartim var", "Dogus Uni ogrencisiyim", "bunu unutma", "aklında tut"), bu bilgiyi hatirlamak icin yanitina su blogu ekle:
```remember
anahtar: kullanici_cihaz
bilgi: HP Victus laptop, i5-13500H, RTX 4050 6GB GPU, EndeavourOS Linux kullaniyor
```
   - Kullanici bir bilgiyi unutmani istediginde ("bunu unut", "su bilgiyi hafizandan sil"):
```forget
anahtar: kullanici_cihaz
```

10. DUSUNCE ZINCIRI (CHAIN-OF-THOUGHT) VE KODLAMA / SIBER GUVENLIK STANDARTLARI:
   - **KODLAMA (Python, Bash, C/C++, Go, Rust, Web):**
     1. Asla yarim, sahte (pseudocode) veya calismayan kod verme; dogrudan derlenebilir/calistirilabilir, uretim kalitesinde kod yaz.
     2. Python'da modern standartlari (PEP 8, type hints `typing`, guclu `try-except` bloklari, context managers) uygula.
     3. Kod guvenligini en bastan sagla: ASLA Command Injection, SQL Injection, Path Traversal, bellek tasmasi veya hardcoded credential barindirma.
   - **LINUX & SISTEM SORUN GIDERME (Arch / EndeavourOS):**
     1. Tahmine dayali tavsiye yerine daima once teshis koy: Sorunun kaynagini gosterecek komutu (`systemctl status`, `journalctl -xeu`, `dmesg -T`, `pacman -Qk`, `ip a`) calistir.
     2. Pacman veritabani kilidi (`db.lck`), Pipewire/Pulseaudio ses sorunlari, Wi-Fi kopmalari, NVIDIA optimus/driver cakismalari ve SUID yetkilerinde kesin Arch cozumunu ver.
   - **SIBER GUVENLIK & OFANSIF/DEFANSIF ANALIZ:**
     1. Analizlerinde MITRE ATT&CK matrisini, CIS Benchmark kontrollerini ve CVE veritabanini esas al.
     2. CTF / Zafiyet incelemelerinde: Enumeration -> Zafiyet Tespiti -> Payload/PoC Analizi -> Yetki Yukseltme (GTFOBins, SUID, Cron) sirasini metodik olarak izle.
"""


def get_runtime_context() -> str:
    """Modelin tarih/sistem bilgisini uydurmamasi icin gercek calisma zamani bilgisini uretir."""
    import getpass
    import platform
    import socket
    from datetime import datetime

    aylar = (
        "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
        "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik",
    )
    now = datetime.now()
    tarih = f"{now.day} {aylar[now.month - 1]} {now.year}, {now.strftime('%H:%M')}"

    distro = platform.system()
    try:
        os_rel = Path("/etc/os-release")
        if os_rel.exists():
            for line in os_rel.read_text(encoding="utf-8").splitlines():
                if line.startswith("PRETTY_NAME="):
                    distro = line.split("=", 1)[1].strip().strip('"')
                    break
    except Exception:
        pass

    try:
        user_host = f"{getpass.getuser()}@{socket.gethostname()}"
    except Exception:
        user_host = "bilinmiyor"

    # Aktif calisma dizini ve projedeki ust dosyalar (Workspace Tree Awareness)
    cwd = Path.cwd()
    top_entries = []
    try:
        top_entries = [p.name + ("/" if p.is_dir() else "") for p in sorted(cwd.iterdir()) if not p.name.startswith(".")][:25]
    except Exception:
        pass
    entries_str = ", ".join(top_entries) if top_entries else "bos"

    # Git branch kontrolu
    git_branch = ""
    git_head = cwd / ".git" / "HEAD"
    if git_head.exists():
        try:
            head_txt = git_head.read_text(encoding="utf-8").strip()
            if head_txt.startswith("ref: refs/heads/"):
                git_branch = head_txt.replace("ref: refs/heads/", "")
        except Exception:
            pass
    git_str = f" [git: {git_branch}]" if git_branch else ""

    return (
        "[GERCEK CALISMA ZAMANI & CALISMA ALANI (WORKSPACE) BILGISI]:\n"
        f"- Bugunun tarihi ve saati: {tarih}\n"
        f"- Sistem: {distro} (cekirdek {platform.release()}), kullanici/host: {user_host}\n"
        f"- Donanim / GPU: NVIDIA GeForce RTX 4050 (6GB VRAM) & Intel Iris Xe\n"
        f"- Bulunulan Calisma Dizini (CWD): {cwd}{git_str}\n"
        f"- Bu Dizindeki Ust Dosyalar / Proje Agaci: {entries_str}\n"
        "- Rapora veya yanita tarih ya da sistem adi yazacaksan SADECE bu bilgileri kullan; "
        "asla tahmini/uydurma bir tarih veya 'Belirtilmemis' yazma."
    )


class OllamaConnectionError(Exception):
    pass


def check_ollama(
    base_url: str = DEFAULT_OLLAMA_URL, target_model: str = DEFAULT_OLLAMA_MODEL
) -> dict:
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        model_ready = any(
            m == target_model or m.startswith(target_model.split(":")[0])
            for m in models
        )
        return {
            "online": True,
            "model_ready": model_ready,
            "models": models,
        }
    except requests.RequestException:
        return {
            "online": False,
            "model_ready": False,
            "models": [],
        }


def _stream_gemini(
    contents: list[dict],
    system_prompt: str,
    model: str,
    api_key: str,
) -> Generator[str, None, None]:
    # Eger secilen model gecici olarak 404/429/503 donerse yedek Gemini 3 modellerini dene
    fallback_chain = [model]
    for candidate in (DEFAULT_GEMINI_MODEL, "gemini-3-flash-preview", "gemini-3.5-flash"):
        if candidate not in fallback_chain:
            fallback_chain.append(candidate)

    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    last_error = ""
    for current_model in fallback_chain:
        gen_config: dict = {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        }
        if "flash" in current_model:
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:streamGenerateContent"
            "?alt=sse"
        )
        yielded_chunks: list[str] = []
        finish_reason: Optional[str] = None
        active_contents = list(contents)

        # DPI / Paket bolucu (ciadpi vb.) veya ag kopmasi nedeniyle SSE akisi finishReason="STOP"
        # gelmeden yarida kesilirse kaldigi yerden otomatik devam et (en fazla 3 parca)
        for attempt in range(3):
            finish_reason = None
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": active_contents,
                "generationConfig": gen_config,
            }
            try:
                with requests.post(
                    url, headers=headers, json=payload, stream=True, timeout=(10, 180)
                ) as resp:
                    if resp.status_code in (404, 429, 503) and not yielded_chunks:
                        last_error = f"{current_model} ({resp.status_code})"
                        break
                    if resp.status_code in (400, 401, 403) and not yielded_chunks:
                        err_text = resp.text[:250]
                        raise OllamaConnectionError(
                            f"Gemini API Hatasi ({resp.status_code}): API anahtarinizi (/api komutuyla) kontrol edin. Detay: {err_text}"
                        )
                    resp.raise_for_status()

                    if current_model != model:
                        save_settings({"gemini_model": current_model})

                    for raw_line in resp.iter_lines(chunk_size=4096):
                        if not raw_line:
                            continue
                        line = (
                            raw_line.decode("utf-8", errors="replace")
                            if isinstance(raw_line, bytes)
                            else raw_line
                        )
                        if not line.startswith("data:"):
                            continue
                        json_str = line[5:].strip()
                        if not json_str or json_str == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(json_str)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                cand = candidates[0]
                                if cand.get("finishReason"):
                                    finish_reason = cand.get("finishReason")
                                parts = cand.get("content", {}).get("parts", [])
                                for p in parts:
                                    if p.get("thought"):
                                        continue
                                    text = p.get("text", "")
                                    if text:
                                        yielded_chunks.append(text)
                                        yield text
                        except json.JSONDecodeError:
                            continue
            except requests.RequestException as exc:
                last_error = str(exc)
                if not yielded_chunks:
                    break

            if finish_reason == "STOP" or not yielded_chunks:
                break

            # Akis STOP olmadan kesildiyse kaldigi yerden devam ettir
            partial_text = "".join(yielded_chunks)
            active_contents = list(contents) + [
                {"role": "model", "parts": [{"text": partial_text}]},
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Yanitin ag kesintisi nedeniyle tam bittigi noktada yarida kaldi. "
                                "Onceki yazdiklarini ASLA tekrarlamadan, tam kaldigin kelimeden/satirdan devam ederek yaniti tamamla."
                            )
                        }
                    ],
                },
            ]

        if yielded_chunks:
            return

    raise OllamaConnectionError(
        f"Gemini API yanit veremedi ({last_error}). '/model' yazarak modeli degistirebilir veya yerel Ollama'ya gecebilirsiniz."
    )


OPENAI_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}


def _stream_openai_compat(
    provider: str,
    api_key: str,
    model: str,
    messages: list[dict],
    system_prompt: str,
) -> Generator[str, None, None]:
    endpoint_url = OPENAI_ENDPOINTS.get(provider, "https://api.groq.com/openai/v1/chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/kayradivrik/kysec-cli"
        headers["X-Title"] = "SecAI Cyber Defense"

    full_msgs = []
    if system_prompt:
        full_msgs.append({"role": "system", "content": system_prompt})
    for m in messages:
        full_msgs.append({"role": m["role"], "content": m["content"]})

    data = {
        "model": model,
        "messages": full_msgs,
        "stream": True,
        "temperature": 0.2,
    }

    try:
        with requests.post(endpoint_url, headers=headers, json=data, stream=True, timeout=(5, 120)) as resp:
            if resp.status_code != 200:
                err_body = resp.text[:300]
                yield f"\n\n**{provider.upper()} API Hatası ({resp.status_code}):** {err_body}\n"
                return

            in_reasoning = False
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                json_str = line[5:].strip()
                if not json_str or json_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(json_str)
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})

                    # DeepSeek R1 Akıl Yürütme (Thinking Chain) Desteği
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        if not in_reasoning:
                            yield "\n> 💭 *[DeepSeek R1 Düşünce Zinciri]*\n> "
                            in_reasoning = True
                        yield reasoning.replace("\n", "\n> ")

                    content = delta.get("content", "")
                    if content:
                        if in_reasoning:
                            yield "\n\n"
                            in_reasoning = False
                        yield content
                except json.JSONDecodeError:
                    continue
    except requests.RequestException as exc:
        yield f"\n\n**{provider.upper()} Bağlantı Hatası:** {exc}\n"


def stream_generate(
    prompt: str,
    system_prompt: str = AUDIT_SYSTEM_PROMPT,
    model: Optional[str] = None,
    base_url: str = DEFAULT_OLLAMA_URL,
) -> Generator[str, None, None]:
    llm_info = get_active_llm_info()
    active_model = model or llm_info["model"]
    active_skill = get_active_skill()
    effective_system = (
        f"{system_prompt}\n\n{active_skill['instructions']}"
        if active_skill
        else system_prompt
    )
    effective_system = f"{effective_system}\n\n{get_runtime_context()}"

    if llm_info["provider"] == "gemini" and llm_info["api_key"]:
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        yield from _stream_gemini(
            contents=contents,
            system_prompt=effective_system,
            model=active_model,
            api_key=llm_info["api_key"],
        )
        return

    if llm_info["provider"] in ("groq", "deepseek", "openrouter") and llm_info["api_key"]:
        yield from _stream_openai_compat(
            provider=llm_info["provider"],
            api_key=llm_info["api_key"],
            model=active_model,
            messages=[{"role": "user", "content": prompt}],
            system_prompt=effective_system,
        )
        return

    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": active_model,
        "prompt": prompt,
        "system": effective_system,
        "stream": True,
        "options": {
            "num_gpu": 99,
            "num_ctx": 8192,
            "temperature": 0.2,
            "top_k": 40,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        },
    }

    try:
        with requests.post(url, json=payload, stream=True, timeout=(5, 300)) as resp:
            if resp.status_code == 404:
                raise OllamaConnectionError(
                    f"Model '{active_model}' bulunamadi. 'ollama pull {active_model}' komutunu calistirin."
                )
            resp.raise_for_status()

            in_think = False
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    if "<think>" in token:
                        token = token.replace("<think>", "\n> 💭 *[DeepSeek R1 Düşünce Zinciri]*\n> ")
                        in_think = True
                    if "</think>" in token:
                        token = token.replace("</think>", "\n\n")
                        in_think = False
                    elif in_think:
                        token = token.replace("\n", "\n> ")
                    yield token
                if chunk.get("done"):
                    break
    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Ollama servisine ulasilamadi ({base_url}). Servisin acik oldugunu kontrol edin veya '/api' ile Gemini API anahtari girin."
        ) from exc
    except requests.RequestException as exc:
        raise OllamaConnectionError(f"Ollama baglanti hatasi: {exc}") from exc


def stream_chat(
    messages: list[dict[str, str]],
    system_prompt: str = CHAT_SYSTEM_PROMPT,
    model: Optional[str] = None,
    base_url: str = DEFAULT_OLLAMA_URL,
) -> Generator[str, None, None]:
    llm_info = get_active_llm_info()
    active_model = model or llm_info["model"]

    latest_user_query = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            latest_user_query = m.get("content", "")
            break

    casebook_ctx = get_casebook_context(user_query=latest_user_query, limit=10)
    memory_ctx = get_memory_context()
    mem_block = f"\n\n{memory_ctx}" if memory_ctx else ""
    active_skill = get_active_skill()
    skill_block = f"\n\n{active_skill['instructions']}" if active_skill else ""
    enriched_system_prompt = (
        f"{system_prompt}{skill_block}\n\n{get_runtime_context()}{mem_block}\n\n{casebook_ctx}"
    )

    if llm_info["provider"] == "gemini" and llm_info["api_key"]:
        gemini_contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            gemini_contents.append({"role": role, "parts": [{"text": m["content"]}]})

        yield from _stream_gemini(
            contents=gemini_contents,
            system_prompt=enriched_system_prompt,
            model=active_model,
            api_key=llm_info["api_key"],
        )
        return

    if llm_info["provider"] in ("groq", "deepseek", "openrouter") and llm_info["api_key"]:
        yield from _stream_openai_compat(
            provider=llm_info["provider"],
            api_key=llm_info["api_key"],
            model=active_model,
            messages=messages,
            system_prompt=enriched_system_prompt,
        )
        return

    url = f"{base_url.rstrip('/')}/api/chat"
    full_messages = [{"role": "system", "content": enriched_system_prompt}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]

    payload = {
        "model": active_model,
        "messages": full_messages,
        "stream": True,
        "options": {
            "num_gpu": 99,
            "num_ctx": 8192,
            "temperature": 0.2,
            "top_k": 40,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        },
    }

    try:
        with requests.post(url, json=payload, stream=True, timeout=(5, 300)) as resp:
            if resp.status_code == 404:
                raise OllamaConnectionError(
                    f"Model '{active_model}' bulunamadi. 'ollama pull {active_model}' komutunu calistirin."
                )
            resp.raise_for_status()

            in_think = False
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                token = msg.get("content", "")
                if token:
                    if "<think>" in token:
                        token = token.replace("<think>", "\n> 💭 *[DeepSeek R1 Düşünce Zinciri]*\n> ")
                        in_think = True
                    if "</think>" in token:
                        token = token.replace("</think>", "\n\n")
                        in_think = False
                    elif in_think:
                        token = token.replace("\n", "\n> ")
                    yield token
                if chunk.get("done"):
                    break
    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Ollama servisine ulasilamadi ({base_url}). Servisin acik oldugunu kontrol edin veya '/api' ile Gemini API anahtari girin."
        ) from exc
    except requests.RequestException as exc:
        raise OllamaConnectionError(f"Ollama baglanti hatasi: {exc}") from exc
