# EKAP Radar

Kamuya açık yazılım ve bilişim ihalelerini izleyen, profile göre puanlayan ve kazanan firmaya yazılacak taslağı hazırlayan yerel bir asistan. Arayüz Streamlit; kayıt `data/app.db` (SQLite, bu klasörün içinde).

Kim için: bireysel geliştirici veya küçük yazılım ekibi. Büyük ihaleye tek başına girmek zorunda değil. Asıl sorular şunlar:

1. Yeni bir yazılım ihalesi çıktı mı?
2. Profilime uyar mı? (şehir, stack, şirket var mı)
3. Kim kazandı — kime freelance / alt yüklenici yazayım?

Akış: ilanı al → ham metni incele → RAG ile kaynaklı cevap → uygunluk skoru → başvuru veya lead taslağı. Taslaklar kaydedilir; mail ve resmi başvuru **gönderilmez**.

Varsayılan profil (`config.py`): şehirler İstanbul, Ankara, İzmir; anahtarlar yazılım, web, mobil, python, geliştirme, destek; şirket yok.

Tasarım notu: [RFC.md](RFC.md)

## Örnekler

Seed’den üç gerçek kayıt. Skorlar varsayılan profil ve Ollama kapalıyken kullanılan kural motoruna göredir (`heuristic`). Ollama açıksa gerekçe modelden gelir; etiket aynı üçlüden biridir: **Uyar / Kısmen / Uymaz**.

### 1 — Aktif ihale, şehir ve stack uyuyor

| | |
| --- | --- |
| İKN | `2026/2124289` |
| İhale | İzmir Büyükşehir Belediyesi web siteleri ve mobil uygulama geliştirme |
| Kurum | İzmir Büyükşehir Belediye Başkanlığı |
| İl | İzmir · teklif `2026-11-26` · durum **aktif** |
| OKAS | `72000000` IT hizmetleri |

Skor: **Kısmen → Kazanan firmaya yaz**

- Eşleşen anahtarlar: yazılım, web, mobil, geliştirme, destek
- Şehir uyumu: İzmir
- Şirket kaydı yok; doğrudan teklif yerine lead daha gerçekçi

CLI:

```bash
python basvuru.py --ikn 2026/2124289
```

Ollama kapalıyken üretilen niyet metninin iskeleti:

```text
# Başvuru / Niyet Taslağı

**İKN:** 2026/2124289
**İhale:** İzmir Büyükşehir Belediyesi Web Siteleri ve Mobil Uygulama Geliştirme ve Destek Hizmeti
**Kurum:** İZMİR BÜYÜKŞEHİR BELEDİYE BAŞKANLIĞI
**Teklif tarihi:** 2026-11-26

## Kısa özet
…web siteleri ve mobil uygulama geliştirme ile destek hizmeti. İşe başlama 01.01.2027…

## Kontrol listesi
- İKN: 2026/2124289
- Teklif son tarihi: 2026-11-26
- Kurum: İZMİR BÜYÜKŞEHİR BELEDİYE BAŞKANLIĞI
- İl / yer: İzmir
- OKAS: 72000000 — IT hizmetleri: danışmanlık, yazılım geliştirme, internet ve destek
- Uyarı: Tüzel kişilik yoksa doğrudan teklif zor olabilir; alt yüklenici / lead düşün.
- Taslak insan onaylıdır; resmi başvuru EKAP'tan yapılır.

## Niyet metni (taslak)
Odak alanlarımız: yazılım, web, mobil, python, geliştirme, destek.
Çalışabileceğimiz şehirler: İstanbul, Ankara, İzmir.
```

Kayıt `basvuru` tablosuna düşer. Streamlit’te **Başvuru taslağı** sekmesi aynı yedi aşamayı tek tek gösterir.

### 2 — Sonuçlanmış ihale, fırsat kazanan firmada

