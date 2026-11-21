"""EKAP Radar — Streamlit MVP."""
from __future__ import annotations

import streamlit as st

from basvuru import ASAMALAR, hazirla_basvuru
from leads import draft_mail, lead_for_ilan, save_lead_draft
from models import (
    get_firma,
    get_ilan,
    ilan_count,
    init_db,
    list_basvurular,
    list_firmalar,
    list_ilanlar,
    list_leads,
    load_profil,
    save_profil,
    update_basvuru_durum,
    update_lead_durum,
)
from rag import answer_question, rebuild_index
from runtime import ollama_ready
from score import score_ilan
from scrape_ilanlar import import_items, load_seed

st.set_page_config(page_title="EKAP Radar", layout="wide")
st.title("EKAP Radar")
st.caption("İlan al → doküman incele → özet/skor → başvuru taslağı (SQLite yerel)")

init_db()

with st.sidebar:
    st.subheader("Durum")
    st.write(f"İlan sayısı: **{ilan_count()}**")
    st.write(f"Ollama: {'açık' if ollama_ready() else 'kapalı (heuristic fallback)'}")
    st.caption("DB: `project/data/app.db` (yalnızca bu proje)")
    if st.button("Seed veriyi yükle"):
        n = import_items(load_seed())
        st.success(f"{n} ilan yüklendi")
        st.rerun()
    if st.button("RAG indeksini kur"):
        try:
            n = rebuild_index()
            st.success(f"{n} chunk indekslendi")
        except Exception as exc:
            st.error(str(exc))

tabs = st.tabs(["İlanlar", "Başvuru taslağı", "Firma takibi", "RAG soru", "Leadler", "Profil"])

