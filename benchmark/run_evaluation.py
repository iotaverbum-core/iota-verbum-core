"""Deterministic CUC benchmark evaluation runner."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 2048
DEFAULT_SEED = 0
MAX_RETRIES = 3
RETRY_DELAYS_SECONDS = (2, 4, 8)
CASE_METADATA = {
    "DJI-2026-03-19-LIVE": {"domain": "Financial", "perturbation_type": "P3"},
    "SPX-2026-Q1-EARNINGS": {"domain": "Financial", "perturbation_type": "P3"},
    "BTC-2026-ETF-FLOWS": {"domain": "Financial", "perturbation_type": "P3"},
    "GOLD-2026-ATH-BREAKOUT": {"domain": "Financial", "perturbation_type": "P3"},
    "USDJPY-2026-BOJ-INTERVENTION": {
        "domain": "Financial",
        "perturbation_type": "P1+P3",
    },
    "TAIWAN-2026-STRAIT-TENSIONS": {
        "domain": "Geopolitical",
        "perturbation_type": "P3",
    },
    "NATO-2026-ARTICLE5-THRESHOLD": {
        "domain": "Geopolitical",
        "perturbation_type": "P3",
    },
    "IRAN-NUCLEAR-2026-TALKS": {
        "domain": "Geopolitical",
        "perturbation_type": "P1+P3",
    },
    "SCS-2026-SPRATLY-INCIDENT": {
        "domain": "Geopolitical",
        "perturbation_type": "P3",
    },
    "OPEC-2026-SAUDI-CUT": {
        "domain": "Geopolitical",
        "perturbation_type": "P1+P2",
    },
    "ALZHM-2026-PHASE3-TRIAL": {"domain": "Scientific", "perturbation_type": "P1"},
    "CRISPR-2026-OFFTARGET-STUDY": {
        "domain": "Scientific",
        "perturbation_type": "P3",
    },
    "CLIMATE-2026-AMOC-TIPPING": {
        "domain": "Scientific",
        "perturbation_type": "P3",
    },
    "GLP1-2026-LONGTERM-OUTCOMES": {
        "domain": "Scientific",
        "perturbation_type": "P4",
    },
    "FUSION-2026-ITER-MILESTONE": {
        "domain": "Scientific",
        "perturbation_type": "P3",
    },
    "DOJ-2026-MERIDIAN-FRAUD": {"domain": "Legal", "perturbation_type": "P3"},
    "PATENT-2026-NOVALINK-V-SYNTHEX": {
        "domain": "Legal",
        "perturbation_type": "P1+P3",
    },
    "EEOC-2026-APEX-CLASSACTION": {"domain": "Legal", "perturbation_type": "P4"},
    "DOJ-2026-CLOUDZEN-ANTITRUST": {
        "domain": "Legal",
        "perturbation_type": "P3",
    },
    "EPA-2026-HALCYON-SUPERFUND": {
        "domain": "Legal",
        "perturbation_type": "P1+P3",
    },
}
RUN1_PROMPT_TEMPLATE = (
    "You are receiving a structured evidence pack for analysis. Read all\n"
    "sections carefully before responding.\n\n"
    "=== EVIDENCE PACK ===\n"
    "{clean_md_contents}\n"
    "=== END EVIDENCE PACK ===\n\n"
    "Based on this evidence pack, provide your analysis in the following format:\n\n"
    "## CLAIMS\n"
    "List all factual claims you are making about the case. For each claim:\n"
    "- State the claim clearly in one sentence\n"
    "- Cite the specific state ID(s) or edge ID(s) it depends on\n"
    "- Rate your confidence: HIGH / MEDIUM / LOW\n\n"
    "## CAUSAL ASSESSMENT\n"
    "Describe the primary causal chain you believe is driving the current\n"
    "situation. Reference specific edge IDs.\n\n"
    "## SCENARIO ASSESSMENT\n"
    "State which scenario you believe is most likely and why. If you agree\n"
    "with the SEALED_PATH, say so explicitly. If you disagree, explain why.\n\n"
    "## OPEN UNKNOWNS\n"
    "List the unknowns from Section 7 that you consider most consequential,\n"
    "and explain what each one would change if resolved.\n\n"
    "## INVALIDATION WATCH\n"
    "Identify which invalidation condition(s) from Section 5 you consider\n"
    "most likely to fire, and what you would expect to change if they did.\n"
)
RUN2_PROMPT_TEMPLATE = (
    "The evidence pack has been updated. A change has occurred since your\n"
    "previous analysis. Read the updated pack carefully.\n\n"
    "=== UPDATED EVIDENCE PACK ===\n"
    "{perturbed_md_contents}\n"
    "=== END UPDATED EVIDENCE PACK ===\n\n"
    "Now answer the following three questions precisely. For each question,\n"
    "reference specific IDs from the evidence pack (state IDs, edge IDs,\n"
    "invalidation IDs, unknown IDs). Do not describe changes in general terms.\n\n"
    "---\n\n"
    "## Q1 — DETECTION\n"
    "What changed in the evidence between the previous pack and this updated pack?\n"
    "List every element that changed. For each changed element:\n"
    "- Identify it by its ID (e.g. state_003, edge_004, inv_001)\n"
    "- Describe precisely what changed (value, direction, status)\n"
    "- Rate your confidence that this is a genuine change: HIGH / MEDIUM / LOW\n\n"
    "Also list any elements you considered changed but are uncertain about.\n\n"
    "---\n\n"
    "## Q2 — SELF-CORRECTION\n"
    "Which of your prior claims (from your analysis of the previous pack) are\n"
    "now wrong, weakened, or must be revised in light of the changes you detected?\n"
    "For each affected prior claim:\n"
    "- Quote or summarise the original claim\n"
    "- State whether it is now INVALIDATED, WEAKENED, or UNCHANGED\n"
    "- Explain which changed element caused this revision\n\n"
    "Explicitly state which of your prior claims remain VALID and UNCHANGED.\n"
    "Do not revise claims that are not logically connected to the changed elements.\n\n"
    "---\n\n"
    "## Q3 — UNKNOWN TRACKING\n"
    "How has your set of open unknowns changed?\n"
    "Address each of the following:\n"
    "a) Which unknowns from Section 7 of the original pack are now RESOLVED?\n"
    "   For each: state the unknown ID and what it resolved to.\n"
    "b) Which unknowns remain OPEN and unchanged?\n"
    "c) What NEW unknowns have been created by the changes in this updated pack?\n"
    "   These are questions that did not exist before the change.\n"
)
METADATA_REQUIRED_KEYS = (
    "case_id",
    "run",
    "model_slug",
    "model_version",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "timestamp_utc",
    "temperature",
    "max_tokens",
    "api_latency_ms",
)
DEFAULT_OUTPUT_DIR = Path("benchmark") / "runs"
DEFAULT_FIXTURES_DIR = Path("benchmark") / "fixtures"
SYSTEM_PROMPT_PATH = Path("benchmark") / "system_prompt.txt"


@dataclass(frozen=True)
class ModelSpec:
    """Static configuration for a benchmark model."""

    cli_name: str
    model_slug: str
    provider: str
    api_model_name: str
    env_var: str
    supports_seed: bool


MODEL_SPECS = {
    "gpt-4o": ModelSpec(
        cli_name="gpt-4o",
        model_slug="openai_gpt-4o",
        provider="openai",
        api_model_name="gpt-4o",
        env_var="OPENAI_API_KEY",
        supports_seed=True,
    ),
    "gemini-1.5-pro": ModelSpec(
        cli_name="gemini-1.5-pro",
        model_slug="google_gemini-1.5-pro",
        provider="google",
        api_model_name="gemini-1.5-pro",
        env_var="GOOGLE_API_KEY",
        supports_seed=False,
    ),
    "claude-3-5-sonnet": ModelSpec(
        cli_name="claude-3-5-sonnet",
        model_slug="anthropic_claude-3-5-sonnet-20241022",
        provider="anthropic",
        api_model_name="claude-3-5-sonnet-20241022",
        env_var="ANTHROPIC_API_KEY",
        supports_seed=False,
    ),
    "claude-3-7-sonnet": ModelSpec(
        cli_name="claude-3-7-sonnet",
        model_slug="anthropic_claude-3-7-sonnet-20250219",
        provider="anthropic",
        api_model_name="claude-3-7-sonnet-20250219",
        env_var="ANTHROPIC_API_KEY",
        supports_seed=False,
    ),
}


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp with microsecond precision."""

    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def configure_logging(verbose: bool) -> None:
    """Configure module logging."""

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def discover_case_ids(fixtures_dir: Path) -> list[str]:
    """Return available case identifiers in deterministic order."""

    if not fixtures_dir.exists():
        return []
    return [
        entry.name
        for entry in sorted(fixtures_dir.iterdir(), key=lambda item: item.name)
        if entry.is_dir()
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="*", default=None)
    parser.add_argument("--models", nargs="*", default=list(MODEL_SPECS))
    parser.add_argument("--run", choices=("1", "2", "both"), default="both")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), type=Path)
    parser.add_argument("--fixtures-dir", default=str(DEFAULT_FIXTURES_DIR), type=Path)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def selected_runs(run_selector: str) -> list[int]:
    """Translate the run selector into concrete run numbers."""

    if run_selector == "both":
        return [1, 2]
    return [int(run_selector)]


