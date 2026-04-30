# agents/hitl_agent.py
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1",verify=False)

def draft_missing_fields_email(missing_fields: list, claimant_email: str = "") -> str:
    """Use Claude / GPT to draft a polite email requesting missing info."""

    prompt = f"""
Draft a professional, empathetic email to a claimant requesting the following missing information 
from their claim submission. Be clear, concise, helpful, and friendly.

Missing fields: {', '.join(missing_fields)}

Write only the email body. Keep it under 250 words. No subject line needed.
"""

    response = bedrock.converse(
        modelId="openai.gpt-oss-120b-1:0",
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        inferenceConfig={
            "maxTokens": 2000,
            "temperature": 0.5
        }
    )

    print("Hackathon:", response)

    # ✅ SAFE extraction of text (NO JSON PARSING)
    content_items = response["output"]["message"]["content"]
    email_text = next(item["text"] for item in content_items if "text" in item)

    print("Extracted email body:", email_text)
    return email_text

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
