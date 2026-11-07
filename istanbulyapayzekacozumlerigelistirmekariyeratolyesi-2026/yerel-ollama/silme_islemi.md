# Ollama'yı kaldırma

Program, `qwen2.5:1.5b` ve `embeddinggemma` bu klasörde durur. `local-ai` başka yerdedir; buradaki silme ona dokunmaz.

Bu klasör silinince içindeki her şey gider:

- `app/` — Ollama programı
- `home/` — modeller ve kimlik dosyası

Ev dizininde bir kısayol kalır. Dosya tutmaz, bu klasörü gösterir:

```text
~/.ollama  →  yerel-ollama/home
```

Klasörü silmek o kısayolu silmez. Kısayol durursa Ollama boş bir yolu göstermeye devam eder.

## Sıra

Servis açıksa kapat:

```bash
pkill -f yerel-ollama/app/ollama
```

Kısayolu sil:

```bash
rm ~/.ollama
```

Sonra bu klasörü sil. Üstteki atölye klasörünün tamamını silmek de aynı işi görür; `yerel-ollama` onun içindedir.

```bash
rm -rf yerel-ollama
```

`~/.local/ollama` ve `~/.local/bin/ollama` bu kurulumda yok. Tekrar bakmak için:

```bash
ls -ld ~/.ollama ~/.local/ollama ~/.local/bin/ollama
```

Üçü de bulunamıyorsa dışarıda Ollama kalmamıştır.