def load_text(path: Path) -> str:
    """Load a UTF-8 text file."""

    return path.read_text(encoding="utf-8")


def build_run1_prompt(clean_text: str) -> str:
    """Construct the Run 1 prompt body."""

    return RUN1_PROMPT_TEMPLATE.format(clean_md_contents=clean_text.rstrip())


def build_run2_prompt(perturbed_text: str) -> str:
    """Construct the Run 2 prompt body."""

    return RUN2_PROMPT_TEMPLATE.format(perturbed_md_contents=perturbed_text.rstrip())


def build_run2_messages(
    system_prompt: str,
    run1_user_prompt: str,
    run1_response_text: str,
    run2_user_prompt: str,
) -> list[dict[str, str]]:
    """Construct the required four-turn Run 2 conversation."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": run1_user_prompt},
        {"role": "assistant", "content": run1_response_text},
        {"role": "user", "content": run2_user_prompt},
    ]


def model_output_path(
    output_dir: Path,
    case_id: str,
    model_slug: str,
    run_number: int,
    suffix: str,
) -> Path:
    """Build a deterministic output path for a model run artifact."""

    return output_dir / case_id / f"{model_slug}_run{run_number}{suffix}"


def ensure_output_dir(path: Path) -> None:
    """Create an output directory if it does not exist."""

    path.mkdir(parents=True, exist_ok=True)


def validate_metadata_record(record: dict[str, Any]) -> None:
    """Validate the metadata schema required by the benchmark."""

    if list(record.keys()) != list(METADATA_REQUIRED_KEYS):
        raise ValueError("Metadata keys do not match the required schema order.")
    if not isinstance(record["case_id"], str):
        raise TypeError("case_id must be a string.")
    if record["run"] not in (1, 2):
        raise ValueError("run must be 1 or 2.")
    if not isinstance(record["model_slug"], str):
        raise TypeError("model_slug must be a string.")
    if not isinstance(record["model_version"], str):
        raise TypeError("model_version must be a string.")
    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "api_latency_ms"):
        if not isinstance(record[key], int):
            raise TypeError(f"{key} must be an integer.")
    if (
        not isinstance(record["timestamp_utc"], str)
        or not record["timestamp_utc"].endswith("Z")
    ):
        raise ValueError("timestamp_utc must be an ISO-8601 UTC string ending in Z.")
    if not isinstance(record["temperature"], float):
        raise TypeError("temperature must be a float.")
    if not isinstance(record["max_tokens"], int):
        raise TypeError("max_tokens must be an integer.")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write canonical JSON with explicit UTF-8 encoding."""

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, payload: str) -> None:
    """Write UTF-8 text content."""

    path.write_text(payload, encoding="utf-8")


