# agents/policy_agent.py
import boto3
import fitz
import re

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1",verify=False)

def fetch_policy_document(state: dict) -> str:
    """Extract text from PDF in S3."""

    s3 = boto3.client("s3", region_name="us-east-1",verify=False)

    policy_pdf = "Policy/HP00000282-policy_document.pdf"

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
    print("Claim Description :" + claim_description)
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

    print("policy extract: ", response)
    extracted_text = None
    reasoning_text = None
    for item in response["output"]["message"]["content"]:
        if "text" in item:
            extracted_text = item["text"]
        if "reasoningContent" in item:
            reasoning_text = item["reasoningContent"]["reasoningText"]["text"]


    print("Reasoning text :", reasoning_text)

    print("extracted_text: ",extracted_text)
    print("✅ policy Section extracted")
    return extracted_text


def clean_pdf_text(text: str) -> str:
    # Convert Windows/Mac newlines to Unix
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove excessive newlines (3+ → 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove line breaks in the middle of sentences
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

    # Fix extra spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)


    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n\d+\n', '\n', text)


    return text.strip()


def reconstruct_paragraphs(text: str) -> str:
    paragraphs = []
    current = []

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(line)

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def policy_agent(state: dict) -> dict:
    """Fetch policy and extract relevant sections."""
    print(state)

    policy_number = state["extracted_fields"].get("policy_number", "UNKNOWN")

    incident_desc= state["extracted_fields"]["Cause of Loss"]

    # Fetch policy
    policy_doc = fetch_policy_document(policy_number)
    
    # Extract relevant sections
    relevant_sections = extract_relevant_policy_sections(
        policy_doc,
        incident_desc,
        region= "us-east-1"
    )

    relevant_sections = clean_pdf_text(relevant_sections)
    relevant_sections = reconstruct_paragraphs(relevant_sections)
    print("After cleaning the pdf:", relevant_sections)
    print(f"✅ Policy Agent: Policy fetched and analyzed")
    
    return {
        **state,
        "policy_doc": policy_doc,
        "relevant_policy_sections": relevant_sections,
        "status": "POLICY_ANALYZED"
    }
