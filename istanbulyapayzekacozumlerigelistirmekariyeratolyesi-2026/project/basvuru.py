"""İhale dokümanını inceleyip başvuru taslağı üretir; aşamaları raporlar."""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.request import Request, urlopen

from config import CHAT_MODEL, OLLAMA_URL, RAW_DIR
from models import create_basvuru, get_ilan, load_profil
from rag import ollama_ready
from score import score_ilan

StageCb = Callable[[str, str, dict[str, Any] | None], None]

ASAMALAR = [
    ("ilan_oku", "İlanı SQLite'tan oku"),
    ("dokuman_incele", "Ham dokümanı incele (data/raw)"),
    ("rag_parca", "İlgili parçaları getir (RAG)"),
    ("ozet_checklist", "Özet ve kontrol listesi çıkar"),
    ("uygunluk", "Profil uygunluğunu skorla"),
    ("taslak", "Başvuru taslağını yaz"),
    ("kaydet", "SQLite'a kaydet"),
]


def _emit(on_stage: StageCb | None, key: str, status: str, detail: dict[str, Any] | None = None) -> None:
    if on_stage:
        on_stage(key, status, detail)


def _raw_path(ikn: str):
    return RAW_DIR / f"{ikn.replace('/', '_')}.md"


def _read_raw(ikn: str) -> str:
    path = _raw_path(ikn)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _rag_snippets(ikn: str, ilan: dict[str, Any]) -> list[str]:
    question = (
        f"{ilan.get('baslik')} {ilan.get('ikn')} ihalesinde istenenler, "
        "süre, yer, yeterlik ve kapsam nedir?"
    )
    try:
        from rag import retrieve_and_rerank

        ranked = retrieve_and_rerank(question, k=6, top_n=3)
        out = []
        for doc, score in ranked:
            if doc.metadata.get("source") == ikn or ikn in doc.page_content:
                out.append(doc.page_content[:600])
        if not out:
            out = [doc.page_content[:600] for doc, _ in ranked]
        return out
    except Exception:
        return []


def _heuristic_checklist(ilan: dict[str, Any], profil: dict[str, Any]) -> list[str]:
    items = [
        f"İKN: {ilan.get('ikn')}",
        f"Teklif son tarihi: {ilan.get('teklif_tarihi') or 'belirtilmemiş'}",
        f"Kurum: {ilan.get('kurum') or '-'}",
        f"İl / yer: {ilan.get('il') or '-'}",
        f"OKAS: {ilan.get('okas') or '-'}",
    ]
    if not profil.get("sirket_var_mi"):
        items.append("Uyarı: Tüzel kişilik yoksa doğrudan teklif zor olabilir; alt yüklenici / lead düşün.")
    text = f"{ilan.get('baslik')} {ilan.get('ozet_text')}".casefold()
    if "yetki" in text or "belge" in text:
        items.append("Kontrol: Kamu bilişim yetki belgesi / benzer iş belgesi gerekebilir.")
    if "e-ihale" in text or "e ihale" in text:
        items.append("Kontrol: EKAP e-ihale üzerinden teklif yükleme.")
    items.append("Taslak insan onaylıdır; resmi başvuru EKAP'tan yapılır.")
    return items


def _fallback_draft(ilan: dict[str, Any], profil: dict[str, Any], ozet: str, checklist: list[str]) -> str:
    stack = ", ".join(profil.get("anahtarlar", [])[:6]) or "yazılım geliştirme"
    cities = ", ".join(profil.get("sehirler", [])[:3]) or "Türkiye"
    checks = "\n".join(f"- {c}" for c in checklist)
    return (
        f"# Başvuru / Niyet Taslağı\n\n"
        f"**İKN:** {ilan.get('ikn')}\n"
        f"**İhale:** {ilan.get('baslik')}\n"
        f"**Kurum:** {ilan.get('kurum')}\n"
        f"**Teklif tarihi:** {ilan.get('teklif_tarihi')}\n\n"
        f"## Kısa özet\n{ozet}\n\n"
        f"## Kontrol listesi\n{checks}\n\n"
        f"## Niyet metni (taslak)\n\n"
        f"Sayın İdare / ilgili birim,\n\n"
        f"{ilan.get('baslik')} (İKN {ilan.get('ikn')}) ihalesine ilişkin olarak "
        f"yazılım geliştirme ve destek kapasitemizi sunmak isteriz. "
        f"Odak alanlarımız: {stack}. Çalışabileceğimiz şehirler: {cities}.\n\n"
        f"Kapsam: web/mobil geliştirme, bakım, entegrasyon ve teknik destek. "
        f"Gerekli yeterlik ve belgeler başvuru öncesi tamamlanacaktır.\n\n"
        f"Saygılarımızla,\nMustafa Berat Aru\n\n"
        f"---\n*Bu metin otomatik taslaktır; gönderilmez. İnsan gözden geçirmelidir.*"
    )


