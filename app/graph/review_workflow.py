"""Compiled LangGraph workflow for contract review."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.graph import review_nodes
from app.graph.review_state import ReviewState


@lru_cache(maxsize=1)
def get_review_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("parse_contract", review_nodes.parse_contract_node)
    builder.add_node("scan_rules", review_nodes.scan_rules_node)
    builder.add_node("retrieve_context", review_nodes.retrieve_context_node)
    builder.add_node("assess", review_nodes.assess_node)
    builder.add_node("save_review", review_nodes.save_review_node)

    builder.set_entry_point("parse_contract")
    builder.add_edge("parse_contract", "scan_rules")
    builder.add_edge("scan_rules", "retrieve_context")
    builder.add_edge("retrieve_context", "assess")
    builder.add_edge("assess", "save_review")
    builder.add_edge("save_review", END)
    return builder.compile()
