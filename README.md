# secai (v0.9.0 - AI Image Studio & Corporate PDF Edition)

Terminal ve modern web tabanlı, çift yönlü sesli SecOps asistanı, vaka defteri ve Linux sıkılaştırma motoru.
Yerel modeller (Ollama RTX 4050 GPU offload) veya Google Gemini API ile çalışır; sistem telemetrisi, tehdit istihbaratı, referans sapma takibi, kurumsal PDF raporlama ve SQLite tabanlı vaka yönetimi sağlar.

---

## Öne Çıkan Yetenekler

- 📄 **Kurumsal Siber Güvenlik PDF Raporlama (New!):** Vaka Defteri kayıtlarını ve penetrasyon testi bulgularını tek tıkla şirketlere ve denetçilere sunulabilecek resmi standartlarda (Executive Summary, Scope, Findings, Hardening Checklist, Sign-off) PDF raporlarına dönüştürme.
- 🎨 **Yapay Zeka Görsel Üretimi (AI Image Studio - New!):** Sıfır kurulum ve API anahtarı istemeden açık GPU ağı (Stable Diffusion) üzerinden `/image` veya Web UI ile saniyeler içinde görsel üretme.
- 🏷️ **Akıllı Sohbet Başlığı Belirleme (New!):** Sohbetleri ilk mesaja göre semantik analizle otomatik adlandırma ve tek tıkla yeniden adlandırabilme (`/rename`).
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

## Gelecek Planları (Roadmap / Yapılacaklar)

- [ ] 🤖 **Multi-Agent Orkestrasyonu (Ajanların Birbiriyle Otonom Konuşması):** Örneğin Recon Ajanının bulduğu açığı otomatik olarak Hardening Ajanına paslayıp çözüm üretmesi.
- [ ] 🔒 **Sandboxed Araç Çalıştırma:** İzolasyonlu container/firejail ortamında nmap, masscan ve tcpdump çıktılarının otonom analizi.
- [ ] 📊 **Gelişmiş Uyumluluk Çerçeveleri:** ISO 27001 ve NIST CSF uyumluluk haritalaması.

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
- `/infomy <bilgi>` : Kendini tanıt, SecAI kim olduğunu ve hedeflerini unutmasın
- `/models` : Model değiştir (Ollama `gemma3:4b`, `qwen2.5-coder:7b` / Gemini)
- `/intel <ip>` : Shodan InternetDB açık port ve CVE sorgusu
- `/baseline` & `/diff` : Sistem snapshot'ı ve sapma analizi
- `/score` : CIS Benchmark puanını hesapla (0-100)
- `/clear` : Sohbet geçmişini temizle
- `@dosya` : Dosya içeriğini analize ekle

---

## Lisans

MIT © [Kayra Divrik (sonuscato)](https://github.com/kayradivrik)
