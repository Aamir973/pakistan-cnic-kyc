import streamlit as st
import tempfile
import os
from PIL import Image

from App.services.ocr_services import extract_text
from App.services.parser import parse_document, detect_side
from App.services.validator import run_full_analysis

st.set_page_config(
    page_title="Pakistan CNIC KYC System",
    layout="wide",
    page_icon="🇵🇰",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.header-banner {
    background: linear-gradient(135deg, #006600 0%, #004d00 50%, #003300 100%);
    color: white;
    padding: 28px 32px;
    border-radius: 14px;
    margin-bottom: 24px;
    text-align: center;
}
.header-banner h1 { font-size: 2.1rem; margin: 0; }
.header-banner p  { font-size: 1rem; margin: 6px 0 0; opacity: 0.85; }
.field-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 2px;
}
.field-value { font-size: 1.05rem; font-weight: 600; color: #1a1a2e; }
.cnic-number {
    font-size: 1.4rem;
    font-weight: 700;
    color: #006600;
    letter-spacing: 0.05em;
    font-family: monospace;
}
.score-bar-container {
    background: #e9ecef; border-radius: 8px; height: 14px; margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-banner">
    <h1>🇵🇰 Pakistan CNIC KYC Verification System</h1>
    <p>AI-Powered OCR &nbsp;•&nbsp; Front &amp; Back Verification &nbsp;•&nbsp; Fraud Detection &nbsp;•&nbsp; Risk Scoring</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    st.markdown("---")
    st.markdown("### 📋 Verification Steps")
    st.markdown("""
    1. Upload CNIC Front  
    2. Upload CNIC Back  
    3. Upload Selfie *(optional)*  
    4. Click Verify
    """)
    st.markdown("---")
    st.markdown("### 🔧 Engine Status")
    st.success("✅ OCR Engine (EasyOCR)")
    st.success("✅ CNIC Parser")
    st.success("✅ Fraud Validator")
    st.success("✅ Risk Scorer")
    st.info("🔜 Face Matching (AI Model)")
    st.info("🔜 Liveness Detection")
    st.info("🔜 QR Code Decoder")
    st.markdown("---")
    st.markdown("### ℹ️ CNIC Format")
    st.code("PPPPP-NNNNNNN-G\n\nP = Province/District\nN = Serial Number\nG = Gender digit\n  Odd  → Male\n  Even → Female", language="text")
    st.markdown("---")
    with st.expander("🗺️ Province Codes"):
        st.markdown("""
        | Code | Province |
        |------|----------|
        | 1x   | KPK/FATA |
        | 2x   | KPK/FATA |
        | 3x   | Punjab   |
        | 4x   | Sindh    |
        | 5x   | Balochistan |
        | 6x   | Islamabad/AJK |
        | 7x   | Gilgit-Baltistan |
        """)

st.markdown("## 📤 Upload CNIC Documents")

col_front, col_back, col_selfie = st.columns(3)

with col_front:
    st.markdown("### 🪪 CNIC Front Side")
    front_file = st.file_uploader(
        "Upload front of CNIC",
        type=["jpg", "jpeg", "png"],
        key="front_upload"
    )
    if front_file:
        st.image(front_file, use_container_width=True, caption="Front Side Preview")

with col_back:
    st.markdown("### 🔄 CNIC Back Side")
    back_file = st.file_uploader(
        "Upload back of CNIC",
        type=["jpg", "jpeg", "png"],
        key="back_upload"
    )
    if back_file:
        st.image(back_file, use_container_width=True, caption="Back Side Preview")

with col_selfie:
    st.markdown("### 🤳 Selfie (Optional)")
    selfie_file = st.file_uploader(
        "Upload selfie for face verification",
        type=["jpg", "jpeg", "png"],
        key="selfie_upload"
    )
    if selfie_file:
        st.image(selfie_file, use_container_width=True, caption="Selfie Preview")

st.markdown("---")

if not front_file:
    st.info("👆 Please upload at least the **CNIC Front Side** to begin verification.")
    st.stop()

btn_col, _ = st.columns([1, 3])
with btn_col:
    verify_btn = st.button("🚀 Start KYC Verification", type="primary", use_container_width=True)

if not verify_btn:
    st.stop()


def save_temp(uploaded):
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(uploaded.getvalue())
        return f.name

def cleanup(*paths):
    for p in paths:
        if p and os.path.exists(p):
            os.remove(p)

def score_color(score):
    if score >= 75: return "#28a745"
    elif score >= 50: return "#ffc107"
    return "#dc3545"

def render_field(label, value, mono=False):
    val_class = "cnic-number" if mono else "field-value"
    display = value if value else '<span style="color:#ccc;">Not detected</span>'
    st.markdown(f"""
    <div style="margin-bottom:14px;">
        <div class="field-label">{label}</div>
        <div class="{val_class}">{display}</div>
    </div>
    """, unsafe_allow_html=True)

front_path = back_path = None

with st.spinner("🔍 Running OCR and analysis... This may take a moment."):
    try:
        front_path = save_temp(front_file)
        front_text = extract_text(front_path)
        front_data = parse_document(front_text)

        back_data = None
        back_text = ""
        if back_file:
            back_path = save_temp(back_file)
            back_text = extract_text(back_path)
            back_data = parse_document(back_text)

        cnic_consistent = None
        if back_data and front_data.get("cnic_number") and back_data.get("cnic_number"):
            cnic_consistent = front_data["cnic_number"] == back_data["cnic_number"]

        analysis = run_full_analysis(front_data, has_selfie=bool(selfie_file))

    except Exception as e:
        st.error(f"❌ Verification failed: {str(e)}")
        st.stop()
    finally:
        cleanup(front_path, back_path)

st.markdown("## 📊 Verification Results")

risk     = analysis["risk_assessment"]
date_val = analysis["date_checks"]
cnic_val = analysis["cnic_format_check"]
score    = risk["score"]
s_color  = score_color(score)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("CNIC Number",   "✅ Found"  if front_data.get("cnic_number") else "❌ Missing")
m2.metric("Format Valid",  "✅ Valid"  if cnic_val.get("valid_format")  else "❌ Invalid")
m3.metric("Dates Valid",   "✅ Valid"  if date_val.get("dates_valid")   else "⚠️ Issues")
m4.metric("CNIC Expired",  "⚠️ Yes"   if date_val["checks"].get("is_expired") else "✅ No")
m5.metric("Risk Score",    f"{score}/100")

st.markdown(f"""
<div class="score-bar-container">
  <div style="width:{score}%; background:{s_color}; height:100%; border-radius:8px;"></div>
</div>
<p style="text-align:center; font-weight:700; color:{s_color}; font-size:1.1rem;">
  {risk["verdict"]}
</p>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("## 🪪 CNIC Front — Extracted Data")

left_col, right_col = st.columns([1, 1])

with left_col:
    st.image(front_file, caption="CNIC Front Side", use_container_width=True)

with right_col:
    render_field("CNIC Number", front_data.get("cnic_number"), mono=True)
    render_field("Full Name (English)", front_data.get("name_english"))
    render_field("Father's Name (English)", front_data.get("father_name_english"))
    g_col, c_col = st.columns(2)
    with g_col:
        render_field("Gender", front_data.get("gender"))
    with c_col:
        render_field("Country of Stay", front_data.get("country_of_stay"))
    d1, d2, d3 = st.columns(3)
    with d1:
        render_field("Date of Birth", front_data.get("date_of_birth"))
    with d2:
        render_field("Date of Issue", front_data.get("date_of_issue"))
    with d3:
        render_field("Date of Expiry", front_data.get("date_of_expiry"))
    age = date_val["checks"].get("age_at_check")
    if age:
        render_field("Current Age", f"{age} years")

    with st.expander("📝 Raw OCR Output (Front)"):
        st.text_area("", front_text, height=160, key="front_raw")

if back_file and back_data:
    st.markdown("---")
    st.markdown("## 🔄 CNIC Back — Extracted Data")
    b_left, b_right = st.columns([1, 1])
    with b_left:
        st.image(back_file, caption="CNIC Back Side", use_container_width=True)
    with b_right:
        render_field("CNIC Number (Back)", back_data.get("cnic_number"), mono=True)
        if cnic_consistent is True:
            st.success("✅ CNIC number matches front and back")
        elif cnic_consistent is False:
            st.error("❌ CNIC number MISMATCH between front and back — possible fraud!")
        else:
            st.info("ℹ️ Could not compare CNIC numbers (one side not detected)")
        render_field("Present Address",   back_data.get("present_address"))
        render_field("Permanent Address", back_data.get("permanent_address"))
        render_field("Registrar General", back_data.get("registrar_info"))
        with st.expander("📝 Raw OCR Output (Back)"):
            st.text_area("", back_text, height=160, key="back_raw")

st.markdown("---")
st.markdown("## 😊 Face Verification")
f1, f2, f3 = st.columns(3)
with f1:
    st.image(front_file, caption="📄 ID Photo (from CNIC)", use_container_width=True)
with f2:
    if selfie_file:
        st.image(selfie_file, caption="🤳 Uploaded Selfie", use_container_width=True)
    else:
        st.warning("No selfie uploaded")
with f3:
    if selfie_file:
        st.metric("Face Match", "⏳ Pending")
        st.info("AI face matching model will be integrated in next release.")
    else:
        st.metric("Face Match", "N/A")

st.markdown("---")
st.markdown("## 🛡️ Fraud Risk Analysis")
fraud_left, fraud_right = st.columns([1, 1])

with fraud_left:
    st.markdown("### 🔍 Validation Checks")
    checks_display = {
        "CNIC Format Valid":     "✅" if cnic_val.get("valid_format") else "❌",
        "Province/Region":       cnic_val.get("province", "Unknown"),
        "Gender (Card)":         front_data.get("gender", "N/A"),
        "Gender (CNIC Code)":    cnic_val.get("gender_from_cnic", "N/A"),
        "Gender Consistent":     "✅" if analysis["gender_consistency"].get("consistent") else "⚠️",
        "DOB Valid":             "✅" if date_val["checks"].get("dob_valid") else "❌",
        "Issue After DOB":       "✅" if date_val["checks"].get("issued_after_dob") else "⚠️",
        "Expiry After Issue":    "✅" if date_val["checks"].get("expiry_after_issue") else "⚠️",
        "CNIC Not Expired":      "✅" if not date_val["checks"].get("is_expired") else "❌",
        "Front/Back Match":      "✅" if cnic_consistent else ("❌" if cnic_consistent is False else "N/A"),
        "Selfie Provided":       "✅" if selfie_file else "⚠️ No",
        "Face Matched":          "⏳ Pending" if selfie_file else "N/A",
        "Document Tampering":    "⏳ AI Pending",
        "Duplicate Check":       "⏳ DB Pending",
    }
    for k, v in checks_display.items():
        icon_color = "#28a745" if "✅" in str(v) else ("#dc3545" if "❌" in str(v) else "#6c757d")
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #f0f0f0;">
            <span style="color:#555;">{k}</span>
            <span style="font-weight:600; color:{icon_color};">{v}</span>
        </div>
        """, unsafe_allow_html=True)

with fraud_right:
    st.markdown("### 📈 Risk Score Breakdown")
    for label, detail in risk["breakdown"].items():
        icon = "🟢" if not detail.startswith("+0") else "🔴"
        st.markdown(f"""
        <div style="padding:6px 0; border-bottom:1px solid #f0f0f0;">
            <span>{icon} <strong>{label.replace('_',' ').title()}</strong></span><br>
            <span style="color:#666; font-size:0.85rem;">{detail}</span>
        </div>
        """, unsafe_allow_html=True)

    all_issues   = date_val.get("issues", []) + cnic_val.get("issues", [])
    all_warnings = date_val.get("warnings", [])
    if all_issues:
        st.markdown("#### ❌ Issues Found")
        for issue in all_issues:
            st.error(f"• {issue}")
    if all_warnings:
        st.markdown("#### ⚠️ Warnings")
        for w in all_warnings:
            st.warning(f"• {w}")
    if not all_issues and not all_warnings:
        st.success("✅ No issues or warnings detected")

st.markdown("---")
st.markdown("## 📋 Final KYC Decision")
decision_col, json_col = st.columns([1, 1])

with decision_col:
    if score >= 75:
        st.success(f"## ✅ IDENTITY VERIFIED\nRisk Score: {score}/100")
        st.balloons()
    elif score >= 50:
        st.warning(f"## ⚠️ MANUAL REVIEW REQUIRED\nRisk Score: {score}/100")
    else:
        st.error(f"## ❌ VERIFICATION FAILED\nRisk Score: {score}/100")

    st.markdown(f"""
    <div style="background:white; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <div class="field-label">Verdict</div>
        <div style="font-size:1.1rem; font-weight:700; color:{s_color};">{risk["verdict"]}</div>
        <br>
        <div class="field-label">CNIC Number</div>
        <div class="cnic-number">{front_data.get("cnic_number", "Not Detected")}</div>
        <br>
        <div class="field-label">Name</div>
        <div class="field-value">{front_data.get("name_english", "Not Detected")}</div>
        <br>
        <div class="field-label">Province / Region</div>
        <div class="field-value">{cnic_val.get("province", "Unknown")}</div>
    </div>
    """, unsafe_allow_html=True)

with json_col:
    st.markdown("#### 🗃️ Full Parsed Data (JSON)")
    st.json({
        "cnic_number":    front_data.get("cnic_number"),
        "name":           front_data.get("name_english"),
        "father_name":    front_data.get("father_name_english"),
        "gender":         front_data.get("gender"),
        "country_of_stay": front_data.get("country_of_stay"),
        "date_of_birth":  front_data.get("date_of_birth"),
        "date_of_issue":  front_data.get("date_of_issue"),
        "date_of_expiry": front_data.get("date_of_expiry"),
        "province":       cnic_val.get("province"),
        "risk_score":     score,
        "verdict":        risk["verdict"],
        "face_match":     "Pending" if selfie_file else "Not Provided",
        "front_back_match": cnic_consistent,
    })

st.markdown("---")
st.caption("Pakistan CNIC KYC System - Built with EasyOCR, OpenCV & Streamlit")