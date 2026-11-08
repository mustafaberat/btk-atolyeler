import html
from pathlib import Path

import streamlit as st

from ai_service import transcribe, translate
from dictionary import SAMPLE, gloss

SAMPLE_PAGE = Path(__file__).parent / "samples" / "ornek.png"

STYLE = """
<style>
.verse { direction: rtl; text-align: right; font-size: 1.7rem; line-height: 2.4; }
.verse p { margin: 0.2rem 0; }
.word { position: relative; display: inline-block; margin: 0 0.2rem; cursor: help; border-bottom: 1px dotted #8a7340; }
.word .tip {
  display: none; position: absolute; bottom: 115%; left: 50%; transform: translateX(-50%);
  background: #2b2416; color: #fff; direction: ltr; font-size: 0.95rem; line-height: 1.3;
  padding: 0.25rem 0.55rem; border-radius: 0.4rem; white-space: nowrap; z-index: 5;
}
.word:hover .tip { display: block; }
.plain { border-bottom: none; cursor: text; }
div.stButton { margin-top: 0.85rem; }
div.stButton > button {
  width: 100%;
  border: 1px solid #2b2416;
  background: #2b2416;
  color: #f7f4ee;
  border-radius: 8px;
  min-height: 2.6rem;
  font-weight: 500;
}
div.stButton > button:hover {
  background: #24362c;
  color: #f7f4ee;
  border-color: #24362c;
}
div.stButton > button:focus {
  color: #f7f4ee;
  background: #2b2416;
}
div.stButton > button[kind="secondary"] {
  background: transparent;
  color: #2b2416;
}
div.stButton > button[kind="secondary"]:hover {
  background: #f4f1ea;
  color: #2b2416;
  border-color: #2b2416;
}
</style>
"""


def verse_html(text):
    paragraphs = []
    for line in text.splitlines():
        if not line.strip():
            continue
        spans = []
        for row in gloss(line):
            word = html.escape(row["farsça"])
            if row["türkçe"] == "—":
                spans.append(f'<span class="word plain">{word}</span>')
                continue
            tip = html.escape(row["türkçe"])
            spans.append(f'<span class="word">{word}<span class="tip">{tip}</span></span>')
        paragraphs.append("<p>" + " ".join(spans) + "</p>")
    return '<div class="verse">' + "".join(paragraphs) + "</div>"


def read_into_box(image_bytes):
    with st.spinner("Görsel okunuyor"):
        try:
            read = transcribe(image_bytes)
        except Exception as error:
            st.error(f"Görsel okunamadı: {error}")
            return
    if read:
        st.session_state.persian = read
    else:
        st.error("Görselden Farsça satır çıkmadı.")


st.set_page_config(page_title="Manuscript AI", layout="centered")
st.markdown(STYLE, unsafe_allow_html=True)
st.title("Manuscript AI")
st.caption("Görseli metne çevir, kelimenin üstüne gel, sonra Türkçeye çevir")

if "persian" not in st.session_state:
    st.session_state.persian = SAMPLE

if st.button("Örnek sayfayı oku", type="secondary"):
    st.image(str(SAMPLE_PAGE), use_container_width=True)
    read_into_box(SAMPLE_PAGE.read_bytes())

uploaded = st.file_uploader("Yazma görseli", type=["png", "jpg", "jpeg", "webp"])
if uploaded is not None:
    st.image(uploaded, use_container_width=True)
    if st.button("Metne çevir", type="primary"):
        read_into_box(uploaded.getvalue())

text = st.text_area("Farsça metin", key="persian", height=140)
if text.strip():
    st.markdown(verse_html(text), unsafe_allow_html=True)

if st.button("Çevir", type="primary"):
    with st.spinner("Çevriliyor"):
        try:
            st.subheader("Türkçe çeviri")
            st.write(translate(text))
        except Exception as error:
            st.error(f"Çeviri alınamadı: {error}")
