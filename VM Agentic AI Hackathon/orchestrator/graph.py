
# orchestrator/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
from agents.extraction_agent import extraction_agent
from agents.validation_agent import validation_agent
from agents.hitl_agent import hitl_agent
from agents.policy_agent import policy_agent
from agents.inow_agent import inow_agent

class ClaimState(TypedDict):
    bucket: str
    key: str
    region: str
    raw_text: str
    extracted_fields: dict
    missing_fields: List[str]
    draft_email: Optional[str]
    policy_doc: Optional[dict]
    relevant_policy_sections: Optional[str]
    inow_claim_id: Optional[str]
    status: str

def route_after_validation(state: ClaimState) -> str:
    """Decide next node based on missing fields."""
    if state.get("missing_fields"):
        return "hitl_agent"
    return "policy_agent"

def build_graph():
    """Build the LangGraph workflow."""
    graph = StateGraph(ClaimState)
    
    # Add agent nodes
    graph.add_node("extraction_agent", extraction_agent)
    graph.add_node("validation_agent", validation_agent)
    graph.add_node("hitl_agent", hitl_agent)
    graph.add_node("policy_agent", policy_agent)
    graph.add_node("inow_agent", inow_agent)
    
    # Define flow
    graph.set_entry_point("extraction_agent")
    graph.add_edge("extraction_agent", "validation_agent")
    graph.add_edge("validation_agent", END)
    # Conditional routing
    graph.add_conditional_edges(
        "validation_agent",
        route_after_validation,
        {
            "hitl_agent": "hitl_agent",
            # "policy_agent": "policy_agent"
        }
    )
    
    # HITL ends here
    graph.add_edge("hitl_agent", END)
    
    # Otherwise continue
    # graph.add_edge("policy_agent", "inow_agent")
    # graph.add_edge("inow_agent", END)
    #
    return graph.compile()

def run_claim_workflow(bucket: str, key: str, region: str = "us-east-1") -> dict:
    """Run the entire workflow and return final state."""
    
    app = build_graph()
    
    initial_state = ClaimState(
        bucket=bucket,
        key=key,
        region=region,
        raw_text="",
        extracted_fields={},
        missing_fields=[],
        draft_email=None,
        policy_doc=None,
        relevant_policy_sections=None,
        inow_claim_id=None,
        status="STARTED"
    )
    
    final_state = app.invoke(initial_state)
    
    return dict(final_state)
