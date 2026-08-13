import os
import requests
import pickle
import streamlit as st

# ---------- PAGE CONFIGURATION ----------
st.set_page_config(
    page_title="Aura Risk Underwriting",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- HTML SANITIZER HELPER ----------
def clean_html(html_str):
    """Strips leading whitespace from each line to prevent Streamlit from rendering HTML as a code block."""
    return "\n".join([line.strip() for line in html_str.split("\n")])

# ---------- CUSTOM CSS BRANDING & ANIMATION ----------
css_branding = """
<style>
/* Load modern typeface */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Apply font globally */
html, body, [class*="css"], .stMarkdown, .stWidgetLabel {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Animated background gradient for the main content page */
div[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 40%, #F1F5F9 70%, #EFF6FF 100%) !important;
    background-size: 300% 300% !important;
    animation: gradientBG 25s ease infinite !important;
}

@keyframes gradientBG {
    0% {
        background-position: 0% 50%;
    }
    50% {
        background-position: 100% 50%;
    }
    100% {
        background-position: 0% 50%;
    }
}

/* Ensure the header is transparent to avoid box overlays */
header[data-testid="stHeader"] {
    background-color: transparent !important;
}

/* Header typography */
h1, h2, h3, h4, h5 {
    color: #0F172A !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

/* Styled containers/cards */
div[data-testid="stContainer"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 24px !important;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
    margin-bottom: 20px !important;
}

/* Focus styled card headers */
.card-header {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #475569;
    margin-top: 0;
    margin-bottom: 16px;
    border-bottom: 1px solid #F1F5F9;
    padding-bottom: 10px;
}

/* Primary CTA Button (Stripe-like modern style) */
div.stButton > button:first-child {
    background-color: #0F172A !important;
    color: #FFFFFF !important;
    border: 1px solid #0F172A !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 14px 28px !important;
    width: 100% !important;
    transition: all 0.2s ease-in-out !important;
    box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.1), 0 2px 4px -1px rgba(15, 23, 42, 0.06) !important;
    margin-top: 10px;
}

div.stButton > button:first-child:hover {
    background-color: #1E293B !important;
    border-color: #1E293B !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.15), 0 4px 6px -2px rgba(15, 23, 42, 0.05) !important;
}

div.stButton > button:first-child:active {
    transform: translateY(0px) !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #F8FAFC !important;
    border-right: 1px solid #E2E8F0 !important;
}

/* Styling for input labels - Forced High Contrast */
label, 
.stWidgetLabel, 
div[data-testid="stWidgetLabel"] label, 
div[data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p {
    color: #0F172A !important; /* Dark Slate for high visibility */
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    opacity: 1 !important;
}

/* Hide Streamlit default hamburger menu and footer for cleaner app feel */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(clean_html(css_branding), unsafe_allow_html=True)

# ---------- FEATURE DISPLAY NAME MAPPINGS ----------
FEATURE_DISPLAY_NAMES = {
    "loan_amnt": "Loan Amount",
    "term_num": "Loan Term",
    "annual_inc_capped": "Annual Income",
    "emp_length_num": "Employment Length",
    "fico_avg": "Average Credit Score (FICO)",
    "dti": "Debt-to-Income (DTI) Ratio",
    "revol_util": "Revolving Credit Utilization",
    "delinq_2yrs": "Delinquencies (Past 2 Years)",
    "inq_last_6mths": "Credit Inquiries (Last 6 Months)",
    "open_acc": "Open Credit Accounts",
    "total_acc": "Total Credit Accounts (Lifetime)",
    "credit_history_years": "Credit History Length",
    "pub_rec_bankruptcies": "Public Bankruptcies",
    "loan_to_income": "Loan-to-Income Ratio",
    # Advanced fields
    "tot_cur_bal": "Total Current Balance",
    "total_rev_hi_lim": "Total Revolving Credit Limit",
    "avg_cur_bal": "Average Current Balance",
    "num_actv_rev_tl": "Active Revolving Accounts",
    "num_actv_bc_tl": "Active Bankcard Accounts",
    "bc_util": "Bankcard Utilization",
    "mort_acc": "Mortgage Accounts",
    "acc_open_past_24mths": "Accounts Opened (Past 24 Months)",
    "tot_hi_cred_lim": "Total High Credit Limit",
    "percent_bc_gt_75": "Bankcards Exceeding 75% Utilized",
}

def get_feature_display_name(feature_name):
    """Maps internal model feature names to user-friendly UI labels."""
    if feature_name in FEATURE_DISPLAY_NAMES:
        return FEATURE_DISPLAY_NAMES[feature_name]
    
    # Handle one-hot encoded purpose features
    if feature_name.startswith("purpose_"):
        purpose_val = feature_name.replace("purpose_", "").replace("_", " ").title()
        return f"Purpose: {purpose_val}"
        
    # Handle one-hot encoded home ownership features
    if feature_name.startswith("home_ownership_"):
        home_val = feature_name.replace("home_ownership_", "").upper()
        return f"Home Ownership: {home_val}"
        
    # Handle missing value flags
    if feature_name.endswith("_missing"):
        base_name = feature_name.replace("_missing", "")
        base_display = FEATURE_DISPLAY_NAMES.get(base_name, base_name.replace("_", " ").title())
        return f"Missing Flag: {base_display}"
        
    return feature_name.replace("_", " ").title()

# ---------- SIDEBAR BRANDING & DETAILS ----------
with st.sidebar:
    st.markdown(clean_html("""
    <div style="padding: 10px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 1.4rem; color: #0F172A; display: flex; align-items: center; gap: 8px;">
            Aura Underwrite
        </h2>
        <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: #64748B; font-weight: 500;">
            Commercial Credit Risk System
        </p>
    </div>
    """), unsafe_allow_html=True)
    
    st.subheader("System Specifications")
    st.markdown(clean_html("""
    **Core Underwriting Engine**  
    Powered by an optimized gradient-boosted decision tree ensemble (XGBoost).
    
    **Predictive Explainability**  
    Local feature contributions are calculated dynamically using SHAP (Shapley Additive exPlanations).
    
    **Standard Risk Tolerances**  
    * <span style="color: #10B981; font-weight: 600;">Low Risk (&lt;15%)</span>: Eligible for automated fast-track approval.
    * <span style="color: #F59E0B; font-weight: 600;">Moderate Risk (15% - 30%)</span>: Flagged for secondary manual underwriter review.
    * <span style="color: #EF4444; font-weight: 600;">High Risk (&ge;30%)</span>: Decline guideline. Requires additional collateral/co-signers.
    """), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(clean_html("""
    <div style="font-size: 0.8rem; color: #94A3B8;">
        Institutional Risk Suite v3.4.1<br>
        Connection: <span style="color: #10B981; font-weight: 600;">Online</span>
    </div>
    """), unsafe_allow_html=True)

# ---------- MAIN BODY HEADER ----------
st.markdown("<h2 style='margin-top: 0; margin-bottom: 4px;'>Applicant Risk Assessment</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748B; font-size: 0.95rem; margin-bottom: 25px;'>Compile the applicant's financial attributes below to generate the risk underwriting scorecard and model explanation.</p>", unsafe_allow_html=True)

# ---------- BACKEND API CONFIGURATION ----------
API_URL = os.getenv("BACKEND_URL", "https://loan-risk-api-gind.onrender.com").rstrip("/") + "/predict"

# ---------- QUICK ASSESSMENT ----------
st.subheader("Core Financial Profile")

# Group 1: Loan Request Parameters
with st.container(border=True):
    st.markdown('<div class="card-header">Loan Parameters</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        loan_amnt = st.number_input("Requested Loan Amount ($)", min_value=1000, max_value=40000, value=15000, step=500)
    with col2:
        term_num = st.selectbox("Loan Term (Months)", [36, 60])
    with col3:
        purpose = st.selectbox("Loan Purpose Classification", [
            "debt_consolidation", "credit_card", "home_improvement", "major_purchase",
            "small_business", "car", "medical", "moving", "vacation", "house",
            "wedding", "renewable_energy", "educational", "other"
        ])

# Group 2: Applicant Employment & Income
with st.container(border=True):
    st.markdown('<div class="card-header">Income & Employment Stability</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        annual_inc = st.number_input("Verified Annual Income ($)", min_value=0, value=65000, step=1000)
    with col2:
        emp_length_num = st.slider("Employment Tenure (Years)", min_value=0, max_value=10, value=5)
    with col3:
        home_ownership = st.selectbox("Home Ownership Classification", ["RENT", "OWN", "MORTGAGE", "OTHER"])

# Group 3: Credit Profile & Behavior Metrics
with st.container(border=True):
    st.markdown('<div class="card-header">Credit Standing & Debt Metrics</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        fico_known = st.radio("Do you know your FICO score?", ["Yes", "No - estimate for me"])
        if fico_known == "Yes":
            fico_avg = st.slider("Specific FICO Score", 300, 850, 690)
        else:
            fico_band = st.selectbox("Approximate Credit Standing", ["Excellent", "Good", "Fair", "Poor"])
            fico_avg = {"Excellent": 780, "Good": 700, "Fair": 640, "Poor": 580}[fico_band]
    with col2:
        dti = st.number_input("Debt-to-Income (DTI) Ratio (%)", min_value=0.0, max_value=60.0, value=18.5)
    with col3:
        revol_util = st.number_input("Revolving Credit Utilization (%)", min_value=0.0, max_value=150.0, value=45.0)
        
    st.markdown("<hr style='margin: 20px 0; border: 0; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)
    st.markdown('<div style="font-weight: 600; font-size: 0.9rem; color: #475569; margin-bottom: 12px;">Credit History & Accounts</div>', unsafe_allow_html=True)
    
    col4, col5, col6 = st.columns(3)
    with col4:
        credit_history_years = st.number_input("Years of Credit History", min_value=0.0, value=10.0)
        open_acc = st.number_input("Active Open Credit Accounts", min_value=0, value=8)
    with col5:
        total_acc = st.number_input("Total Credit Accounts (Lifetime)", min_value=0, value=15)
        delinq_2yrs = st.number_input("Delinquency Incidents (Past 2 Years)", min_value=0, value=0)
    with col6:
        inq_last_6mths = st.number_input("Hard Credit Inquiries (Past 6 Months)", min_value=0, value=0)
        pub_rec_bankruptcies = st.number_input("Public Record Bankruptcies", min_value=0, value=0)

# ---------- ADVANCED ASSESSMENT (Optional) ----------
st.markdown("<div style='margin: 10px 0 20px 0;'></div>", unsafe_allow_html=True)
show_advanced = st.checkbox("Include Advanced Credit Data Fields", value=False)

advanced_inputs = {}
if show_advanced:
    st.subheader("Extended Credit & Asset Valuation")
    with st.container(border=True):
        st.markdown('<div class="card-header">Supplementary Balance & Limit Fields</div>', unsafe_allow_html=True)
        
        acol1, acol2 = st.columns(2)
        with acol1:
            advanced_inputs['tot_cur_bal'] = st.number_input("Total Current Balance ($)", min_value=0, value=50000)
            advanced_inputs['total_rev_hi_lim'] = st.number_input("Total Revolving Credit Limit ($)", min_value=0, value=25000)
            advanced_inputs['avg_cur_bal'] = st.number_input("Average Current Balance ($)", min_value=0, value=10000)
            advanced_inputs['num_actv_rev_tl'] = st.number_input("Number of Active Revolving Accounts", min_value=0, value=5)
            advanced_inputs['num_actv_bc_tl'] = st.number_input("Number of Active Bankcard Accounts", min_value=0, value=3)
        with acol2:
            advanced_inputs['bc_util'] = st.number_input("Bankcard Utilization (%)", min_value=0.0, max_value=150.0, value=40.0)
            advanced_inputs['mort_acc'] = st.number_input("Mortgage Accounts", min_value=0, value=1)
            advanced_inputs['acc_open_past_24mths'] = st.number_input("Accounts Opened (Past 24 Months)", min_value=0, value=2)
            advanced_inputs['tot_hi_cred_lim'] = st.number_input("Total High Credit Limit ($)", min_value=0, value=80000)
            advanced_inputs['percent_bc_gt_75'] = st.number_input("Percent Bankcards Exceeding 75% Utilized", min_value=0.0, max_value=100.0, value=20.0)

# ---------- BUILD FEATURE DICTIONARY ----------
def build_features():
    features = {
        "loan_amnt": loan_amnt,
        "term_num": term_num,
        "annual_inc_capped": annual_inc,
        "emp_length_num": emp_length_num,
        "fico_avg": fico_avg,
        "dti": dti,
        "revol_util": revol_util,
        "delinq_2yrs": delinq_2yrs,
        "inq_last_6mths": inq_last_6mths,
        "open_acc": open_acc,
        "total_acc": total_acc,
        "credit_history_years": credit_history_years,
        "pub_rec_bankruptcies": pub_rec_bankruptcies,
        "loan_to_income": loan_amnt / annual_inc if annual_inc > 0 else 0,
    }

    # One-hot: purpose
    purpose_cols = ["credit_card", "debt_consolidation", "educational", "home_improvement",
                     "house", "major_purchase", "medical", "moving", "other",
                     "renewable_energy", "small_business", "vacation", "wedding"]
    for p in purpose_cols:
        features[f"purpose_{p}"] = 1 if purpose == p else 0

    # One-hot: home_ownership
    home_cols = ["MORTGAGE", "NONE", "OTHER", "OWN", "RENT"]
    for h in home_cols:
        features[f"home_ownership_{h}"] = 1 if home_ownership == h else 0

    # Missing-value flags: all 0 since user provided real values
    for col in ["dti_missing", "delinq_2yrs_missing", "inq_last_6mths_missing",
                "open_acc_missing", "revol_util_missing", "total_acc_missing",
                "credit_history_missing", "pub_rec_bankruptcies_missing"]:
        features[col] = 0

    # Merge advanced fields if provided
    features.update(advanced_inputs)

    return features

# ---------- PREDICT ACTION ----------
if st.button("Assess Credit Risk", type="primary"):
    features = build_features()
    
    with st.spinner("Calculating Underwriting Scorecard..."):
        try:
            response = requests.post(API_URL, json={"features": features})
            result = response.json()
            
            risk_pct = result["risk_probability"] * 100
            
            # Select colors and labels based on risk threshold
            if risk_pct < 15:
                bg_color = "#ECFDF5"      # Emerald 50
                text_color = "#065F46"    # Emerald 800
                border_color = "#10B981"  # Emerald 500
                risk_tier = "LOW RISK (Fast-Track Approved)"
            elif risk_pct < 30:
                bg_color = "#FFFBEB"      # Amber 50
                text_color = "#92400E"    # Amber 800
                border_color = "#F59E0B"  # Amber 500
                risk_tier = "MODERATE RISK (Manual Audit Flagged)"
            else:
                bg_color = "#FEF2F2"      # Red 50
                text_color = "#991B1B"    # Red 800
                border_color = "#EF4444"  # Red 500
                risk_tier = "HIGH RISK (Declined Guideline)"
                
            # Render Results Section Title
            st.markdown("<h3 style='margin-top: 25px; margin-bottom: 15px;'>Underwriting Assessment Results</h3>", unsafe_allow_html=True)
            
            # Render Results Scorecard Dashboard Card
            scorecard_html = f"""
            <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-left: 6px solid {border_color}; padding: 24px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                    <div>
                        <h4 style="margin: 0; color: #0F172A; font-size: 1.15rem; font-weight: 700;">Credit Risk Decision Matrix</h4>
                        <p style="margin: 4px 0 0 0; color: #475569; font-size: 0.9rem;">
                            Model-derived default probability and credit profile evaluation metrics.
                        </p>
                    </div>
                    <div style="text-align: right; min-width: 200px;">
                        <span style="font-size: 2.6rem; font-weight: 800; color: {border_color}; font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1;">
                            {risk_pct:.1f}%
                        </span>
                        <span style="display: block; font-size: 0.78rem; font-weight: 700; color: {text_color}; letter-spacing: 0.05em; margin-top: 4px; text-transform: uppercase;">
                            {risk_tier}
                        </span>
                    </div>
                </div>
                <!-- Linear Risk Progress Bar -->
                <div style="margin-top: 20px; width: 100%; background-color: #E2E8F0; height: 12px; border-radius: 6px; overflow: hidden; border: 1px solid #E2E8F0;">
                    <div style="width: {min(risk_pct, 100.0):.1f}%; background-color: {border_color}; height: 100%; border-radius: 6px; transition: width 0.8s ease-out;"></div>
                </div>
            </div>
            """
            st.markdown(clean_html(scorecard_html), unsafe_allow_html=True)
            
            # Render Core Metrics Details Grid
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric(label="Default Probability", value=f"{risk_pct:.2f}%", delta=None)
            with mcol2:
                st.metric(label="Calculated Credit Score", value=str(fico_avg), delta=None)
            with mcol3:
                st.metric(label="Debt-to-Income (DTI)", value=f"{dti:.1f}%", delta=None)
                
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            
            # ---------- SHAP GRAPHICAL VISUALIZATION ----------
            # Extract risk factors
            factors = result.get("top_risk_factors", [])
            max_impact = max(abs(f['impact']) for f in factors) if factors else 1.0
            if max_impact == 0:
                max_impact = 1.0
                
            html_factors = ""
            for factor in factors:
                feat = factor["feature"]
                imp = factor["impact"]
                display_name = get_feature_display_name(feat)
                
                # Check impact direction
                if imp > 0:
                    color = "#EF4444"      # Red 500
                    direction_icon = "▲"
                    direction_label = "Increases Risk"
                    sign = "+"
                else:
                    color = "#10B981"      # Emerald 500
                    direction_icon = "▼"
                    direction_label = "Reduces Risk"
                    sign = ""
                
                # Calculate bar width proportion (minimum 4% to remain visible)
                width_pct = max(4, int((abs(imp) / max_impact) * 100))
                
                html_factors += f"""
                <div style="margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
                        <div style="font-weight: 600; font-size: 0.92rem; color: #1E293B; display: flex; align-items: center; gap: 6px;">
                            <span>{display_name}</span>
                            <span style="font-size: 0.78rem; color: #94A3B8; font-weight: 400;">({feat})</span>
                        </div>
                        <div style="font-size: 0.8rem; font-weight: 600; color: {color}; display: flex; align-items: center; gap: 6px;">
                            <span style="background-color: {color}15; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">{direction_label}</span>
                            <span style="font-size: 0.85rem;">{direction_icon}</span>
                            <span style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-weight: 700;">{sign}{imp:.4f}</span>
                        </div>
                    </div>
                    <div style="width: 100%; background-color: #F1F5F9; height: 10px; border-radius: 5px; overflow: hidden; border: 1px solid #E2E8F0;">
                        <div style="width: {width_pct}%; background-color: {color}; height: 100%; border-radius: 5px; transition: width 0.6s ease-out;"></div>
                    </div>
                </div>
                """
                
            shap_card_html = f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-top: 10px;">
                <h4 style="margin-top: 0; margin-bottom: 6px; color: #0F172A; font-size: 1.05rem; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                    Explainable AI (XAI) Risk Factors
                </h4>
                <p style="margin-top: 0; margin-bottom: 20px; color: #64748B; font-size: 0.85rem; line-height: 1.4;">
                    The dashboard below charts the mathematical drivers of the applicant's credit decision score using Shapley value decomposition. 
                    <span style="color: #EF4444; font-weight: 600;">Red factors (▲)</span> escalate predicted risk, while 
                    <span style="color: #10B981; font-weight: 600;">green factors (▼)</span> mitigate or reduce risk.
                </p>
                {html_factors}
            </div>
            """
            st.markdown(clean_html(shap_card_html), unsafe_allow_html=True)
            
        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Unable to reach the credit prediction service. Please verify the FastAPI backend status.")