
============================================================
  INSURANCE CLAIM PROCESSING AGENT — ARCHITECTURE & FLOW
============================================================

Tech Stack
----------
Layer               Technology                  Purpose
---------           ----------                  -------
Frontend            Streamlit                   4-tab UI, session state, human-in-the-loop controls
Workflow Engine     LangGraph                   Phased agent orchestration (4 phases)
LLM                 AWS Bedrock                 Field extraction, policy analysis, email drafting, adjuster scoring
                    (openai.gpt-oss-120b-1:0)
PDF Extraction      PyMuPDF (fitz)              Raw text extraction from claim PDFs
File Storage        AWS S3                      Source PDFs, policy documents, approved email drafts
State Management    Streamlit Session State     In-memory, no database needed


Project Structure (Actual)
--------------------------
VM Agentic AI Hackathon/
├── app.py                          # Main Streamlit app (4 tabs)
├── orchestrator/
│   └── graph.py                    # LangGraph 4-phase workflow builder
├── agents/
│   ├── extraction_agent.py         # Phase 1 — PDF text extraction (NO LLM)
│   ├── validation_agent.py         # Phase 1 — Field extraction via LLM
│   ├── hitl_agent.py               # Phase 1 — Missing fields email draft via LLM
│   ├── policy_agent.py             # Phase 2 — Policy section analysis via LLM
│   ├── inow_agent.py               # Phase 3 — Claim registration (NO LLM)
│   └── adjuster_agent.py           # Phase 4 — Adjuster scoring via LLM
├── tools/
│   └── aws_tools.py                # S3 helpers, required fields config
├── config/
│   ├── required_fields.json        # List of mandatory claim fields
│   └── adjusters.json              # Adjuster profiles (region, expertise, experience)
├── settings.py                     # AWS region, S3 bucket, model ID constants
├── requirements.txt
├── .env
└── Readme.txt


LLM Usage Summary
-----------------
Agent                   Uses LLM?   Model                       Why
-----                   ---------   -----                       ---
extraction_agent        NO          —                           PyMuPDF handles raw text extraction
validation_agent        YES         openai.gpt-oss-120b-1:0    Extracts structured fields from unstructured PDF text
hitl_agent              YES         openai.gpt-oss-120b-1:0    Drafts professional email requesting missing fields
policy_agent            YES         openai.gpt-oss-120b-1:0    Identifies policy sections relevant to the claim
inow_agent              NO          —                           Deterministic mock claim ID generation (MD5 hash)
adjuster_agent          YES         openai.gpt-oss-120b-1:0    Scores & ranks adjusters by region, expertise, complexity


Complete 4-Phase Architecture Flow
-----------------------------------