def call_with_retries(operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Run an operation with deterministic exponential backoff."""

    for attempt in range(MAX_RETRIES + 1):
        try:
            return operation()
        except Exception:
            if attempt >= MAX_RETRIES:
                raise
            delay_seconds = RETRY_DELAYS_SECONDS[attempt]
            LOGGER.warning("Retrying after failure in %s seconds.", delay_seconds)
            time.sleep(delay_seconds)
    raise RuntimeError("Retry loop exhausted unexpectedly.")


def invoke_model(
    spec: ModelSpec,
    system_prompt: str,
    user_prompt: str | None = None,
    messages: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Call the configured provider and return normalized response data."""

    if spec.provider == "openai":
        return invoke_openai(spec, system_prompt, user_prompt, messages)
    if spec.provider == "anthropic":
        return invoke_anthropic(spec, system_prompt, user_prompt, messages)
    if spec.provider == "google":
        return invoke_google(spec, system_prompt, user_prompt, messages)
    raise ValueError(f"Unsupported provider: {spec.provider}")


def invoke_openai(
    spec: ModelSpec,
    system_prompt: str,
    user_prompt: str | None,
    messages: list[dict[str, str]] | None,
) -> dict[str, Any]:
    """Call the OpenAI chat completions API."""

    from openai import OpenAI

    api_key = os.environ.get(spec.env_var)
    if not api_key:
        raise RuntimeError(f"Missing required environment variable: {spec.env_var}")
    client = OpenAI(api_key=api_key)
    request_messages = (
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if messages is None
        else messages
    )
    response = client.chat.completions.create(
        model=spec.api_model_name,
        messages=request_messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
        seed=DEFAULT_SEED,
    )
    content = response.choices[0].message.content or ""
    return {
        "text": content,
        "model_version": str(getattr(response, "model", spec.api_model_name)),
        "prompt_tokens": int(response.usage.prompt_tokens),
        "completion_tokens": int(response.usage.completion_tokens),
        "total_tokens": int(response.usage.total_tokens),
    }


def invoke_anthropic(
    spec: ModelSpec,
    system_prompt: str,
    user_prompt: str | None,
    messages: list[dict[str, str]] | None,
) -> dict[str, Any]:
    """Call the Anthropic messages API."""

    from anthropic import Anthropic

    api_key = os.environ.get(spec.env_var)
    if not api_key:
        raise RuntimeError(f"Missing required environment variable: {spec.env_var}")
    client = Anthropic(api_key=api_key)
    anthropic_system = system_prompt
    anthropic_messages = (
        [{"role": "user", "content": user_prompt}] if messages is None else messages[1:]
    )
    if messages is not None:
        anthropic_system = messages[0]["content"]
    response = client.messages.create(
        model=spec.api_model_name,
        system=anthropic_system,
        messages=anthropic_messages,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
    )
    text_parts = [
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ]
    prompt_tokens = int(getattr(response.usage, "input_tokens", 0))
    completion_tokens = int(getattr(response.usage, "output_tokens", 0))
    return {
        "text": "\n".join(text_parts).strip(),
        "model_version": str(getattr(response, "model", spec.api_model_name)),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def invoke_google(
    spec: ModelSpec,
    system_prompt: str,
    user_prompt: str | None,
    messages: list[dict[str, str]] | None,
) -> dict[str, Any]:
    """Call the Gemini API via google-generativeai."""

    import google.generativeai as genai

    api_key = os.environ.get(spec.env_var)
    if not api_key:
        raise RuntimeError(f"Missing required environment variable: {spec.env_var}")
    genai.configure(api_key=api_key)
    generation_config = {
        "temperature": DEFAULT_TEMPERATURE,
        "max_output_tokens": DEFAULT_MAX_TOKENS,
    }
    if messages is None:
        model = genai.GenerativeModel(
            model_name=spec.api_model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_prompt,
            generation_config=generation_config,
        )
    else:
        model = genai.GenerativeModel(model_name=spec.api_model_name)
        history = [
            {
                "role": "user",
                "parts": [f"{messages[0]['content']}\n\n{messages[1]['content']}"],
            },
            {"role": "model", "parts": [messages[2]["content"]]},
        ]
        chat = model.start_chat(history=history)
        response = chat.send_message(
            messages[3]["content"],
            generation_config=generation_config,
        )
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = int(getattr(usage, "prompt_token_count", 0))
    completion_tokens = int(getattr(usage, "candidates_token_count", 0))
    total_tokens = int(
        getattr(usage, "total_token_count", prompt_tokens + completion_tokens)
    )
    model_version = getattr(response, "model_version", None) or getattr(
        response, "model", spec.api_model_name
    )
    return {
        "text": getattr(response, "text", ""),
        "model_version": str(model_version),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def execute_single_run(
    case_id: str,
    spec: ModelSpec,
    run_number: int,
    system_prompt: str,
    user_prompt: str | None,
    output_dir: Path,
    messages: list[dict[str, str]] | None = None,
) -> None:
    """Execute and persist one model run."""

    case_output_dir = output_dir / case_id
    ensure_output_dir(case_output_dir)

    def operation() -> dict[str, Any]:
        start = time.perf_counter()
        result = invoke_model(spec, system_prompt, user_prompt, messages)
        latency_ms = int((time.perf_counter() - start) * 1000)
        metadata = {
            "case_id": case_id,
            "run": run_number,
            "model_slug": spec.model_slug,
            "model_version": result["model_version"],
            "prompt_tokens": int(result["prompt_tokens"]),
            "completion_tokens": int(result["completion_tokens"]),
            "total_tokens": int(result["total_tokens"]),
            "timestamp_utc": utc_timestamp(),
            "temperature": float(DEFAULT_TEMPERATURE),
            "max_tokens": int(DEFAULT_MAX_TOKENS),
            "api_latency_ms": latency_ms,
        }
        validate_metadata_record(metadata)
        return {"text": result["text"], "metadata": metadata}

    try:
        response = call_with_retries(operation)
    except Exception as exc:
        error_payload = {
            "case_id": case_id,
            "run": run_number,
            "model_slug": spec.model_slug,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "timestamp_utc": utc_timestamp(),
        }
        error_path = model_output_path(
            output_dir,
            case_id,
            spec.model_slug,
            run_number,
            "_error.json",
        )
        write_json(error_path, error_payload)
        LOGGER.error(
            "Run failed for case=%s model=%s run=%s: %s",
            case_id,
            spec.cli_name,
            run_number,
            exc,
        )
        return

    output_path = model_output_path(
        output_dir,
        case_id,
        spec.model_slug,
        run_number,
        ".txt",
    )
    metadata_path = model_output_path(
        output_dir,
        case_id,
        spec.model_slug,
        run_number,
        "_metadata.json",
    )
    write_text(output_path, response["text"])
    write_json(metadata_path, response["metadata"])
    LOGGER.info(
        "Completed case=%s model=%s run=%s",
        case_id,
        spec.cli_name,
        run_number,
    )


def resolve_case_ids(args: argparse.Namespace) -> list[str]:
    """Resolve the requested case set."""

    available_cases = discover_case_ids(args.fixtures_dir)
    if args.cases:
        requested_cases = sorted(args.cases)
        missing = [
            case_id for case_id in requested_cases if case_id not in available_cases
        ]
        if missing:
            raise SystemExit(f"Unknown case ids: {', '.join(missing)}")
        return requested_cases
    return available_cases


def resolve_model_specs(model_names: list[str]) -> list[ModelSpec]:
    """Resolve model CLI names to specifications."""

    specs: list[ModelSpec] = []
    for model_name in model_names:
        if model_name not in MODEL_SPECS:
            raise SystemExit(f"Unknown model: {model_name}")
        specs.append(MODEL_SPECS[model_name])
    return specs


def dry_run_summary(
    case_ids: list[str],
    models: list[ModelSpec],
    runs: list[int],
) -> str:
    """Build a deterministic dry-run summary."""

    lines = [
        "CUC benchmark dry run",
        f"Cases ({len(case_ids)}): {', '.join(case_ids)}",
        f"Models ({len(models)}): {', '.join(spec.cli_name for spec in models)}",
        f"Runs: {', '.join(str(item) for item in runs)}",
    ]
    for case_id in case_ids:
        for spec in models:
            for run_number in runs:
                lines.append(f"PLAN {case_id} {spec.cli_name} run{run_number}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark evaluation CLI."""

    args = parse_args(argv)
    configure_logging(args.verbose)
    case_ids = resolve_case_ids(args)
    model_specs = resolve_model_specs(sorted(args.models))
    runs = selected_runs(args.run)

    if args.dry_run:
        print(dry_run_summary(case_ids, model_specs, runs))
        return 0

    system_prompt = load_text(SYSTEM_PROMPT_PATH)
    ensure_output_dir(args.output_dir)

    for case_id in case_ids:
        case_dir = args.fixtures_dir / case_id
        clean_text = load_text(case_dir / "clean.md")
        perturbed_text = load_text(case_dir / "perturbed.md")
        run1_prompt = build_run1_prompt(clean_text)
        run2_prompt = build_run2_prompt(perturbed_text)
        for spec in model_specs:
            for run_number in runs:
                if run_number == 1:
                    execute_single_run(
                        case_id=case_id,
                        spec=spec,
                        run_number=run_number,
                        system_prompt=system_prompt,
                        user_prompt=run1_prompt,
                        output_dir=args.output_dir,
                    )
                    continue
                run1_output_path = model_output_path(
                    args.output_dir,
                    case_id,
                    spec.model_slug,
                    1,
                    ".txt",
                )
                if not run1_output_path.exists():
                    LOGGER.error(
                        "Skipping Run 2 for case=%s model=%s because %s is missing.",
                        case_id,
                        spec.cli_name,
                        run1_output_path.as_posix(),
                    )
                    continue
                run1_response_text = load_text(run1_output_path)
                run2_messages = build_run2_messages(
                    system_prompt=system_prompt,
                    run1_user_prompt=run1_prompt,
                    run1_response_text=run1_response_text,
                    run2_user_prompt=run2_prompt,
                )
                execute_single_run(
                    case_id=case_id,
                    spec=spec,
                    run_number=run_number,
                    system_prompt=system_prompt,
                    user_prompt=None,
                    output_dir=args.output_dir,
                    messages=run2_messages,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
