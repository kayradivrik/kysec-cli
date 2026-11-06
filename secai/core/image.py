"""
SecAI Görsel Oluşturma (Image Generation) Motoru.

Merkezi olmayan açık yapay zeka kümesi (AI Horde / Stable Diffusion) ve
yedekleme kanalları (Pollinations) üzerinden komut satırından (/image) ve Web
arayüzünden yüksek kaliteli siber güvenlik, konsept sanatı, logo ve diyagram
görselleri üretir. Sıfır kurulum ve API anahtarı gerektirmeden çalışır.
"""

import base64
from datetime import datetime
from pathlib import Path
import re
import secrets
import time
from typing import Optional
import urllib.parse
import urllib.request

import requests

from secai.config import get_data_dir


def get_images_dir() -> Path:
    img_dir = get_data_dir() / "images"
    if not img_dir.exists():
        img_dir.mkdir(parents=True, exist_ok=True)
    return img_dir


def _slugify(text: str, max_words: int = 4) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    words = cleaned.split()[:max_words]
    return "_".join(words) or "art"


def _generate_via_aihorde(prompt: str, timeout_sec: int = 40) -> Optional[tuple[bytes, str]]:
    """AI Horde açık Stable Diffusion GPU havuzundan görsel üretir."""
    submit_url = "https://aihorde.net/api/v2/generate/async"
    headers = {
        "apikey": "0000000000",
        "Client-Agent": "SecAI:0.9.0:user",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": f"{prompt}, highly detailed, sharp focus, 4k",
        "params": {
            "steps": 25,
            "width": 512,
            "height": 512,
            "cfg_scale": 7.5,
            "sampler_name": "k_euler_a",
        },
    }
    try:
        r = requests.post(submit_url, json=payload, headers=headers, timeout=12)
        if r.status_code != 202:
            return None
        task_id = r.json().get("id")
        if not task_id:
            return None

        status_url = f"https://aihorde.net/api/v2/generate/status/{task_id}"
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            time.sleep(2.5)
            st = requests.get(status_url, headers=headers, timeout=10).json()
            if st.get("done") and st.get("generations"):
                gen = st["generations"][0]
                img_src = gen.get("img", "")
                if img_src.startswith("http"):
                    img_resp = requests.get(img_src, timeout=15)
                    if img_resp.status_code == 200:
                        mime = img_resp.headers.get("content-type", "image/webp")
                        return img_resp.content, mime
                elif img_src:
                    raw = base64.b64decode(img_src)
                    return raw, "image/webp"
            if st.get("faulted"):
                break
    except Exception:
        pass
    return None


def _generate_via_pollinations(prompt: str) -> Optional[tuple[bytes, str]]:
    """Pollinations açık uç noktası üzerinden yedek görsel üretir."""
    encoded_prompt = urllib.parse.quote(prompt.strip())
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nofeed=true"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Referer": "https://pollinations.ai/",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            if data and len(data) > 1000:
                mime = resp.headers.get("Content-Type", "image/jpeg")
                return data, mime
    except Exception:
        pass
    return None


def generate_image(prompt: str) -> Optional[Path]:
    """
    Prompt'tan yüksek kaliteli görsel üretir ve yerel diskte (~/.config/secai/images) saklar.
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return None

    # 1. Öncelik: AI Horde (Stable Diffusion GPU Cluster)
    res = _generate_via_aihorde(clean_prompt)
    ext = "webp"

    # 2. Öncelik: Pollinations
    if not res:
        res = _generate_via_pollinations(clean_prompt)
        ext = "jpg"

    if not res:
        return None

    data, mime = res
    if "png" in mime:
        ext = "png"
    elif "webp" in mime:
        ext = "webp"
    elif "jpeg" in mime or "jpg" in mime:
        ext = "jpg"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(clean_prompt)
    out_file = get_images_dir() / f"secai_{stamp}_{slug}.{ext}"
    out_file.write_bytes(data)
    return out_file


def generate_image_data(prompt: str) -> Optional[dict]:
    """Web arayüzü ve API için dosya yolu + Base64 veri paketini döndürür."""
    img_path = generate_image(prompt)
    if not img_path or not img_path.exists():
        return None

    raw_bytes = img_path.read_bytes()
    mime = "image/png"
    if img_path.suffix == ".webp":
        mime = "image/webp"
    elif img_path.suffix in (".jpg", ".jpeg"):
        mime = "image/jpeg"

    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return {
        "filename": img_path.name,
        "path": str(img_path),
        "prompt": prompt,
        "mime": mime,
        "b64": f"data:{mime};base64,{b64}",
        "size": len(raw_bytes),
    }


def list_generated_images(limit: int = 20) -> list[dict]:
    """Daha önce oluşturulmuş görselleri listeler."""
    img_dir = get_images_dir()
    files = sorted(img_dir.glob("secai_*.*"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    res = []
    for f in files:
        res.append({
            "filename": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return res
