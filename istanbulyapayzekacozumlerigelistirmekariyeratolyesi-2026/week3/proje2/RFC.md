# RFC

Durum: taslak. Yapılacaklar buraya yazılacak.

## Şu an

Kampüs asistanı, verisiyle birlikte `week3/proje1/` içindedir. Yeni uygulama `week3/proje2/` altında sıfırdan başlar. Bu dosya oradadır.

İki projenin ortak kullandığı parça çıkınca `week3/` dışına alınır. Şimdilik dışarı taşınan bir parça yok.

## Asil amac 
Prototip için hazır teknolojilerden yararlan: Sıfırdan bir yapay zekâ modeli eğitmek yerine, mevcut açık kaynaklı Vision-Language modellerini (ör. Qwen-2.5-VL veya TrOCR) ve dil modellerini prompt zincirleriyle (Prompt Engineering) test et.
Sözlük veritabanı: Farsça-Türkçe açık kaynaklı dijital leksikon verilerini (veya yapılandırılmış sözlük API'lerini) projene entegre etmeyi planla.
Örnek Bir Sayfayla Deneme Yap: Seçtiğin bir Farsça el yazması sayfasını al; transkripsiyonunu ve kelime kelime dökümünü elle yapıp jürine ya da danışman hocana sunacağın "kavram kanıtı" (Proof of Concept) taslağını oluştur.

## Yapılacaklar

Manuscript AI – Minimal MVP
Projenin amacı: Kullanıcının yüklediği Farsça el yazması görselini yapay zekâ ile okuyarak metne dönüştürmek, kelimeleri analiz etmek ve Türkçeye çevirmek.
1. Uygulama nasıl çalışacak?
1. Görsel yükleme
   
   Kullanıcı Farsça el yazması sayfasını yükler.
   
   
   
   
   
   
   
   m-kermani.ir
2. Yapay zekâ ile metin tanıma
   
   Qwen2.5-VL görseli analiz ederek Farsça metni çıkarır.
3. Kelime analizi
   
   Metin kelimelere ayrılır. Farsça kelimelerin Türkçe karşılıkları bulunur.
4. Türkçe çeviri
   
   LLM, cümlenin bağlamını dikkate alarak Türkçe çevirisini oluşturur.
5. Sonuç ekranı
   
   Orijinal görsel, Farsça metin, kelime karşılıkları ve Türkçe çeviri gösterilir.

2. Teknoloji seçimi
Katman	Teknoloji
Frontend + Backend	Python Streamlit
Görsel analizi	Qwen2.5-VL
Metin analizi	LLM
Sözlük	JSON tabanlı Farsça-Türkçe sözlük
Görsel işleme	Pillow

Neden Streamlit? Ayrı bir React frontend ve FastAPI backend geliştirmeden tek Python uygulamasıyla çalışan bir demo hazırlayabiliriz.

PostgreSQL, Docker, Redis, Kafka, mikroservis gibi teknolojilere ihtiyacımız yok.
3. Ekran tasarımı
Manuscript AI
Persian Manuscript Recognition & Translation

1. Manuscript Image
Upload manuscript image

PNG, JPG, JPEG

2. Persian Transcription
متن فارسی
Extracted by AI

3. Word Analysis
Persian	Turkish
کتاب	Kitap
علم	Bilgi
دوست	Dost

4. Turkish Translation
AI-generated contextual translation will appear here.

Minimal MVP interface

4. Proje klasör yapısı
manuscript-ai/
│
├── app.py
├── ai_service.py
├── dictionary.py
├── requirements.txt
├── dictionary.json
├── .env
└── README.md


Dosyaların sorumlulukları:
- app.py: Streamlit arayüzü.
- ai_service.py: Görselden metin çıkarma ve çeviri.
- dictionary.py: Kelime ayrıştırma ve sözlük sorgulama.
- dictionary.json: Farsça-Türkçe sözlük verileri.
5. Geliştirme aşamaları
1. Streamlit arayüzünü oluştur.
2. Görsel yükleme özelliğini ekle.
3. Qwen2.5-VL entegrasyonuyla Farsça metni çıkar.
4. Metni kelimelere ayır ve sözlükte ara.
5. LLM ile Türkçe çeviri oluştur.
6. Sonuçları tek ekranda göster.
7. Bir gerçek el yazması üzerinde CER/WER ölçümü yap.
6. Jüriye sunacağımız çıktı
Proje sonunda çalışan bir uygulamamız olacak:
- Farsça el yazması yüklenebilecek.
- AI görseli okuyabilecek.
- Farsça transkripsiyon oluşturulabilecek.
- Kelimelerin Türkçe karşılıkları gösterilebilecek.
- Cümlenin Türkçe çevirisi üretilebilecek.
- OCR doğruluğu ölçülebilecek.

Benim önerim: Bu kapsam yeterli. Projenin teknik zorluğunu mikroservis veya veritabanı geliştirmek yerine Farsça el yazısının doğru okunması, kelime anlamlarının bulunması ve çeviri kalitesine odaklayalım.

Bu RFC'yi AI coding agent'a verdiğimizde önce çalışan bir prototip üretmesini, gereksiz mimari oluşturmamasını istemeliyiz.