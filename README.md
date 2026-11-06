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
- `/api` : Gemini API anahtarı tanımla
- `/models` : Model değiştir (Gemini / Ollama)
- `/skills` : Yetenek seç veya ekle (`recon`, `hardening`, `detection`, `ctf`)
- `/check` : Sistem güvenlik taraması
- `/report` : Oturum raporu (`.md`) üret
- `@dosya` : Dosya içeriğini sohbete dahil et

Doğrudan komutlar:
```bash
journalctl -n 30 | secai audit --save "Log Analizi"
secai status
secai backup
```

## Lisans

MIT © [Kayra Divrik (sonuscato)](https://github.com/sonuscato)
