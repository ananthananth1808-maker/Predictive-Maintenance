from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import shap
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

TARGET_COLUMN = "Machine failure"
LEAKAGE_COLUMNS = ["UDI", "Product ID", "TWF", "HDF", "PWF", "OSF", "RNF"]
FEATURE_COLUMNS = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]


def load_dataset(data_path: str | Path = "data/ai4i2020.csv") -> pd.DataFrame:
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path)
    return df


def inspect_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    summary = {
        "shape": df.shape,
        "missing_values": int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "target_distribution": df[TARGET_COLUMN].value_counts().to_dict(),
        "column_names": df.columns.tolist(),
    }
    return summary


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = cleaned.drop(columns=[col for col in LEAKAGE_COLUMNS if col in cleaned.columns], errors="ignore")
    missing = [col for col in FEATURE_COLUMNS if col not in cleaned.columns]
    if missing:
        raise ValueError(f"Missing required predictive columns: {missing}")
    if TARGET_COLUMN not in cleaned.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' is missing from the dataset.")
    return cleaned


def build_preprocessor() -> ColumnTransformer:
    numeric_features = [
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]",
    ]
    categorical_features = ["Type"]
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
        ]
    )


def calculate_scale_pos_weight(y_train: pd.Series) -> float:
    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())
    if positive_count == 0:
        raise ValueError("Positive class is missing in the training data.")
    weight = negative_count / positive_count
    return float(weight)


def classify_failure(probability: float, thresholds: Dict[str, float] | None = None) -> str:
    if thresholds is None:
        thresholds = {"normal": 0.30, "warning": 0.70}
    if probability < thresholds["normal"]:
        return "NORMAL"
    if probability <= thresholds["warning"]:
        return "WARNING"
    return "CRITICAL"


def predict_from_features(model: Any, preprocessor: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = pd.DataFrame([payload])
    processed = preprocessor.transform(row)
    prob = float(model.predict_proba(processed)[0, 1])
    health = classify_failure(prob)
    return {"failure_probability": prob, "health_status": health}


def train_model(output_dir: str | Path = "ml/models") -> Dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset()
    inspected = inspect_dataset(df)
    prepared = prepare_features(df)

    X = prepared[FEATURE_COLUMNS]
    y = prepared[TARGET_COLUMN].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    scale_pos_weight = calculate_scale_pos_weight(y_train)
    preprocessor = build_preprocessor()
    model = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=1,
        reg_lambda=1.0,
        random_state=42,
        scale_pos_weight=scale_pos_weight,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", model),
        ]
    )

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "classification_report": classification_report(y_test, y_pred, target_names=["No Failure", "Failure"]),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "target_distribution": inspected["target_distribution"],
        "shape": inspected["shape"],
        "missing_values": inspected["missing_values"],
        "duplicate_rows": inspected["duplicate_rows"],
    }

    model_path = output_dir / "predictive_maintenance_model.pkl"
    preprocessor_path = output_dir / "preprocessor.pkl"
    classifier = pipeline.named_steps["classifier"]
    joblib.dump(classifier, model_path)
    joblib.dump(preprocessor, preprocessor_path)

    sns.set_style("whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=axes[0], cbar=False)
    axes[0].set_title("Confusion Matrix")
    axes[0].set_xlabel("Predicted")
    axes[0].set_ylabel("Actual")

    feature_importances = pipeline.named_steps["classifier"].feature_importances_
    feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    top_idx = np.argsort(feature_importances)[-10:][::-1]
    axes[1].barh([feature_names[i] for i in top_idx], feature_importances[top_idx])
    axes[1].set_title("Top Feature Importances")
    axes[1].invert_yaxis()

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    axes[2].plot(fpr, tpr, linewidth=2)
    axes[2].plot([0, 1], [0, 1], linestyle="--", color="gray")
    axes[2].set_title("ROC Curve")
    axes[2].set_xlabel("False Positive Rate")
    axes[2].set_ylabel("True Positive Rate")
    plt.tight_layout()
    plt.savefig(output_dir / "evaluation_dashboard.png", dpi=200)
    plt.close()

    explainer = shap.Explainer(pipeline.named_steps["classifier"], pipeline.named_steps["preprocessor"].transform(X_test))
    shap_values = explainer.shap_values(pipeline.named_steps["preprocessor"].transform(X_test))
    shap.summary_plot(shap_values, pipeline.named_steps["preprocessor"].transform(X_test), show=False)
    plt.tight_layout()
    plt.savefig(output_dir / "shap_summary.png", dpi=200)
    plt.close()

    result = {
        "model_path": str(model_path),
        "preprocessor_path": str(preprocessor_path),
        "metrics": metrics,
        "scale_pos_weight": scale_pos_weight,
        "feature_columns": FEATURE_COLUMNS,
    }

    with (output_dir / "training_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)

    return result


if __name__ == "__main__":
    result = train_model()
    print(json.dumps({"metrics": result["metrics"], "scale_pos_weight": result["scale_pos_weight"]}, indent=2))
