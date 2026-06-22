"""
output/exporter.py

Zapisuje formatirane izvestaje na disk (Modul M4).
"""

import json
import os

OUTPUT_DIR = "output/reports"


def ensure_output_dir(directory=OUTPUT_DIR):
    """Kreira output direktorijum ako ne postoji."""
    os.makedirs(directory, exist_ok=True)
    return directory


def export_markdown(markdown_text, filename="risk_report.md", directory=OUTPUT_DIR):
    """
    Zapisuje Markdown izvestaj na disk.

    Args:
        markdown_text: Generisan Markdown tekst.
        filename: Naziv fajla.
        directory: Direktorijum u koji se zapisuje.

    Returns:
        Putanja do sacuvanog fajla.
    """
    ensure_output_dir(directory)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    return path


def export_json(data_dict, filename="risk_report.json", directory=OUTPUT_DIR):
    """
    Zapisuje JSON izvestaj na disk.

    Args:
        data_dict: Recnik sa rezultatima analize.
        filename: Naziv fajla.
        directory: Direktorijum u koji se zapisuje.

    Returns:
        Putanja do sacuvanog fajla.
    """
    ensure_output_dir(directory)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=2)
    return path
