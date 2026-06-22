#!/usr/bin/env python3
"""
main.py

Ulazna tacka AI agenta za analizu rizika chat aplikacije.
Podrzava unos teksta kroz terminal (UC-01) i upload fajla (UC-02).

Upotreba:
    python main.py                          # interaktivni unos teksta
    python main.py --file primer.txt        # ucitavanje iz fajla
    python main.py --file primer.txt --model mistral:7b
"""

import argparse
import sys

from data.loader import load_from_text, load_from_file, InputValidationError
from data.preprocessor import preprocess
from agent.graph import run_risk_analysis
from agent.models import check_ollama_availability, OLLAMA_BASE_URL
from output.formatter import format_as_json, format_as_markdown
from output.exporter import export_markdown, export_json


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI agent za analizu rizika chat aplikacije (MSF metodologija)."
    )
    parser.add_argument(
        "--file", "-f", type=str, default=None,
        help="Putanja do .txt ili .md fajla sa opisom projekta (SRS, user stories, itd.)"
    )
    parser.add_argument(
        "--model", "-m", type=str, default=None,
        help="Naziv Ollama modela (npr. llama3.2, mistral:7b, codellama:13b)"
    )
    parser.add_argument(
        "--output-dir", "-o", type=str, default="output/reports",
        help="Direktorijum u koji se zapisuju izvestaji"
    )
    return parser.parse_args()


def get_text_input():
    print("=" * 70)
    print("AI AGENT ZA ANALIZU RIZIKA CHAT APLIKACIJE")
    print("=" * 70)
    print()
    print("Unesite opis vaseg chat projekta (SRS, arhitektura, user stories).")
    print("Pritisnite Ctrl+D (Linux/Mac) ili Ctrl+Z+Enter (Windows) za kraj unosa.")
    print()
    print("-" * 70)

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    return "\n".join(lines)


def main():
    args = parse_args()

    print()
    print("Provera dostupnosti Ollama servisa na " + OLLAMA_BASE_URL + " ...")
    if not check_ollama_availability():
        print()
        print("GRESKA: Ollama servis nije dostupan na " + OLLAMA_BASE_URL)
        print("Pokrenite Ollama servis komandom: ollama serve")
        print("I provernite da je zeljeni model preuzet komandom: ollama pull llama3.2")
        sys.exit(1)
    print("Ollama servis je dostupan.")
    print()

    # ── M1: Unos podataka ──────────────────────────────────────
    try:
        if args.file:
            print("Ucitavanje fajla: " + args.file)
            raw_text = load_from_file(args.file)
        else:
            raw_text = get_text_input()
            raw_text = load_from_text(raw_text)
    except InputValidationError as e:
        print()
        print("GRESKA PRI UNOSU: " + str(e))
        sys.exit(1)

    preprocessed = preprocess(raw_text)
    print()
    print("Ucitano i preprocesirano. Broj segmenata (chunkova): " + str(preprocessed["chunk_count"]))

    # ── M2 + M3: AI analiza, prioritizacija i akcioni plan ─────
    print()
    print("Pokrecem LangGraph workflow analize rizika...")
    if args.model:
        print("Koristim model: " + args.model)

    final_state = run_risk_analysis(preprocessed["cleaned_text"], model=args.model)

    if final_state.get("error"):
        print()
        print("GRESKA TOKOM ANALIZE: " + final_state["error"])
        sys.exit(1)

    risks = final_state.get("risks", [])
    top_risks = final_state.get("top_risks", [])

    print()
    print("Analiza zavrsena.")
    print("Ukupno identifikovanih rizika: " + str(len(risks)))
    print("Top prioritetnih rizika: " + str(len(top_risks)))

    # ── M4: Generisanje i izvoz izvestaja ──────────────────────
    markdown_report = format_as_markdown(final_state)
    json_report = format_as_json(final_state)

    md_path = export_markdown(markdown_report, directory=args.output_dir)
    json_path = export_json(json_report, directory=args.output_dir)

    print()
    print("Izvestaji sacuvani:")
    print("  - Markdown: " + md_path)
    print("  - JSON:     " + json_path)
    print()
    print("=" * 70)
    print("TOP 5 PRIORITETNIH RIZIKA:")
    print("=" * 70)
    for i, risk in enumerate(top_risks[:5], start=1):
        print(str(i) + ". [" + risk.get("priority_level", "?") + "] " + risk.get("name", "")
              + " (Score: " + str(risk.get("exposure_score", "?")) + ")")
    print()


if __name__ == "__main__":
    main()
