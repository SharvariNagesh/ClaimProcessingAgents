# agents/inow_agent.py
import json

def inow_agent(state: dict) -> dict:
    """
    Simulate INOW claim registration.
    In reality, this would call INOW API or use Playwright.
    """
    
    # Generate a mock claim ID
    import hashlib
    claim_data = json.dumps(state["extracted_fields"], sort_keys=True)
    mock_claim_id = "CLAIM-" + hashlib.md5(claim_data.encode()).hexdigest()[:8].upper()
    
    print(f"✅ INOW Agent: Claim registered with ID {mock_claim_id}")
    
    return {
        **state,
        "inow_claim_id": mock_claim_id,
        "status": "CLAIM_CREATED"
    }
