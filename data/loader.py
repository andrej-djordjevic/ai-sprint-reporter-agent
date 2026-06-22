"""
data/loader.py

Modul za učitavanje ulaznih podataka agenta (Modul M1).
Podržava unos teksta kroz terminal (UC-01) i upload fajla (UC-02).
"""

import os

SUPPORTED_EXTENSIONS = [".txt", ".md"]
MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB, u skladu sa NF zahtevima iz SRS dokumenta
MIN_TEXT_LENGTH = 50  # minimalna dužina unosa, u skladu sa UC-01


class InputValidationError(Exception):
    """Greška pri validaciji ulaznih podataka."""
    pass


def load_from_text(raw_text: str) -> str:
    """
    UC-01: Učitavanje teksta unetog direktno kroz terminal.

    Args:
        raw_text: Tekst koji je korisnik uneo.

    Returns:
        Validiran i očišćen tekst, spreman za preprocesiranje.

    Raises:
        InputValidationError: ako je unos prazan ili prekratak.
    """
    if raw_text is None or not raw_text.strip():
        raise InputValidationError(
            "Unos je prazan. Molimo unesite opis ili zahteve chat projekta."
        )

    cleaned = raw_text.strip()

    if len(cleaned) < MIN_TEXT_LENGTH:
        raise InputValidationError(
            f"Unos je prekratak ({len(cleaned)} karaktera). "
            f"Potrebno je najmanje {MIN_TEXT_LENGTH} karaktera za pouzdanu analizu rizika."
        )

    return cleaned


def load_from_file(file_path: str) -> str:
    """
    UC-02: Učitavanje teksta iz fajla (SRS dokument, opis arhitekture, user stories).

    Args:
        file_path: Putanja do fajla.

    Returns:
        Sadržaj fajla kao tekst.

    Raises:
        InputValidationError: ako fajl ne postoji, format nije podržan,
                               ili je fajl prevelik / prazan.
    """
    if not os.path.exists(file_path):
        raise InputValidationError(
            f"Fajl '{file_path}' ne postoji. Provernite putanju i pokušajte ponovo."
        )

    if not os.path.isfile(file_path):
        raise InputValidationError(f"'{file_path}' nije fajl.")

    _, ext = os.path.splitext(file_path)
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        raise InputValidationError(
            f"Nepodržan format fajla '{ext}'. "
            f"Podržani formati su: {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise InputValidationError(
            f"Fajl je previše veliki ({file_size / 1024:.1f} KB). "
            f"Maksimalna veličina u v1.0 je {MAX_FILE_SIZE_BYTES / 1024:.0f} KB."
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        raise InputValidationError(
            "Fajl nije moguće pročitati kao UTF-8 tekst. Provernite enkoding fajla."
        )

    return load_from_text(content)
