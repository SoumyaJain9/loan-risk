import streamlit as st
import requests
import pickle

st.set_page_config(page_title="Loan Risk Assessment", layout="centered")
st.title("🏦 Loan Risk Assessment System")
st.write("Estimate default risk and understand the key drivers behind the prediction.")

API_URL = "http://127.0.0.1:8000/predict"

# ---------- QUICK ASSESSMENT ----------
st.header("Quick Assessment")

loan_amnt = st.number_input("Loan Amount ($)", min_value=1000, max_value=40000, value=15000, step=500)
term_num = st.selectbox("Loan Term (months)", [36, 60])
purpose = st.selectbox("Loan Purpose", [
    "debt_consolidation", "credit_card", "home_improvement", "major_purchase",
    "small_business", "car", "medical", "moving", "vacation", "house",
    "wedding", "renewable_energy", "educational", "other"
])
annual_inc = st.number_input("Annual Income ($)", min_value=0, value=65000, step=1000)
emp_length_num = st.slider("Years Employed", 0, 10, 5)
home_ownership = st.selectbox("Home Ownership", ["RENT", "OWN", "MORTGAGE", "OTHER"])

fico_known = st.radio("Do you know your FICO score?", ["Yes", "No - estimate for me"])
if fico_known == "Yes":
    fico_avg = st.slider("FICO Score", 300, 850, 690)
else:
    fico_band = st.selectbox("Approximate Credit Standing", ["Excellent", "Good", "Fair", "Poor"])
    fico_avg = {"Excellent": 780, "Good": 700, "Fair": 640, "Poor": 580}[fico_band]

dti = st.number_input("Debt-to-Income Ratio (%)", min_value=0.0, max_value=60.0, value=18.5)
revol_util = st.number_input("Revolving Credit Utilization (%)", min_value=0.0, max_value=150.0, value=45.0)
delinq_2yrs = st.number_input("Delinquencies (past 2 years)", min_value=0, value=0)
inq_last_6mths = st.number_input("Credit Inquiries (last 6 months)", min_value=0, value=0)
open_acc = st.number_input("Open Credit Accounts", min_value=0, value=8)
total_acc = st.number_input("Total Credit Accounts (ever)", min_value=0, value=15)
credit_history_years = st.number_input("Years of Credit History", min_value=0.0, value=10.0)
pub_rec_bankruptcies = st.number_input("Public Bankruptcies", min_value=0, value=0)

# ---------- ADVANCED ASSESSMENT (optional) ----------
show_advanced = st.checkbox("Add More Financial Information (Advanced)")

advanced_inputs = {}
if show_advanced:
    st.header("Advanced Assessment")
    advanced_inputs['tot_cur_bal'] = st.number_input("Total Current Balance ($)", min_value=0, value=50000)
    advanced_inputs['total_rev_hi_lim'] = st.number_input("Total Revolving Credit Limit ($)", min_value=0, value=25000)
    advanced_inputs['avg_cur_bal'] = st.number_input("Average Current Balance ($)", min_value=0, value=10000)
    advanced_inputs['num_actv_rev_tl'] = st.number_input("Active Revolving Accounts", min_value=0, value=5)
    advanced_inputs['num_actv_bc_tl'] = st.number_input("Active Bankcard Accounts", min_value=0, value=3)
    advanced_inputs['bc_util'] = st.number_input("Bankcard Utilization (%)", min_value=0.0, max_value=150.0, value=40.0)
    advanced_inputs['mort_acc'] = st.number_input("Mortgage Accounts", min_value=0, value=1)
    advanced_inputs['acc_open_past_24mths'] = st.number_input("Accounts Opened (past 24 months)", min_value=0, value=2)
    advanced_inputs['tot_hi_cred_lim'] = st.number_input("Total High Credit Limit ($)", min_value=0, value=80000)
    advanced_inputs['percent_bc_gt_75'] = st.number_input("% Bankcards Over 75% Utilized", min_value=0.0, max_value=100.0, value=20.0)

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

# ---------- PREDICT BUTTON ----------
if st.button("Assess Risk", type="primary"):
    features = build_features()
    
    with st.spinner("Analyzing..."):
        try:
            response = requests.post(API_URL, json={"features": features})
            result = response.json()
            
            risk_pct = result["risk_probability"] * 100
            
            st.subheader("Results")
            
            if risk_pct < 15:
                st.success(f"Estimated Default Risk: {risk_pct:.1f}% (Low Risk)")
            elif risk_pct < 30:
                st.warning(f"Estimated Default Risk: {risk_pct:.1f}% (Moderate Risk)")
            else:
                st.error(f"Estimated Default Risk: {risk_pct:.1f}% (High Risk)")
            
            st.progress(min(risk_pct / 100, 1.0))
            
            st.subheader("Key Factors Behind This Prediction")
            for factor in result["top_risk_factors"]:
                direction = "increased" if factor["impact"] > 0 else "decreased"
                st.write(f"- **{factor['feature']}** {direction} risk (impact: {factor['impact']:.4f})")
        
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the prediction API. Make sure the FastAPI server is running on port 8000.")