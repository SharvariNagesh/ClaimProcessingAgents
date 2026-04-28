Project Structure
claim-agent-streamlit/
├── app.py                          # Main Streamlit app
├── agents/
│   ├── __init__.py
│   ├── extraction_agent.py
│   ├── validation_agent.py
│   ├── policy_agent.py
│   ├── inow_agent.py
│   └── hitl_agent.py
├── orchestrator/
│   └── graph.py                    # LangGraph workflow
├── tools/
│   ├── pdf_tools.py
│   ├── aws_tools.py
│   ├── inow_tools.py
│   └── policy_tools.py
├── config/
│   ├── required_fields.json
│   └── settings.py
├── requirements.txt
├── .env
├── s3_sample_data/                 # Sample claims for demo
│   ├── claim_001.pdf
│   ├── claim_002.pdf
│   └── claim_003.pdf
└── README.md

Tech Stack:
------------

Layer                Technology               Why
Frontend            Streamlit                No React build, instant deployment, live updates
Backend Logic       Python + LangGraph       Same agents as before
LLM                 AWS Bedrock (Claude)    Same as before
PDF Extract         PyMuPDF                  Fast, free, pure Python
File Storage        S3                        Source of all data (PDFs + outputs)
State               Streamlit Session State  In-memory, no database needed

Complete Call Flow

┌─────────────────────────────────────────────────────┐
│ STREAMLIT APP (Single Process)                      │
│                                                      │
│ 1. Load & list PDFs from S3                        │
│    st.selectbox() → ["claim_001.pdf", ...]         │
│                                                      │
│ 2. User clicks "Process Claim"                      │
│    ↓                                                │
│ 3. Download PDF from S3                            │
│    ↓                                                │
│ 4. Run LangGraph Workflow (All Agents in-memory)   │
│    • Extraction Agent                              │
│    • Validation Agent                              │
│    • Policy Agent (or HITL Agent)                  │
│    • INOW Agent                                    │
│    ↓                                                │
│ 5. MISSING FIELDS?                                 │
│    ├─ YES: Show draft email in Streamlit           │
│    │        User edits & clicks "Approve"          │
│    │        Save to S3: drafts/claim_001_email.txt │
│    │        STOP (wait for manual follow-up)       │
│    │                                                │
│    └─ NO: Continue to Policy Agent                 │
│            → INOW Agent                            │
│            → Show success with claim ID            │
│                                                      │
│ 6. Display results in Streamlit UI                 │
│    • Extracted fields table                        │
│    • Policy sections (if complete)                 │
│    • INOW claim ID (if created)                    │
│                                                      │
└─────────────────────────────────────────────────────┘



==================
# 1. Clone repo
git clone <your-repo>
cd claim-agent-streamlit

# 2. Create virtual env
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set AWS credentials
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
# OR use AWS CLI: aws configure

# 5. Create .env file
echo "AWS_REGION=us-east-1" > .env
echo "S3_BUCKET=claims-bucket" >> .env

# 6. Run Streamlit app
streamlit run app.py

# Opens at http://localhost:8501

