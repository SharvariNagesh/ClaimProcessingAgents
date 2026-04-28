# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "vm-kendra-chatbot-db-to-be-deleted")

# Bedrock
BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

# Streamlit
STREAMLIT_PAGE_TITLE = "Claims Processing Center"
STREAMLIT_PAGE_ICON = "📋"
