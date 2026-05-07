# app.py
import streamlit as st
import boto3
import json
import os
from datetime import datetime
from orchestrator.graph import (
    run_claim_workflow_phase1,
    run_claim_workflow_phase2,
    run_claim_workflow_phase3,
    run_claim_workflow_phase4,
)
from tools.aws_tools import get_s3_pdf_list
from agents.hitl_agent import draft_missing_fields_email

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="Claims Processing Center",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== HARDCODED CONFIG (sidebar removed) =====
s3_bucket = os.getenv("S3_BUCKET", "kendra-it-helpdesk-docs-development")
aws_region = "us-east-1"
with open("config/required_fields.json", "r") as f:
    required_fields = json.load(f)
st.markdown("""
<style>
    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 16px;
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background: #F5F5F5; }
    /* ── Hide sidebar and toggle button completely ── */
    section[data-testid="stSidebar"] { display: none !important; }
    button[data-testid="collapsedControl"] { display: none !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }

    /* ── Header Banner ── */
    .header-banner {
        background: #B22020; color: white; padding: 22px 36px;
        border-radius: 0; margin-bottom: 18px;
        display: flex; align-items: center; gap: 18px;
        border-bottom: 4px solid #8B0000;
    }
    .header-banner .icon { font-size: 2.6rem; line-height: 1; }
    .header-banner h1 {
        margin: 0 0 3px 0; font-size: 1.7rem; font-weight: 700;
        letter-spacing: 0.5px; color: #FFFFFF !important; text-transform: uppercase;
    }
    .header-banner p { margin: 0; font-size: 0.90rem; color: #FFCCCC; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0; background: #FFFFFF; border-radius: 0; padding: 0;
        border-bottom: 2px solid #B22020;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 0; font-weight: 700; font-size: 0.88rem;
        padding: 12px 26px; color: #1a1a1a; background: #FFFFFF;
        text-transform: uppercase; letter-spacing: 0.6px;
        border-right: 1px solid #EEEEEE;
    }
    .stTabs [data-baseweb="tab"]:hover { background: #F5F5F5 !important; color: #B22020 !important; }
    .stTabs [aria-selected="true"] {
        background: #B22020 !important; color: #FFFFFF !important; border-bottom: none !important;
    }

    /* ── Step label (small red uppercase) ── */
    .step-label {
        font-size: 0.78rem; font-weight: 800; letter-spacing: 1.8px;
        text-transform: uppercase; color: #B22020; margin: 20px 0 4px 0;
        display: block;
    }

    /* ── Step title (bold black heading) ── */
    .step-title {
        font-size: 1.25rem; font-weight: 700; color: #1a1a1a;
        margin: 0 0 10px 0; display: block;
    }

    /* ── Step description text ── */
    .step-desc {
        font-size: 1.0rem; color: #444444; margin: 0 0 16px 0;
        line-height: 1.6; display: block;
    }

    /* ── Step divider ── */
    .step-divider {
        display: flex; align-items: center; margin: 28px 0 20px 0;
    }
    .step-divider-line { flex: 1; height: 1px; background: #DDDDDD; }
    .step-divider-label {
        margin: 0 14px; font-size: 0.78rem; font-weight: 800; color: #B22020;
        text-transform: uppercase; letter-spacing: 1.5px; padding: 5px 14px;
        border: 1.5px solid #B22020; border-radius: 4px; background: #FFF;
    }

    /* ── Action card (white box around each step action) ── */
    .action-card {
        background: white; border: 1px solid #DDDDDD; border-left: 4px solid #B22020;
        border-radius: 4px; padding: 20px 24px; margin-bottom: 16px;
    }
    .action-card-title {
        font-weight: 700; font-size: 1.05rem; color: #1a1a1a; margin-bottom: 6px;
    }
    .action-card-desc { font-size: 0.95rem; color: #555555; line-height: 1.5; }

    /* ── Metric Row ── */
    .metric-row { display: flex; gap: 14px; margin: 14px 0; }
    .metric-card {
        flex: 1; background: white; border: 1px solid #DDDDDD;
        border-left: 3px solid #B22020; border-radius: 4px; padding: 14px 18px;
    }
    .metric-card .metric-label {
        font-size: 0.72rem; font-weight: 700; letter-spacing: 1px;
        text-transform: uppercase; color: #888888; margin-bottom: 4px;
    }
    .metric-card .metric-value {
        font-size: 1.0rem; font-weight: 600; color: #1a1a1a;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }

    /* ── Badges ── */
    .badge {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 10px; border-radius: 3px; font-size: 0.80rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.3px;
    }
    .badge-green  { background: #E6F4EA; color: #1E7E34; border: 1px solid #C3E6CB; }
    .badge-yellow { background: #FFF8E1; color: #856404; border: 1px solid #FFE69C; }
    .badge-red    { background: #FDECEA; color: #B22020; border: 1px solid #F5C6CB; }
    .badge-black  { background: #1a1a1a; color: #FFFFFF; border: 1px solid #1a1a1a; }

    /* ── Alert Boxes ── */
    .alert { border-radius: 4px; padding: 14px 18px; margin: 10px 0; border-left: 4px solid; border: 1px solid; }
    .alert-success { background: #F4FAF6; border-color: #28A745; border-left-color: #28A745; color: #155724; }
    .alert-warning { background: #FFFBF0; border-color: #FFC107; border-left-color: #E6A817; color: #664D03; }
    .alert-info    { background: #F8F8F8; border-color: #DDDDDD; border-left-color: #B22020; color: #1a1a1a; }
    .alert-title   { font-weight: 700; font-size: 1.0rem; margin-bottom: 6px; }
    .alert span, .alert div:not(.alert-title) { font-size: 0.95rem !important; }

    /* ── Field Pills ── */
    .field-pill {
        display: inline-flex; align-items: center; gap: 4px;
        background: #FDECEA; border: 1px solid #F5C6CB; border-radius: 3px;
        padding: 5px 12px; margin: 3px 3px 3px 0;
        font-size: 0.90rem; font-weight: 600; color: #B22020;
    }

    /* ── Email Prompt Card ── */
    .email-prompt-card {
        background: white; border: 1px solid #DDDDDD; border-top: 3px solid #B22020;
        border-radius: 4px; padding: 24px 28px; margin: 16px 0; text-align: center;
    }
    .email-prompt-card .ep-icon { font-size: 2.2rem; margin-bottom: 8px; }
    .email-prompt-card h3 {
        margin: 0 0 6px 0; font-size: 1.1rem; font-weight: 700;
        color: #1a1a1a; text-transform: uppercase; letter-spacing: 0.3px;
    }
    .email-prompt-card p { margin: 0 0 16px 0; font-size: 0.95rem; color: #555555; }

    /* ── Buttons — uniform size and placement ── */
    div.stButton > button {
        width: 100%; border-radius: 4px; font-weight: 700;
        font-size: 0.92rem; padding: 11px 18px; transition: all 0.12s ease;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    div.stButton > button:hover { opacity: 0.88; }
    div.stButton > button[kind="primary"] {
        background: #B22020 !important; border-color: #8B0000 !important; color: white !important;
    }
    div.stButton > button[kind="primary"]:hover { background: #8B0000 !important; }

    /* ── Section Heading ── */
    .section-heading {
        font-size: 0.80rem; font-weight: 800; color: #B22020;
        margin: 20px 0 10px 0; display: flex; align-items: center; gap: 8px;
        text-transform: uppercase; letter-spacing: 1.2px;
    }
    .section-heading::after { content: ''; flex: 1; height: 1px; background: #DDDDDD; margin-left: 6px; }

    /* ── Misc ── */
    .stDataFrame { border-radius: 4px; overflow: hidden; border: 1px solid #DDDDDD; }
    .stTextArea textarea {
        border-radius: 4px !important; font-size: 0.95rem !important;
        line-height: 1.6 !important; border-color: #CCCCCC !important;
    }
    .stSelectbox > div > div { border-radius: 4px !important; border-color: #CCCCCC !important; font-size: 0.95rem !important; }
    .stTextInput > div > div > input { border-radius: 4px !important; border-color: #CCCCCC !important; }

    /* ── Card (used in locked adjuster state) ── */
    .card {
        background: white; border: 1px solid #DDDDDD; border-top: 3px solid #B22020;
        border-radius: 4px; padding: 20px 24px; margin-bottom: 14px;
    }
    .card-label {
        font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px;
        text-transform: uppercase; color: #B22020; margin-bottom: 4px;
    }
    .card-title { font-size: 1.05rem; font-weight: 600; color: #1a1a1a; margin-bottom: 12px; }

    /* ── Footer ── */
    .footer-bar {
        background: #1a1a1a; border-radius: 0; padding: 12px 24px;
        display: flex; justify-content: space-between; align-items: center;
        margin-top: 24px; font-size: 0.80rem; border-top: 3px solid #B22020;
    }
    .footer-bar span { color: #AAAAAA; }
</style>
""", unsafe_allow_html=True)

