"""Compiled LangGraph workflow for legal Q&A."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.graph import qa_nodes
from app.graph.qa_state import QAState


@lru_cache(maxsize=1)
def get_qa_graph():
    builder = StateGraph(QAState)
    builder.add_node("analyze_question", qa_nodes.analyze_question_node)
    builder.add_node("retrieve_laws", qa_nodes.retrieve_laws_node)
    builder.add_node("calculate", qa_nodes.calculate_node)
    builder.add_node("compose_answer", qa_nodes.compose_answer_node)
    builder.add_node("save_record", qa_nodes.save_qa_node)

    builder.set_entry_point("analyze_question")
    builder.add_edge("analyze_question", "retrieve_laws")
    builder.add_edge("retrieve_laws", "calculate")
    builder.add_edge("calculate", "compose_answer")
    builder.add_edge("compose_answer", "save_record")
    builder.add_edge("save_record", END)
    return builder.compile()
