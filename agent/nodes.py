"""
agent/nodes.py

Cvorovi LangGraph workflow-a (Modul M2 i M3).
Svaki cvor predstavlja jedan korak obrade u state masini agenta.
"""

import json
import re

from agent.models import call_llm, LLMConnectionError, LLMResponseError
from agent.prompts import (
    IDENTIFY_RISKS_SYSTEM_PROMPT,
    ASSESS_RISKS_SYSTEM_PROMPT,
    GENERATE_ACTIONS_SYSTEM_PROMPT,
    build_identify_prompt,
    build_assess_prompt,
    build_actions_prompt,
)

TOP_N_RISKS = 10
HIGH_THRESHOLD = 15
MEDIUM_THRESHOLD = 8


def _extract_json(raw_response):
    raw_response = raw_response.strip()
    raw_response = re.sub(r"^```(?:json)?\s*", "", raw_response)
    raw_response = re.sub(r"\s*```$", "", raw_response)

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", raw_response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            raise LLMResponseError("Model je vratio neispravan JSON: " + str(e))

    raise LLMResponseError("Odgovor modela ne sadrzi prepoznatljiv JSON niz.")


def identify_risks_node(state):
    project_text = state["project_text"]
    model = state.get("model")
    prompt = build_identify_prompt(project_text)

    try:
        if model:
            raw_response = call_llm(prompt=prompt, system_prompt=IDENTIFY_RISKS_SYSTEM_PROMPT, model=model)
        else:
            raw_response = call_llm(prompt=prompt, system_prompt=IDENTIFY_RISKS_SYSTEM_PROMPT)
    except LLMConnectionError as e:
        state["error"] = str(e)
        state["risks"] = []
        return state

    try:
        risks = _extract_json(raw_response)
    except LLMResponseError as e:
        state["error"] = str(e)
        state["risks"] = []
        return state

    state["risks"] = risks
    return state


def assess_risks_node(state):
    if state.get("error") or not state.get("risks"):
        return state

    risks = state["risks"]
    model = state.get("model")

    risks_for_prompt = []
    for r in risks:
        risks_for_prompt.append({"id": r["id"], "name": r["name"]})

    prompt = build_assess_prompt(json.dumps(risks_for_prompt, ensure_ascii=False))

    try:
        if model:
            raw_response = call_llm(prompt=prompt, system_prompt=ASSESS_RISKS_SYSTEM_PROMPT, model=model)
        else:
            raw_response = call_llm(prompt=prompt, system_prompt=ASSESS_RISKS_SYSTEM_PROMPT)
    except LLMConnectionError as e:
        state["error"] = str(e)
        return state

    try:
        assessments = _extract_json(raw_response)
    except LLMResponseError as e:
        state["error"] = str(e)
        return state

    assessment_map = {}
    for a in assessments:
        assessment_map[a["id"]] = a

    for risk in risks:
        default_assessment = {"probability": 3, "impact": 3}
        assessment = assessment_map.get(risk["id"], default_assessment)
        probability = int(assessment.get("probability", 3))
        impact = int(assessment.get("impact", 3))
        probability = max(1, min(5, probability))
        impact = max(1, min(5, impact))

        risk["probability"] = probability
        risk["impact"] = impact
        risk["exposure_score"] = probability * impact
        risk["priority_level"] = _exposure_to_level(risk["exposure_score"])

    state["risks"] = risks
    return state


def _exposure_to_level(score):
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def prioritize_node(state):
    if state.get("error") or not state.get("risks"):
        state["top_risks"] = []
        return state

    sorted_risks = sorted(state["risks"], key=lambda r: r.get("exposure_score", 0), reverse=True)
    state["top_risks"] = sorted_risks[:TOP_N_RISKS]
    return state


def generate_actions_node(state):
    if state.get("error") or not state.get("top_risks"):
        return state

    top_risks = state["top_risks"]
    model = state.get("model")

    risks_for_prompt = []
    for r in top_risks:
        risks_for_prompt.append({"id": r["id"], "name": r["name"], "category": r["category"]})

    prompt = build_actions_prompt(json.dumps(risks_for_prompt, ensure_ascii=False))

    try:
        if model:
            raw_response = call_llm(prompt=prompt, system_prompt=GENERATE_ACTIONS_SYSTEM_PROMPT, model=model)
        else:
            raw_response = call_llm(prompt=prompt, system_prompt=GENERATE_ACTIONS_SYSTEM_PROMPT)
    except LLMConnectionError as e:
        state["error"] = str(e)
        return state

    try:
        actions = _extract_json(raw_response)
    except LLMResponseError as e:
        state["error"] = str(e)
        return state

    action_map = {}
    for a in actions:
        action_map[a["id"]] = a.get("action", "")

    for risk in top_risks:
        default_action = "Akcija nije generisana - preporucuje se manuelna analiza."
        risk["action"] = action_map.get(risk["id"], default_action)

    state["top_risks"] = top_risks
    return state
