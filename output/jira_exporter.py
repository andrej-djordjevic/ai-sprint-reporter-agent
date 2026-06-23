"""
output/jira_exporter.py

Izvoz top rizika u Jira kao Task issue-e (Modul M4 - prosirenje).
Koristi Jira Cloud REST API v3 sa Basic Auth (email + API token).
"""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "")

PRIORITY_MAP = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}
DEFAULT_MAX_ISSUES = 5


class JiraConfigError(Exception):
    """Nedostaju ili su neispravne Jira konfiguracione varijable."""
    pass


class JiraAPIError(Exception):
    """Greska pri komunikaciji sa Jira API-jem."""
    pass


def _slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _check_config(base_url, email, api_token, project_key):
    missing = []
    if not base_url:
        missing.append("JIRA_BASE_URL")
    if not email:
        missing.append("JIRA_EMAIL")
    if not api_token:
        missing.append("JIRA_API_TOKEN")
    if not project_key:
        missing.append("JIRA_PROJECT_KEY")
    if missing:
        raise JiraConfigError(
            "Nedostaju Jira konfiguracione varijable: " + ", ".join(missing) +
            ". Podesite ih u .env fajlu (vidi .env.example)."
        )


def _build_description_adf(risk):
    """Pravi Atlassian Document Format (ADF) opis issue-a od podataka o riziku."""
    summary_text = (
        "Kategorija: {category} | Verovatnoca: {probability}/5 | "
        "Uticaj: {impact}/5 | Exposure score: {score} ({level})"
    ).format(
        category=risk.get("category", "N/A"),
        probability=risk.get("probability", "N/A"),
        impact=risk.get("impact", "N/A"),
        score=risk.get("exposure_score", "N/A"),
        level=risk.get("priority_level", "N/A"),
    )

    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": risk.get("description", "")}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": summary_text}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Predlozena akcija: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": risk.get("action", "Nije generisana.")},
                ],
            },
        ],
    }


def create_issue_from_risk(
    risk,
    project_key=None,
    base_url=None,
    email=None,
    api_token=None,
):
    """
    Kreira jedan Jira Task issue od jednog rizika.

    Args:
        risk: Recnik sa podacima o riziku (id, name, category, description,
              probability, impact, exposure_score, priority_level, action).
        project_key: Jira kljuc projekta (default iz JIRA_PROJECT_KEY).
        base_url, email, api_token: Opcioni override Jira konfiguracije.

    Returns:
        Recnik {"key": "CRA-6", "url": "https://.../browse/CRA-6"}.

    Raises:
        JiraConfigError: ako konfiguracija nedostaje.
        JiraAPIError: ako Jira API vrati gresku.
    """
    base_url = (base_url or JIRA_BASE_URL).rstrip("/")
    email = email or JIRA_EMAIL
    api_token = api_token or JIRA_API_TOKEN
    project_key = project_key or JIRA_PROJECT_KEY

    _check_config(base_url, email, api_token, project_key)

    priority_name = PRIORITY_MAP.get(risk.get("priority_level"), "Medium")
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": "[{}] {}".format(risk.get("priority_level", "?"), risk.get("name", "Nepoznat rizik")),
            "issuetype": {"name": "Task"},
            "description": _build_description_adf(risk),
            "priority": {"name": priority_name},
            "labels": ["risk-management", _slugify(risk.get("category", "ostalo"))],
        }
    }

    try:
        response = requests.post(
            "{}/rest/api/3/issue".format(base_url),
            json=payload,
            auth=(email, api_token),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        raise JiraAPIError("Nije moguce povezati se sa Jira API-jem: " + str(e))

    if response.status_code not in (200, 201):
        raise JiraAPIError(
            "Jira API je vratio gresku ({}): {}".format(response.status_code, response.text)
        )

    data = response.json()
    issue_key = data["key"]
    return {"key": issue_key, "url": "{}/browse/{}".format(base_url, issue_key)}


def create_jira_tasks_from_risks(top_risks, max_issues=DEFAULT_MAX_ISSUES, project_key=None):
    """
    Kreira Jira Task issue-e za top N rizika.

    Args:
        top_risks: Lista prioritizovanih rizika (iz state["top_risks"]).
        max_issues: Maksimalan broj issue-a koji se kreira.
        project_key: Jira kljuc projekta (default iz JIRA_PROJECT_KEY).

    Returns:
        Lista recnika sa rezultatom po riziku:
        {"risk_id", "risk_name", "key", "url", "error"}.

    Raises:
        JiraConfigError: ako konfiguracija nedostaje (provereno pre prve izmene).
    """
    _check_config(JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, project_key or JIRA_PROJECT_KEY)

    results = []
    for risk in top_risks[:max_issues]:
        entry = {
            "risk_id": risk.get("id"),
            "risk_name": risk.get("name"),
            "key": None,
            "url": None,
            "error": None,
        }
        try:
            issue = create_issue_from_risk(risk, project_key=project_key)
            entry["key"] = issue["key"]
            entry["url"] = issue["url"]
        except JiraAPIError as e:
            entry["error"] = str(e)
        results.append(entry)

    return results
