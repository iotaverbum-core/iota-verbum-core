from core.extraction import normalize_input


class CreditScoringExtractors:
    domain = "credit_scoring"

    def normalize_input(self, data: dict) -> dict:
        return data or {}

    def extract(self, normalized_input: dict, context: dict):
        income = float(normalized_input.get("income_monthly", 0) or 0)
        debt = float(normalized_input.get("debt_monthly", 0) or 0)
        credit_score = int(normalized_input.get("credit_score", 0) or 0)
        delinq = int(normalized_input.get("delinquencies_12mo", 0) or 0)
        employment = int(normalized_input.get("employment_months", 0) or 0)

        dti = round(debt / income, 2) if income else 0.0

        risk_signals = [
            {
                "id": "signal_0",
                "type": "debt_to_income",
                "value": dti,
                "threshold": 0.55,
                "status": "pass" if dti <= 0.55 else "fail",
            },
            {
                "id": "signal_1",
                "type": "recent_delinquency",
                "count": delinq,
                "threshold": 0,
                "status": "caution" if delinq > 0 else "pass",
            },
            {
                "id": "signal_2",
                "type": "credit_score",
                "value": credit_score,
                "threshold": 640,
                "status": "pass" if credit_score >= 640 else "caution",
            },
            {
                "id": "signal_3",
                "type": "employment_months",
                "value": employment,
                "threshold": 24,
                "status": "pass" if employment >= 24 else "caution",
            },
        ]

        frames = [
            {
                "id": "frame_0",
                "actor": f"applicant_{normalized_input.get('applicant_id', 'unknown')}",
                "action": "earn",
                "amount": income,
                "frequency": "monthly",
            },
            {
                "id": "frame_1",
                "actor": f"applicant_{normalized_input.get('applicant_id', 'unknown')}",
                "action": "owe",
                "amount": debt,
                "frequency": "monthly",
            },
        ]

        risk_tier = context.get("risk_tier") or ("subprime_tier3" if credit_score < 640 else "prime_tier1")
        decision = "approved_conditional" if dti <= 0.55 else "denied"
        if delinq > 0 and decision == "approved_conditional":
            decision = "approved_conditional"

        return {
            "income": income,
            "debt": debt,
            "dti": dti,
            "credit_score": credit_score,
            "delinquencies": delinq,
            "employment_months": employment,
            "risk_tier": risk_tier,
            "decision": decision,
            "signals": risk_signals,
            "frames": frames,
        }

    def build_evidence_map(self, extracted: dict, normalized_input: dict):
        return {
            "signals": extracted["signals"],
            "frames": extracted["frames"],
        }

    def template_fallback(self, input_ref: str, context: dict, normalized_input: dict):
        return None

    def build_context(self, input_ref, input_data, normalized_input, extracted, evidence_map, context):
        return {
            "applicant_id": normalized_input.get("applicant_id"),
            "risk_tier": extracted["risk_tier"],
            "decision": extracted["decision"],
            "rate": 0.089 if extracted["risk_tier"] == "subprime_tier3" else 0.049,
            "collateral_type": normalized_input.get("collateral"),
            "threshold_dti": 0.55,
            "threshold_delinquency_months": 12,
            "threshold_delinquency_count": 0,
            "verification_method": "bank_statement",
            "signal_income_stability": f"employment {extracted['employment_months']} months",
            "signal_credit_history": f"credit score {extracted['credit_score']}",
            "signal_collateral": "none",
            "risk_signal_1": "debt_to_income" if extracted["dti"] > 0.55 else "none",
            "risk_signal_2": "recent_delinquency" if extracted["delinquencies"] > 0 else "none",
            "improvement_action": "reduce debt-to-income ratio",
            "evidence_1": f"debt-to-income ratio {extracted['dti']}",
            "evidence_2": f"employment {extracted['employment_months']} months",
            "evidence_3": f"delinquencies {extracted['delinquencies']} in 12 months",
        }

    def render_output(self, input_ref, input_data, normalized_input, extracted, evidence_map, rendered, context):
        output = {
            "decision": extracted["decision"],
            "risk_tier": extracted["risk_tier"],
            "interest_rate": rendered.get("interest_rate"),
            "evidence_map": evidence_map,
            "explanation": rendered.get("explanation"),
            "spec_version": "credit_v1",
        }
        return output