def _looks_repetitive(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 8:
        return False
    uniq = len(set(lines))
    return uniq / len(lines) < 0.45


def _llm_draft(ilan: dict[str, Any], profil: dict[str, Any], ozet: str, checklist: list[str], kaynak: str) -> str:
    prompt = (
        "Kamu ihalesi için kısa Türkçe BAŞVURU / NİYET TASLAĞI yaz. "
        "En fazla 250 kelime. Tekrar etme. "
        "Bölümler: Özet, Kontrol listesi, Niyet metni, Eksik belgeler. "
        "Otomatik gönderilmeyecek.\n\n"
        f"PROFİL: {json.dumps(profil, ensure_ascii=False)}\n"
        f"İLAN: {json.dumps({k: ilan.get(k) for k in ('ikn','baslik','kurum','il','teklif_tarihi','okas','durum')}, ensure_ascii=False)}\n"
        f"ÖZET: {ozet}\n"
        f"CHECKLIST: {json.dumps(checklist, ensure_ascii=False)}\n"
        f"KAYNAK PARÇA:\n{kaynak[:1800]}\n"
    )
    body = json.dumps(
        {
            "model": CHAT_MODEL,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 380, "repeat_penalty": 1.25},
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = Request(
        f"{OLLAMA_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode())
    text = (payload["message"]["content"] or "").strip()
    if not text or _looks_repetitive(text):
        return ""
    return text

def hazirla_basvuru(ikn: str, on_stage: StageCb | None = None) -> dict[str, Any]:
    """Aşama aşama başvuru taslağı üretir. on_stage(key, status, detail) ile UI güncellenir."""
    result: dict[str, Any] = {"ikn": ikn, "asamalar": []}

    # 1
    _emit(on_stage, "ilan_oku", "running")
    ilan = get_ilan(ikn)
    if not ilan:
        _emit(on_stage, "ilan_oku", "error", {"mesaj": f"İlan yok: {ikn}"})
        raise ValueError(f"İlan yok: {ikn}")
    _emit(on_stage, "ilan_oku", "done", {"baslik": ilan["baslik"], "kurum": ilan.get("kurum")})
    result["ilan"] = ilan

    # 2
    _emit(on_stage, "dokuman_incele", "running")
    raw = _read_raw(ikn)
    if not raw:
        raw = ilan.get("ozet_text") or ilan.get("baslik") or ""
        _emit(on_stage, "dokuman_incele", "done", {"kaynak": "ozet_text (raw yok)", "karakter": len(raw)})
    else:
        _emit(on_stage, "dokuman_incele", "done", {"kaynak": str(_raw_path(ikn).name), "karakter": len(raw)})
    result["raw_excerpt"] = raw[:800]

    # 3
    _emit(on_stage, "rag_parca", "running")
    snippets = _rag_snippets(ikn, ilan)
    if snippets:
        _emit(on_stage, "rag_parca", "done", {"parca_sayisi": len(snippets)})
    else:
        _emit(on_stage, "rag_parca", "done", {"parca_sayisi": 0, "not": "Chroma yok veya boş; özet kullanıldı"})
    result["rag_snippets"] = snippets

    # 4
    _emit(on_stage, "ozet_checklist", "running")
    profil = load_profil()
    ozet = (ilan.get("ozet_text") or "").strip() or raw[:400]
    checklist = _heuristic_checklist(ilan, profil)
    _emit(on_stage, "ozet_checklist", "done", {"checklist_adet": len(checklist)})
    result["ozet"] = ozet
    result["checklist"] = checklist

    # 5
    _emit(on_stage, "uygunluk", "running")
    uygunluk = score_ilan(ilan, profil)
    _emit(
        on_stage,
        "uygunluk",
        "done",
        {"skor": uygunluk.get("skor"), "aksiyon": uygunluk.get("aksiyon"), "kaynak": uygunluk.get("kaynak")},
    )
    result["uygunluk"] = uygunluk

    # 6
    _emit(on_stage, "taslak", "running")
    kaynak = "\n\n".join(snippets) if snippets else raw
    kaynak_llm = "llm" if ollama_ready() else "sablon"
    try:
        if ollama_ready():
            taslak = _llm_draft(ilan, profil, ozet, checklist, kaynak) or _fallback_draft(
                ilan, profil, ozet, checklist
            )
        else:
            taslak = _fallback_draft(ilan, profil, ozet, checklist)
    except Exception:
        taslak = _fallback_draft(ilan, profil, ozet, checklist)
        kaynak_llm = "sablon"
    _emit(on_stage, "taslak", "done", {"kaynak": kaynak_llm, "karakter": len(taslak)})
    result["taslak"] = taslak
    result["taslak_kaynak"] = kaynak_llm

    # 7
    _emit(on_stage, "kaydet", "running")
    basvuru_id = create_basvuru(
        ikn=ikn,
        ozet=ozet,
        checklist=checklist,
        taslak=taslak,
        uygunluk=uygunluk,
    )
    _emit(on_stage, "kaydet", "done", {"basvuru_id": basvuru_id, "db": "data/app.db"})
    result["basvuru_id"] = basvuru_id
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Başvuru taslağı üret")
    parser.add_argument("--ikn", required=True)
    args = parser.parse_args()

    def _print(key: str, status: str, detail: dict[str, Any] | None) -> None:
        label = next((a[1] for a in ASAMALAR if a[0] == key), key)
        extra = f" | {detail}" if detail else ""
        print(f"[{status}] {label}{extra}")

    out = hazirla_basvuru(args.ikn, on_stage=_print)
    print("\n=== TASLAK ===\n")
    print(out["taslak"])
    print(f"\nKayıt id: {out['basvuru_id']}")
