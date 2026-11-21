"""EKAP Radar — Vercel Flask girişi (canlı web)."""
from __future__ import annotations

from flask import Flask, jsonify, request

from leads import lead_for_ilan
from models import get_ilan, ilan_count, init_db, list_ilanlar, list_leads, update_lead_durum
from scrape_ilanlar import import_items, load_seed
from score import score_ilan

app = Flask(__name__)

_ready = False


def ensure_ready() -> None:
    global _ready
    if _ready:
        return
    init_db()
    # Vercel /tmp soğuk başlangıçta boş veya yarım kalabilir; seed'i doldur.
    if ilan_count() < 10:
        import_items(load_seed())
    _ready = True


def lead_for(ikn: str) -> dict | None:
    for lead in list_leads():
        if lead.get("ikn") == ikn:
            return lead
    return None


@app.before_request
def _boot():
    ensure_ready()


@app.get("/api/ilanlar")
def api_ilanlar():
    rows = list_ilanlar(
        q=request.args.get("q", ""),
        il=request.args.get("il", ""),
        durum=request.args.get("durum", ""),
    )
    return jsonify({"toplam": ilan_count(), "kayit": len(rows), "ilanlar": rows})


@app.get("/api/ilan")
def api_ilan():
    ikn = request.args.get("ikn", "")
    ilan = get_ilan(ikn)
    if not ilan:
        return jsonify({"hata": "İlan yok"}), 404
    return jsonify({"ilan": ilan, "lead": lead_for(ikn)})


@app.post("/api/skor")
def api_skor():
    data = request.get_json(silent=True) or {}
    ikn = (data.get("ikn") or "").strip()
    ilan = get_ilan(ikn)
    if not ilan:
        return jsonify({"hata": "İlan yok"}), 404
    return jsonify({"uygunluk": score_ilan(ilan)})


@app.post("/api/lead")
def api_lead():
    data = request.get_json(silent=True) or {}
    ikn = (data.get("ikn") or "").strip()
    existing = lead_for(ikn)
    if existing:
        return jsonify({"lead": existing, "yeni": False})
    ilan = get_ilan(ikn)
    if not ilan or not ilan.get("kazanan_firma"):
        return jsonify({"hata": "Kazanan firma yok"}), 400
    lead_id, _draft = lead_for_ilan(ikn, notlar="Web arayüzünden")
    lead = next(item for item in list_leads() if item["id"] == lead_id)
    return jsonify({"lead": lead, "yeni": True})


@app.post("/api/lead/durum")
def api_lead_durum():
    data = request.get_json(silent=True) or {}
    durum = data.get("durum") or ""
    if durum not in {"yazilacak", "yazildi", "cevap_yok"}:
        return jsonify({"hata": "Durum geçersiz"}), 400
    update_lead_durum(int(data["id"]), durum)
    return jsonify({"ok": True})


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "ilan": ilan_count()})
