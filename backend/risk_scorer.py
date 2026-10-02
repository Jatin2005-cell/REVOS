"""XGBoost deal-risk scorer: predicts probability a deal will slip."""
import os
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from config import settings


MODEL_PATH = os.path.join(settings.MODEL_DIR, "risk_model.pkl")


def create_labels(df: pd.DataFrame, deals_df: pd.DataFrame) -> np.ndarray:
    """Label: 1 if deal slipped (close_date pushed > 1x OR lost)."""
    labels = []
    for _, row in deals_df.iterrows():
        slipped = (
            row.get("close_date_pushed_count", 0) >= 1
            or row.get("is_won") == False and row.get("is_closed") == True
        )
        labels.append(int(slipped))
    return np.array(labels)


def train_risk_model(X: pd.DataFrame, y: np.ndarray) -> xgb.XGBClassifier:
    """Train XGBoost classifier and save to disk."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    print("Risk Model Evaluation:")
    print(classification_report(y_test, y_pred, target_names=["healthy", "at_risk"]))
    print(f"AUC-ROC: {roc_auc_score(y_test, y_proba):.3f}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved -> {MODEL_PATH}")

    return model


def load_risk_model() -> xgb.XGBClassifier:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Risk model not found at {MODEL_PATH}. Run training first.")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def score_deals(model: xgb.XGBClassifier, X: pd.DataFrame) -> pd.DataFrame:
    """Return risk scores (0–100) and labels for each deal."""
    probas = model.predict_proba(X)[:, 1]
    scores = (probas * 100).round(1)
    labels = np.where(scores >= 70, "high_risk", np.where(scores >= 40, "medium_risk", "low_risk"))
    return pd.DataFrame({"risk_score": scores, "risk_label": labels})
