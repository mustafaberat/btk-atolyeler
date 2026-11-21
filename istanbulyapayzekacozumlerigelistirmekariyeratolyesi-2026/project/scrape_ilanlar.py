"""İlan toplama: MVP'de seed JSON yükler; isteğe bağlı canlı kaynak denemesi yapar."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from config import RAW_DIR, SEED_PATH
from models import init_db, upsert_ilan, upsert_sonuc, connect, ilan_count


def load_seed(path: Path = SEED_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_items(items: list[dict]) -> int:
    init_db()
    conn = connect()
    n = 0
    for item in items:
        payload = {k: v for k, v in item.items() if k != "kazanan"}
        upsert_ilan(payload, conn)
        kazanan = item.get("kazanan")
        if kazanan and kazanan.get("unvan"):
            upsert_sonuc(
                item["ikn"],
                kazanan["unvan"],
                kazanan.get("tutar"),
                kazanan.get("sonuc_tarihi"),
                conn,
            )
        try:
            raw = RAW_DIR / f"{item['ikn'].replace('/', '_')}.md"
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            raw.write_text(
                f"# {item['baslik']}\n\n"
                f"İKN: {item['ikn']}\n"
                f"Kurum: {item.get('kurum')}\n"
                f"İl: {item.get('il')}\n"
                f"İlan tarihi: {item.get('ilan_tarihi')}\n"
                f"Teklif tarihi: {item.get('teklif_tarihi')}\n"
                f"Tür: {item.get('tur')}\n"
                f"OKAS: {item.get('okas')}\n"
                f"Durum: {item.get('durum')}\n"
                f"URL: {item.get('url')}\n\n"
                f"{item.get('ozet_text', '')}\n",
                encoding="utf-8",
            )
        except OSError:
            # Canlı ortamda ham metin yazılamasa da ilan kaydı devam eder.
            pass
        n += 1
    conn.close()
    return n


def try_live_ekapveri(query: str = "yazılım", limit: int = 5) -> list[dict]:
    """Best-effort canlı deneme. Başarısız olursa boş döner; seed kullanılır."""
    url = f"https://ekapveri.com/?s={query}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 EKAP-Radar-MVP"})
        with urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    found = re.findall(r"/ihale/ekap-(\d{4})-(\d+)/", html)
    items = []
    seen = set()
    for year, num in found:
        ikn = f"{year}/{num}"
        if ikn in seen:
            continue
        seen.add(ikn)
        items.append(
            {
                "ikn": ikn,
                "baslik": f"Canlı bulunan yazılım ihalesi {ikn}",
                "kurum": "EKAPVeri (önizleme)",
                "il": "",
                "ilan_tarihi": "",
                "teklif_tarihi": "",
                "tur": "Hizmet",
                "okas": "72260000",
                "url": f"https://ekapveri.com/ihale/ekap-{year}-{num}/",
                "durum": "aktif",
                "ozet_text": f"Canlı aramadan bulunan kayıt. Detay için {ikn} incelenmeli.",
                "kazanan": None,
            }
        )
        if len(items) >= limit:
            break
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="EKAP Radar ilan yükleyici")
    parser.add_argument("--live", action="store_true", help="Canlı kaynak dene (best-effort)")
    parser.add_argument("--seed-only", action="store_true", default=True)
    args = parser.parse_args()

    items = load_seed()
    if args.live:
        live = try_live_ekapveri()
        by_ikn = {x["ikn"]: x for x in items}
        for row in live:
            by_ikn.setdefault(row["ikn"], row)
        items = list(by_ikn.values())

    n = import_items(items)
    print(f"Yüklenen/güncellenen ilan: {n}")
    print(f"Veritabanı toplam: {ilan_count()}")


if __name__ == "__main__":
    main()
