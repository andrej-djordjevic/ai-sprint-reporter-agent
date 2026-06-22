"""
tests/test_agent.py

Unit i integration testovi agenta.
Sadrzi 3 testna primera ulaznih podataka (zahtev 14 iz specifikacije zadatka)
i validaciju strukture i sadrzaja outputa.

NAPOMENA: Integration testovi (test_full_pipeline_*) zahtevaju pokrenut
Ollama servis sa instaliranim modelom i NECE proci ako Ollama nije dostupan.
Pokrenuti ih posebno komandom: pytest tests/test_agent.py -m integration -v
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.loader import load_from_text, load_from_file, InputValidationError
from data.preprocessor import clean_text, chunk_text, preprocess
from agent.models import check_ollama_availability
from agent.graph import run_risk_analysis
from agent.nodes import _exposure_to_level, _extract_json
from agent.models import LLMResponseError


# ── PRIMER 1: Mala chat aplikacija za interni timski rad ───────
PROJECT_TEXT_1 = """
Razvijamo internu chat aplikaciju za komunikaciju izmedju zaposlenih u maloj firmi (50 korisnika).
Aplikacija koristi WebSocket protokol za real-time razmenu poruka, JWT autentikaciju za login,
i PostgreSQL bazu za cuvanje istorije poruka. Planiran je rad iskljucivo unutar firme,
bez potrebe za skaliranjem na vise od 100 istovremenih korisnika. Tim ima 2 developera
sa ogranicenim iskustvom u real-time sistemima i rok od 6 nedelja za prvu verziju.
"""

# ── PRIMER 2: Javna chat aplikacija sa visokim opterecenjem ────
PROJECT_TEXT_2 = """
Razvijamo javnu chat aplikaciju namenjenu sirokoj publici, slicnu WhatsApp-u, sa ocekivanih
50.000 istovremenih korisnika u prvih 6 meseci. Aplikacija ce koristiti end-to-end enkripciju
poruka, podrsku za slanje slika i video fajlova, push notifikacije, i potrebu za GDPR
uskladjenoscu jer ce raditi u EU. Planirano je koriscenje MongoDB baze, Redis za cache,
i CDN za distribuciju medijskih fajlova. Tim ima 8 developera i budzet je ogranicen
na 3 meseca razvoja pre lansiranja.
"""

# ── PRIMER 3: Customer support chat widget za web sajt ─────────
PROJECT_TEXT_3 = """
Razvijamo customer support chat widget koji se integrise na web sajtove klijenata (B2B SaaS proizvod).
Widget mora da podrzi vise istovremenih razgovora po agentu, integraciju sa eksternim CRM sistemom
putem REST API-ja, i automatski routing poruka prema dostupnim agentima. Bezbednost je kriticna
posto se razmenjuju osetljivi podaci klijenata. Planirano je koriscenje Node.js backend-a
i Socket.io biblioteke. Tim je nov i nema prethodno iskustvo sa multi-tenant arhitekturom.
"""


# ═══════════════════════════════════════════════════════════════
# UNIT TESTOVI - data/loader.py
# ═══════════════════════════════════════════════════════════════

class TestLoader:
    def test_load_from_text_valid(self):
        result = load_from_text(PROJECT_TEXT_1)
        assert len(result) > 50
        assert "WebSocket" in result

    def test_load_from_text_empty_raises_error(self):
        with pytest.raises(InputValidationError):
            load_from_text("")

    def test_load_from_text_too_short_raises_error(self):
        with pytest.raises(InputValidationError):
            load_from_text("Kratak tekst.")

    def test_load_from_file_nonexistent_raises_error(self):
        with pytest.raises(InputValidationError):
            load_from_file("/nonexistent/path/file.txt")

    def test_load_from_file_unsupported_format_raises_error(self):
        with pytest.raises(InputValidationError):
            load_from_file(__file__.replace(".py", ".pdf"))


# ═══════════════════════════════════════════════════════════════
# UNIT TESTOVI - data/preprocessor.py
# ═══════════════════════════════════════════════════════════════

class TestPreprocessor:
    def test_clean_text_removes_extra_whitespace(self):
        dirty = "Tekst   sa    viskom\t\trazmaka\n\n\n\nI praznih linija."
        cleaned = clean_text(dirty)
        assert "   " not in cleaned
        assert "\n\n\n" not in cleaned

    def test_chunk_text_short_text_single_chunk(self):
        chunks = chunk_text("Kratak tekst.", chunk_size=8000)
        assert len(chunks) == 1

    def test_chunk_text_long_text_multiple_chunks(self):
        long_text = "\n\n".join(["Paragraf broj " + str(i) + " sa dosta teksta unutra." * 20 for i in range(50)])
        chunks = chunk_text(long_text, chunk_size=500)
        assert len(chunks) > 1

    def test_preprocess_returns_expected_keys(self):
        result = preprocess(PROJECT_TEXT_2)
        assert "cleaned_text" in result
        assert "chunks" in result
        assert "chunk_count" in result
        assert result["chunk_count"] >= 1


# ═══════════════════════════════════════════════════════════════
# UNIT TESTOVI - agent/nodes.py (pomocne funkcije, bez LLM-a)
# ═══════════════════════════════════════════════════════════════

class TestNodeHelpers:
    def test_exposure_to_level_high(self):
        assert _exposure_to_level(20) == "HIGH"
        assert _exposure_to_level(15) == "HIGH"

    def test_exposure_to_level_medium(self):
        assert _exposure_to_level(10) == "MEDIUM"
        assert _exposure_to_level(8) == "MEDIUM"

    def test_exposure_to_level_low(self):
        assert _exposure_to_level(5) == "LOW"
        assert _exposure_to_level(1) == "LOW"

    def test_extract_json_valid_array(self):
        raw = '[{"id": "R01", "name": "Test rizik"}]'
        result = _extract_json(raw)
        assert len(result) == 1
        assert result[0]["id"] == "R01"

    def test_extract_json_with_markdown_fences(self):
        raw = '```json\n[{"id": "R01", "name": "Test"}]\n```'
        result = _extract_json(raw)
        assert len(result) == 1

    def test_extract_json_with_surrounding_text(self):
        raw = 'Evo rezultata:\n[{"id": "R01", "name": "Test"}]\nKraj.'
        result = _extract_json(raw)
        assert len(result) == 1

    def test_extract_json_invalid_raises_error(self):
        with pytest.raises(LLMResponseError):
            _extract_json("Ovo nije JSON nikako.")


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TESTOVI - kompletan workflow sa 3 testna primera
# Zahtevaju pokrenut Ollama servis (zahtev 14 iz specifikacije)
# ═══════════════════════════════════════════════════════════════

requires_ollama = pytest.mark.skipif(
    not check_ollama_availability(),
    reason="Ollama servis nije dostupan na localhost:11434 - integration test je preskocen."
)


class TestFullPipelineIntegration:
    """
    Testira kompletan LangGraph workflow na 3 realna primera projekata,
    u skladu sa zahtevom 14: 'Testirati agenta na najmanje 3 primera
    ulaznih podataka i sprovesti osnovnu validaciju outputa.'
    """

    @requires_ollama
    def test_full_pipeline_example_1_internal_chat(self):
        result = run_risk_analysis(PROJECT_TEXT_1)
        self._validate_output(result)

    @requires_ollama
    def test_full_pipeline_example_2_public_chat(self):
        result = run_risk_analysis(PROJECT_TEXT_2)
        self._validate_output(result)

    @requires_ollama
    def test_full_pipeline_example_3_support_widget(self):
        result = run_risk_analysis(PROJECT_TEXT_3)
        self._validate_output(result)

    def _validate_output(self, result):
        """Validacija strukture i sadrzaja outputa (NF-02 - Tacnost)."""
        assert result.get("error") is None, "Agent je vratio gresku: " + str(result.get("error"))

        risks = result.get("risks", [])
        assert len(risks) >= 5, "Agent treba da identifikuje najmanje 5 rizika."

        for risk in risks:
            assert "id" in risk
            assert "category" in risk
            assert "name" in risk
            assert "description" in risk
            assert "probability" in risk
            assert 1 <= risk["probability"] <= 5
            assert "impact" in risk
            assert 1 <= risk["impact"] <= 5
            assert "exposure_score" in risk
            assert risk["exposure_score"] == risk["probability"] * risk["impact"]

        top_risks = result.get("top_risks", [])
        assert len(top_risks) <= 10
        assert len(top_risks) > 0

        # Provera da je top lista sortirana opadajuce po exposure_score
        scores = [r["exposure_score"] for r in top_risks]
        assert scores == sorted(scores, reverse=True), "Top lista nije pravilno sortirana."

        # Svaki top rizik mora imati predlozenu akciju
        for risk in top_risks:
            assert "action" in risk
            assert len(risk["action"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
