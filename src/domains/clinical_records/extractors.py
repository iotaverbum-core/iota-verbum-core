import re
from datetime import datetime, timedelta


class ClinicalRecordsExtractors:
    domain = "clinical_records"

    def normalize_input(self, data: dict) -> dict:
        return data or {}

    def extract(self, normalized_input: dict, context: dict):
        vitals = normalized_input.get("vitals", {})
        systolic = int(vitals.get("blood_pressure_systolic", 0) or 0)
        diastolic = int(vitals.get("blood_pressure_diastolic", 0) or 0)
        hr = int(vitals.get("heart_rate", 0) or 0)
        temp = float(vitals.get("temperature", 0) or 0)
        o2 = int(vitals.get("o2_saturation", 0) or 0)

        chief = normalized_input.get("chief_complaint", "")
        symptoms = _parse_symptoms(chief)

        history = normalized_input.get("history", {})
        risk_factors = [
            {
                "id": "risk_0",
                "type": "age",
                "value": history.get("age"),
                "category": "moderate_risk"
                if (history.get("age") or 0) >= 50
                else "low_risk",
            },
            {
                "id": "risk_1",
                "type": "family_history",
                "value": history.get("family_hypertension"),
                "category": "high_risk"
                if history.get("family_hypertension")
                else "low_risk",
            },
        ]

        vitals_map = [
            {
                "id": "vital_0",
                "type": "bp_systolic",
                "value": systolic,
                "threshold": 140,
                "status": "elevated" if systolic >= 140 else "normal",
            },
            {
                "id": "vital_1",
                "type": "bp_diastolic",
                "value": diastolic,
                "threshold": 90,
                "status": "elevated" if diastolic >= 90 else "normal",
            },
        ]

        positive = systolic >= 140 or diastolic >= 90
        assessment = "positive_screen_hypertension" if positive else "negative_screen"

        return {
            "vitals": {
                "systolic": systolic,
                "diastolic": diastolic,
                "heart_rate": hr,
                "temperature": temp,
                "o2_saturation": o2,
            },
            "vitals_map": vitals_map,
            "risk_factors": risk_factors,
            "symptoms": symptoms,
            "assessment": assessment,
        }

    def build_evidence_map(self, extracted: dict, normalized_input: dict):
        return {
            "vitals": extracted["vitals_map"],
            "risk_factors": extracted["risk_factors"],
            "symptoms": extracted["symptoms"],
        }

    def template_fallback(self, input_ref: str, context: dict, normalized_input: dict):
        return None

    def build_context(
        self, input_ref, input_data, normalized_input, extracted, evidence_map, context
    ):
        encounter_date = normalized_input.get("encounter_date")
        next_date = _next_assessment(encounter_date, 30)
        bp_text = _bp_text(extracted["vitals"])
        return {
            "threshold_systolic": 140,
            "threshold_diastolic": 90,
            "measurement_count": 1,
            "risk_age": extracted["risk_factors"][0]["value"],
            "risk_family_history": extracted["risk_factors"][1]["value"],
            "risk_lifestyle": "unknown",
            "evidence_bp_1": bp_text,
            "evidence_bp_2": bp_text,
            "intervention_1": "lifestyle modification counseling",
            "intervention_2": "repeat BP measurement",
            "follow_up_interval": "2 weeks",
            "bp_reading_1": _bp_reading(extracted["vitals"]),
            "bp_reading_2": _bp_reading(extracted["vitals"]),
            "next_assessment_date": next_date,
        }

    def render_output(
        self,
        input_ref,
        input_data,
        normalized_input,
        extracted,
        evidence_map,
        rendered,
        context,
    ):
        return {
            "assessment": extracted["assessment"],
            "evidence_map": evidence_map,
            "recommendation": rendered.get("recommendation"),
            "spec_version": "clinical_v1",
        }


def _parse_symptoms(chief: str):
    symptoms = []
    if not chief:
        return symptoms
    parts = [p.strip() for p in chief.split(",") if p.strip()]
    for idx, part in enumerate(parts):
        text = part
        duration_days = None
        match = re.search(r"(\d+)\s*days", chief)
        if match:
            duration_days = int(match.group(1))
        symptoms.append(
            {
                "id": f"symptom_{idx}",
                "text": text.split(" for ")[0].strip(),
                "duration_days": duration_days,
                "severity": "moderate",
            }
        )
    return symptoms


def _next_assessment(encounter_date: str | None, days: int):
    if not encounter_date:
        return "{missing:next_assessment_date}"
    try:
        date = datetime.strptime(encounter_date, "%Y-%m-%d")
        return (date + timedelta(days=days)).strftime("%Y-%m-%d")
    except ValueError:
        return "{missing:next_assessment_date}"


def _bp_text(vitals: dict) -> str:
    return f"BP {vitals['systolic']}/{vitals['diastolic']} mmHg"


def _bp_reading(vitals: dict) -> str:
    return f"{vitals['systolic']}/{vitals['diastolic']} mmHg"
