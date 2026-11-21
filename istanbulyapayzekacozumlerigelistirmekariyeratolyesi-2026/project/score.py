"""Profil bazlı uygunluk skoru."""
from __future__ import annotations

import json
import re
from typing import Any

from config import CHAT_MODEL, OLLAMA_URL
from models import load_profil
from rag import ollama_ready


def _heuristic(ilan: dict[str, Any], profil: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(ilan.get(k) or "")
        for k in ("baslik", "kurum", "il", "okas", "ozet_text", "tur")
    ).casefold()
    keys = [k.casefold() for k in profil.get("anahtarlar", [])]
    cities = [c.casefold() for c in profil.get("sehirler", [])]
    hit_keys = [k for k in keys if k and k in text]
    city_hit = any(c and c in (ilan.get("il") or "").casefold() for c in cities)
    sirket = bool(profil.get("sirket_var_mi"))

    # Büyük kurumsal SAP / lisans işleri bireysel için zayıf
    hard = any(x in text for x in ("sap", "basis", "lisans", "sanallaştırma", "sunucu lisansı"))
    yazilim = any(x in text for x in ("yazılım", "web", "mobil", "geliştirme", "python", "api"))

    if not yazilim and not hit_keys:
        label = "Uymaz"
        aksiyon = "Atla"
        gerekce = ["Profil anahtarlarıyla örtüşme zayıf.", "Yazılım geliştirme sinyali düşük."]
    elif hard and not sirket:
        label = "Uymaz" if not hit_keys else "Kısmen"
        aksiyon = "Kazanan firmaya yaz"
        gerekce = [
            "İş deneyimi / yetki belgesi ağırlıklı görünüyor.",
            "Bireysel teklif yerine kazanan firmaya lead daha gerçekçi.",
        ]
        if hit_keys:
            gerekce.append(f"Eşleşen anahtarlar: {', '.join(hit_keys[:5])}")
    elif hit_keys and city_hit:
        label = "Uyar" if sirket else "Kısmen"
        aksiyon = "Teklif ver" if sirket else "Kazanan firmaya yaz"
        gerekce = [
            f"Eşleşen anahtarlar: {', '.join(hit_keys[:5])}",
            f"Şehir uyumu: {ilan.get('il')}",
        ]
        if not sirket:
            gerekce.append("Şirket/yeterlik belgesi yoksa doğrudan teklif zor olabilir.")
    elif hit_keys or yazilim:
        label = "Kısmen"
        aksiyon = "Kazanan firmaya yaz" if not sirket else "İncele"
        gerekce = [
            f"Eşleşen anahtarlar: {', '.join(hit_keys[:5]) or 'yazılım genel'}",
            "Şehir veya yeterlik kriterleri sınırlayıcı olabilir.",
        ]
    else:
        label = "Uymaz"
        aksiyon = "Atla"
        gerekce = ["Profil ile zayıf örtüşme."]

    if ilan.get("durum") == "sonuclanmis":
        aksiyon = "Kazanan firmaya yaz" if ilan.get("kazanan_firma") else "Sonuç bekle"
        gerekce.append("İhale sonuçlanmış; fırsat kazanan firmada.")

    return {
        "skor": label,
        "aksiyon": aksiyon,
        "gerekce": gerekce,
        "kaynak": "heuristic",
    }


def score_ilan(ilan: dict[str, Any], profil: dict[str, Any] | None = None) -> dict[str, Any]:
    profil = profil or load_profil()
    base = _heuristic(ilan, profil)
    if not ollama_ready():
        return base

    try:
        from urllib.request import Request, urlopen

        prompt = (
            "Kamu ihale uygunluk skorla. Sadece JSON döndür.\n"
            'Şema: {"skor":"Uyar|Kısmen|Uymaz","aksiyon":"Teklif ver|Kazanan firmaya yaz|İncele|Atla",'
            '"gerekce":["...","..."]}\n\n'
            f"PROFİL: {json.dumps(profil, ensure_ascii=False)}\n\n"
            f"İLAN: başlık={ilan.get('baslik')}; kurum={ilan.get('kurum')}; il={ilan.get('il')}; "
            f"durum={ilan.get('durum')}; okas={ilan.get('okas')}; "
            f"özet={ilan.get('ozet_text')}; kazanan={ilan.get('kazanan_firma')}\n"
        )
        body = json.dumps(
            {
                "model": CHAT_MODEL,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 220},
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
        content = payload["message"]["content"]
        data = json.loads(content)
        if data.get("skor") not in {"Uyar", "Kısmen", "Uymaz"}:
            return base
        return {
            "skor": data["skor"],
            "aksiyon": data.get("aksiyon") or base["aksiyon"],
            "gerekce": data.get("gerekce") or base["gerekce"],
            "kaynak": "llm",
        }
    except Exception:
        return base


def score_many(ilanlar: list[dict[str, Any]], profil: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    profil = profil or load_profil()
    out = []
    for ilan in ilanlar:
        row = dict(ilan)
        row["uygunluk"] = score_ilan(ilan, profil)
        out.append(row)
    return out