┌─────────────────────────────────────────────────────────┐
│                   STREAMLIT APP                         │
│                   (Single Python App)                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Sidebar: Configure S3 Bucket + AWS Region       │   │
│  └──────────────────────────────────────────────────┘   │
│                          ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Tab 1: Select PDF from S3 Dropdown              │   │
│  │ [claim_001.pdf, claim_002.pdf, ...]             │   │
│  └──────────────────────────────────────────────────┘   │
│                          ↓                               │
│              Click "Process Claim"                       │
│                          ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │ LangGraph Workflow (In-Memory)                   │   │
│  │ ┌─ Extraction Agent  ──────────────────────┐    │   │
│  │ │ Download PDF from S3                     │    │   │
│  │ │ Extract text with PyMuPDF                │    │   │
│  │ └──────────────────────────────────────────┘    │   │
│  │                     ↓                           │   │
│  │ ┌─ Validation Agent ──────────────────────┐    │   │
│  │ │ Use Bedrock Claude to extract fields    │    │   │
│  │ │ Check for missing fields                │    │   │
│  │ └──────────────────────────────────────────┘    │   │
│  │                     ↓                           │   │
│  │  ┌─ If Missing Fields ──┐  ┌─ If Complete ──┐  │   │
│  │  │ HITL Agent           │  │ Policy Agent    │  │   │
│  │  │ (Draft Email)        │  │ (Analysis)      │  │   │
│  │  └──────────────────────┘  └─────────────────┘  │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                          ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Tab 2: Display Results                           │   │
│  │ • Extracted fields (table)                       │   │
│  │ • Missing fields (alerts)                        │   │
│  │ • Policy sections (if complete)                  │   │
│  │ • INOW Claim ID (if created)                     │   │
│  └──────────────────────────────────────────────────┘   │
│                          ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Tab 3: Draft Email (Human Review)                │   │
│  │ • Show missing fields                            │   │
│  │ • Allow editing of draft email                   │   │
│  │ • "Approve & Save" button                        │   │
│  │   → Saves to S3: drafts/claim_001_email.txt      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          ↓↓↓
                    AWS SERVICES
                    
    S3 Bucket              Bedrock
    • PDFs                 • Claude LLM
    • Draft Emails         • Field extraction
                           • Policy analysis

                           Sample test data
s3://claims-bucket/
├── claim_001.pdf
├── claim_002.pdf
├── claim_003.pdf
└── drafts/
    └── (draft emails saved here)

Team work division
---------------------------------------------------------------------
Developer 1 — "Frontend Specialist"
├── Build Streamlit app structure (tabs, layout, styling)
├── Design PDF selector dropdown
├── Create results display UI
└── Learn: Streamlit widgets, session state, CSS

Developer 2 — "Orchestrator & Workflow"
├── Build LangGraph workflow
├── Implement extraction + validation agents
├── Handle state transitions
└── Learn: LangGraph, state management, Bedrock

Developer 3 — "HITL & Email"
├── Implement HITL agent (draft email generation)
├── Draft email display in Streamlit
├── Save approved drafts to S3
└── Learn: LLM prompting, Streamlit text areas

Developer 4 — "Policy & Integration"
├── Implement policy agent
├── Implement INOW agent
├── AWS tools (S3, Bedrock)
└── Learn: API integration, mock systems


bash
# Step 1: Setup
git clone <repo>
pip install -r requirements.txt
aws configure
# Step 2: Add sample PDFs to S3
aws s3 cp sample_claims/ s3://claims-bucket/ --recursive
# Step 3: Run app
streamlit run app.py

Complete File Tree (Final)
==========================

claim-agent-streamlit/
├── app.py                           ✨ MAIN FILE (Run this!)
├── orchestrator/
│   └── graph.py
├── agents/
│   ├── extraction_agent.py
│   ├── validation_agent.py
│   ├── hitl_agent.py
│   ├── policy_agent.py
│   └── inow_agent.py
├── tools/
│   ├── pdf_tools.py
│   ├── aws_tools.py
│   └── inow_tools.py
├── config/
│   ├── required_fields.json
│   └── settings.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
└── sample_claims/
    ├── claim_001.txt
    ├── claim_002.txt
    └── claim_003.txt

Streamlit (Demo) → FastAPI Backend + React Frontend (Production)
For now:
✅ Streamlit reads from S3
✅ LangGraph processes locally
✅ Results displayed in Streamlit
✅ Drafts saved back to S3
✅ No database/email needed

1. User opens app at localhost:85012.
2. Sidebar shows: "S3 Bucket: claims-bucket"
3. Tab 1 shows: [Select PDF dropdown]
4. User picks: "claim_001.pdf"
5. User clicks: "Process Claim"
6. App shows: "🔄 Processing claim..."
   • Extraction: ✅ 1500 chars extracted
   • Validation: ✅ Checking fields...
   • HITL: ⚠️ Missing phone number
7. Tab 2 shows: Extracted fields table + missing list
8. Tab 3 shows: Draft email (editable)
9. User clicks: "Approve & Save Email"
10. Email saved to: s3://claims-bucket/drafts/claim_001_email_20240425_143022.txt
11. Success message: "✅ Email approved and saved to S3!"