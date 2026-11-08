import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORDS = json.loads((ROOT / "dictionary.json").read_text(encoding="utf-8"))
SAMPLE = (ROOT / "ornek.txt").read_text(encoding="utf-8").strip()


def normalize(word):
    word = word.replace("\u200c", "").replace("\u200d", "")
    word = word.replace("ي", "ی").replace("ك", "ک").replace("آ", "ا")
    return word.strip(".,،؛:!?؟\"'«»()[]")


def tokens(text):
    return [part for part in re.split(r"\s+", text.strip()) if part]


def gloss(text):
    parts = tokens(text)
    keys = [normalize(part) for part in parts]
    rows = []
    index = 0
    while index < len(parts):
        if index + 1 < len(parts):
            pair = keys[index] + keys[index + 1]
            if pair in WORDS:
                rows.append({
                    "farsça": parts[index] + " " + parts[index + 1],
                    "türkçe": WORDS[pair],
                })
                index += 2
                continue
        rows.append({
            "farsça": parts[index],
            "türkçe": WORDS.get(keys[index], "—"),
        })
        index += 1
    return rows
