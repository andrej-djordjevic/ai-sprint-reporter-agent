"""
agent/models.py

Apstrakcija LLM provajdera. Podržava više Ollama modela
(napredni zahtev: "Podrška za više modela") i obezbeđuje
error handling za nedostupan Ollama servis.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT", "120"))

SUPPORTED_MODELS = ["llama3.2", "llama3.1:8b", "mistral:7b", "codellama:13b"]


class LLMConnectionError(Exception):
    """Greška pri komunikaciji sa Ollama servisom."""
    pass


class LLMResponseError(Exception):
    """Greška pri obradi odgovora modela."""
    pass


def check_ollama_availability(base_url: str = OLLAMA_BASE_URL) -> bool:
    """
    Provera da li je Ollama servis dostupan (NF-04 — Pouzdanost).

    Args:
        base_url: URL Ollama servisa.

    Returns:
        True ako je servis dostupan, False inače.
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def list_available_models(base_url: str = OLLAMA_BASE_URL) -> list[str]:
    """
    Vraća listu modela koji su trenutno instalirani u lokalnom Ollama servisu.

    Args:
        base_url: URL Ollama servisa.

    Returns:
        Lista naziva modela.
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]
    except requests.exceptions.RequestException as e:
        raise LLMConnectionError(
            f"Ollama servis nije dostupan na {base_url}. "
            f"Provernite da je servis pokrenut komandom: ollama serve\nDetalji: {e}"
        )


def call_llm(
    prompt: str,
    system_prompt: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    base_url: str = OLLAMA_BASE_URL,
) -> str:
    """
    Glavna funkcija za pozivanje Ollama LLM-a.

    Args:
        prompt: Korisnička poruka / zadatak za model.
        system_prompt: Sistemski prompt koji definiše ulogu modela.
        model: Naziv Ollama modela (npr. "llama3.2").
        temperature: Temperatura modela (niža = konzistentniji rezultati, NF-05).
        base_url: URL Ollama servisa.

    Returns:
        Tekstualni odgovor modela.

    Raises:
        LLMConnectionError: ako Ollama servis nije dostupan ili je došlo do timeout-a.
        LLMResponseError: ako odgovor modela nije moguće parsirati.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise LLMConnectionError(
            f"Nije moguće povezati se sa Ollama servisom na {base_url}.\n"
            f"Provernite da je servis pokrenut komandom: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise LLMConnectionError(
            f"Ollama servis nije odgovorio u roku od {REQUEST_TIMEOUT_SECONDS} sekundi. "
            f"Pokušajte sa manjim modelom ili kraćim ulaznim tekstom."
        )
    except requests.exceptions.HTTPError as e:
        raise LLMConnectionError(f"Ollama servis je vratio grešku: {e}")

    try:
        data = response.json()
        return data["response"]
    except (ValueError, KeyError) as e:
        raise LLMResponseError(f"Nije moguće parsirati odgovor modela: {e}")
