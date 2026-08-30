from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd

from app.config import ML_MODEL_PATH, MODEL_THRESHOLDS, PREPROCESSOR_PATH


class MLService:
    def __init__(self, model_path: str | None = None, preprocessor_path: str | None = None):
        self.model_path = Path(model_path or ML_MODEL_PATH)
        self.preprocessor_path = Path(preprocessor_path or PREPROCESSOR_PATH)
        self.model = None
        self.preprocessor = None
        self._load()

    def _load(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        if not self.preprocessor_path.exists():
            raise FileNotFoundError(f"Preprocessor not found at {self.preprocessor_path}")

        loaded_model = joblib.load(self.model_path)
        self.preprocessor = joblib.load(self.preprocessor_path)

        if hasattr(loaded_model, "named_steps") and "classifier" in loaded_model.named_steps:
            self.model = loaded_model.named_steps["classifier"]
            if "preprocessor" in loaded_model.named_steps:
                self.preprocessor = loaded_model.named_steps["preprocessor"]
        else:
            self.model = loaded_model

    def _classify(self, probability: float, thresholds: Dict[str, float] | None = None) -> str:
        t = thresholds or MODEL_THRESHOLDS
        if probability < t["normal"]:
            return "NORMAL"
        if probability <= t["warning"]:
            return "WARNING"
        return "CRITICAL"

    def predict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None or self.preprocessor is None:
            raise RuntimeError("Model or preprocessor not loaded.")

        feature_names = [
            "Type",
            "Air temperature [K]",
            "Process temperature [K]",
            "Rotational speed [rpm]",
            "Torque [Nm]",
            "Tool wear [min]",
        ]
        df = pd.DataFrame([payload], columns=feature_names)
        transformed = self.preprocessor.transform(df)
        probability = float(self.model.predict_proba(transformed)[0, 1])
        health_status = self._classify(probability)
        return {
            "failure_probability": probability,
            "health_status": health_status,
            "risk_level": "LOW" if health_status == "NORMAL" else "MEDIUM" if health_status == "WARNING" else "HIGH",
        }

    def predict_machine_input(self, machine_input: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "Type": machine_input.get("type", "M"),
            "Air temperature [K]": float(machine_input["air_temperature"]),
            "Process temperature [K]": float(machine_input["process_temperature"]),
            "Rotational speed [rpm]": float(machine_input["rotational_speed"]),
            "Torque [Nm]": float(machine_input["torque"]),
            "Tool wear [min]": float(machine_input["tool_wear"]),
        }
        return self.predict(payload)

    def get_model_summary(self) -> Dict[str, Any]:
        summary_path = Path(self.model_path).with_name("training_summary.json")
        if summary_path.exists():
            with summary_path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        return {"model_path": str(self.model_path), "preprocessor_path": str(self.preprocessor_path)}
