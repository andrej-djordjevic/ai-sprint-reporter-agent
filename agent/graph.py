"""
agent/graph.py

LangGraph StateGraph definicija koja povezuje cetiri cvora
u jedan visekoracni workflow agenta.
"""

from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from agent.nodes import (
    identify_risks_node,
    assess_risks_node,
    prioritize_node,
    generate_actions_node,
)


class AgentState(TypedDict, total=False):
    project_text: str
    model: Optional[str]
    risks: List[dict]
    top_risks: List[dict]
    error: Optional[str]


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("identify_risks", identify_risks_node)
    graph.add_node("assess_risks", assess_risks_node)
    graph.add_node("prioritize", prioritize_node)
    graph.add_node("generate_actions", generate_actions_node)

    graph.set_entry_point("identify_risks")
    graph.add_edge("identify_risks", "assess_risks")
    graph.add_edge("assess_risks", "prioritize")
    graph.add_edge("prioritize", "generate_actions")
    graph.add_edge("generate_actions", END)

    return graph.compile()


def run_risk_analysis(project_text, model=None):
    app = build_graph()

    initial_state = {"project_text": project_text}
    if model:
        initial_state["model"] = model

    final_state = app.invoke(initial_state)
    return final_state
