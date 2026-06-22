"""
data/preprocessor.py

Modul za čišćenje i pripremu teksta pre slanja LLM-u (deo Modula M1).
Implementira naprednu obradu podataka: normalizaciju i chunking,
u skladu sa "napredni zahtevi" stavkom 2 iz specifikacije zadatka.
"""

import re

CHUNK_SIZE_CHARS = 8000  # ~2000 tokena, u skladu sa SRS specifikacijom


def clean_text(text: str) -> str:
    """
    Čisti tekst od suvišnih razmaka, tabova i praznih linija.

    Args:
        text: Sirovi tekst.

    Returns:
        Očišćen tekst.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> list[str]:
    """
    Deli dugačak tekst na manje segmente (chunkove) radi efikasnije LLM obrade.
    Pokušava da deli na granicama paragrafa kako bi se očuvao kontekst.

    Args:
        text: Tekst za deljenje.
        chunk_size: Maksimalna veličina jednog chunka u karakterima.

    Returns:
        Lista chunkova teksta. Ako je tekst kraći od chunk_size, vraća listu sa jednim elementom.
    """
    if len(text) <= chunk_size:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def preprocess(raw_text: str) -> dict:
    """
    Glavna funkcija preprocesiranja: čisti tekst i deli ga na chunkove.

    Args:
        raw_text: Sirovi, validirani ulazni tekst.

    Returns:
        Rečnik sa očišćenim tekstom i listom chunkova:
        {"cleaned_text": str, "chunks": list[str], "chunk_count": int}
    """
    cleaned = clean_text(raw_text)
    chunks = chunk_text(cleaned)

    return {
        "cleaned_text": cleaned,
        "chunks": chunks,
        "chunk_count": len(chunks),
    }
