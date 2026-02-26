import json
import re
from pathlib import Path

from core.attestation import sha256_text, sha256_bytes


def _find_repo_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "pyproject.toml").exists():
            return p
    return start.parent


def _to_repo_relative(path: Path) -> str:
    path = Path(path)
    repo_root = _find_repo_root(Path(__file__).resolve())
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
        rel_str = str(rel).replace("\\", "/")
        if rel_str.startswith("src/"):
            rel_str = rel_str[len("src/") :]
        return rel_str
    except Exception:
        return str(path).replace("\\", "/")


def _slugify(value: str) -> str:
    value = value.lower().replace(":", "_").replace(" ", "_")
    value = re.sub(r"[^a-z0-9_]+", "", value)
    return value


def fallback_chain(ref: str, template_dir: Path, extra_chain=None):
    chain = []
    slug = _slugify(ref)
    if slug:
        chain.append(template_dir / f"{slug}.json")
    parts = ref.split()
    if parts:
        chain.append(template_dir / f"{_slugify(parts[0])}.json")
    if extra_chain:
        for name in extra_chain:
            chain.append(template_dir / name)
    chain.append(template_dir / "generic.json")
    return chain


def load_template(ref: str, template_dir: Path, chain=None):
    template_dir = Path(template_dir)
    paths = chain or fallback_chain(ref, template_dir)
    for path in paths:
        if path.exists():
            raw = path.read_text(encoding="utf-8-sig")
            normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
            template = json.loads(raw)
            template["_template_path"] = _to_repo_relative(path)
            template["_template_sha256"] = sha256_text(normalized)
            return template
    raise FileNotFoundError(f"No template found for ref '{ref}' in {template_dir}")


def resolve_placeholders(value, context: dict):
    if isinstance(value, str):
        return _render_text(value, context)
    if isinstance(value, list):
        return [resolve_placeholders(v, context) for v in value]
    if isinstance(value, dict):
        return {k: resolve_placeholders(v, context) for k, v in value.items()}
    return value


def _render_text(text: str, context: dict) -> str:
    def repl(match):
        key = match.group(1)
        resolved = _resolve_key(key, context)
        if resolved is None:
            return f"{{missing:{key}}}"
        return str(resolved)

    return re.sub(r"\{([^{}]+)\}", repl, text)


def _resolve_key(key: str, context: dict):
    if "." in key:
        base, rest = key.split(".", 1)
        base_val = _resolve_base(base, context)
        if isinstance(base_val, dict):
            return base_val.get(rest)
        return None
    return _resolve_base(key, context)


def _resolve_base(key: str, context: dict):
    if key in context:
        return context[key]

    match = re.match(r"([a-zA-Z_]+)_(\d+)", key)
    if match:
        base = match.group(1)
        index = int(match.group(2))
        candidates = [base, f"{base}s", f"{base}_list", f"{base}s_detailed", f"{base}_detailed"]
        for name in candidates:
            if name in context and isinstance(context[name], list):
                list_val = context[name]
                idx = 0 if index == 0 else index - 1
                if 0 <= idx < len(list_val):
                    return list_val[idx]
    return None
