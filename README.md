# Explainable AI Loan Risk Assessment System

An end-to-end credit risk system built on the LendingClub Accepted Loans dataset (2007–2017). Predicts probability of loan default, explains predictions with SHAP, and serves live predictions via a FastAPI backend + Streamlit dashboard.

**Scope note:** this is a risk-scoring system for loans that have already been originated (e.g. for risk-based pricing or portfolio monitoring) — not a loan approval/rejection classifier. The public dataset only contains already-accepted loans, so an accept/reject model isn't something this data can honestly support. Details in [`decisions.md`](decisions.md).

**Live demo:** loanrisk.soumyajain.com · **API docs:** [api link]/docs

---

## Results

| Model | AUC-ROC | Recall (default class) |
|---|---|---|
| Logistic Regression | 0.714 | 0.61 |
| **XGBoost (primary model)** | **0.721** | **0.65** |
| LightGBM | 0.718 | 0.65 |

**Key finding:** Retraining XGBoost with LendingClub's own risk grade removed (`grade`, `sub_grade`, `int_rate`) dropped AUC by only 0.56 points (0.721 → 0.715) — the model derives nearly all its predictive power from raw applicant/credit-bureau data, not from reproducing LendingClub's existing score.

## Project Architecture

```
Raw CSV (2.26M rows, 151 cols)
        │
        ▼
Data Cleaning & Leakage Removal ──▶ Target Construction (Fully Paid / Charged Off)
        │
        ▼
EDA ──▶ Right-Censoring Detection (2018 loans excluded)
        │
        ▼
Feature Engineering (ratios, encoding, scaling) ──▶ 171 features
        │
        ▼
Time-Based Train/Test Split (train ≤2015, test 2016–2017)
        │
        ▼
Model Training & Comparison (Logistic Regression, XGBoost, LightGBM)
        │
        ▼
SHAP Explainability ──▶ FastAPI Backend ──▶ Streamlit Dashboard
```

## Pipeline Steps

1. **Data cleaning & leakage removal** — dropped ~44 columns only knowable after a loan starts repaying (`total_pymnt`, `recoveries`, `hardship_*`, `settlement_*`, etc.); every remaining column was checked against "would a lender know this at origination?"
2. **Target construction** — consolidated 9 raw `loan_status` categories into a binary target (Fully Paid vs. Charged Off); excluded non-terminal statuses (Current, Late, Grace Period) since their outcome isn't known yet
3. **EDA & bias detection** — plotting default rate by issue year revealed right-censoring in 2018 loans (not enough time to mature/default), so 2018 was excluded from the modeling dataset
4. **Feature engineering** — built `loan_to_income` and `installment_to_income` ratios, derived `credit_history_years`, merged perfectly-correlated `fico_range_low`/`fico_range_high` into `fico_avg`, capped `annual_inc` at the 99th percentile to remove extreme outliers
5. **Missing value handling** — added explicit `_missing` flag columns instead of silent imputation, since several fields are missing *by design* (e.g. no delinquency history) rather than by error
6. **Encoding** — ordinal encoding for `grade`/`sub_grade` (genuine order), one-hot encoding for unordered categoricals (`purpose`, `home_ownership`, `addr_state`, `verification_status`) — 171 final features
7. **Time-based train/test split** — trained on 2007–2015, tested on 2016–2017, to avoid leaking shared macroeconomic conditions across a random split
8. **Model training & comparison** — Logistic Regression, XGBoost, and LightGBM, all class-balanced to handle the ~80/20 default imbalance; selected XGBoost as the primary model based on AUC and recall on the default class
9. **With-grade vs. without-grade test** — retrained XGBoost without LendingClub's own grade/rate features to confirm the model isn't just reproducing an existing score (see Results)
10. **Explainability** — SHAP `TreeExplainer` for global feature importance and per-loan explanations
11. **Deployment** — FastAPI backend serving live predictions + SHAP explanations, with a Streamlit dashboard offering a realistic two-tier input experience (Quick / Advanced)

## What's in this repo

- `notebooks/loan.ipynb` — full pipeline: cleaning, leakage removal, EDA, feature engineering, modeling, SHAP
- `api/main.py` — FastAPI backend serving live predictions + SHAP explanations
- `dashboard/app.py` — Streamlit frontend (Quick / Advanced input tiers)
- `decisions.md` — the reasoning log: why certain data was excluded, how the target was defined, leakage handling, the right-censoring finding, and other judgment calls made along the way

## Tech stack

Python · pandas · scikit-learn · XGBoost · LightGBM · SHAP · FastAPI · Streamlit

## Running locally

```bash
git clone https://github.com/SoumyaJain9/loan-risk.git
cd loan-risk
pip install -r requirements.txt

# Download the LendingClub Accepted/Rejected Loans dataset from Kaggle,
# place accepted_2007_to_2018Q4.csv.gz in the project root, then run
# notebooks/loan.ipynb top to bottom to regenerate model artifacts.

# Terminal 1
cd api && uvicorn main:app --reload

# Terminal 2
cd dashboard && streamlit run app.py
```

## Dataset

[LendingClub Accepted/Rejected Loans, 2007–2018 (Kaggle)](https://www.kaggle.com/datasets/wordsforthewise/lending-club) — ~2.26M rows, 151 raw columns, reduced to ~1.29M rows / 171 engineered features after cleaning.

---

**Author:** Soumya Jain
