# orchestrator/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
from agents.extraction_agent import extraction_agent
from agents.validation_agent import validation_agent
from agents.hitl_agent import hitl_agent
from agents.policy_agent import policy_agent
from agents.inow_agent import inow_agent
from agents.adjuster_agent import adjuster_agent


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
    adjuster_evaluation: Optional[list]
    recommended_adjuster: Optional[dict]
    assigned_adjuster: Optional[dict]
    status: str


def route_after_validation(state: ClaimState) -> str:
    """Route to HITL if missing fields, otherwise stop for human prompt."""
    if state.get("missing_fields"):
        return "hitl_agent"
    return "stop"   # UI will take over


# ── Phase 1: Extract + Validate ──────────────────────────────────────────────
def build_phase1_graph():
    """Extract text and validate fields. Stops before policy fetch."""
    graph = StateGraph(ClaimState)

    graph.add_node("extraction_agent", extraction_agent)
    graph.add_node("validation_agent", validation_agent)
    graph.add_node("hitl_agent", hitl_agent)

    graph.set_entry_point("extraction_agent")
    graph.add_edge("extraction_agent", "validation_agent")

    graph.add_conditional_edges(
        "validation_agent",
        route_after_validation,
        {
            "hitl_agent": "hitl_agent",
            "stop": END              # all fields present — UI prompts user next
        }
    )
    graph.add_edge("hitl_agent", END)

    return graph.compile()


# ── Phase 2: Policy fetch only ───────────────────────────────────────────────
def build_phase2_graph():
    """Fetch and analyse policy document only."""
    graph = StateGraph(ClaimState)
    graph.add_node("policy_agent", policy_agent)
    graph.set_entry_point("policy_agent")
    graph.add_edge("policy_agent", END)
    return graph.compile()


# ── Phase 3: Register claim in INOW ─────────────────────────────────────────
def build_phase3_graph():
    """Register the claim in INOW and return a claim ID."""
    graph = StateGraph(ClaimState)
    graph.add_node("inow_agent", inow_agent)
    graph.set_entry_point("inow_agent")
    graph.add_edge("inow_agent", END)
    return graph.compile()


# ── Phase 4: Assign adjuster ─────────────────────────────────────────────────
def build_phase4_graph():
    """Score and recommend an adjuster."""
    graph = StateGraph(ClaimState)
    graph.add_node("adjuster_agent", adjuster_agent)
    graph.set_entry_point("adjuster_agent")
    graph.add_edge("adjuster_agent", END)
    return graph.compile()


# ── Public entrypoints ────────────────────────────────────────────────────────
def run_claim_workflow_phase1(bucket: str, key: str, region: str = "us-east-1") -> dict:
    """Phase 1: Extract text and validate required fields."""
    app = build_phase1_graph()
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
        adjuster_evaluation=None,
        recommended_adjuster=None,
        assigned_adjuster=None,
        status="STARTED"
    )
    return dict(app.invoke(initial_state))


def run_claim_workflow_phase2(state: dict) -> dict:
    """Phase 2: Fetch and analyse the policy document."""
    app = build_phase2_graph()
    return dict(app.invoke(state))


def run_claim_workflow_phase3(state: dict) -> dict:
    """Phase 3: Register claim in INOW and return claim ID."""
    app = build_phase3_graph()
    return dict(app.invoke(state))


def run_claim_workflow_phase4(state: dict) -> dict:
    """Phase 4: Score adjusters and return ranked recommendations."""
    app = build_phase4_graph()
    return dict(app.invoke(state))