| | |
| --- | --- |
| İKN | `2026/2084948` |
| İhale | Afetlerde kullanılmak üzere bilgisayar yazılım programı |
| Kurum | Kağıthane Belediye Başkanlığı · İstanbul |
| Durum | **sonuçlanmış** |
| Kazanan | AFET YAZILIM ÇÖZÜMLERİ A.Ş. · 1.850.000,00 TRY |

Skor: **Kısmen → Kazanan firmaya yaz** (ihale kapanmış; aksiyon kazanan firmaya lead).

Arayüzde “Bu kazanan için lead taslağı üret” şuna benzer bir metin kaydeder (`lead` tablosu, durum `yazilacak`):

```text
Konu: AFET YAZILIM ÇÖZÜMLERİ A.Ş. — Yazılım işbirliği / alt yüklenici teklifi

Merhaba AFET YAZILIM ÇÖZÜMLERİ A.Ş. ekibi,

Ben yazılım geliştiricisiyim. Odak alanlarım: yazılım, web, mobil, python, geliştirme, destek.
Çalışabileceğim şehirler: İstanbul, Ankara, İzmir.

Özellikle KAĞITHANE BELEDİYE BAŞKANLIĞI bünyesindeki
“Afetlerde Kullanılmak Üzere Bilgisayar Yazılım Programı Hizmet Alım İşi”
(İKN 2026/2084948) işiyle ilgili alt yüklenici / freelance destek sunabileceğimi düşünüyorum.
```

Aynı firmayı **Firma takibi** sekmesinden açınca aldığı diğer işler de listelenir. Durum elle `yazildi` veya `cevap yok` yapılır.

### 3 — Kaynaklı soru

```bash
python rag.py --ask "İstanbul mobil uygulama ihalesi var mı?"
```

Cevap yalnızca indekslenmiş ilan metinlerine dayanır ve `[K1]`, `[K2]` ile işaretlenir. Kanıt yoksa model “Bu bilgi dokümanlarda bulunamadı.” der. Atıf listede yoksa doğrulama geçersiz sayar.

CLI üç blok basar:

```text
CEVAP:
…iddia… [K1]
KAYNAKLAR: {'K1': {'source': '2026/…', 'chunk_id': 0, 'score': 0.42}}
DOĞRULAMA: {'valid': True, 'found': ['K1'], 'unknown': [], 'missing': False}
```

`source` bir İKN’dir. Cevaptaki etiket bu listede yoksa `unknown` dolu gelir ve `valid` false olur. Ollama kapalıysa en yakın parçanın ilk 500 karakteri `[K1]` ile basılır.

### Skorun ayrıldığı bir iş

Aynı profil, SAP ağırlıklı ilan `2026/1839882` (Darphane, İstanbul, Basis / SAP 4HANA): **Kısmen → Kazanan firmaya yaz**. Anahtarlar kısmen tutar; yetki ve deneyim şartı bireysel teklifi zayıflatır.

## Kurulum

```bash
cd project
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ollama (RAG / LLM için):

```bash
ollama pull embeddinggemma
ollama pull qwen2.5:1.5b
```

## Veri yükle

```bash
python scrape_ilanlar.py
python scrape_sonuclar.py --from-seed
```

## RAG indeks

```bash
python rag.py --rebuild
python rag.py --ask "İstanbul mobil uygulama ihalesi var mı?"
```

## Başvuru taslağı (CLI)

```bash
python basvuru.py --ikn 2026/2124289
```

Aşamalar: ilan oku → raw incele → RAG → özet/checklist → uygunluk → taslak → SQLite kaydet.

## Uygulama

```bash
streamlit run app.py
```

## Notlar

- Seed: `data/seed_ilanlar.json`. Ham metin: `data/raw/`.
- Ollama kapalıysa skor/taslak şablona düşer.
- Mail ve başvuru **gönderilmez**; yalnızca taslak kaydedilir (`basvuru` tablosu).
