# Create test claim in S3
import boto3

s3 = boto3.client("s3")

test_claim = """
CLAIM SUBMISSION FORM

Claimant Name: John Doe
Policy Number: POL-2024-001
Date of Incident: 2024-04-15
Incident Description: Car accident on highway 101. Damage to front bumper and fender.
Claim Amount: $5,000
Contact Email: john.doe@email.com
Phone: 555-1234

Supporting Documents:
- Police report
- Photos of damage
- Repair estimates
"""

s3.put_object(
    Bucket="",
    Key="claim_001.txt",  # Will be treated as text
    Body=test_claim
)
