# app.py
import streamlit as st
import boto3
import json
import os
from datetime import datetime
from orchestrator.graph import run_claim_workflow
from tools.aws_tools import get_s3_pdf_list
from agents.hitl_agent import draft_missing_fields_email
from agents.adjuster_agent import adjuster_agent

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="Claims Processing Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background: #f8f9fc; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] { background: #1e1b4b; border-right: none; }
    section[data-testid="stSidebar"] * { color: #e0e7ff !important; }
    section[data-testid="stSidebar"] hr { border-color: #4338ca !important; }

    /* ── Header Banner ── */
    .header-banner {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white; padding: 36px 48px; border-radius: 16px;
        margin-bottom: 28px; display: flex; align-items: center;
        gap: 20px; box-shadow: 0 4px 24px rgba(79,70,229,0.25);
    }
    .header-banner .icon { font-size: 3rem; line-height: 1; }
    .header-banner h1 { margin: 0 0 4px 0; font-size: 1.9rem; font-weight: 700; letter-spacing: -0.5px; color: white !important; }
    .header-banner p { margin: 0; font-size: 0.95rem; opacity: 0.85; }

    /* ── Step Cards ── */
    .step-card {
        background: white; border: 1px solid #e5e7eb; border-radius: 12px;
        padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .step-label {
        font-size: 0.72rem; font-weight: 700; letter-spacing: 1.2px;
        text-transform: uppercase; color: #6366f1; margin-bottom: 6px;
    }
    .step-title { font-size: 1.05rem; font-weight: 600; color: #111827; margin-bottom: 16px; }

    /* ── Metric Cards ── */
    .metric-row { display: flex; gap: 16px; margin: 16px 0; }
    .metric-card {
        flex: 1; background: white; border: 1px solid #e5e7eb;
        border-radius: 10px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-card .metric-label {
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.8px;
        text-transform: uppercase; color: #9ca3af; margin-bottom: 4px;
    }
    .metric-card .metric-value {
        font-size: 0.95rem; font-weight: 600; color: #111827;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }

    /* ── Badges ── */
    .badge {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 4px 12px; border-radius: 999px; font-size: 0.78rem; font-weight: 600;
    }
    .badge-green  { background: #dcfce7; color: #15803d; }
    .badge-yellow { background: #fef9c3; color: #a16207; }
    .badge-blue   { background: #dbeafe; color: #1d4ed8; }
    .badge-purple { background: #ede9fe; color: #6d28d9; }

    /* ── Alert Boxes ── */
    .alert { border-radius: 10px; padding: 16px 20px; margin: 12px 0; border-left: 4px solid; }
    .alert-success { background: #f0fdf4; border-color: #22c55e; color: #166534; }
    .alert-warning { background: #fffbeb; border-color: #f59e0b; color: #78350f; }
    .alert-info    { background: #eff6ff; border-color: #3b82f6; color: #1e40af; }
    .alert-title   { font-weight: 700; font-size: 0.92rem; margin-bottom: 8px; }

    /* ── Field Pills ── */
    .field-pill {
        display: inline-flex; align-items: center; gap: 6px;
        background: #fff7ed; border: 1px solid #fed7aa; border-radius: 6px;
        padding: 6px 14px; margin: 4px 4px 4px 0; font-size: 0.88rem;
        font-weight: 500; color: #9a3412;
    }

    /* ── Email Prompt Card ── */
    .email-prompt-card {
        background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
        border: 1.5px solid #c7d2fe; border-radius: 14px;
        padding: 28px 32px; margin: 24px 0 16px 0; text-align: center;
    }
    .email-prompt-card .ep-icon { font-size: 2.2rem; margin-bottom: 10px; }
    .email-prompt-card h3 { margin: 0 0 6px 0; font-size: 1.1rem; font-weight: 700; color: #3730a3; }
    .email-prompt-card p  { margin: 0 0 20px 0; font-size: 0.88rem; color: #6b7280; }

    /* ── Buttons ── */
    div.stButton > button {
        width: 100%; border-radius: 8px; font-weight: 600;
        font-size: 0.88rem; padding: 10px 16px; transition: all 0.15s ease;
    }
    div.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.12); }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: #f3f4f6; border-radius: 10px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px; font-weight: 600; font-size: 0.88rem;
        padding: 8px 20px; color: #6b7280;
    }
    .stTabs [aria-selected="true"] {
        background: white !important; color: #4f46e5 !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    }

    /* ── Section Headings ── */
    .section-heading {
        font-size: 1.0rem; font-weight: 700; color: #1e1b4b;
        margin: 24px 0 12px 0; display: flex; align-items: center; gap: 8px;
    }
    .section-heading::after { content: ''; flex: 1; height: 1px; background: #e5e7eb; margin-left: 8px; }

    /* ── Misc ── */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    .stTextArea textarea {
        border-radius: 8px !important; font-family: 'Inter', sans-serif !important;
        font-size: 0.88rem !important; line-height: 1.6 !important;
    }
    .stSelectbox > div > div { border-radius: 8px !important; }
    .stTextInput > div > div > input { border-radius: 8px !important; }

    /* ── Footer ── */
    .footer-bar {
        background: white; border: 1px solid #e5e7eb; border-radius: 10px;
        padding: 12px 24px; display: flex; justify-content: space-between;
        align-items: center; margin-top: 32px; font-size: 0.78rem; color: #9ca3af;
    }
</style>
""", unsafe_allow_html=True)

# ===== SIDEBAR =====
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")
    s3_bucket = st.text_input(
        "S3 Bucket",
        value=os.getenv("S3_BUCKET", "kendra-it-helpdesk-docs-development"),
        help="AWS S3 bucket containing claim PDFs"
    )
    aws_region = st.selectbox("AWS Region", ["us-east-1", "us-west-2", "eu-west-1"], index=0)
    st.markdown("---")
    st.markdown("**Required Fields**")
    with open("config/required_fields.json", "r") as f:
        required_fields = json.load(f)
    
    st.json(required_fields, expanded=False)
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem; color:#a5b4fc; line-height:2.0;">
        🚀 <b>Stack:</b> LangGraph + Bedrock<br>
        🔧 <b>PDF:</b> PyMuPDF<br>
        💾 <b>Storage:</b> Amazon S3
    </div>
    """, unsafe_allow_html=True)

# ===== SESSION STATE =====
for key, default in {
    "workflow_result": None, "selected_claim": None,
    "draft_email": None, "email_approved": False, "email_requested": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ===== HEADER =====
st.markdown("""
<div class="header-banner">
    <div class="icon">📋</div>
    <div>
        <h1>Claims Processing Center</h1>
        <p>Agentic AI &nbsp;·&nbsp; Human-in-the-Loop &nbsp;·&nbsp; Streamlit + LangGraph + AWS Bedrock</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ===== TABS =====
tab1, tab2, tab3, tab4 = st.tabs(["  📁  Process Claim  ", "  📊  View Results  ", "  ✉️  Draft Email  ", " 🕵️ Adjuster Allocation"])

# ══════════════════════════════════════════════════════════
#  TAB 1 — Process Claim
# ══════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown('<div class="step-label">Step 1 of 2</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-title">Select a Claim PDF from S3</div>', unsafe_allow_html=True)
    try:
        pdf_list = get_s3_pdf_list(s3_bucket, region=aws_region)
        
        if not pdf_list:
            st.warning("No PDF files found in the S3 bucket. Please upload claim PDFs first.")
        else:
            selected_pdf = st.selectbox("docs", options=pdf_list, key="pdf_selector", label_visibility="collapsed")
            st.session_state.selected_claim = selected_pdf
            fname = selected_pdf.split("/")[-1]
            st.markdown(f"""
            <div class="metric-row">
                <div class="metric-card">
                    <div class="metric-label">📄 Selected File</div>
                    <div class="metric-value" title="{fname}">{fname}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">🪣 S3 Bucket</div>
                    <div class="metric-value">{s3_bucket}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">🌍 Region</div>
                    <div class="metric-value">{aws_region}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Failed to fetch PDF list from S3: {str(e)}")
        st.info("Make sure AWS credentials are configured and the S3 bucket is accessible.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown('<div class="step-label">Step 2 of 2</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-title">Run the AI Workflow</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="alert alert-info" style="margin-bottom:20px;">
        <div class="alert-title">ℹ️ What happens next?</div>
        The workflow extracts text from the PDF, validates required fields using Claude,
        cross-checks the policy document, and flags any missing information for your review.
    </div>
    """, unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 2])
    with col_btn:
        process_clicked = st.button("▶️ Process Claim", type="primary", key="process_btn")
    if process_clicked:
        if not st.session_state.get("selected_claim"):
            st.warning("Please select a claim PDF first.")
        else:
            with st.spinner("🔄 Running AI workflow… this may take 30–60 seconds"):
                try:
                    result = run_claim_workflow(
                        bucket=s3_bucket, key=st.session_state.selected_claim, region=aws_region
                    )
                    st.session_state.workflow_result = result
                    st.session_state.email_approved = False
                    st.session_state.email_requested = False
                    st.session_state.draft_email = None
                    st.success("✅ Workflow complete! Switch to the **View Results** tab.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error processing claim: {str(e)}")
                    st.exception(e)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  TAB 2 — View Results
# ══════════════════════════════════════════════════════════
with tab2:
    if st.session_state.workflow_result is None:
        st.markdown("""
        <div class="alert alert-info" style="margin-top:12px;">
            <div class="alert-title">👈 No results yet</div>
            Select a claim PDF and click <b>Process Claim</b> to see results here.
        </div>
        """, unsafe_allow_html=True)
    else:
        result = st.session_state.workflow_result
        status = result.get("status", "UNKNOWN")
        if any(k in status for k in ["SUCCESS", "CREATED", "APPROVED"]):
            badge_cls, badge_dot = "badge-green", "🟢"
        elif any(k in status for k in ["PENDING", "DRAFTED"]):
            badge_cls, badge_dot = "badge-yellow", "🟡"
        else:
            badge_cls, badge_dot = "badge-blue", "🔵"

        inow_id = result.get("inow_claim_id", "—")
        ts = datetime.now().strftime("%d %b %Y, %H:%M")
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">⚡ Workflow Status</div>
                <div class="metric-value"><span class="badge {badge_cls}">{badge_dot} {status}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">🕐 Processed At</div>
                <div class="metric-value">{ts}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">🆔 INOW Claim ID</div>
                <div class="metric-value">{inow_id}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if result.get("extracted_fields"):
            st.markdown('<div class="section-heading">📋 Extracted Fields</div>', unsafe_allow_html=True)
            field_data = [
                {"Field": f, "Value": str(v) if v else "—", "Status": "✅ Present" if v else "❌ Missing"}
                for f, v in result["extracted_fields"].items()
            ]
            st.dataframe(field_data, hide_index=True, use_container_width=True)

        missing = result.get("missing_fields", [])
        if missing:
            pills = "".join(f'<span class="field-pill">❌ {f}</span>' for f in missing)
            st.markdown(f"""
            <div class="alert alert-warning" style="margin-top:16px;">
                <div class="alert-title">⚠️ Missing Fields Detected</div>
                <div style="margin-bottom:10px;">The following required fields were not found:</div>
                {pills}
                <div style="margin-top:12px; font-size:0.85rem; opacity:0.85;">
                    📧 Go to the <b>Draft Email</b> tab to generate a follow-up email.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            missing = result["missing_fields"]
            for field in missing:
                st.warning(f"❌ {field}")
            
            st.info("📧 A draft email has been prepared to request these missing fields. See the 'Draft Email' tab.")
        
        else:
            st.markdown("""
            <div class="alert alert-success" style="margin-top:16px;">
                <div class="alert-title">✅ All Required Fields Present</div>
                The claim document contains all required fields and is ready for processing.
            </div>
            """, unsafe_allow_html=True)

        if result.get("relevant_policy_sections"):
            st.markdown('<div class="section-heading">📚 Relevant Policy Sections</div>', unsafe_allow_html=True)
            # st.text_area("ps", value=result["relevant_policy_sections"], height=220, disabled=True, label_visibility="collapsed")
            st.markdown(result["relevant_policy_sections"])
        with st.expander("🔍 Raw Workflow Data (JSON)"):
            st.json(result)

# ══════════════════════════════════════════════════════════
#  TAB 3 — Draft Email
# ══════════════════════════════════════════════════════════
with tab3:
    st.subheader("📧 Draft Email (Human Review)")
    
    if st.session_state.workflow_result is None:
        st.markdown("""
        <div class="alert alert-info" style="margin-top:12px;">
            <div class="alert-title">👈 No claim processed yet</div>
            Process a claim first to see email options here.
        </div>
        """, unsafe_allow_html=True)
    else:
        result = st.session_state.workflow_result
        missing = result.get("missing_fields", [])

        if not missing:
            st.markdown("""
            <div class="alert alert-success" style="margin-top:12px;">
                <div class="alert-title">✅ No email needed</div>
                All required fields are present — no follow-up email is required.
            </div>
            """, unsafe_allow_html=True)
        
        else:
            pills = "".join(f'<span class="field-pill">❌ {f}</span>' for f in missing)
            st.markdown(f"""
            <div class="alert alert-warning">
                <div class="alert-title">⚠️ Missing Fields</div>
                <div style="margin-bottom:10px;">The following fields are missing from the claim:</div>
                {pills}
            </div>
            """, unsafe_allow_html=True)

            if not st.session_state.email_requested:
                st.markdown("""
                <div class="email-prompt-card">
                    <div class="ep-icon">📬</div>
                    <h3>Generate a Follow-Up Email?</h3>
                    <p>Would you like the AI to draft a professional email to the claimant<br>requesting the missing information above?</p>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, _ = st.columns([2, 2, 1])
                with col1:
                    if st.button("✉️ Yes, Generate Draft Email", type="primary", key="generate_email_btn"):
                        with st.spinner("✍️ Drafting email with AI…"):
                            claimant_email = result["extracted_fields"].get("claimant_contact_email", "")
                            draft = draft_missing_fields_email(missing, claimant_email)
                            st.session_state.draft_email = draft
                            st.session_state.email_requested = True
                            st.session_state.workflow_result["status"] = "EMAIL_DRAFTED_PENDING_VERIFICATION"
                            st.rerun()
                with col2:
                    if st.button("🚫 No, Skip for Now", key="skip_email_btn"):
                        st.markdown("""
                        <div class="alert alert-info" style="margin-top:8px;">
                            Skipped. Refresh the page to generate an email later if needed.
                        </div>
                        """, unsafe_allow_html=True)

            if st.session_state.email_requested and st.session_state.draft_email:
                st.markdown("""
                <div class="alert alert-info" style="margin-top:16px;">
                    <div class="alert-title">✍️ Review &amp; Edit the Draft</div>
                    The AI has generated the email below. Edit if needed, then approve to save to S3.
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="display:flex; align-items:center; justify-content:space-between; margin:16px 0 8px 0;">
                    <span style="font-weight:700; font-size:0.95rem; color:#111827;">📧 Email Draft</span>
                    <span class="badge badge-yellow">⏳ Pending Verification</span>
                </div>
                """, unsafe_allow_html=True)

                edited_email = st.text_area(
                    "email_editor", value=st.session_state.draft_email,
                    height=280, label_visibility="collapsed", key="email_editor"
                )
                st.session_state.draft_email = edited_email

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✅ Approve & Save to S3", type="primary", key="approve_btn"):
                        s3 = boto3.client("s3", region_name=aws_region, verify=False)
                        claim_name = st.session_state.selected_claim.split("/")[-1].replace(".pdf", "")
                        draft_key = f"drafts/{claim_name}_email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        try:
                            s3.put_object(Bucket=s3_bucket, Key=draft_key, Body=edited_email.encode("utf-8"), ContentType="text/plain")
                            st.session_state.email_approved = True
                            st.session_state.workflow_result["status"] = "EMAIL_APPROVED"
                            st.markdown(f"""
                            <div class="alert alert-success" style="margin-top:12px;">
                                <div class="alert-title">✅ Email approved and saved!</div>
                                Saved to <code>s3://{s3_bucket}/{draft_key}</code><br><br>
                                <b>Next steps:</b> In production this would be dispatched via Amazon SES.
                                The claimant's reply would trigger automatic re-validation.
                            </div>
                            """, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Failed to save email to S3: {str(e)}")
                with col2:
                    if st.button("❌ Reject & Regenerate", key="reject_btn"):
                        st.session_state.draft_email = None
                        st.session_state.email_requested = False
                        st.warning("Draft rejected. Click 'Yes, Generate Draft Email' to try again.")
                        st.rerun()

with tab4:
    st.subheader("🤖 Agentic Adjuster Assignment")

    if st.session_state.workflow_result is None:
        st.info("Process a claim first.")
    else:
        state = st.session_state.workflow_result


    # --- Run agent once ---
        if "recommended_adjuster" not in state:
            with st.spinner("Agent analyzing claim and routing adjuster..."):
                updated_state = adjuster_agent(state)
                st.session_state.workflow_result = updated_state
                st.rerun()

        recommendation = st.session_state.workflow_result.get("recommended_adjuster")
        evaluation = st.session_state.workflow_result.get("adjuster_evaluation", [])

        if not recommendation:
            st.error("No suitable adjuster found.")
        else:
            # --- Recommendation ---
            st.markdown("### ✅ Agent Recommendation")

            st.success(
                f"**{recommendation['name']}** "
                f"(Score: {recommendation['score']})"
            )

            st.markdown("**Reasoning:**")
            for r in recommendation["reasons"]:
                st.markdown(f"- {r}")

            st.divider()

            # --- Human Override ---
            st.markdown("### 👤 Human Review & Override")

            options = {
                f"{e['adjuster']['name']} (Score {e['score']})": e["adjuster"]
                for e in evaluation
            }

            selected = st.selectbox(
                "Select Adjuster (optional override)",
                options=list(options.keys()),
                index=0
            )

            chosen_adjuster = options[selected]

            if st.button("✅ Assign Adjuster", type="primary", width="stretch"):
                st.session_state.workflow_result["assigned_adjuster"] = {
                    "id": chosen_adjuster["id"],
                    "name": chosen_adjuster["name"],
                    "assigned_by": "HUMAN_IN_LOOP",
                    "assigned_at": datetime.utcnow().isoformat()
                }

                st.success(f"Assigned {chosen_adjuster['name']} to this claim")
# ===== FOOTER =====
st.markdown("""
<div class="footer-bar">
    <span>🚀 Streamlit · LangGraph · AWS Bedrock</span>
    <span>🔧 PyMuPDF · Claude 3.5 Sonnet</span>
    <span>💾 Amazon S3 · us-east-1</span>
</div>
""", unsafe_allow_html=True)