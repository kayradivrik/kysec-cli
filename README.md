# secai (v0.8.0 - Altın Sürüm / Golden Release)

Terminal ve modern web tabanlı, çift yönlü sesli SecOps asistanı, vaka defteri ve Linux sıkılaştırma motoru.
Yerel modeller (Ollama) veya Google Gemini API ile çalışır; sistem telemetrisi, tehdit istihbaratı, referans sapma takibi ve SQLite tabanlı vaka yönetimi sağlar.

---

## Öne Çıkan Yetenekler

- 🎙️ **Çift Yönlü Sesli Sohbet (Voice Mode):** Mikrofon konuşma tanıma (STT) ve Microsoft Edge Neural TTS (`tr-TR-AhmetNeural` / `tr-TR-EmelNeural`) ile hem terminalde hem web arayüzünde canlı sesli diyalog.
- 🕵️ **SecOps Ajanları Hub (Agent Switcher):** Göreve özel uzmanlık profilleri:
  - `🎯 Genel SecOps Ajanı`: Temel Linux ve güvenlik analizi.
  - `🔍 Recon Ajanı`: Ağ keşfi, nmap, açık port ve servis haritalama.
  - `🛡️ Hardening Ajanı`: CIS Benchmark sıkılaştırma, SSH, firewall, kernel parametreleri.
  - `⚡ Detection Ajanı`: YARA, Sigma kuralları, Fail2ban ve tehdit tespiti.
  - `🚩 CTF & PrivEsc Ajanı`: Yetki yükseltme, GTFOBins, SUID ve cron zafiyetleri.
- 🌐 **Tehdit İstihbaratı (Threat Intel):** Shodan InternetDB & GeoIP sorguları ile açık portlar, CVE zafiyetleri ve CPE bilgileri.
- 📈 **Sistem Baseline & Sapma Takibi (Drift Detection):** Sistem referans noktası alıp yeni açılan portları veya başlatılan yetkisiz servisleri anında tespit etme.
- 🛡️ **Deterministik CIS Linux Güvenlik Skoru (0-100):** Çekirdek, ağ ve yetki ayarlarını denetleyip tek tıkla düzeltme önerileri sunma.
- 🎨 **Minimalist Geliştirici Arayüzü (Linear / Raycast Style):** Sıfır generic efekt, derin koyu tema (`#08080a`), syntax-highlighted kopyalanabilir kod blokları ve responsive düzen.

---

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Kullanım

### Web Arayüzü:
```bash
secai web
```
Tarayıcında `http://127.0.0.1:8765/` adresinde SecAI Çalışma Alanı açılır.

### Terminal (CLI) Modu:
```bash
secai
```

Kısayollar (`secai` içinde):
- `/web` : Web arayüzünü başlat (`127.0.0.1:8765`)
- `/agent` : SecOps ajanlarını listele veya değiştir (`/agent recon`, `/agent ctf`, `/agent hardening`)
- `/v` & `/voice` : Bas-konuş ve canlı sesli diyalog modu
- `/ses` : Ses profili ve okuma ayarları
- `/models` : Model değiştir (Ollama `gemma3:4b`, `qwen2.5-coder:7b` / Gemini)
- `/intel <ip>` : Shodan InternetDB açık port ve CVE sorgusu
- `/baseline` & `/diff` : Sistem snapshot'ı ve sapma analizi
- `/score` : CIS Benchmark puanını hesapla (0-100)
- `/clear` : Sohbet geçmişini temizle
- `@dosya` : Dosya içeriğini analize ekle

---

## Lisans

MIT © [Kayra Divrik (sonuscato)](https://github.com/kayradivrik)
