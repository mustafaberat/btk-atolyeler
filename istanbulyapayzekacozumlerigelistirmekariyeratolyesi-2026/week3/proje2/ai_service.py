import base64
import io
import json
import re
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
CHAT_MODEL = "qwen2.5:7b"
VISION_MODEL = "qwen2.5vl:3b"
READ_PROMPT = (
    "This page is Persian or Ottoman Turkish, written in Arabic script. "
    "Transcribe every line from top to bottom. "
    "Keep the line breaks. "
    "Use Arabic letters only. "
    "Do not translate. Do not use Latin letters. Do not explain."
)


def ask(model, content, images=None, timeout=180, num_predict=512):
    message = {"role": "user", "content": content}
    if images:
        message["images"] = images
    body = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": 0, "num_predict": num_predict, "repeat_penalty": 1.15},
        "messages": [message],
    }).encode()
    request = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode())
    return payload["message"]["content"].strip()


def fit_image(image_bytes):
    try:
        from PIL import Image
    except ImportError:
        return image_bytes
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    longest = max(image.size)
    if longest <= 1400 and len(image_bytes) <= 1_500_000:
        return image_bytes
    if longest > 1400:
        scale = 1400 / longest
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def persian_lines(text):
    kept = []
    for line in text.splitlines():
        line = line.strip().strip("`")
        if not line:
            continue
        letters = sum(1 for char in line if "\u0600" <= char <= "\u06FF")
        if letters:
            kept.append(line)
    return "\n".join(kept).strip()


def transcribe(image_bytes):
    encoded = base64.b64encode(fit_image(image_bytes)).decode("ascii")
    raw = ask(VISION_MODEL, READ_PROMPT, images=[encoded], timeout=300, num_predict=700)
    return persian_lines(raw)


def cut_repeat(text):
    words = text.split()
    for size in range(6, 2, -1):
        for index in range(len(words) - size * 2 + 1):
            if words[index:index + size] == words[index + size:index + size * 2]:
                return " ".join(words[:index + size])
    return text


def clean_translation(text):
    kept = []
    for line in text.splitlines():
        line = line.strip().strip('"').strip("“”")
        folded = line.lower()
        if not line or line.endswith(":"):
            continue
        if folded.startswith(("here is", "çeviri", "translation", "bu metin", "okunuş", "metin", "işte", "çıktı", "girdi")):
            continue
        if any(mark in folded for mark in ("bilmiyorum", "çevrilmez", "paylaşın", "yardımcı", "daha fazla", "bu çeviri", "çeviride", "açıklanabilir")):
            continue
        if re.search(r"\b[12]\d{3}\b", line):
            continue
        arabic = sum(1 for char in line if "\u0600" <= char <= "\u06FF")
        if arabic > len(line) / 3:
            continue
        kept.append(cut_repeat(line))
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(kept))
    spoken = []
    for sentence in sentences:
        folded = sentence.lower()
        if any(mark in folded for mark in ("çevir", "kelimesi", "ifadesi", "metnin anlam", "açıklama")):
            break
        spoken.append(sentence)
    return " ".join(spoken).strip()


def text_chunks(source):
    lines = []
    for line in source.splitlines():
        line = line.strip()
        if line and line not in lines:
            lines.append(line)
    if not lines and source.strip():
        lines = [source.strip()]
    chunk = []
    count = 0
    for line in lines:
        words = line.split()
        if chunk and count + len(words) > 40:
            yield "\n".join(chunk)
            chunk = []
            count = 0
        chunk.append(line)
        count += len(words)
    if chunk:
        yield "\n".join(chunk)


def meaning_prompt(chunk):
    return (
        "Arap harfli metnin anlamını bugünkü Türkçe ile yaz. Okunuş yazma.\n\n"
        "Girdi: بنی‌آدم اعضای یکدیگرند\n"
        "Çıktı: İnsanlar birbirinin uzuvlarıdır.\n\n"
        "Girdi: بو كتاب علمه دايردر\n"
        "Çıktı: Bu kitap ilim hakkındadır.\n\n"
        f"Girdi: {chunk}\n"
        "Çıktı:"
    )


def translate(source):
    source = source.strip()
    if not source:
        return "Çevrilecek metin yok."
    parts = []
    for chunk in text_chunks(source):
        cleaned = clean_translation(ask(CHAT_MODEL, meaning_prompt(chunk), timeout=180, num_predict=180))
        if cleaned:
            parts.append(cleaned)
    if not parts:
        return "Çeviri alınamadı."
    return "\n\n".join(parts)
