"""SecAI Smart Mode (Akıllı Model Yönlendirici & Asistanı).

Karmaşık analizleri (C/C++ tersine mühendislik, bellek dump incelemesi, ROP/exploit zinciri)
algılar ve yerel küçük model yerine yüksek akıl yürütme kapasitesine sahip bulut/büyük modelleri
(Groq 120B, OpenRouter 32B/70B, DeepSeek R1, Gemini) önerir veya yönlendirir.
"""

import re
from typing import Any, Dict, Optional, Tuple

from secai.config import (
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    get_active_llm_info,
    load_settings,
    save_settings,
)

# Karmaşık Güvenlik Görevlerini Tanıyan Regex ve Anahtar Kalıplar
COMPLEX_PATTERNS = [
    (
        r"\b(decompile|decompiled|decompiler|disassemble|disassembled|disassembler|dekompile|disas|ghidra|ida pro|radare2|\br2\b|objdump|readelf|gdb|pwndbg|peda|reverse engineering|tersine m[uü]hendislik)\b",
        "Tersine Mühendislik & İkili Dosya (Binary) Analizi",
    ),
    (
        r"\b(buffer overflow|stack overflow|heap overflow|use after free|\buaf\b|rop chain|gadget|shellcode|format string|ret2libc|heap exploitation)\b",
        "Bellek Bozulması (Memory Corruption) & Exploit Geliştirme",
    ),
    (
        r"\b(kernel exploit|privilege escalation chain|multi-step exploit|exploit zinciri|weaponization|edr bypass|amsi bypass)\b",
        "Çok Adımlı Yetki Yükseltme & Exploit Mantığı",
    ),
    (
        r"\b(memory dump|core dump|volatility|ram dump|bellegin dökümü|crash dump|segfault at [0-9a-fA-F]+)\b",
        "Adli Bellek (Memory Forensics) & Dump Analizi",
    ),
    (
        r"\b(malware deobfuscation|packed binary|upx unpack|anti-debugging|yara kuralı|yara rule)\b",
        "Zararlı Yazılım Analizi & Deobfuscation",
    ),
]


def is_complex_security_task(prompt: str) -> Tuple[bool, str]:
    """
    Kullanıcı girdisini veya dosya/çıktı analizini tarar.
    Karmaşık bir analiz görevi içeriyorsa (True, 'Görev Açıklaması') döner.
    """
    clean = prompt.lower()

    for pattern, description in COMPLEX_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return True, description

    # C/C++ Assembly kod tespiti (özel göstergeler: asm blokları, ham pointer aritmetiği)
    if (
        ("typedef" in clean or "#include <" in clean or "int main(" in clean)
        and ("*" in clean or "malloc" in clean or "free(" in clean or "memcpy" in clean or "ptr" in clean)
    ):
        return True, "C/C++ Kaynak Kodu & Pointer / Bellek Güvenliği Analizi"

    # Hex shellcode veya ROP gadget tespiti
    if len(re.findall(r"\\x[0-9a-fA-F]{2}", prompt)) >= 8 or len(re.findall(r"0x[0-9a-fA-F]{4,16}", prompt)) >= 10:
        return True, "Hex Shellcode / ROP Gadget Analizi"

    return False, ""


def is_smart_mode_enabled() -> bool:
    """Smart Mode ayarının açık olup olmadığını kontrol eder."""
    settings = load_settings()
    return bool(settings.get("smart_mode", True))


def set_smart_mode(enabled: bool) -> None:
    """Smart Mode ayarını açar veya kapatır."""
    save_settings({"smart_mode": enabled})


