from __future__ import annotations


class LLMConstrainer:
    def build_prompt(
        self, ground_truth: dict, task: str, persona: str | None = None
    ) -> str:
        persona_line = (
            persona or "You are a precise assistant constrained to verified facts."
        )
        facts = ground_truth.get("facts", [])
        constraints = ground_truth.get("constraints", {})
        cannot = constraints.get("CANNOT_invent", [])
        must_cite = constraints.get("MUST_cite", [])
        max_words = constraints.get("max_words", 200)

        lines = [
            "SYSTEM:",
            persona_line,
            "",
            "TASK:",
            task,
            "",
            "FACTS (must use exactly, no invention):",
        ]
        lines.extend(f"- {fact}" for fact in facts)
        lines.extend(
            [
                "",
                "CONSTRAINTS:",
                "MUST include all facts above.",
                f"Word limit: {max_words} words.",
            ]
        )
        if cannot:
            lines.append("CANNOT invent or mention missing fields/topics:")
            lines.extend(f"- {item}" for item in cannot)
        if must_cite:
            lines.append("CITATION REQUIRED: reference evidence IDs in your response.")
            lines.append("Use format: evidence:ID")
            lines.extend(f"- {eid}" for eid in must_cite)
        return "\n".join(lines).rstrip() + "\n"

    def add_rejection_context(self, prompt: str, violations: dict) -> str:
        lines = [
            prompt.rstrip(),
            "",
            "REJECTION CONTEXT:",
            "Your previous response violated constraints:",
        ]
        for name, detail in violations.items():
            lines.append(f"- {name}: {detail}")
        lines.append("Return a corrected response that strictly follows constraints.")
        return "\n".join(lines).rstrip() + "\n"
