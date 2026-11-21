"""Basit eval: beklenen İKN / firma getiriliyor mu?"""
from __future__ import annotations

from models import get_ilan, init_db, list_ilanlar
from score import score_ilan


CASES = [
    {
        "q": "İzmir web mobil",
        "expect_ikn_any": {"2026/2124289", "2026/2039527"},
    },
    {
        "q": "DHMİONLINE yazılım",
        "expect_ikn_any": {"2026/1915537"},
    },
    {
        "ikn": "2026/595393",
        "expect_firma": "BRIDGE BİLİŞİM",
    },
    {
        "ikn": "2026/2084948",
        "expect_firma": "AFET YAZILIM",
    },
]


def main() -> None:
    init_db()
    ok = 0
    for case in CASES:
        if "q" in case:
            rows = list_ilanlar(q=case["q"])
            ikns = {r["ikn"] for r in rows}
            hit = bool(ikns & case["expect_ikn_any"])
            print(("OK" if hit else "FAIL"), "search", case["q"], "->", sorted(ikns)[:5])
            ok += int(hit)
        else:
            ilan = get_ilan(case["ikn"])
            firma = (ilan or {}).get("kazanan_firma") or ""
            hit = case["expect_firma"].casefold() in firma.casefold()
            print(("OK" if hit else "FAIL"), "winner", case["ikn"], "->", firma)
            ok += int(hit)
            if ilan:
                skor = score_ilan(ilan)
                print("   skor:", skor["skor"], skor["aksiyon"])
    print(f"Sonuç: {ok}/{len(CASES)}")


if __name__ == "__main__":
    main()
