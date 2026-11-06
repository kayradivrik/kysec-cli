import json
from typing import Generator, Optional
import requests

from secai.config import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    get_active_llm_info,
    save_settings,
)
from secai.core.database import get_casebook_context
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
   - Kullanici bir notu silmek isterse ("#2 numarali notu sil"):
```delete-note
id: 2
```
   - Kullanici bir notu Markdown (.md) dosyasi olarak disa aktarmak isterse ("#3 numarali notu rapor/markdown olarak cikar"):
```export-note
id: 3
```
7. CANLI WEB & CVE ARAMASI:
   - Kullanici guncel bir bilgi, CVE zafiyeti, haber, dokumantasyon veya internette arastirilmasi gereken bir sey sorarsa ("webde ara", "internette arastir", "son CVE'ler neler", "su aracin github sayfasina bak"), ASLA "internete erisemem" deme! Yanitinda sadece su blogu ver (sistem otomatik aramayi yapip sonuclari sana getirecek):
```web-search
sorgu: aranacak anahtar kelimeler
```
8. OTOMATIK TEHDIT ISTIHBARATI (SHODAN INTERNETDB) & SECOPS MOTORLARI:
   - Kullanici bir veya birden fazla dis (public) IPv4 adresini sorgulamak, arastirmak veya tehdit istihbarati almak isterse ("bu IP'ye bak: 185.220.101.45", "su IP'leri Shodan'da sorgula"), yanitinda su blogu ver:
```intel-lookup
185.220.101.45
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
"""


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

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.2},
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    last_error = ""
    for current_model in fallback_chain:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:streamGenerateContent"
            "?alt=sse"
        )
        try:
            with requests.post(
                url, headers=headers, json=payload, stream=True, timeout=(10, 300)
            ) as resp:
                if resp.status_code in (404, 429, 503):
                    last_error = f"{current_model} ({resp.status_code})"
                    continue
                if resp.status_code in (400, 401, 403):
                    err_text = resp.text[:250]
                    raise OllamaConnectionError(
                        f"Gemini API Hatasi ({resp.status_code}): API anahtarinizi (/api komutuyla) kontrol edin. Detay: {err_text}"
                    )
                resp.raise_for_status()
                resp.encoding = "utf-8"

                if current_model != model:
                    save_settings({"gemini_model": current_model})

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    json_str = line[5:].strip()
                    if not json_str or json_str == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(json_str)
                        candidates = chunk.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for p in parts:
                                text = p.get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue
                return
        except requests.RequestException as exc:
            last_error = str(exc)
            continue

    raise OllamaConnectionError(
        f"Gemini API yanit veremedi ({last_error}). '/model' yazarak modeli degistirebilir veya yerel Ollama'ya gecebilirsiniz."
    )


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

    if llm_info["provider"] == "gemini" and llm_info["api_key"]:
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        yield from _stream_gemini(
            contents=contents,
            system_prompt=effective_system,
            model=active_model,
            api_key=llm_info["api_key"],
        )
        return

    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": active_model,
        "prompt": prompt,
        "system": effective_system,
        "stream": True,
        "options": {"temperature": 0.2},
    }

    try:
        with requests.post(url, json=payload, stream=True, timeout=(5, 300)) as resp:
            if resp.status_code == 404:
                raise OllamaConnectionError(
                    f"Model '{active_model}' bulunamadi. 'ollama pull {active_model}' komutunu calistirin."
                )
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
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
    active_skill = get_active_skill()
    skill_block = f"\n\n{active_skill['instructions']}" if active_skill else ""
    enriched_system_prompt = f"{system_prompt}{skill_block}\n\n{casebook_ctx}"

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

    url = f"{base_url.rstrip('/')}/api/chat"
    full_messages = [{"role": "system", "content": enriched_system_prompt}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]

    payload = {
        "model": active_model,
        "messages": full_messages,
        "stream": True,
        "options": {"temperature": 0.2},
    }

    try:
        with requests.post(url, json=payload, stream=True, timeout=(5, 300)) as resp:
            if resp.status_code == 404:
                raise OllamaConnectionError(
                    f"Model '{active_model}' bulunamadi. 'ollama pull {active_model}' komutunu calistirin."
                )
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                token = msg.get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
    except requests.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Ollama servisine ulasilamadi ({base_url}). Servisin acik oldugunu kontrol edin veya '/api' ile Gemini API anahtari girin."
        ) from exc
    except requests.RequestException as exc:
        raise OllamaConnectionError(f"Ollama baglanti hatasi: {exc}") from exc
