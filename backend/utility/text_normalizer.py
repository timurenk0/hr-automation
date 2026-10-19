import re
import unicodedata


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = text.replace("\u00a0", " ")  # Non-breaking space
    text = text.replace("\u200b", "")  # Zero-width space
    text = text.replace("\ufeff", "")  # Byte-order mark

    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n")]

    clean_lines = []

    for line in lines:
        if line:
            clean_lines.append(line)
        elif clean_lines and clean_lines[-1] != "":
            clean_lines.append("")

    return "\n".join(clean_lines).strip()