# ===== SIDEBAR =====
# ===== SESSION STATE =====
for key, default in {
    "workflow_result": None,
    "selected_claim": None,
    "draft_email": None,
    "email_approved": False,
    "email_requested": False,
    "phase": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ===== HEADER =====
st.markdown("""
<div class="header-banner">
    <div class="icon">📋</div>
    <div>
        <h1>Claims Processing Center</h1>
        <p>Agentic AI &nbsp;·&nbsp; Human-in-the-Loop &nbsp;·&nbsp; LangGraph &nbsp;·&nbsp; AWS Bedrock</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ===== TABS =====
tab1, tab2, tab3, tab4 = st.tabs([
    "  📁  Process Claim  ",
    "  📊  View Results  ",
    "  ✉️  Draft Email  ",
    "  🕵️  Adjuster Allocation  "
])

# ══════════════════════════════════════════════════════════
#  TAB 1 — Process Claim
# ══════════════════════════════════════════════════════════
with tab1:

    # ── Step 1 divider ──
    st.markdown("""
    <div class="step-divider">
        <div class="step-divider-line"></div>
        <div class="step-divider-label">Step 1 — Select Claim</div>
        <div class="step-divider-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<span class="step-title">Select a Claim Document</span>', unsafe_allow_html=True)
    st.markdown('<span class="step-desc">Choose the claim PDF from the S3 bucket to begin processing.</span>', unsafe_allow_html=True)

    try:
        pdf_list = get_s3_pdf_list(s3_bucket, region=aws_region)
        if not pdf_list:
            st.warning("No PDF files found in the S3 bucket.")
        else:
            selected_pdf = st.selectbox("Available claim documents:", options=pdf_list, key="pdf_selector")
            st.session_state.selected_claim = selected_pdf
    except Exception as e:
        st.error(f"Failed to fetch PDF list from S3: {str(e)}")

    # ── Step 2 divider ──
    st.markdown("""
    <div class="step-divider">
        <div class="step-divider-line"></div>
        <div class="step-divider-label">Step 2 — Process Claim</div>
        <div class="step-divider-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<span class="step-title">Run the AI Workflow</span>', unsafe_allow_html=True)
    st.markdown('<span class="step-desc">The AI will extract text from the PDF, validate all required fields using OpenAI LLM model, and flag any missing information for human review.</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        process_clicked = st.button("▶ Process Claim", type="primary", key="process_btn")
    with col2:
        if st.session_state.workflow_result is not None:
            if st.button("→ View Results", key="goto_results_btn"):
                st.info("Click the **View Results** tab above to see results.")

    if process_clicked:
        if not st.session_state.get("selected_claim"):
            st.warning("Please select a claim PDF first.")
        else:
            with st.spinner("Extracting and validating claim fields…"):
                try:
                    result = run_claim_workflow_phase1(
                        bucket=s3_bucket, key=st.session_state.selected_claim, region=aws_region
                    )
                    st.session_state.workflow_result = result
                    st.session_state.email_approved = False
                    st.session_state.email_requested = False
                    st.session_state.draft_email = None
                    st.session_state.phase = 1
                    st.success("✅ Validation complete! Click → View Results to continue.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.exception(e)

# ══════════════════════════════════════════════════════════
#  TAB 2 — View Results
# ══════════════════════════════════════════════════════════
with tab2:

    if st.session_state.workflow_result is None:
        st.markdown("""
        <div class="alert alert-info" style="margin-top:8px;">
            <div class="alert-title">No Results Yet</div>
            Select a claim PDF and click Process Claim to see results here.
        </div>
        """, unsafe_allow_html=True)
    else:
        result = st.session_state.workflow_result
        phase = st.session_state.phase
        status = result.get("status", "UNKNOWN")
        missing = result.get("missing_fields", [])

        # ── Status row ──
        if any(k in status for k in ["SUCCESS", "CREATED", "APPROVED", "ALLOCATED"]):
            badge_cls, badge_dot = "badge-green", "●"
        elif any(k in status for k in ["PENDING", "DRAFTED"]):
            badge_cls, badge_dot = "badge-yellow", "●"
        else:
            badge_cls, badge_dot = "badge-black", "●"

        claim_id = result.get("inow_claim_id") or "—"
        ts = datetime.now().strftime("%d %b %Y, %H:%M")
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">Status</div>
                <div class="metric-value"><span class="badge {badge_cls}">{badge_dot} {status}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Processed At</div>
                <div class="metric-value">{ts}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Claim Reference</div>
                <div class="metric-value">{claim_id}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Extracted fields ──
        if result.get("extracted_fields"):
            st.markdown('<div class="section-heading">Extracted Fields</div>', unsafe_allow_html=True)
            field_data = [
                {"Field": f, "Value": str(v) if v else "—", "Status": "✅ Present" if v else "❌ Missing"}
                for f, v in result["extracted_fields"].items()
            ]
            st.dataframe(field_data, hide_index=True, use_container_width=True)

        # ── Missing fields path ──
        if missing:
            pills = "".join(f'<span class="field-pill">✕ {f}</span>' for f in missing)
            st.markdown(f"""
            <div class="alert alert-warning" style="margin-top:12px;">
                <div class="alert-title">⚠ Missing Fields Detected</div>
                <div style="margin-bottom:8px;">The following required fields were not found in the document:</div>
                {pills}
                <div style="margin-top:10px;">Go to the <b>Draft Email</b> tab to generate a follow-up email to the claimant.</div>
            </div>
            """, unsafe_allow_html=True)

        # ── All fields present — stepped human flow ──
        else:
            st.markdown("""
            <div class="alert alert-success" style="margin-top:12px;">
                <div class="alert-title">✅ All Required Fields Present</div>
                The claim document is complete. Follow the steps below to proceed.
            </div>
            """, unsafe_allow_html=True)

            # ══ STEP 3 — Policy Review ══
            st.markdown("""
            <div class="step-divider">
                <div class="step-divider-line"></div>
                <div class="step-divider-label">Step 3 — Policy Review</div>
                <div class="step-divider-line"></div>
            </div>
            """, unsafe_allow_html=True)

            if phase < 2:
                st.markdown("""
                <div class="action-card">
                    <div class="action-card-title">📄 Fetch Relevant Policy Sections</div>
                    <div class="action-card-desc">The AI will analyse the policy document and extract
                    the sections most relevant to this claim, helping you make an informed decision.</div>
                </div>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📄 Fetch Policy Sections", type="primary", key="fetch_policy_btn"):
                        with st.spinner("Fetching and analysing policy document…"):
                            try:
                                updated = run_claim_workflow_phase2(result)
                                st.session_state.workflow_result = updated
                                st.session_state.phase = 2
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                                st.exception(e)
                with col2:
                    if st.button("✕ Skip Policy Fetch", key="skip_policy_btn"):
                        st.session_state.phase = 2
                        st.rerun()
            else:
                if result.get("relevant_policy_sections"):
                    st.markdown('<div class="section-heading">Relevant Policy Sections</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:0.95rem;line-height:1.7;color:#333;">{result["relevant_policy_sections"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="alert alert-info">
                        <div class="alert-title">Policy Fetch Skipped</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ══ STEP 4 — Register Claim ══
            if phase >= 2:
                st.markdown("""
                <div class="step-divider">
                    <div class="step-divider-line"></div>
                    <div class="step-divider-label">Step 4 — Register Claim</div>
                    <div class="step-divider-line"></div>
                </div>
                """, unsafe_allow_html=True)

                if phase < 3:
                    st.markdown("""
                    <div class="action-card">
                        <div class="action-card-title">🗂 Register &amp; Create Claim</div>
                        <div class="action-card-desc">This will formally register the claim in the system
                        and generate a unique Claim Reference ID for tracking and audit purposes.</div>
                    </div>
                    """, unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗂 Register & Create Claim", type="primary", key="create_claim_btn"):
                            with st.spinner("Registering and creating claim…"):
                                try:
                                    updated = run_claim_workflow_phase3(st.session_state.workflow_result)
                                    st.session_state.workflow_result = updated
                                    st.session_state.phase = 3
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                                    st.exception(e)
                else:
                    cid = st.session_state.workflow_result.get("inow_claim_id", "—")
                    st.markdown(f"""
                    <div class="alert alert-success">
                        <div class="alert-title">✅ Claim Registered Successfully</div>
                        <div style="font-size:1.0rem;margin-top:4px;">
                            Claim Reference ID: <b style="font-size:1.15rem;letter-spacing:0.5px;">{cid}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # ══ After Step 4 — point user to Adjuster tab ══
            if phase >= 3:
                st.markdown("""
                <div class="alert alert-info" style="margin-top:16px;">
                    <div class="alert-title">🕵️ Next: Assign an Adjuster</div>
                    The claim has been registered. Go to the <b>Adjuster Allocation</b> tab
                    to complete Step 5 — the AI will score and recommend the best adjuster for this claim.
                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  TAB 3 — Draft Email
# ══════════════════════════════════════════════════════════
with tab3:

    if st.session_state.workflow_result is None:
        st.markdown("""
        <div class="alert alert-info" style="margin-top:8px;">
            <div class="alert-title">No Claim Processed Yet</div>
            Process a claim first to see email options here.
        </div>
        """, unsafe_allow_html=True)
    else:
        result = st.session_state.workflow_result
        missing = result.get("missing_fields", [])

        if not missing:
            st.markdown("""
            <div class="alert alert-success" style="margin-top:8px;">
                <div class="alert-title">✅ No Email Needed</div>
                All required fields are present — no follow-up email is required.
            </div>
            """, unsafe_allow_html=True)
        else:
            pills = "".join(f'<span class="field-pill">✕ {f}</span>' for f in missing)
            st.markdown(f"""
            <div class="alert alert-warning">
                <div class="alert-title">⚠ Missing Fields</div>
                <div style="margin-bottom:8px;">The following fields are missing from the claim:</div>
                {pills}
            </div>
            """, unsafe_allow_html=True)

            if not st.session_state.email_requested:
                st.markdown("""
                <div class="email-prompt-card">
                    <div class="ep-icon">📬</div>
                    <h3>Generate a Follow-Up Email?</h3>
                    <p>The AI will draft a professional email to the claimant requesting the missing information above.</p>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✉ Yes, Generate Draft Email", type="primary", key="generate_email_btn"):
                        with st.spinner("Drafting email with AI…"):
                            claimant_email = result["extracted_fields"].get("claimant_contact_email", "")
                            draft = draft_missing_fields_email(missing, claimant_email)
                            st.session_state.draft_email = draft
                            st.session_state.email_requested = True
                            st.session_state.workflow_result["status"] = "EMAIL_DRAFTED_PENDING_VERIFICATION"
                            st.rerun()
                with col2:
                    if st.button("✕ Skip for Now", key="skip_email_btn"):
                        st.info("Skipped. Refresh to generate an email later.")

            if st.session_state.email_requested and st.session_state.draft_email:
                st.markdown("""
                <div class="alert alert-info" style="margin-top:12px;">
                    <div class="alert-title">Review &amp; Edit the Draft</div>
                    Edit if needed, then approve to save to S3.
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div style="display:flex;align-items:center;justify-content:space-between;margin:12px 0 6px 0;">
                    <span style="font-weight:700;font-size:1.0rem;color:#1a1a1a;text-transform:uppercase;letter-spacing:0.5px;">📧 Email Draft</span>
                </div>
                """, unsafe_allow_html=True)

                edited_email = st.text_area(
                    "email_editor", value=st.session_state.draft_email,
                    height=260, label_visibility="collapsed", key="email_editor"
                )
                st.session_state.draft_email = edited_email

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve & Save to S3", type="primary", key="approve_btn"):
                        s3 = boto3.client("s3", region_name=aws_region, verify=False)
                        claim_name = st.session_state.selected_claim.split("/")[-1].replace(".pdf", "")
                        draft_key = f"drafts/{claim_name}_email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        try:
                            s3.put_object(Bucket=s3_bucket, Key=draft_key,
                                          Body=edited_email.encode("utf-8"), ContentType="text/plain")
                            st.session_state.email_approved = True
                            st.session_state.workflow_result["status"] = "EMAIL_APPROVED"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to save: {str(e)}")
                with col2:
                    if st.button("✕ Reject & Regenerate", key="reject_btn"):
                        st.session_state.draft_email = None
                        st.session_state.email_requested = False
                        st.rerun()

            if st.session_state.email_approved:
                st.markdown("""
                <div class="alert alert-success" style="margin-top:12px;">
                    <div class="alert-title">✅ Email Approved &amp; Saved</div>
                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  TAB 4 — Adjuster Allocation
# ══════════════════════════════════════════════════════════
with tab4:

    phase = st.session_state.phase
    result = st.session_state.workflow_result

    if result is None:
        st.markdown("""
        <div class="alert alert-info" style="margin-top:8px;">
            <div class="alert-title">No Claim Processed Yet</div>
            Process a claim first to see adjuster allocation here.
        </div>
        """, unsafe_allow_html=True)

    elif result.get("missing_fields"):
        st.markdown("""
        <div class="alert alert-warning">
            <div class="alert-title">⚠ Adjuster Assignment Unavailable</div>
            This claim has missing fields. Resolve them via the <b>Draft Email</b> tab
            before adjuster assignment can proceed.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="opacity:0.25;pointer-events:none;filter:grayscale(1);margin-top:14px;">
            <div class="card">
                <div class="card-label">Adjuster Assignment</div>
                <div class="card-title">🔒 Locked — Pending Missing Field Resolution</div>
                <p style="color:#999;font-size:0.95rem;margin:0;">
                    Scoring and recommendation will appear once all required fields are present.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif phase < 3:
        st.markdown("""
        <div class="alert alert-info" style="margin-top:8px;">
            <div class="alert-title">🔒 Complete Previous Steps First</div>
            Please complete Steps 3 and 4 in the <b>View Results</b> tab
            (fetch policy sections and register the claim) before adjuster assignment becomes available.
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="step-divider">
            <div class="step-divider-line"></div>
            <div class="step-divider-label">Step 5 — Adjuster Allocation</div>
            <div class="step-divider-line"></div>
        </div>
        """, unsafe_allow_html=True)

        if phase == 3:
            st.markdown("""
            <div class="action-card">
                <div class="action-card-title">🕵️ Score &amp; Recommend an Adjuster</div>
                <div class="action-card-desc">The AI will evaluate all available adjusters based on
                geographic region, claim type expertise, and loss complexity, then recommend the
                best match. You can review the reasoning and override the recommendation before confirming.</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🕵️ Score & Recommend Adjuster", type="primary", key="run_adjuster_btn"):
                    with st.spinner("Scoring adjusters based on claim profile…"):
                        try:
                            updated = run_claim_workflow_phase4(st.session_state.workflow_result)
                            st.session_state.workflow_result = updated
                            st.session_state.phase = 4
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            st.exception(e)

        else:
            recommendation = result.get("recommended_adjuster")
            evaluation     = result.get("adjuster_evaluation", [])
            assigned       = result.get("assigned_adjuster")

            if assigned:
                st.markdown(f"""
                <div class="alert alert-success">
                    <div class="alert-title">✅ Adjuster Assigned &amp; Confirmed</div>
                    <div style="font-size:1.1rem;font-weight:700;margin:8px 0 4px 0;">
                        {assigned['name']}
                        <span class="badge badge-green" style="margin-left:10px;">Confirmed</span>
                    </div>
                    <div>Assigned by: Human-in-the-Loop &nbsp;·&nbsp; At: {assigned.get('assigned_at', '—')}</div>
                </div>
                """, unsafe_allow_html=True)

            else:
                if recommendation:
                    score = recommendation['score']
                    name  = recommendation['name']
                    reasons_html = "".join(
                        f'<li style="margin:4px 0;font-size:0.95rem;">{r}</li>'
                        for r in recommendation["reasons"]
                    ) or "<li style='font-size:0.95rem;'>No specific match criteria</li>"

                    st.markdown(f"""
                    <div class="alert alert-success" style="margin-bottom:16px;">
                        <div class="alert-title">✅ AI Recommendation</div>
                        <div style="font-size:1.15rem;font-weight:700;margin:8px 0 6px 0;">
                            {name}
                            <span class="badge badge-green" style="margin-left:10px;">Score: {score}</span>
                        </div>
                        <div style="font-weight:700;font-size:0.85rem;text-transform:uppercase;
                                    letter-spacing:0.5px;margin-bottom:6px;">Reasoning:</div>
                        <ul style="margin:0;padding-left:18px;">{reasons_html}</ul>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="alert alert-warning">
                        <div class="alert-title">⚠ No Suitable Adjuster Found</div>
                        No adjusters matched the claim criteria. Please select one manually below.
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown('<div class="section-heading">Human Review &amp; Override</div>', unsafe_allow_html=True)
                st.markdown('<span class="step-desc">Review the AI recommendation above. You may keep it or select a different adjuster from the list below before confirming.</span>', unsafe_allow_html=True)

                options = {
                    f"{e['adjuster']['name']} (Score: {e['score']})": e["adjuster"]
                    for e in evaluation
                }
                if options:
                    selected = st.selectbox(
                        "Select adjuster (or keep AI recommendation):",
                        options=list(options.keys()), index=0
                    )
                    chosen = options[selected]

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm & Assign Adjuster", type="primary", key="confirm_adjuster_btn"):
                            st.session_state.workflow_result["assigned_adjuster"] = {
                                "id": chosen["id"],
                                "name": chosen["name"],
                                "assigned_by": "HUMAN_IN_LOOP",
                                "assigned_at": datetime.utcnow().isoformat()
                            }
                            st.session_state.workflow_result["status"] = "ADJUSTER_ALLOCATED"
                            st.rerun()

# ===== FOOTER =====
st.markdown("""
<div class="footer-bar">
    <span>Claims Processing Center</span>
    <span>Streamlit · LangGraph · AWS Bedrock · PyMuPDF</span>
</div>
""", unsafe_allow_html=True)