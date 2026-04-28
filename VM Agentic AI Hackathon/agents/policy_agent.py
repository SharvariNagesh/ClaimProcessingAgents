# agents/policy_agent.py
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def fetch_policy_document(policy_number: str) -> dict:
    """
    Fetch policy from internal API.
    For demo: return mock policy.
    """
    
    # Mock policy data (in reality, call an API)
    mock_policy = {
        "policy_number": policy_number,
        "policy_type": "Auto Insurance",
        "coverage": {
            "liability": "$100,000",
            "collision": "$50,000",
            "comprehensive": "$25,000"
        },
        "exclusions": [
            "Acts of war",
            "Intentional damage",
            "Mechanical breakdown"
        ],
        "deductibles": {
            "collision": "$500",
            "comprehensive": "$250"
        }
    }
    
    return mock_policy

def extract_relevant_policy_sections(policy_doc: dict, claim_description: str, region: str = "us-east-1") -> str:
    """Use Claude to find relevant policy sections."""
    
    policy_text = json.dumps(policy_doc, indent=2)
    
    prompt = f"""
You are an insurance policy analyst. Given the policy document and claim description,
identify and extract ONLY the policy sections relevant to processing this claim.
Format as a clear bulleted list with section names and key clauses.

Claim Description: {claim_description[:500]}

Policy Document:
{policy_text}

Return only relevant sections. Be concise. Under 300 words.
"""
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    bedrock_client = boto3.client("bedrock-runtime", region_name=region)
    
    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=body,
        contentType="application/json"
    )
    
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

def policy_agent(state: dict) -> dict:
    """Fetch policy and extract relevant sections."""
    
    policy_number = state["extracted_fields"].get("policy_number", "UNKNOWN")
    incident_desc = state["extracted_fields"].get("incident_description", "")
    
    # Fetch policy
    policy_doc = fetch_policy_document(policy_number)
    
    # Extract relevant sections
    relevant_sections = extract_relevant_policy_sections(
        policy_doc,
        incident_desc,
        region=state.get("region", "us-east-1")
    )
    
    print(f"✅ Policy Agent: Policy fetched and analyzed")
    
    return {
        **state,
        "policy_doc": policy_doc,
        "relevant_policy_sections": relevant_sections,
        "status": "POLICY_ANALYZED"
    }