┌─────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT APP                                │
│                                                                     │
│  Sidebar: S3 Bucket + AWS Region config                            │
│                                                                     │
│  Tab 1: Select Claim   Tab 2: View Results   Tab 3: Draft Email    │
│  Tab 4: Adjuster Allocation                                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    User selects PDF from S3
                    clicks "Process Claim"
                               │
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 1 — Extract & Validate  (LangGraph: build_phase1_graph)     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ extraction_agent  [NO LLM]                                  │   ║
║  │ • Downloads PDF from S3                                     │   ║
║  │ • Extracts raw text using PyMuPDF                           │   ║
║  │ • Output: raw_text                                          │   ║
║  └──────────────────────────────┬──────────────────────────────┘   ║
║                                 ▼                                   ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ validation_agent  [LLM]                                     │   ║
║  │ • Sends raw_text to LLM                                     │   ║
║  │ • Extracts structured fields (policy number, claimant,      │   ║
║  │   cause of loss, loss date, location, claim type, etc.)     │   ║
║  │ • Identifies missing required fields                        │   ║
║  │ • Output: extracted_fields, missing_fields                  │   ║
║  └──────────────────────────────┬──────────────────────────────┘   ║
║                                 ▼                                   ║
║              ┌──────────────────────────────┐                      ║
║              │  Missing fields present?     │                      ║
║              └────────┬─────────────────────┘                      ║
║                       │                                             ║
║            YES ───────┘──────── NO                                 ║
║             ▼                    ▼                                  ║
║  ┌──────────────────┐     STOP — UI prompts                        ║
║  │ hitl_agent [LLM] │     user to continue                         ║
║  │ • Flags missing  │     to Phase 2                               ║
║  │   fields for     │                                              ║
║  │   human review   │                                              ║
║  │ • Email drafted  │                                              ║
║  │   on user demand │                                              ║
║  └──────────────────┘                                              ║
╚══════════════════════════════════════════════════════════════════════╝
                               │
                    User clicks "Fetch Policy Sections"
                               │
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 2 — Policy Analysis  (LangGraph: build_phase2_graph)        ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ policy_agent  [LLM]                                         │   ║
║  │ • Fetches policy PDF from S3                                │   ║
║  │ • Extracts full policy text via PyMuPDF                     │   ║
║  │ • Sends policy text + claim description to LLM             │   ║
║  │ • LLM returns only relevant policy sections                 │   ║
║  │ • Output: policy_doc, relevant_policy_sections              │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝
                               │
                    User clicks "Register Claim in INOW"
                               │
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 3 — Claim Registration  (LangGraph: build_phase3_graph)     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ inow_agent  [NO LLM]                                        │   ║
║  │ • Generates deterministic claim ID (MD5 hash of fields)     │   ║
║  │ • Simulates INOW system registration                        │   ║
║  │ • Output: inow_claim_id, status = CLAIM_CREATED             │   ║
║  └─────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════╝
                               │
                    User clicks "Score & Recommend Adjuster"
                               │
                               ▼
╔══════════════════════════════════════════════════════════════════════╗
║  PHASE 4 — Adjuster Allocation  (LangGraph: build_phase4_graph)    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐   ║
║  │ adjuster_agent  [LLM]                                       │   ║
║  │ • Loads all adjusters from config/adjusters.json            │   ║
║  │ • Sends claim extracted_fields + adjuster profiles to LLM   │   ║
║  │ • LLM scores each adjuster (0-100) based on:                │   ║
║  │     - Geographic region match                               │   ║
║  │     - Claim type expertise                                  │   ║
║  │     - Loss complexity                                       │   ║
║  │     - Years of experience                                   │   ║
║  │ • Returns ranked list with reasoning per adjuster           │   ║
║  │ • Output: adjuster_evaluation, recommended_adjuster         │   ║
║  └──────────────────────────────┬──────────────────────────────┘   ║
║                                 ▼                                   ║
║         Human reviews AI recommendation in Tab 4                   ║
║         Can override selection before confirming                    ║
║         Output: assigned_adjuster (HUMAN_IN_LOOP confirmed)        ║
╚══════════════════════════════════════════════════════════════════════╝


Tab 3 — Draft Email Flow (HITL)
--------------------------------
Triggered only when missing_fields are detected in Phase 1:

  User clicks "Generate Draft Email"
          ↓
  hitl_agent calls LLM with list of missing fields
          ↓
  LLM drafts professional email to claimant
          ↓
  User reviews & edits email in Streamlit text area
          ↓
  ┌─ Approve & Save ──────────────────────────────────────┐
  │  Saves to S3: drafts/<claim_name>_email_<timestamp>.txt│
  │  Status → EMAIL_APPROVED                              │
  └───────────────────────────────────────────────────────┘
  ┌─ Reject & Regenerate ─────────────────────────────────┐
  │  Clears draft, user can request a new one             │
  └───────────────────────────────────────────────────────┘


S3 Bucket Structure
-------------------
s3://<your-bucket>/
├── claims/                         # Source claim PDFs
│   ├── claim_001.pdf
│   └── claim_002.pdf
├── Policy/                         # Policy documents
│   └── HP00000282-policy_document.pdf
└── drafts/                         # Approved missing-field emails
    └── claim_001_email_20240425_143022.txt


Setup & Run
-----------
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure AWS credentials
aws configure
# OR set in .env:
#   AWS_REGION=us-east-1
#   S3_BUCKET=your-bucket-name

# 3. Run the app
streamlit run app.py
# Opens at http://localhost:8501