def recommend_or_route_model(
    query: str,
    current_settings: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Girdiyi analiz eder. Eğer görev karmaşıksa ve kullanıcı yereldeki küçük bir modeldeyse,
    kullanıcıya önerilecek veya yönlendirilecek en uygun bulut/büyük modeli döner.
    """
    if not is_smart_mode_enabled():
        return None

    is_complex, task_desc = is_complex_security_task(query)
    if not is_complex:
        return None

    settings = current_settings or load_settings()
    llm_info = get_active_llm_info()
    current_provider = llm_info.get("provider", "ollama")
    current_model = llm_info.get("model", "")

    # Eğer kullanıcı zaten 120B/70B veya derin akıl yürüten bir modeldeyse yönlendirmeye gerek yok
    heavy_models = ("120b", "70b", "deepseek-reasoner", "gemini-3-flash-preview")
    if any(h in current_model.lower() for h in heavy_models) and current_provider != "ollama":
        return None

    # En güçlü adayları kullanıcı anahtarlarına göre sırayla tara
    candidates = []

    # 1. Groq (Ultra hızlı 120B / 27B)
    if settings.get("groq_api_key", "").strip():
        candidates.append({
            "provider": "groq",
            "model": settings.get("groq_model", DEFAULT_GROQ_MODEL),
            "label": f"Groq LPU ({settings.get('groq_model', DEFAULT_GROQ_MODEL)})",
            "reason": "Ultra hızlı 120B/27B karmaşık mantık ve exploit akıl yürütme",
        })

    # 2. OpenRouter (Universal Qwen-Coder 32B veya Llama-3.3 70B)
    if settings.get("openrouter_api_key", "").strip():
        candidates.append({
            "provider": "openrouter",
            "model": settings.get("openrouter_model", DEFAULT_OPENROUTER_MODEL),
            "label": f"OpenRouter ({settings.get('openrouter_model', DEFAULT_OPENROUTER_MODEL)})",
            "reason": "Geniş parametreli uzman kodlayıcı ve tersine mühendislik modeli",
        })

    # 3. DeepSeek Reasoning (R1)
    if settings.get("deepseek_api_key", "").strip():
        candidates.append({
            "provider": "deepseek",
            "model": settings.get("deepseek_model", "deepseek-reasoner"),
            "label": "DeepSeek R1 (deepseek-reasoner)",
            "reason": "Derin matematiksel ve kriptografik düşünce zinciri",
        })

    # 4. Google Gemini
    if settings.get("gemini_api_key", "").strip():
        candidates.append({
            "provider": "gemini",
            "model": settings.get("gemini_model", "gemini-3-flash-preview"),
            "label": f"Google Gemini ({settings.get('gemini_model', 'gemini-3-flash-preview')})",
            "reason": "Büyük bağlam penceresi ve gelişmiş kod sentezi",
        })

    if not candidates:
        return {
            "is_complex": True,
            "task_desc": task_desc,
            "current_provider": current_provider,
            "current_model": current_model,
            "has_cloud_alternative": False,
            "message": (
                f"⚡ [Smart Mode]: Bu işlem ({task_desc}) derin akıl yürütme gerektiriyor. "
                "Daha yüksek doğruluk için `/api` ile Groq (120B) veya OpenRouter (Qwen-32B) anahtarı eklemeniz önerilir."
            ),
        }

    chosen = candidates[0]
    return {
        "is_complex": True,
        "task_desc": task_desc,
        "current_provider": current_provider,
        "current_model": current_model,
        "has_cloud_alternative": True,
        "recommended_provider": chosen["provider"],
        "recommended_model": chosen["model"],
        "recommended_label": chosen["label"],
        "recommended_reason": chosen["reason"],
        "message": (
            f"⚡ [Smart Mode]: Tespit edilen işlem: [bold yellow]{task_desc}[/bold yellow].\n"
            f"Bu derin analiz için yerel {current_model} yerine [bold cyan]{chosen['label']}[/bold cyan] önerilir."
        ),
    }


def switch_to_recommended_model(rec: Dict[str, Any]) -> bool:
    """Önerilen modele geçiş yapar ve ayarları kaydeder."""
    target_provider = rec.get("recommended_provider")
    target_model = rec.get("recommended_model")
    if not target_provider or not target_model:
        return False

    update_payload: Dict[str, Any] = {"provider": target_provider}
    if target_provider == "groq":
        update_payload["groq_model"] = target_model
    elif target_provider == "openrouter":
        update_payload["openrouter_model"] = target_model
    elif target_provider == "deepseek":
        update_payload["deepseek_model"] = target_model
    elif target_provider == "gemini":
        update_payload["gemini_model"] = target_model

    save_settings(update_payload)
    return True
