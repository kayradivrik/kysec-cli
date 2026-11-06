# secai

Terminal tabanlı SecOps asistanı ve vaka/proje defteri.
Yerel modeller (Ollama) veya Google Gemini API ile çalışır; log analizi, sistem denetimi ve SQLite tabanlı not yönetimi sağlar.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Kullanım

```bash
secai
```

Kısayollar (`secai` içinde):
- `/web` : Sade React web arayüzünü aç (`127.0.0.1:8765`)
- `/v` & `/voice` : Bas-konuş ve canlı sesli diyalog (telsiz) modu
- `/ses` : Ses ayarları (Ahmet/Emel ses seçimi, sesli yanıt aç/kapat)
- `/api` : Gemini API anahtarı tanımla
- `/models` : Model değiştir (Gemini / Ollama)
- `/skills` : Yetenek seç veya ekle (`recon`, `hardening`, `detection`, `ctf`)
- `/intel <ip/log>` : Shodan InternetDB & GeoIP tehdit istihbaratı
- `/baseline` & `/diff` : Sistem referans kaydı ve anomali/sapma tespiti
- `/score` : Deterministik CIS Linux güvenlik skoru (0-100)
- `/check` : Sistem güvenlik taraması
- `/report` : Oturum raporu (`.md`) üret
- `@dosya` : Dosya içeriğini sohbete dahil et

Doğrudan komutlar:
```bash
secai web          # Sade React web arayüzü
journalctl -n 30 | secai audit --save "Log Analizi"
secai status
secai backup
```

## Lisans

MIT © [Kayra Divrik (sonuscato)](https://github.com/kayradivrik)
