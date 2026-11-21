"""SQLite şema ve CRUD yardımcıları."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DB_PATH, DEFAULT_PROFILE


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ilan (
            ikn TEXT PRIMARY KEY,
            baslik TEXT NOT NULL,
            kurum TEXT,
            il TEXT,
            ilan_tarihi TEXT,
            teklif_tarihi TEXT,
            tur TEXT,
            okas TEXT,
            url TEXT,
            durum TEXT,
            ozet_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS firma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unvan TEXT NOT NULL UNIQUE,
            normalized_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sonuc (
            ikn TEXT PRIMARY KEY,
            firma_id INTEGER NOT NULL,
            tutar TEXT,
            sonuc_tarihi TEXT,
            FOREIGN KEY (ikn) REFERENCES ilan(ikn),
            FOREIGN KEY (firma_id) REFERENCES firma(id)
        );

        CREATE TABLE IF NOT EXISTS lead (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_id INTEGER NOT NULL,
            ikn TEXT,
            durum TEXT NOT NULL DEFAULT 'yazilacak',
            notlar TEXT,
            mail_taslagi TEXT,
            olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (firma_id) REFERENCES firma(id),
            FOREIGN KEY (ikn) REFERENCES ilan(ikn)
        );

        CREATE TABLE IF NOT EXISTS profil (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            sehirler TEXT,
            anahtarlar TEXT,
            sirket_var_mi INTEGER,
            notlar TEXT
        );

        CREATE TABLE IF NOT EXISTS basvuru (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ikn TEXT NOT NULL,
            ozet TEXT,
            checklist_json TEXT,
            taslak TEXT NOT NULL,
            uygunluk_json TEXT,
            durum TEXT NOT NULL DEFAULT 'taslak',
            olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ikn) REFERENCES ilan(ikn)
        );
        """
    )
    row = conn.execute("SELECT id FROM profil WHERE id = 1").fetchone()
    if row is None:
        save_profil(DEFAULT_PROFILE, conn)
    conn.commit()
    if own:
        conn.close()


def normalize_name(unvan: str) -> str:
    text = unvan.casefold()
    text = re.sub(r"[^\w\sçğıöşü]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def upsert_ilan(item: dict[str, Any], conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    conn.execute(
        """
        INSERT INTO ilan (
            ikn, baslik, kurum, il, ilan_tarihi, teklif_tarihi,
            tur, okas, url, durum, ozet_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ikn) DO UPDATE SET
            baslik=excluded.baslik,
            kurum=excluded.kurum,
            il=excluded.il,
            ilan_tarihi=excluded.ilan_tarihi,
            teklif_tarihi=excluded.teklif_tarihi,
            tur=excluded.tur,
            okas=excluded.okas,
            url=excluded.url,
            durum=excluded.durum,
            ozet_text=excluded.ozet_text
        """,
        (
            item["ikn"],
            item["baslik"],
            item.get("kurum"),
            item.get("il"),
            item.get("ilan_tarihi"),
            item.get("teklif_tarihi"),
            item.get("tur"),
            item.get("okas"),
            item.get("url"),
            item.get("durum", "aktif"),
            item.get("ozet_text", ""),
        ),
    )
    conn.commit()
    if own:
        conn.close()


def get_or_create_firma(unvan: str, conn: sqlite3.Connection | None = None) -> int:
    own = conn is None
    conn = conn or connect()
    normalized = normalize_name(unvan)
    row = conn.execute(
        "SELECT id FROM firma WHERE normalized_name = ?",
        (normalized,),
    ).fetchone()
    if row:
        firma_id = row["id"]
    else:
        cur = conn.execute(
            "INSERT INTO firma (unvan, normalized_name) VALUES (?, ?)",
            (unvan.strip(), normalized),
        )
        firma_id = cur.lastrowid
        conn.commit()
    if own:
        conn.close()
    return int(firma_id)


