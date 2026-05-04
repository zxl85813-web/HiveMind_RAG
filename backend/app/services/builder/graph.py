"""
LangGraph definition for the Agent Builder Assistant (REQ-014).
Implements the 6-stage structured interview protocol.
"""
from langgraph.graph import StateGraph, END

from .state import BuilderState
from .nodes import (
    template_search_node,
    interview_node,
    context_injection_node,
    scope_guardian_node,
    testset_creation_node,
    confirm_node,
    generate_config_node,
    eval_preview_node
)

def build_builder_graph() -> StateGraph:
    """Build and compile the Agent Builder graph."""
    workflow = StateGraph(BuilderState)

    # Add Nodes
    workflow.add_node("template_search", template_search_node)
    workflow.add_node("interview", interview_node)
    workflow.add_node("context_injection", context_injection_node)
    workflow.add_node("scope_guardian", scope_guardian_node)
    workflow.add_node("testset_creation", testset_creation_node)
    workflow.add_node("eval_preview", eval_preview_node)
    workflow.add_node("confirm", confirm_node)
    workflow.add_node("generate_config", generate_config_node)

    # Define Routing Functions
    def route_from_template(state: BuilderState) -> str:
        # TODO: Implement matching logic
        # if found_match: return "interview" (or show_template if we add that node)
        return "interview"

    def route_from_guardian(state: BuilderState) -> str:
        step = state.get("next_step")
        if step == "force_scope_review" or step == "warn_scope":
            return "interview" # Go back to interview to resolve scope issue
        return "context_injection"

    def route_from_context(state: BuilderState) -> str:
        # Normally goes to web research, then gap analysis, but for simplicity
        # we route to testset_creation if coverage is met, else back to interview.
        if state.get("coverage_pct", 0.0) >= 0.7:
            return "testset_creation"
        return "interview"

    def route_from_testset(state: BuilderState) -> str:
        step = state.get("next_step")
        if step == "test_cases_passed":
            return "eval_preview"
        return "interview" # Go back to interview to ask for better tests

    def route_from_eval(state: BuilderState) -> str:
        return "confirm"

    def route_from_confirm(state: BuilderState) -> str:
        step = state.get("next_step")
        if step == "approved":
            return "generate_config"
        return "interview"

    # Define Edges
    workflow.set_entry_point("template_search")
    
    workflow.add_conditional_edges(
        "template_search",
        route_from_template,
        {"interview": "interview"}
    )
    
    workflow.add_edge("interview", "scope_guardian")
    
    workflow.add_conditional_edges(
        "scope_guardian",
        route_from_guardian,
        {
            "interview": "interview",
            "context_injection": "context_injection"
        }
    )
    
    workflow.add_conditional_edges(
        "context_injection",
        route_from_context,
        {
            "testset_creation": "testset_creation",
            "interview": "interview"
        }
    )
    
    workflow.add_conditional_edges(
        "testset_creation",
        route_from_testset,
        {
            "eval_preview": "eval_preview",
            "interview": "interview"
        }
    )
    
    workflow.add_edge("eval_preview", "confirm")
    
    workflow.add_conditional_edges(
        "confirm",
        route_from_confirm,
        {
            "generate_config": "generate_config",
            "interview": "interview"
        }
    )
    
    workflow.add_edge("generate_config", END)

    return workflow.compile()
