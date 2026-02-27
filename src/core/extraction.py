import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


def normalize_input(text: str) -> str:
    if text is None:
        return ""
    cleaned = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2019", "'")
        .replace("\u2018", "'")
    )
    paragraphs = re.split(r"\n\s*\n", cleaned.strip())
    normalized = [" ".join(p.split()) for p in paragraphs if p.strip()]
    return "\n\n".join(normalized)


def tokenize(text: str):
    tokens = []
    for match in re.finditer(r"[A-Za-z0-9']+", text):
        tokens.append(Token(match.group(0), match.start(), match.end()))
    return tokens


def segment(text: str, abbreviations=None):
    abbreviations = abbreviations or set()
    sentence_spans = []
    start = 0
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == "\n":
            end = i
            if end > start:
                sentence_spans.append((start, end))
            i += 1
            while i < length and text[i].isspace():
                i += 1
            start = i
            continue
        if ch in ".!?":
            last_word_match = re.search(r"[A-Za-z']+$", text[:i])
            last_word = last_word_match.group(0).lower() if last_word_match else ""
            if last_word and last_word in abbreviations:
                i += 1
                continue
            end = i + 1
            sentence_spans.append((start, end))
            i = end
            while i < length and text[i].isspace():
                i += 1
            start = i
            continue
        i += 1
    if start < length:
        sentence_spans.append((start, length))

    segments = []
    boundaries = []
    clause_splitters = [";", ":", "—", "–"]
    clause_conj = [" and ", " but ", " yet "]
    for s_idx, (s_start, s_end) in enumerate(sentence_spans):
        sentence_text = text[s_start:s_end]
        clause_starts = [0]
        for splitter in clause_splitters:
            for match in re.finditer(re.escape(splitter), sentence_text):
                clause_starts.append(match.end())
                boundaries.append({"boundary": s_start + match.start(), "type": "punct"})
        for conj in clause_conj:
            for match in re.finditer(re.escape(conj), sentence_text):
                clause_starts.append(match.start())
        clause_starts = sorted(set([c for c in clause_starts if 0 <= c < len(sentence_text)]))
        clause_starts.append(len(sentence_text))
        for c_idx in range(len(clause_starts) - 1):
            c_start = clause_starts[c_idx]
            c_end = clause_starts[c_idx + 1]
            clause_text = sentence_text[c_start:c_end].strip()
            if not clause_text:
                continue
            token_start = s_start + c_start
            token_end = s_start + c_end
            segments.append(
                {
                    "sentence_id": s_idx,
                    "clause_id": f"s{s_idx}.c{c_idx}",
                    "text": clause_text,
                    "token_start": token_start,
                    "token_end": token_end,
                }
            )
    return segments, boundaries, sentence_spans


def extract_entities(text: str, segments, patterns):
    entities = []
    for label, pattern in patterns:
        for match in re.finditer(pattern, text):
            entities.append(
                {
                    "label": label,
                    "token_span": [match.start(), match.end()],
                    "surface": match.group(0),
                }
            )
    entities.sort(key=lambda e: (e["token_span"][0], e["label"]))
    return entities


def resolve_references(segments, entities, pronoun_map, lookback_sentences=2):
    candidate_mentions = []
    for ent in entities:
        sent_id = _sentence_for_span(segments, ent["token_span"][0])
        candidate_mentions.append(
            {
                "label": ent["label"],
                "gender": ent.get("gender"),
                "number": ent.get("number"),
                "sentence_id": sent_id,
                "token_start": ent["token_span"][0],
                "role": "subject",
            }
        )

    coref_links = []
    unknown_state = {"M": 0, "F": 0, "N": 0, "P": 0}
    pronoun_pattern = re.compile(r"\b(he|she|they|him|her|them|his|their|it|its)\b", re.IGNORECASE)
    for seg in segments:
        for match in pronoun_pattern.finditer(seg["text"]):
            pronoun = match.group(1)
            start = seg["token_start"] + match.start()
            end = seg["token_start"] + match.end()
            gender, number = pronoun_map.get(pronoun.lower(), ("N", "S"))
            lookback = [
                c
                for c in candidate_mentions
                if 0 <= seg["sentence_id"] - c["sentence_id"] <= lookback_sentences
            ]
            filtered = []
            for c in lookback:
                if gender in {"M", "F"} and c.get("gender") and c["gender"] != gender:
                    continue
                if number == "P" and c.get("number") and c["number"] != "P":
                    continue
                filtered.append(c)
            if not filtered:
                unknown_state[gender] += 1
                unknown_id = f"unknown_{gender}_{unknown_state[gender]}"
                coref_links.append(
                    {
                        "from": {"token_span": [start, end], "surface_pronoun": pronoun},
                        "to": unknown_id,
                        "rule": "lookback_limit",
                        "evidence": f"no match within lookback for {pronoun}",
                    }
                )
                continue
            filtered.sort(key=lambda c: (seg["sentence_id"] - c["sentence_id"], -c["token_start"]))
            chosen = filtered[0]
            rule = "recency"
            coref_links.append(
                {
                    "from": {"token_span": [start, end], "surface_pronoun": pronoun},
                    "to": chosen["label"],
                    "rule": rule,
                    "evidence": f"resolved {pronoun} to {chosen['label']} by {rule}",
                }
            )
    for idx, link in enumerate(coref_links):
        link["id"] = f"coref_{idx}"
    return coref_links


