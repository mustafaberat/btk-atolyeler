"""Sonuç / kazanan firma güncelleme yardımcıları."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import SEED_PATH
from models import init_db, upsert_sonuc, get_ilan, list_firmalar


def sync_winners_from_seed(path: Path = SEED_PATH) -> int:
    init_db()
    items = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for item in items:
        kazanan = item.get("kazanan")
        if not kazanan or not kazanan.get("unvan"):
            continue
        if get_ilan(item["ikn"]) is None:
            continue
        upsert_sonuc(
            item["ikn"],
            kazanan["unvan"],
            kazanan.get("tutar"),
            kazanan.get("sonuc_tarihi"),
        )
        n += 1
    return n


def add_winner(ikn: str, unvan: str, tutar: str = "", sonuc_tarihi: str = "") -> None:
    init_db()
    if get_ilan(ikn) is None:
        raise SystemExit(f"İlan yok: {ikn}. Önce scrape_ilanlar.py çalıştır.")
    upsert_sonuc(ikn, unvan, tutar or None, sonuc_tarihi or None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kazanan firma senkronu")
    parser.add_argument("--from-seed", action="store_true", help="Seed'deki kazananları yükle")
    parser.add_argument("--ikn", help="Manuel İKN")
    parser.add_argument("--firma", help="Kazanan unvan")
    parser.add_argument("--tutar", default="")
    parser.add_argument("--tarih", default="")
    parser.add_argument("--list", action="store_true", help="Firmaları listele")
    args = parser.parse_args()

    if args.list:
        init_db()
        for row in list_firmalar():
            print(f"{row['id']:>3} | {row['ihale_sayisi']} ihale | {row['unvan']}")
        return

    if args.from_seed:
        n = sync_winners_from_seed()
        print(f"Kazanan güncellendi: {n}")
        return

    if args.ikn and args.firma:
        add_winner(args.ikn, args.firma, args.tutar, args.tarih)
        print(f"OK {args.ikn} -> {args.firma}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
