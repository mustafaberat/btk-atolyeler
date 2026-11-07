# Kurulum

Kampüs asistanı alıştırması yerel Ollama ile çalışır. Belgeler kurgusaldır; gerçek kişisel veri koymayın. Python dosyaları ve `data/` klasörü `week3/proje1/` içindedir. Ollama ile Qwen modeli bu klasörün dışında, makinede durur. Hiçbir script Ollama'yı başlatmaz.

## 1. Ollama'yı ayağa kaldır

[ollama.com](https://ollama.com/download) üzerinden kurun. Mac'te menü çubuğu uygulaması açıksa servis dinliyordur. Değilse ayrı bir terminalde şu komutu çalıştırıp pencereyi açık bırakın:

```bash
ollama serve
```

Komut bulunamazsa bu makinedeki ikili `~/.local/bin/ollama` yolundadır. Kontrol:

```bash
curl -sf http://127.0.0.1:11434/api/tags
```

Cevap gelmeli. 11434 portunu internete açmayın.

## 2. Modelleri indir

Aynı makinede, servis ayaktayken:

```bash
ollama pull qwen2.5:1.5b
ollama pull embeddinggemma
ollama list
```

Listede `qwen2.5:1.5b` ve `embeddinggemma` görünmeli. İndirmeyi ders sırasında tüm sınıfa aynı anda yaptırmayın.

## 3. Python ortamı

Python 3.11 veya 3.12. Komutları `week3/proje1/` klasöründe çalıştırın:

Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Mac / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Paketleri kur

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python 00_kurulum_kontrol.py
```

Kontrol scripti paketlerin ve iki modelin görünüp görünmediğini yazar.

## 5. Veriyi koy

Metinler `week3/proje1/data/` altındadır. `week3/proje1/meta.json` hangi dosyanın hangi birime ait olduğunu söyler. Klasör boşsa belge sayısı 0 olur.

## 6. Scripti çalıştır

`week3/proje1/` klasöründe, sanal ortam açıkken:

```bash
python dosya.py
```

İlk scriptler yalnızca `data/` içindeki dosyaları okur. Embedding ve cevap üreten scriptler 1. adımdaki Ollama'ya `http://127.0.0.1:11434` üzerinden istek atar. İndeks scripti vektörleri ayrı bir sunucuya değil, `chroma_kampus/` klasörüne yazar. Bu klasör yerelde kalır ve git'e girmez.