def _sentence_for_span(segments, token_start):
    for seg in segments:
        if seg["token_start"] <= token_start < seg["token_end"]:
            return seg["sentence_id"]
    return 0


def extract_relationships(
    text: str, segments, verbs, entity_patterns, pronoun_map, coref_links=None
):
    coref_links = coref_links or []
    frames = []
    unknown_actor_state = 0

    entity_matches = []
    for label, pattern in entity_patterns:
        for match in re.finditer(pattern, text):
            entity_matches.append((match.start(), match.end(), label))
    entity_matches.sort()

    pronoun_pattern = re.compile(r"\b(he|she|they|him|her|them|his|their|it|its)\b", re.IGNORECASE)
    pronoun_matches = [(m.start(), m.end(), m.group(1)) for m in pronoun_pattern.finditer(text)]

    for verb in verbs:
        clause = next((s for s in segments if s["clause_id"] == verb["clause_id"]), None)
        if not clause:
            continue
        clause_start = clause["token_start"]
        clause_end = clause["token_end"]
        verb_start = verb["token_span"][0]

        local_entities = [m for m in entity_matches if clause_start <= m[0] < clause_end]
        local_pronouns = [m for m in pronoun_matches if clause_start <= m[0] < clause_end]
        matches = local_entities + local_pronouns
        before = [m for m in matches if m[0] < verb_start]
        after = [m for m in matches if m[0] > verb_start]

        actor = None
        if before:
            start, end, label = sorted(before)[-1]
            actor = _resolve_pronoun_label([start, end], coref_links) or label
        else:
            unknown_actor_state += 1
            actor = f"unknown_actor_{unknown_actor_state}"

        obj = None
        if after:
            start, end, label = sorted(after)[0]
            obj = _resolve_pronoun_label([start, end], coref_links) or label

        suffix = text[verb_start:clause_end]
        io_match = re.search(r"\b(to|for)\s+([^,.;!?]+)", suffix)
        indirect_object = io_match.group(2).strip() if io_match else None

        modifiers = []
        prep_patterns = [
            "in",
            "on",
            "at",
            "by",
            "with",
            "among",
            "into",
            "from",
            "about",
            "that day",
            "the next day",
        ]
        for prep in prep_patterns:
            m = re.search(rf"\b{re.escape(prep)}\b[^,.;!?]*", suffix)
            if m:
                mod = m.group(0).strip()
                if mod not in modifiers:
                    modifiers.append(mod)

        polarity = "affirm"
        if re.search(r"\b(not|no|never)\b", clause["text"].lower()):
            polarity = "neg"

        voice_guess = "active"
        if re.search(r"\b(was|were|is|are|been|be)\s+\w+(ed|en)\b", clause["text"].lower()):
            voice_guess = "passive"

        frames.append(
            {
                "id": None,
                "actor": actor,
                "verb": verb["verb_text"],
                "object": obj,
                "indirect_object": indirect_object,
                "modifiers": modifiers,
                "polarity": polarity,
                "voice_guess": voice_guess,
                "clause_id": verb["clause_id"],
                "token_span": verb["token_span"],
            }
        )

    frames.sort(key=lambda f: (f["token_span"][0], f["verb"], f["actor"]))
    for idx, frame in enumerate(frames):
        frame["id"] = f"frame_{idx}"
    return frames


def _resolve_pronoun_label(token_span, coref_links):
    for link in coref_links:
        if link["from"]["token_span"] == token_span:
            return link["to"]
    return None
