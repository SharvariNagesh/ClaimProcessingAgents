# agents/hitl_agent.py
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def draft_missing_fields_email(missing_fields: list, claimant_email: str = "") -> str:
    """Use Claude to draft a polite email requesting missing info."""
    
    prompt = f"""
Draft a professional, empathetic email to a claimant requesting the following missing information 
from their claim submission. Be clear, concise, helpful, and friendly.

Missing fields: {', '.join(missing_fields)}

Write only the email body. Keep it under 250 words. No subject line needed.
"""
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=body,
        contentType="application/json"
    )
    
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

def hitl_agent(state: dict) -> dict:
    """
    Human-in-the-Loop: Draft email for missing fields.
    Streamlit will display this and wait for human approval.
    """
    
    claimant_email = state["extracted_fields"].get("claimant_contact_email", "")
    
    # Generate draft email using LLM
    draft_email = draft_missing_fields_email(
        state["missing_fields"],
        claimant_email
    )
    
    print(f"✅ HITL Agent: Draft email prepared (waiting for human review)")
    
    return {
        **state,
        "draft_email": draft_email,
        "status": "PENDING_HUMAN_REVIEW"
    }