with tabs[0]:
    c1, c2, c3 = st.columns(3)
    q = c1.text_input("Ara", placeholder="yazılım, web, mobil...")
    il = c2.text_input("İl")
    durum = c3.selectbox("Durum", ["", "aktif", "sonuclanmis"])
    rows = list_ilanlar(q=q, il=il, durum=durum)
    st.write(f"{len(rows)} kayıt")

    if rows:
        table = [
            {
                "İKN": r["ikn"],
                "Başlık": r["baslik"][:70],
                "Kurum": (r.get("kurum") or "")[:40],
                "İl": r.get("il"),
                "Teklif": r.get("teklif_tarihi"),
                "Durum": r.get("durum"),
                "Kazanan": r.get("kazanan_firma") or "-",
            }
            for r in rows
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

        ikn = st.selectbox("Detay / skor için İKN", [r["ikn"] for r in rows])
        ilan = get_ilan(ikn)
        if ilan:
            st.markdown(f"### {ilan['baslik']}")
            st.write(
                f"**Kurum:** {ilan.get('kurum')} · **İl:** {ilan.get('il')} · "
                f"**Teklif:** {ilan.get('teklif_tarihi')} · **OKAS:** {ilan.get('okas')}"
            )
            st.write(ilan.get("ozet_text") or "")
            if ilan.get("kazanan_firma"):
                st.info(
                    f"Kazanan: **{ilan['kazanan_firma']}**"
                    + (f" · {ilan.get('kazanan_tutar')}" if ilan.get("kazanan_tutar") else "")
                )
            if st.button("Uygunluk skorunu hesapla", type="primary"):
                with st.spinner("Skorlanıyor"):
                    result = score_ilan(ilan)
                st.session_state["last_score"] = result
            if "last_score" in st.session_state:
                result = st.session_state["last_score"]
                st.success(f"{result['skor']} → {result['aksiyon']} ({result['kaynak']})")
                for g in result.get("gerekce", []):
                    st.write(f"- {g}")
            if ilan.get("kazanan_firma") and st.button("Bu kazanan için lead taslağı üret"):
                try:
                    lead_id, draft = lead_for_ilan(ikn)
                    st.session_state["last_draft"] = draft
                    st.success(f"Lead #{lead_id} kaydedildi (gönderilmedi)")
                except Exception as exc:
                    st.error(str(exc))
            if st.session_state.get("last_draft"):
                st.text_area("Mail taslağı", st.session_state["last_draft"], height=220)
            if st.button("Bu ihale için başvuru taslağı hazırla", key="basvuru_from_ilan"):
                st.session_state["basvuru_ikn"] = ikn
                st.session_state["basvuru_run"] = True
                st.info("Başvuru taslağı sekmesine geçildi — aşamalar orada.")

with tabs[1]:
    st.markdown(
        """
**Aşamalar:**  
1. İlanı SQLite'tan oku → 2. Ham dokümanı incele → 3. RAG parçaları →  
4. Özet + checklist → 5. Uygunluk skoru → 6. Taslak yaz → 7. `app.db`'ye kaydet
"""
    )
    aktif = [r for r in list_ilanlar() if (r.get("durum") or "") != ""]
    if not aktif:
        st.warning("Önce sidebar'dan seed yükle.")
    else:
        default_ikn = st.session_state.get("basvuru_ikn") or aktif[0]["ikn"]
        options = [r["ikn"] for r in aktif]
        idx = options.index(default_ikn) if default_ikn in options else 0
        secilen = st.selectbox(
            "İKN",
            options,
            index=idx,
            format_func=lambda i: f"{i} — {next((x['baslik'][:55] for x in aktif if x['ikn']==i), '')}",
        )
        calistir = st.button("Başvuru taslağını aşama aşama üret", type="primary") or st.session_state.pop(
            "basvuru_run", False
        )
        if calistir:
            placeholders = {key: st.empty() for key, _ in ASAMALAR}
            status_map = {k: "wait" for k, _ in ASAMALAR}
            detail_map: dict = {}

            def paint(key: str) -> None:
                label = next(lbl for k, lbl in ASAMALAR if k == key)
                st_status = status_map.get(key, "wait")
                icon = {"wait": "○", "running": "…", "done": "✓", "error": "✗"}.get(st_status, "○")
                detail = detail_map.get(key)
                line = f"{icon} **{label}**"
                if detail:
                    short = ", ".join(f"{k}={v}" for k, v in list(detail.items())[:4])
                    line += f" — `{short}`"
                slot = placeholders[key]
                if st_status == "running":
                    slot.info(line)
                elif st_status == "done":
                    slot.success(line)
                elif st_status == "error":
                    slot.error(line)
                else:
                    slot.write(line)

            for key, _ in ASAMALAR:
                paint(key)

            def on_stage(key: str, status: str, detail=None) -> None:
                status_map[key] = status
                if detail:
                    detail_map[key] = detail
                paint(key)

            try:
                out = hazirla_basvuru(secilen, on_stage=on_stage)
                st.session_state["last_basvuru"] = out
                st.success(f"Kaydedildi · başvuru #{out['basvuru_id']} (gönderilmedi)")
            except Exception as exc:
                st.error(str(exc))
        if st.session_state.get("last_basvuru"):
            out = st.session_state["last_basvuru"]
            st.subheader("Özet")
            st.write(out.get("ozet") or "")
            st.subheader("Kontrol listesi")
            for c in out.get("checklist") or []:
                st.write(f"- {c}")
            uygun = out.get("uygunluk") or {}
            if uygun:
                st.info(f"Uygunluk: {uygun.get('skor')} → {uygun.get('aksiyon')} ({uygun.get('kaynak')})")
            st.subheader("Başvuru taslağı")
            st.text_area("Taslak metin", out.get("taslak") or "", height=320)

        kayitlar = list_basvurular()
        if kayitlar:
            st.divider()
            st.subheader("Kayıtlı taslaklar (SQLite)")
            for b in kayitlar[:15]:
                with st.expander(f"#{b['id']} · {b['ikn']} · {b.get('durum')} · {(b.get('ihale_baslik') or '')[:50]}"):
                    st.write(b.get("ozet") or "")
                    st.text_area("Taslak", b.get("taslak") or "", key=f"basvuru_txt_{b['id']}", height=180)
                    cols = st.columns(3)
                    if cols[0].button("gözden geçirildi", key=f"bg_{b['id']}"):
                        update_basvuru_durum(b["id"], "gozden_gecirildi")
                        st.rerun()
                    if cols[1].button("kullanıldı", key=f"bk_{b['id']}"):
                        update_basvuru_durum(b["id"], "kullanildi")
                        st.rerun()
                    if cols[2].button("taslak", key=f"bt_{b['id']}"):
                        update_basvuru_durum(b["id"], "taslak")
                        st.rerun()

with tabs[2]:
    firmalar = list_firmalar()
    st.write(f"{len(firmalar)} firma")
    if firmalar:
        st.dataframe(
            [
                {
                    "ID": f["id"],
                    "Unvan": f["unvan"],
                    "İhale": f["ihale_sayisi"],
                    "Son": f["son_kazanma"],
                    "Kurumlar": (f.get("kurumlar") or "")[:60],
                }
                for f in firmalar
            ],
            use_container_width=True,
            hide_index=True,
        )
        fid = st.selectbox("Firma detayı", [f["id"] for f in firmalar], format_func=lambda i: next(x["unvan"] for x in firmalar if x["id"] == i))
        firma = get_firma(fid)
        if firma:
            st.subheader(firma["unvan"])
            for ih in firma.get("ihaleler", []):
                st.write(
                    f"- `{ih['ikn']}` {ih['baslik'][:70]} · {ih.get('kurum')} · {ih.get('tutar') or '-'}"
                )
            if st.button("Firmaya genel lead taslağı"):
                lead_id, draft = save_lead_draft(firma["unvan"])
                st.session_state["firma_draft"] = draft
                st.success(f"Lead #{lead_id}")
            if st.session_state.get("firma_draft"):
                st.text_area("Taslak", st.session_state["firma_draft"], height=200)

with tabs[3]:
    st.write("İlan metinleri üzerinde kaynaklı soru-cevap (`[K1]`).")
    question = st.text_input("Soru", value="İstanbul'da mobil uygulama geliştirme ihalesi var mı?")
    if st.button("Sor", type="primary"):
        try:
            with st.spinner("Yanıt üretiliyor"):
                answer, provenance, validation = answer_question(question)
            st.markdown("**Cevap**")
            st.write(answer)
            st.markdown("**Kaynaklar**")
            st.json(provenance)
            if validation.get("valid"):
                st.success("Atıflar geçerli")
            elif validation.get("missing"):
                st.warning("Atıf yok")
            else:
                st.error(f"Geçersiz atıf: {validation.get('unknown')}")
        except Exception as exc:
            st.error(str(exc))

with tabs[4]:
    leads = list_leads()
    if not leads:
        st.info("Henüz lead yok. Sonuçlanmış bir ihale veya firma kartından üret.")
    else:
        for lead in leads:
            with st.expander(f"#{lead['id']} · {lead['firma_unvan']} · {lead['durum']}"):
                st.write(lead.get("ihale_baslik") or lead.get("ikn") or "-")
                st.text_area("Taslak", lead.get("mail_taslagi") or "", key=f"mail_{lead['id']}", height=160)
                cols = st.columns(3)
                if cols[0].button("yazildi", key=f"y_{lead['id']}"):
                    update_lead_durum(lead["id"], "yazildi")
                    st.rerun()
                if cols[1].button("cevap yok", key=f"c_{lead['id']}"):
                    update_lead_durum(lead["id"], "cevap_yok")
                    st.rerun()
                if cols[2].button("yazilacak", key=f"z_{lead['id']}"):
                    update_lead_durum(lead["id"], "yazilacak")
                    st.rerun()

with tabs[5]:
    profil = load_profil()
    sehirler = st.text_input("Şehirler (virgülle)", ", ".join(profil.get("sehirler", [])))
    anahtarlar = st.text_input("Anahtarlar (virgülle)", ", ".join(profil.get("anahtarlar", [])))
    sirket = st.checkbox("Şirketim / tüzel kişiliğim var", value=bool(profil.get("sirket_var_mi")))
    notlar = st.text_area("Notlar", profil.get("notlar") or "")
    if st.button("Profili kaydet"):
        save_profil(
            {
                "sehirler": [x.strip() for x in sehirler.split(",") if x.strip()],
                "anahtarlar": [x.strip() for x in anahtarlar.split(",") if x.strip()],
                "sirket_var_mi": sirket,
                "notlar": notlar,
            }
        )
        st.success("Kaydedildi")