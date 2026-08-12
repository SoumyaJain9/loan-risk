from fastapi import FastAPI
import pickle
import pandas as pd

with open('../xgboost_final_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('../shap_explainer.pkl', 'rb') as f:
    explainer = pickle.load(f)

with open('../feature_columns.pkl', 'rb') as f:
    feature_columns = pickle.load(f)

app = FastAPI()

print("Model, explainer, feature loaded successfully")

from pydantic import BaseModel

class LoanApplication(BaseModel):
    loan_amnt: float
    int_rate: float
    installment: float
    dti: float
    annual_inc_capped: float
    fico_avg: float
    emp_length_num: float
    credit_history_years: float

@app.post("/predict")
def predict_risk(application: LoanApplication):
    input_dict = application.dict()
    input_df = pd.DataFrame([input_dict])
    
    for col in feature_columns:
        if col not in input_df.columns:
            input_df[col] = 0
    
    input_df = input_df[feature_columns]
    
    risk_probability = model.predict_proba(input_df)[0][1]
    
    return {
        "risk_probability": float(risk_probability),
        "risk_percentage": f"{risk_probability * 100:.1f}%"
    }