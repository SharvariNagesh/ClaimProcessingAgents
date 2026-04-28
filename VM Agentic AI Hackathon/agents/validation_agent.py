# agents/validation_agent.py
import boto3
import json
from tools.aws_tools import REQUIRED_FIELDS

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def extract_fields_with_llm(raw_text: str) -> dict:
    """Use Claude to extract structured fields from raw text."""
    
    prompt = f"""
You are a claims processing assistant. Extract the following fields from the claim document text below.
Return ONLY a valid JSON object. If a field is not found, set its value to null.

Required fields: {json.dumps(REQUIRED_FIELDS)}

Document text:
---
{raw_text[:3000]}
---

Return only the JSON, nothing else.
"""
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 800,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=body,
        contentType="application/json"
    )
    
    result_body = json.loads(response["body"].read())
    extracted_text = result_body["content"][0]["text"]
    
    # Parse JSON response
    try:
        extracted_fields = json.loads(extracted_text)
    except json.JSONDecodeError:
        extracted_fields = {}
    
    return extracted_fields

def validation_agent(state: dict) -> dict:
    """Validate all required fields are present."""
    
    extracted = extract_fields_with_llm(state["raw_text"])
    
    missing_fields = [
        field for field in REQUIRED_FIELDS
        if not extracted.get(field)
    ]
    
    print(f"✅ Validation complete: {len(missing_fields)} missing fields")
    
    return {
        **state,
        "extracted_fields": extracted,
        "missing_fields": missing_fields,
        "status": "VALIDATION_COMPLETE"
    }
