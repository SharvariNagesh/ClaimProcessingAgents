# tools/aws_tools.py
import boto3
from typing import List

REQUIRED_FIELDS = [
    "Policy Number",
    "Date of Loss",
    "Reported By",
    "Reported To",
    "Loss Description",
    "Cause of Loss"
]

def get_s3_pdf_list(bucket: str, prefix: str = "", region: str = "us-east-1") -> List[str]:
    """List all PDF files in S3 bucket."""
    
    s3 = boto3.client("s3", region_name=region)
    
    try:
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        pdfs = [
            obj["Key"]
            for obj in response.get("Contents", [])
            if obj["Key"].lower().endswith(".pdf")
        ]
        
        return sorted(pdfs)
    
    except Exception as e:
        print(f"Error listing S3 objects: {e}")
        return []

def download_file_from_s3(bucket: str, key: str, region: str = "us-east-1") -> bytes:
    """Download file from S3."""
    
    s3 = boto3.client("s3", region_name=region)
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()

def upload_file_to_s3(bucket: str, key: str, data: bytes, region: str = "us-east-1"):
    """Upload file to S3."""
    
    s3 = boto3.client("s3", region_name=region)
    s3.put_object(Bucket=bucket, Key=key, Body=data)

def download_policy_file_from_s3(bucket: str, key: str, region: str = "us-east-1") -> bytes:
    """Download Policy file from S3."""

    policy_pdf = "Policy/HP00000282-policy.pdf"
    s3 = boto3.client("s3", region_name=region)
    obj = s3.get_object(Bucket=bucket, Key=policy_pdf)
    return obj["Body"].read()

