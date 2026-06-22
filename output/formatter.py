"""
output/formatter.py

Formatira rezultate analize rizika u Markdown i JSON format (Modul M4).
"""

import json
from datetime import datetime


def format_as_json(state):
    """
    Formatira kompletan rezultat analize u JSON strukturu.

    Args:
        state: Konacno stanje LangGraph workflow-a (sadrzi "risks" i "top_risks").

    Returns:
        Python recnik spreman za json.dump.
    """
    return {
        "generated_at": datetime.now().isoformat(),
        "total_risks_identified": len(state.get("risks", [])),
        "all_risks": state.get("risks", []),
        "top_10_risks": state.get("top_risks", []),
    }


def format_as_markdown(state):
    """
    Formatira kompletan rezultat analize u Markdown izvestaj citljiv za PM-a.

    Args:
        state: Konacno stanje LangGraph workflow-a.

    Returns:
        Markdown tekst kao string.
    """
    risks = state.get("risks", [])
    top_risks = state.get("top_risks", [])
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

    lines = []
    lines.append("# Izvestaj o rizicima chat aplikacije")
    lines.append("")
    lines.append("Generisano: " + timestamp)
    lines.append("")
    lines.append("## Sazetak")
    lines.append("")
    lines.append("Ukupno identifikovano rizika: **" + str(len(risks)) + "**")
    lines.append("")

    lines.append("## Top " + str(len(top_risks)) + " prioritetnih rizika")
    lines.append("")
    lines.append("| # | Kategorija | Naziv | P | I | Score | Prioritet | Akcija |")
    lines.append("|---|---|---|---|---|---|---|---|")

    for i, risk in enumerate(top_risks, start=1):
        row = "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
            i,
            risk.get("category", ""),
            risk.get("name", ""),
            risk.get("probability", ""),
            risk.get("impact", ""),
            risk.get("exposure_score", ""),
            risk.get("priority_level", ""),
            risk.get("action", ""),
        )
        lines.append(row)

    lines.append("")
    lines.append("## Svi identifikovani rizici po kategorijama")
    lines.append("")

    categories = {}
    for risk in risks:
        cat = risk.get("category", "Nepoznato")
        categories.setdefault(cat, []).append(risk)

    for cat, cat_risks in categories.items():
        lines.append("### " + cat)
        lines.append("")
        for risk in cat_risks:
            score = risk.get("exposure_score", "N/A")
            level = risk.get("priority_level", "N/A")
            lines.append(
                "- **" + risk.get("name", "") + "** (Score: " + str(score) + ", " + str(level) + ") - "
                + risk.get("description", "")
            )
        lines.append("")

    return "\n".join(lines)
