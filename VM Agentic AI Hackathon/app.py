# app.py
import streamlit as st
import boto3
import json
import os
from datetime import datetime
from orchestrator.graph import run_claim_workflow
from tools.aws_tools import get_s3_pdf_list

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="Claims Processor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    .header-main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 40px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 30px;
    }
    .header-main h1 {
        margin: 0;
        font-size: 2.5rem;
    }
    .status-success {
        background: #e8f5e9;
        color: #2e7d32;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2e7d32;
        margin: 10px 0;
    }
    .status-warning {
        background: #fff3e0;
        color: #e65100;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #e65100;
        margin: 10px 0;
    }
    .status-error {
        background: #ffebee;
        color: #c62828;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #c62828;
        margin: 10px 0;
    }
    .field-table {
        background: #f5f5f5;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# ===== SIDEBAR CONFIG =====
with st.sidebar:
    st.title("⚙️ Configuration")
    
    s3_bucket = st.text_input(
        "S3 Bucket Name",
        value=os.getenv("S3_BUCKET", "kendra-it-helpdesk-docs-development"),
        help="AWS S3 bucket containing claim PDFs"
    )
    
    aws_region = st.selectbox(
        "AWS Region",
        ["us-east-1", "us-west-2", "eu-west-1"],
        index=0
    )
    
    st.divider()
    
    st.subheader("Required Fields")
    with open("config/required_fields.json", "r") as f:
        required_fields = json.load(f)
    
    st.json(required_fields, expanded=False)

# ===== INITIALIZE SESSION STATE =====
if "workflow_result" not in st.session_state:
    st.session_state.workflow_result = None

if "selected_claim" not in st.session_state:
    st.session_state.selected_claim = None

if "draft_email" not in st.session_state:
    st.session_state.draft_email = None

if "email_approved" not in st.session_state:
    st.session_state.email_approved = False

# ===== HEADER =====
st.markdown("""
<div class="header-main">
    <h1>📋 Claims Processing Center</h1>
    <p>Agentic AI with Human-in-the-Loop (Streamlit + LangGraph)</p>
</div>
""", unsafe_allow_html=True)

# ===== MAIN CONTENT =====
st.header("🚀 Process Claim")

# --- TAB 1: SELECT & PROCESS ---
tab1, tab2, tab3 = st.tabs(["Process Claim", "View Results", "Draft Email"])

with tab1:
    st.subheader("Step 1: Select Claim PDF")
    
    # Fetch PDF list from S3
    try:
        pdf_list = get_s3_pdf_list(s3_bucket, region=aws_region)
        
        if not pdf_list:
            st.warning("No PDF files found in S3 bucket. Please upload some claim PDFs first.")
        else:
            selected_pdf = st.selectbox(
                "Select a claim PDF to process:",
                options=pdf_list,
                key="pdf_selector"
            )
            
            st.session_state.selected_claim = selected_pdf
            
            # Display file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Selected File", selected_pdf.split("/")[-1])
            with col2:
                st.metric("Bucket", s3_bucket)
            with col3:
                st.metric("Region", aws_region)
            
            st.divider()
            
            # --- PROCESS BUTTON ---
            st.subheader("Step 2: Run Workflow")
            
            if st.button("▶️ Process Claim", type="primary", use_container_width=True, key="process_btn"):
                with st.spinner("🔄 Processing claim... This may take 30-60 seconds"):
                    try:
                        # Run the LangGraph workflow
                        result = run_claim_workflow(
                            bucket=s3_bucket,
                            key=selected_pdf,
                            region=aws_region
                        )
                        
                        # Store result in session state
                        st.session_state.workflow_result = result
                        st.session_state.email_approved = False
                        
                        # Show success
                        st.success("✅ Workflow completed!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error processing claim: {str(e)}")
                        st.exception(e)
    
    except Exception as e:
        st.error(f"Failed to fetch PDF list from S3: {str(e)}")
        st.info("Make sure AWS credentials are configured and S3 bucket is accessible.")

with tab2:
    st.subheader("Workflow Results")
    
    if st.session_state.workflow_result is None:
        st.info("👈 Select a claim and click 'Process' to see results here.")
    else:
        result = st.session_state.workflow_result
        
        # --- STATUS SUMMARY ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = result.get("status", "UNKNOWN")
            status_color = "🟢" if "SUCCESS" in status or "CREATED" in status else "🟡" if "PENDING" in status else "🔴"
            st.metric("Workflow Status", f"{status_color} {status}")
        
        with col2:
            st.metric("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        with col3:
            if result.get("inow_claim_id"):
                st.metric("INOW Claim ID", result["inow_claim_id"], delta="✅ Created")
        
        st.divider()
        
        # --- EXTRACTED FIELDS ---
        if result.get("extracted_fields"):
            st.subheader("📋 Extracted Fields")
            
            extracted = result["extracted_fields"]
            
            # Create a nice table
            field_data = []
            for field, value in extracted.items():
                status_icon = "✅" if value else "❌"
                field_data.append({
                    "Field": field,
                    "Value": str(value) if value else "[MISSING]",
                    "Status": status_icon
                })
            
            st.dataframe(
                field_data,
                use_container_width=True,
                hide_index=True
            )
        
        # --- MISSING FIELDS ---
        if result.get("missing_fields") and len(result["missing_fields"]) > 0:
            st.markdown("""
            <div class="status-warning">
                <strong>⚠️ Missing Fields Detected</strong>
            </div>
            """, unsafe_allow_html=True)
            
            missing = result["missing_fields"]
            for field in missing:
                st.warning(f"❌ {field}")
            
            st.info("📧 A draft email has been prepared to request these missing fields. See the 'Draft Email' tab.")
        
        else:
            st.markdown("""
            <div class="status-success">
                <strong>✅ All Required Fields Present</strong>
            </div>
            """, unsafe_allow_html=True)
        
        # --- POLICY SECTIONS (if present) ---
        if result.get("relevant_policy_sections"):
            st.subheader("📚 Relevant Policy Sections")
            
            st.markdown("""
            The following policy sections are relevant to this claim:
            """)
            
            st.text_area(
                "Policy Analysis",
                value=result["relevant_policy_sections"],
                height=250,
                disabled=True
            )
        
        # --- RAW RESULT (for debugging) ---
        with st.expander("🔍 Raw Workflow Data (JSON)"):
            st.json(result)

with tab3:
    st.subheader("📧 Draft Email (Human Review)")
    
    if st.session_state.workflow_result is None:
        st.info("👈 Process a claim first to see the draft email.")
    else:
        result = st.session_state.workflow_result
        
        if not result.get("missing_fields") or len(result["missing_fields"]) == 0:
            st.markdown("""
            <div class="status-success">
                <strong>✅ No missing fields - no email needed!</strong>
            </div>
            """, unsafe_allow_html=True)
        
        else:
            st.info(f"📧 This email will request the following missing fields:")
            
            missing = result["missing_fields"]
            for field in missing:
                st.caption(f"• {field}")
            
            st.divider()
            
            # Draft email
            draft = result.get("draft_email", "[No draft available]")
            
            st.markdown("### ✍️ Email Draft (Editable)")
            
            # Allow user to edit the draft
            edited_email = st.text_area(
                "Edit the email before sending:",
                value=draft,
                height=300,
                label_visibility="collapsed"
            )
            
            st.session_state.draft_email = edited_email
            
            # Approval buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(
                    "✅ Approve & Save Email",
                    type="primary",
                    use_container_width=True,
                    key="approve_btn"
                ):
                    # Save to S3
                    s3 = boto3.client("s3", region_name=aws_region)
                    
                    claim_name = st.session_state.selected_claim.split("/")[-1].replace(".pdf", "")
                    draft_key = f"drafts/{claim_name}_email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    
                    try:
                        s3.put_object(
                            Bucket=s3_bucket,
                            Key=draft_key,
                            Body=edited_email.encode("utf-8"),
                            ContentType="text/plain"
                        )
                        
                        st.session_state.email_approved = True
                        
                        st.markdown("""
                        <div class="status-success">
                            <strong>✅ Email approved and saved to S3!</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.info(f"📁 Saved to: `s3://{s3_bucket}/{draft_key}`")
                        
                        st.success("""
                        **Next Steps:**
                        1. In production, this email would be sent to the claimant via SES
                        2. Claimant receives email and responds with missing information
                        3. System processes the reply and re-validates
                        """)
                    
                    except Exception as e:
                        st.error(f"Failed to save email: {str(e)}")
            
            with col2:
                if st.button(
                    "❌ Reject Draft",
                    use_container_width=True,
                    key="reject_btn"
                ):
                    st.warning("Draft email rejected. You can edit and try again.")

# ===== FOOTER =====
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.caption("🚀 Tech Stack: Streamlit + LangGraph + AWS Bedrock")

with col2:
    st.caption("🔧 PDF: PyMuPDF | LLM: Claude 3.5 Sonnet")

with col3:
    st.caption("💾 Data: S3 Bucket | State: Streamlit Session")
