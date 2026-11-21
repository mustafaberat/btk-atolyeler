"""Kazanan firmaya insan onaylı mail taslağı."""
from __future__ import annotations

from typing import Any

from config import CHAT_MODEL, OLLAMA_URL
from models import create_lead, get_firma, get_ilan, get_or_create_firma, load_profil
from runtime import ollama_ready


def draft_mail(
    firma_unvan: str,
    ikn: str | None = None,
    profil: dict[str, Any] | None = None,
) -> str:
    profil = profil or load_profil()
    ilan = get_ilan(ikn) if ikn else None
    ihale_line = ""
    if ilan:
        ihale_line = (
            f"Özellikle {ilan.get('kurum')} bünyesindeki "
            f"“{ilan.get('baslik')}” (İKN {ilan.get('ikn')}) işiyle ilgili "
            f"alt yüklenici / freelance destek sunabileceğimi düşünüyorum."
        )
    stack = ", ".join(profil.get("anahtarlar", [])[:6]) or "yazılım geliştirme"
    cities = ", ".join(profil.get("sehirler", [])[:3]) or "Türkiye"

    fallback = (
        f"Konu: {firma_unvan} — Yazılım işbirliği / alt yüklenici teklifi\n\n"
        f"Merhaba {firma_unvan} ekibi,\n\n"
        f"Ben yazılım geliştiricisiyim. Odak alanlarım: {stack}. "
        f"Çalışabileceğim şehirler: {cities}.\n\n"
        f"{ihale_line}\n\n"
        "Kamu bilişim işlerinde geliştirme, bakım veya entegrasyon tarafında "
        "kısa süreli veya proje bazlı destek verebilirim. "
        "Uygun görürseniz 15 dakikalık bir ön görüşme planlamaktan memnuniyet duyarım.\n\n"
        "İyi çalışmalar,\n"
        "Mustafa Berat Aru"
    )

    if not ollama_ready():
        return fallback

    try:
        import json
        from urllib.request import Request, urlopen

        prompt = (
            "Kısa, profesyonel Türkçe işbirliği e-postası yaz. "
            "Abartma, spam gibi durma. Konu satırı + gövde. "
            "Otomatik gönderilmeyecek; insan kopyalayacak.\n\n"
            f"Firma: {firma_unvan}\nProfil: {json.dumps(profil, ensure_ascii=False)}\n"
            f"İhale: {json.dumps({k: ilan.get(k) for k in ('ikn','baslik','kurum','il')}, ensure_ascii=False) if ilan else 'yok'}"
        )
        body = json.dumps(
            {
                "model": CHAT_MODEL,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 350},
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        req = Request(
            f"{OLLAMA_URL}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode())
        text = (payload["message"]["content"] or "").strip()
        return text or fallback
    except Exception:
        return fallback


def save_lead_draft(firma_unvan: str, ikn: str | None = None, notlar: str = "") -> tuple[int, str]:
    firma_id = get_or_create_firma(firma_unvan)
    draft = draft_mail(firma_unvan, ikn)
    lead_id = create_lead(firma_id, ikn, draft, notlar=notlar)
    return lead_id, draft


def lead_for_ilan(ikn: str, notlar: str = "") -> tuple[int, str]:
    ilan = get_ilan(ikn)
    if not ilan:
        raise ValueError(f"İlan yok: {ikn}")
    unvan = ilan.get("kazanan_firma")
    if not unvan:
        raise ValueError("Bu ilanda kazanan firma yok.")
    return save_lead_draft(unvan, ikn, notlar)