def upsert_sonuc(
    ikn: str,
    unvan: str,
    tutar: str | None = None,
    sonuc_tarihi: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    own = conn is None
    conn = conn or connect()
    firma_id = get_or_create_firma(unvan, conn)
    conn.execute(
        """
        INSERT INTO sonuc (ikn, firma_id, tutar, sonuc_tarihi)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(ikn) DO UPDATE SET
            firma_id=excluded.firma_id,
            tutar=excluded.tutar,
            sonuc_tarihi=excluded.sonuc_tarihi
        """,
        (ikn, firma_id, tutar, sonuc_tarihi or datetime.now().date().isoformat()),
    )
    conn.execute("UPDATE ilan SET durum = 'sonuclanmis' WHERE ikn = ?", (ikn,))
    conn.commit()
    if own:
        conn.close()


def list_ilanlar(
    q: str = "",
    il: str = "",
    durum: str = "",
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own = conn is None
    conn = conn or connect()
    sql = """
        SELECT i.*, f.unvan AS kazanan_firma, s.tutar AS kazanan_tutar
        FROM ilan i
        LEFT JOIN sonuc s ON s.ikn = i.ikn
        LEFT JOIN firma f ON f.id = s.firma_id
        WHERE 1=1
    """
    params: list[Any] = []
    for token in [t for t in re.split(r"\s+", q.strip()) if t]:
        like = f"%{token}%"
        sql += (
            " AND (i.baslik LIKE ? OR i.kurum LIKE ? OR i.il LIKE ? OR i.okas LIKE ?"
            " OR i.ozet_text LIKE ? OR i.ikn LIKE ? OR IFNULL(f.unvan, '') LIKE ?)"
        )
        params.extend([like, like, like, like, like, like, like])
    if il.strip():
        sql += " AND i.il LIKE ?"
        params.append(f"%{il.strip()}%")
    if durum.strip():
        sql += " AND i.durum = ?"
        params.append(durum.strip())
    sql += " ORDER BY COALESCE(i.teklif_tarihi, i.ilan_tarihi) DESC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    if own:
        conn.close()
    return rows


def get_ilan(ikn: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    own = conn is None
    conn = conn or connect()
    row = conn.execute(
        """
        SELECT i.*, f.unvan AS kazanan_firma, s.tutar AS kazanan_tutar, s.sonuc_tarihi
        FROM ilan i
        LEFT JOIN sonuc s ON s.ikn = i.ikn
        LEFT JOIN firma f ON f.id = s.firma_id
        WHERE i.ikn = ?
        """,
        (ikn,),
    ).fetchone()
    if own:
        conn.close()
    return dict(row) if row else None


def list_firmalar(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    conn = conn or connect()
    rows = conn.execute(
        """
        SELECT f.id, f.unvan,
               COUNT(s.ikn) AS ihale_sayisi,
               GROUP_CONCAT(DISTINCT i.kurum) AS kurumlar,
               MAX(s.sonuc_tarihi) AS son_kazanma
        FROM firma f
        LEFT JOIN sonuc s ON s.firma_id = f.id
        LEFT JOIN ilan i ON i.ikn = s.ikn
        GROUP BY f.id
        ORDER BY ihale_sayisi DESC, f.unvan
        """
    ).fetchall()
    if own:
        conn.close()
    return [dict(r) for r in rows]


def get_firma(firma_id: int, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    own = conn is None
    conn = conn or connect()
    row = conn.execute("SELECT * FROM firma WHERE id = ?", (firma_id,)).fetchone()
    if not row:
        if own:
            conn.close()
        return None
    ihaleler = conn.execute(
        """
        SELECT i.ikn, i.baslik, i.kurum, i.il, s.tutar, s.sonuc_tarihi
        FROM sonuc s
        JOIN ilan i ON i.ikn = s.ikn
        WHERE s.firma_id = ?
        ORDER BY s.sonuc_tarihi DESC
        """,
        (firma_id,),
    ).fetchall()
    data = dict(row)
    data["ihaleler"] = [dict(x) for x in ihaleler]
    if own:
        conn.close()
    return data


def save_profil(profil: dict[str, Any], conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    conn.execute(
        """
        INSERT INTO profil (id, sehirler, anahtarlar, sirket_var_mi, notlar)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            sehirler=excluded.sehirler,
            anahtarlar=excluded.anahtarlar,
            sirket_var_mi=excluded.sirket_var_mi,
            notlar=excluded.notlar
        """,
        (
            json.dumps(profil.get("sehirler", []), ensure_ascii=False),
            json.dumps(profil.get("anahtarlar", []), ensure_ascii=False),
            1 if profil.get("sirket_var_mi") else 0,
            profil.get("notlar", ""),
        ),
    )
    conn.commit()
    if own:
        conn.close()


def load_profil(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    conn = conn or connect()
    row = conn.execute("SELECT * FROM profil WHERE id = 1").fetchone()
    if own:
        conn.close()
    if not row:
        return dict(DEFAULT_PROFILE)
    return {
        "sehirler": json.loads(row["sehirler"] or "[]"),
        "anahtarlar": json.loads(row["anahtarlar"] or "[]"),
        "sirket_var_mi": bool(row["sirket_var_mi"]),
        "notlar": row["notlar"] or "",
    }


def create_lead(
    firma_id: int,
    ikn: str | None,
    mail_taslagi: str,
    notlar: str = "",
    conn: sqlite3.Connection | None = None,
) -> int:
    own = conn is None
    conn = conn or connect()
    cur = conn.execute(
        """
        INSERT INTO lead (firma_id, ikn, durum, notlar, mail_taslagi)
        VALUES (?, ?, 'yazilacak', ?, ?)
        """,
        (firma_id, ikn, notlar, mail_taslagi),
    )
    conn.commit()
    lead_id = int(cur.lastrowid)
    if own:
        conn.close()
    return lead_id


def list_leads(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    conn = conn or connect()
    rows = conn.execute(
        """
        SELECT l.*, f.unvan AS firma_unvan, i.baslik AS ihale_baslik
        FROM lead l
        JOIN firma f ON f.id = l.firma_id
        LEFT JOIN ilan i ON i.ikn = l.ikn
        ORDER BY l.olusturma_tarihi DESC
        """
    ).fetchall()
    if own:
        conn.close()
    return [dict(r) for r in rows]


def update_lead_durum(lead_id: int, durum: str, conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    conn.execute("UPDATE lead SET durum = ? WHERE id = ?", (durum, lead_id))
    conn.commit()
    if own:
        conn.close()


def ilan_count(conn: sqlite3.Connection | None = None) -> int:
    own = conn is None
    conn = conn or connect()
    n = conn.execute("SELECT COUNT(*) AS c FROM ilan").fetchone()["c"]
    if own:
        conn.close()
    return int(n)


def create_basvuru(
    ikn: str,
    ozet: str,
    checklist: list[Any],
    taslak: str,
    uygunluk: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    own = conn is None
    conn = conn or connect()
    cur = conn.execute(
        """
        INSERT INTO basvuru (ikn, ozet, checklist_json, taslak, uygunluk_json, durum)
        VALUES (?, ?, ?, ?, ?, 'taslak')
        """,
        (
            ikn,
            ozet,
            json.dumps(checklist, ensure_ascii=False),
            taslak,
            json.dumps(uygunluk or {}, ensure_ascii=False),
        ),
    )
    conn.commit()
    basvuru_id = int(cur.lastrowid)
    if own:
        conn.close()
    return basvuru_id


def list_basvurular(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    own = conn is None
    conn = conn or connect()
    rows = conn.execute(
        """
        SELECT b.*, i.baslik AS ihale_baslik, i.kurum
        FROM basvuru b
        LEFT JOIN ilan i ON i.ikn = b.ikn
        ORDER BY b.olusturma_tarihi DESC
        """
    ).fetchall()
    if own:
        conn.close()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["checklist"] = json.loads(item.get("checklist_json") or "[]")
        except json.JSONDecodeError:
            item["checklist"] = []
        try:
            item["uygunluk"] = json.loads(item.get("uygunluk_json") or "{}")
        except json.JSONDecodeError:
            item["uygunluk"] = {}
        out.append(item)
    return out


def update_basvuru_durum(basvuru_id: int, durum: str, conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    conn.execute("UPDATE basvuru SET durum = ? WHERE id = ?", (durum, basvuru_id))
    conn.commit()
    if own:
        conn.close()
