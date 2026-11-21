# RFC — EKAP Radar

Durum: MVP uygulandı  
Konum: `week4/`  
Tarih: 11.11.2026

## Şu an

`week3/proje1` kampüs RAG, `week3/proje2` Manuscript AI denemesi. Final / ürün odaklı yeni proje `week4` altında başlar. Ortak kütüphane şimdilik yok; atölyedeki RAG + Ollama kalıbı buraya taşınır.

## Asıl amaç

Kamuya açık yazılım / bilişim ihalelerini izleyen, profiline göre filtreleyen ve **kazanan firmaları takip eden** bir asistan üretmek.

Kullanıcı ihaleye tek başına girmek zorunda değil. Asıl değer:
1. Yeni yazılım ihalesi çıktı mı?
2. Bana uyar mı? (şirket / bireysel / stack / şehir)
3. Kim kazandı? → kime freelance / alt yüklenici yazayım?

Atölye kazanımlarıyla örtüşür: scrape/toplama → chunk → embedding → RAG → kaynaklı cevap → agent araçları → insan onayı.

## Problem

- Yazılım ihaleleri EKAP’ta dağınık; günlük takip zahmetli.
- Bireysel geliştirici çoğu büyük ihaleye giremez; fırsat **kazanan firmada**.
- Mevcut siteler arşiv/arama sunar; profil skoru + lead aksiyonu zayıf kalır.

## Ürün özeti

**EKAP Radar** = ilan radar + uygunluk skoru + kazanan firma takibi + mail taslağı (onaylı).

Hedef kullanıcı:
- Bireysel geliştirici (kişisel kullanım)
- Küçük yazılım şirketi (ileride abonelik)

## Uygulama nasıl çalışacak?

1. **Veri toplama**  
   Kamuya açık ihale kaynaklarından (EKAP / türevi açık listeler) yazılım-bilişim ilanlarını çek. İKN, başlık, kurum, il, tarihler, OKAS, link kaydet.

2. **Filtre ve liste**  
   Anahtar kelime (`yazılım`, `web`, `mobil`), OKAS `72xxxx`, il, durum (aktif / sonuçlanmış).

3. **Uygunluk skoru (LLM)**  
   Kullanıcı profiline göre: Uyar / Kısmen / Uymaz + kısa gerekçe.  
   “Teklif ver” vs “Kazanan firmaya yaz” ayrımı yap.

4. **Kaynaklı RAG**  
   İlan / şartname metninden soru-cevap (`[K1]` atıf). Kanıt yoksa uydurma.

5. **Kazanan firma takibi**  
   Sonuçlanan ihalede kazanan unvan (+ tutar varsa). Firma kartı: aldığı işler, kurumlar, son aktivite.

6. **Lead / aksiyon**  
   “Bu firmaya yaz” mail taslağı üret. Göndermez; insan kopyalar / onaylar.  
   Basit durum: yazılacak / yazıldı / cevap yok.

## Teknoloji seçimi

| Katman | Teknoloji |
| --- | --- |
| Arayüz | Streamlit |
| Yerel LLM | Ollama (`qwen2.5` vb.) |
| Embedding | Ollama embedding modeli (atölyedeki gibi) |
| Vektör / arama | Chroma |
| Kayıt | SQLite (ilan + firma + lead) |
| Toplama | Python (`requests` / HTML parse); kırılganlığa karşı İKN merkezli şema |
| Agent (sonraki adım) | Basit tool calling veya LangGraph (Gün 7+) |

PostgreSQL cluster, mikroservis, Docker zorunlu değil. Önce çalışan demo.

## Klasör taslağı

```
week4/
├── RFC.md
├── app.py                 # Streamlit
├── config.py
├── scrape_ilanlar.py      # ilan toplama
├── scrape_sonuclar.py     # kazanan firma
├── models.py              # sqlite şema yardımcıları
├── rag.py                 # chunk / index / retrieve / answer
├── score.py               # uygunluk skoru
├── leads.py               # mail taslağı
├── data/
│   ├── raw/               # ham ilan metinleri
│   └── app.db
├── chroma_ekap/
├── requirements.txt
└── README.md
```

## Veri şeması (özet)

**ilan:** ikn, baslik, kurum, il, ilan_tarihi, teklif_tarihi, tur, okas, url, durum, ozet_text  
**firma:** unvan, normalized_name  
**sonuc:** ikn → firma_id, tutar?, sonuc_tarihi  
**lead:** firma_id, ikn?, durum, not, olusturma_tarihi  
**profil:** sehirler, anahtarlar, sirket_var_mi, notlar

## MVP kapsamı (jüri + kişisel kullanım)

Yapılacak:
1. 30–50 yazılım/bilişim ihalesini kaydet
2. Filtreli liste ekranı
3. AI özet + uygunluk skoru
4. Sonuçlanmış kayıtlarda kazanan firma
5. Firma → mail taslağı (onaylı, göndermez)
6. Kaynaklı 3–5 soru-cevap + basit eval (doğru İKN / firma)

Yapılmayacak (MVP dışı):
- Gerçek teklif / e-imza
- Otomatik mail gönderimi
- Çok kaynaklı kırılgan scrape ordusu
- Fine-tuning

## Geliştirme aşamaları

1. RFC + boş iskelet + SQLite şema  
2. Örnek/statik 10 ilan ile UI  
3. Toplama scripti (yazılım filtresi)  
4. RAG indeksi + kaynaklı cevap  
5. Uygunluk skoru  
6. Sonuç / kazanan firma  
7. Lead taslağı + insan onayı  
8. Eval seti ve demo senaryosu  

## Başarı ölçütleri

- Yeni yazılım ihalesi listede görünüyor
- Uygunluk gerekçesi profille uyumlu
- Kaynak etiketi geçersizse reddediliyor
- Sonuçlanmış örnekte kazanan firma doğru
- Mail taslağı gönderilmeden üretiliyor

## Riskler

- EKAP arayüzü / ToS / teknik engel → az kaynak, sağlam İKN şeması; gerekirse yarı-manuel CSV
- İletişim bilgisi eksik → firma adı + web/LinkedIn arama yeterli
- Büyük ihale beklentisi → ürün vaadi “kazan”, değil “fırsat + lead”

## Jüriye anlatım

Klasik chatbot değil: kamu ihale verisi üzerinde çalışan, kaynaklı RAG + agent adımlı (ara / skorla / kazananı getir / taslak üret) bir iş asistanı. İnsan onayı kritik adımda durur.
