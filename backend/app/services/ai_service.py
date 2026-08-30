from __future__ import annotations

import os
from typing import Any, Dict, List

from app.config import LLM_API_KEY, LLM_MODEL


class AIService:
    def __init__(self):
        self.llm_api_key = LLM_API_KEY
        self.model_name = LLM_MODEL

    def _rule_based_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        probability = float(context.get("failure_probability", 0.0))
        health_status = context.get("health_status", "NORMAL")
        sensor_values = context.get("sensor_values", {})
        recent_maintenance = context.get("recent_maintenance", [])

        possible_causes: List[str] = []
        recommended_actions: List[str] = []

        if sensor_values.get("air_temperature", 0) > 300:
            possible_causes.append("Elevated air temperature beyond the expected operating range.")
            recommended_actions.append("Inspect cooling systems and airflow paths for restrictions or degradation.")
        if sensor_values.get("process_temperature", 0) > 310:
            possible_causes.append("Process temperature is elevated relative to typical operating conditions.")
            recommended_actions.append("Check thermal load, coolant flow, and process stability before the next run.")
        if sensor_values.get("torque", 0) > 40:
            possible_causes.append("Torque is elevated, which can indicate increased mechanical resistance or abnormal load.")
            recommended_actions.append("Review tooling condition and verify the machine is not under excessive mechanical stress.")
        if sensor_values.get("tool_wear", 0) > 100:
            possible_causes.append("Tool wear is high, which can increase failure risk over time.")
            recommended_actions.append("Schedule tool replacement and inspect the cutting or wear components.")
        if not possible_causes:
            possible_causes.append("No strong abnormal pattern is visible from the provided sensor values.")
            recommended_actions.append("Continue routine monitoring and review the next sensor cycle for changes.")

        if recent_maintenance:
            recommended_actions.append("Review recent maintenance history to confirm whether the current issue aligns with prior repairs or recurring wear patterns.")

        summary = (
            f"Machine {context.get('machine_id', 'unknown')} is currently {health_status} with a failure probability of {probability:.2f}. "
            "The recommendation is based only on the available sensor readings and system history."
        )

        priority = "LOW"
        if health_status == "CRITICAL" or probability > 0.70:
            priority = "CRITICAL"
        elif health_status == "WARNING" or probability > 0.30:
            priority = "HIGH"
        elif probability > 0.15:
            priority = "MEDIUM"

        return {
            "summary": summary,
            "possible_causes": possible_causes,
            "recommended_actions": recommended_actions,
            "priority": priority,
        }

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.llm_api_key:
            return self._rule_based_analysis(context)

        # LLM integration is intentionally abstracted for environment-based configuration.
        # This environment is not expected to provide a live API key in the local portfolio setup.
        return self._rule_based_analysis(context)
