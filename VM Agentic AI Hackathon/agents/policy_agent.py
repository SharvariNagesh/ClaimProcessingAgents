# agents/policy_agent.py
import boto3
import json
import fitz

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def fetch_policy_document(state: dict) -> str:
    """Extract text from PDF in S3."""

    s3 = boto3.client("s3", region_name="us-east-1")

    policy_pdf = "Policy/HP00000282-policy.pdf"

    response = s3.get_object(
        Bucket="kendra-it-helpdesk-docs-development",
        Key=policy_pdf
    )

    pdf_bytes = response["Body"].read()

    # Extract using PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    raw_text = ""

    for page in doc:
        raw_text += page.get_text("text")

    doc.close()
    print("✅ Policy document extracted:")

    return raw_text


def extract_relevant_policy_sections(policy_doc: str, claim_description: str, region: str = "us-east-1") -> str:

    prompt = f"""
You are an insurance policy analyst. Given the policy document and claim description,
identify and extract ONLY the policy sections relevant to processing this claim.
Format as a clear bulleted list with section names and key clauses.

Claim Description: {claim_description[:500]}

Policy Document:
{policy_doc}

Return only relevant sections. Be concise. Under 300 words.
"""
    

    model_id = "openai.gpt-oss-120b-1:0"

    response = bedrock.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {"text": prompt}
                ]
            }
        ],
        inferenceConfig={
            "maxTokens": 2000,
            "temperature": 0.5
        }
    )

    extracted_text = response

    print("extracted_text: ",extracted_text)
    print("✅ policy Section extracted")
    return extracted_text



def policy_agent(state: dict) -> dict:
    """Fetch policy and extract relevant sections."""
    
    policy_number = state["extracted_fields"].get("policy_number", "UNKNOWN")

    incident_desc="Water clogging"

    # Fetch policy
    policy_doc = fetch_policy_document(policy_number)
    
    # Extract relevant sections
    relevant_sections = extract_relevant_policy_sections(
        policy_doc,
        incident_desc,
        region= "us-east-1"
    )
    
    print(f"✅ Policy Agent: Policy fetched and analyzed")
    
    return {
        **state,
        "policy_doc": policy_doc,
        "relevant_policy_sections": relevant_sections,
        "status": "POLICY_ANALYZED"
    }
