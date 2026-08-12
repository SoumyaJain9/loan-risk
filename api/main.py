from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
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

class LoanApplication(BaseModel):
    features: Dict[str, float]

@app.post("/predict")
def predict_risk(application: LoanApplication):
    input_dict = application.features
    input_df = pd.DataFrame([input_dict])
    
    # Fill in any of the 171 features not provided, with 0 as default
    for col in feature_columns:
        if col not in input_df.columns:
            input_df[col] = 0
    
    # Reorder to exactly match training order
    input_df = input_df[feature_columns]
    
    risk_probability = model.predict_proba(input_df)[0][1]
    
    shap_vals = explainer.shap_values(input_df)
    feature_contributions = dict(zip(feature_columns, shap_vals[0].tolist()))
    top_features = sorted(feature_contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
    
    explanation = [
        {"feature": name, "impact": round(value, 4)}
        for name, value in top_features
    ]
    
    return {
        "risk_probability": float(risk_probability),
        "risk_percentage": f"{risk_probability * 100:.1f}%",
        "top_risk_factors": explanation
    }