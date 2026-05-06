# agents/extraction_agent.py
import fitz
import boto3

def extraction_agent(state: dict) -> dict:
    """Extract text from PDF in S3."""

    s3 = boto3.client("s3", region_name=state.get("region", "us-east-1"), verify = False)
# Download PDF from S3
    obj = s3.get_object(Bucket=state["bucket"], Key=state["key"])
    pdf_bytes = obj["Body"].read()
    
    # Extract using PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    raw_text = ""
    
    for page in doc:
        raw_text += page.get_text("text")
    
    doc.close()
    
    print(f"✅ Extraction complete: {len(raw_text)} characters extracted")
    
    return {
        **state,
        "raw_text": raw_text,
        "status": "EXTRACTION_COMPLETE"
    }
