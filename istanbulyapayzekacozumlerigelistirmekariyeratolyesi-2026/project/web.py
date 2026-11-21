"""EKAP Radar web arayüzü. Sunumdaki akış + çalışan masa. stdlib only."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from leads import lead_for_ilan
from models import get_ilan, ilan_count, list_ilanlar, list_leads, update_lead_durum
from score import score_ilan

ROOT = Path(__file__).resolve().parent / "web"
HOST = "127.0.0.1"
PORT = 8765


def _lead_for(ikn: str) -> dict | None:
    for lead in list_leads():
        if lead.get("ikn") == ikn:
            return lead
    return None


def _json(handler: BaseHTTPRequestHandler, payload: dict | list, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[web] {self.address_string()} {fmt % args}")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/ilanlar":
            qs = parse_qs(parsed.query)
            rows = list_ilanlar(
                q=(qs.get("q") or [""])[0],
                il=(qs.get("il") or [""])[0],
                durum=(qs.get("durum") or [""])[0],
            )
            _json(self, {"toplam": ilan_count(), "kayit": len(rows), "ilanlar": rows})
            return
        if parsed.path == "/api/ilan":
            ikn = (parse_qs(parsed.query).get("ikn") or [""])[0]
            ilan = get_ilan(ikn)
            if not ilan:
                _json(self, {"hata": "İlan yok"}, 404)
                return
            _json(self, {"ilan": ilan, "lead": _lead_for(ikn)})
            return
        if parsed.path in ("/", "/index.html"):
            self._file("index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.css":
            self._file("app.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._file("app.js", "text/javascript; charset=utf-8")
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        data = self._read_json()
        ikn = (data.get("ikn") or "").strip()
        if parsed.path == "/api/skor":
            ilan = get_ilan(ikn)
            if not ilan:
                _json(self, {"hata": "İlan yok"}, 404)
                return
            _json(self, {"uygunluk": score_ilan(ilan)})
            return
        if parsed.path == "/api/lead":
            existing = _lead_for(ikn)
            if existing:
                _json(self, {"lead": existing, "yeni": False})
                return
            ilan = get_ilan(ikn)
            if not ilan or not ilan.get("kazanan_firma"):
                _json(self, {"hata": "Kazanan firma yok"}, 400)
                return
            lead_id, _draft = lead_for_ilan(ikn, notlar="Web arayüzünden")
            lead = next(item for item in list_leads() if item["id"] == lead_id)
            _json(self, {"lead": lead, "yeni": True})
            return
        if parsed.path == "/api/lead/durum":
            durum = data.get("durum") or ""
            if durum not in {"yazilacak", "yazildi", "cevap_yok"}:
                _json(self, {"hata": "Durum geçersiz"}, 400)
                return
            update_lead_durum(int(data["id"]), durum)
            _json(self, {"ok": True})
            return
        self.send_error(404)

    def _file(self, name: str, content_type: str) -> None:
        path = ROOT / name
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"EKAP Radar arayüz: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
