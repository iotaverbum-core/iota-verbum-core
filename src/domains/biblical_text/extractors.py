import re

from core.extraction import extract_relationships, normalize_input, segment

VERB_LEXICON = {
    "am",
    "are",
    "is",
    "was",
    "were",
    "be",
    "became",
    "have",
    "has",
    "had",
    "say",
    "said",
    "spoke",
    "answered",
    "cried",
    "come",
    "came",
    "go",
    "went",
    "make",
    "made",
    "dwell",
    "dwelt",
    "see",
    "seen",
    "saw",
    "give",
    "gave",
    "stand",
    "stood",
    "sit",
    "sat",
    "walk",
    "walked",
    "turn",
    "turned",
    "stay",
    "stayed",
    "follow",
    "followed",
    "hear",
    "heard",
    "look",
    "looked",
}

PAST_TENSE = {"was", "were", "had", "said", "came", "went", "made", "dwelt", "saw", "gave"}

PRONOUNS = {
    "he": ("M", "S"),
    "him": ("M", "S"),
    "his": ("M", "S"),
    "she": ("F", "S"),
    "her": ("F", "S"),
    "they": ("P", "P"),
    "them": ("P", "P"),
    "their": ("P", "P"),
    "it": ("N", "S"),
    "its": ("N", "S"),
}

TIME_MARKER_PATTERNS = [
    ("the next day", "sequence"),
    ("after these things", "sequence"),
    ("in those days", "anchor"),
    ("at that time", "anchor"),
    ("when", "simultaneity"),
    ("while", "simultaneity"),
    ("before", "sequence"),
    ("after", "sequence"),
    ("now", "anchor"),
    ("then", "sequence"),
    ("behold", "anchor"),
]

ATTRIBUTION_VERBS = {
    "said",
    "asked",
    "replied",
    "answered",
    "declared",
    "proclaimed",
    "spoke",
    "told",
    "cried",
    "responded",
}


def _entity_patterns():
    return [
        ("woman_of_Samaria", r"\bwoman of Samaria\b"),
        ("woman_of_Samaria", r"\bSamaritan woman\b"),
        ("Jesus", r"\bJesus\b"),
        ("John", r"\bJohn\b"),
        ("disciples", r"\bdisciples\b"),
    ]


def _entity_meta():
    return {
        "Jesus": {"char_id": "char_jesus", "label": "Jesus", "gender": "M", "number": "S"},
        "John": {"char_id": "char_john", "label": "John", "gender": "M", "number": "S"},
        "disciples": {
            "char_id": "char_disciples",
            "label": "disciples",
            "gender": "P",
            "number": "P",
        },
        "woman_of_Samaria": {
            "char_id": "char_woman_of_samaria",
            "label": "woman_of_Samaria",
            "gender": "F",
            "number": "S",
        },
    }


class BiblicalTextExtractors:
    domain = "biblical_text"

    def normalize_input(self, text: str) -> str:
        return normalize_input(text)

    def extract(self, normalized_text: str, context: dict):
        segments, boundaries, sentence_spans = segment(normalized_text)
        verbs = _extract_verbs(normalized_text, segments)
        time_markers = _extract_time_markers(normalized_text, segments)
        utterances = _extract_utterances(normalized_text, segments)
        characters = _build_characters(normalized_text, segments)
        coref_links = _build_coref_links(normalized_text, segments, characters)
        frames = extract_relationships(
            normalized_text,
            segments,
            verbs,
            _entity_patterns(),
            PRONOUNS,
            coref_links=coref_links,
        )

        return {
            "segments": segments,
            "verbs": verbs,
            "time_markers": time_markers,
            "utterances": utterances,
            "characters": characters,
            "coref_links": coref_links,
            "frames": frames,
        }

    def build_evidence_map(self, extracted: dict, normalized_text: str):
        evidence = {
            "frames": [],
            "characters": [],
            "coref_links": [],
            "utterances": [],
        }
        for idx, frame in enumerate(extracted["frames"]):
            evidence["frames"].append(
                {
                    "id": f"frame_{idx}",
                    "clause_id": frame["clause_id"],
                    "token_span": frame["token_span"],
                    "actor": frame["actor"],
                    "verb": frame["verb"],
                    "object": frame["object"],
                    "indirect_object": frame["indirect_object"],
                }
            )
        for char in extracted["characters"]:
            first = char["mentions"][0] if char["mentions"] else None
            evidence["characters"].append(
                {
                    "char_id": char["char_id"],
                    "label": char["label"],
                    "first_mention_clause_id": first["clause_id"] if first else None,
                    "first_mention_token_span": first["token_span"] if first else None,
                }
            )
        for link in extracted["coref_links"]:
            evidence["coref_links"].append(link)
        for idx, utterance in enumerate(extracted["utterances"]):
            evidence["utterances"].append(
                {
                    "id": f"utterance_{idx}",
                    "clause_id": utterance.get("clause_id"),
                    "token_span": utterance.get("token_span"),
                    "speaker_guess": utterance.get("speaker_guess"),
                    "text": utterance.get("text"),
                    "speech_act": utterance.get("speech_act"),
                }
            )
        return evidence

    def template_fallback(self, input_ref: str, context: dict, normalized_text: str):
        return None

    def build_context(
        self, input_ref, input_data, normalized_text, extracted, evidence_map, context
    ):
        frames = extracted["frames"]
        frame_strings = [
            _frame_string(f["actor"], f["verb"], f["object"], f["indirect_object"]) for f in frames
        ]
        actors = [f["actor"] for f in frames]
        actions = [f["verb"] for f in frames]
        objects = [f["object"] for f in frames if f.get("object")]
        utterances = extracted["utterances"]
        questions = [u["text"] for u in utterances if u.get("speech_act") == "question"]
        utterance_texts = [u["text"] for u in utterances]
        speakers = [u["speaker_guess"] for u in utterances if u.get("speaker_guess")]
        movement = None
        for f in frames:
            if f["verb"].lower() not in ATTRIBUTION_VERBS:
                movement = _frame_string(f["actor"], f["verb"], f["object"], f["indirect_object"])
                break

        return {
            "moment": context.get("moment"),
            "passage_ref": input_ref,
            "passage_text": normalized_text,
            "frames": frame_strings,
            "actors": actors,
            "actions": actions,
            "objects": objects,
            "questions": questions,
            "utterances": utterance_texts,
            "speakers": speakers,
            "movement_1": movement or "{missing:movement_1}",
        }

    def render_output(
        self, input_ref, input_data, normalized_text, extracted, evidence_map, rendered, context
    ):
        template_id = rendered.get("template_id") or rendered.get("id")
        return {
            "spec_version": "biblical_v1",
            "domain": "biblical_text",
            "passage": {"ref": input_ref, "text": normalized_text},
            "context": context,
            "scene": {
                "segments": extracted["segments"],
                "time_markers": extracted["time_markers"],
                "frames": extracted["frames"],
                "characters": extracted["characters"],
                "coref_links": extracted["coref_links"],
                "utterances": extracted["utterances"],
            },
            "evidence_map": evidence_map,
            "rendered": {
                "witness_prompts": rendered.get("witness_prompts", []),
                "prayer": rendered.get("prayer", ""),
                "safety_notes": rendered.get("safety_notes", []),
            },
            "template": {"id": template_id, "path": rendered.get("_template_path")},
        }


def _extract_verbs(text: str, segments):
    verbs = []
    for seg in segments:
        for match in re.finditer(r"[A-Za-z']+", seg["text"]):
            token = match.group(0)
            lower = token.lower()
            if lower in VERB_LEXICON or lower.endswith("ed") or lower.endswith("ing"):
                lemma = lower
                tense = "past" if lower in PAST_TENSE or lower.endswith("ed") else "present"
                verbs.append(
                    {
                        "verb_text": token,
                        "lemma_guess": lemma,
                        "tense_guess": tense,
                        "role": "speech_introducer" if lower in ATTRIBUTION_VERBS else "verb",
                        "token_span": [
                            seg["token_start"] + match.start(),
                            seg["token_start"] + match.end(),
                        ],
                        "clause_id": seg["clause_id"],
                    }
                )
    verbs.sort(key=lambda v: (v["token_span"][0], v["verb_text"].lower()))
    return verbs


def _extract_time_markers(text: str, segments):
    markers = []
    for phrase, kind in TIME_MARKER_PATTERNS:
        for match in re.finditer(re.escape(phrase), text, re.IGNORECASE):
            clause_id = None
            for seg in segments:
                if seg["token_start"] <= match.start() < seg["token_end"]:
                    clause_id = seg["clause_id"]
                    break
            markers.append(
                {
                    "text": match.group(0),
                    "type": kind,
                    "clause_id": clause_id,
                    "token_span": [match.start(), match.end()],
                }
            )
    markers.sort(key=lambda m: (m["token_span"][0], m["text"]))
    return markers


def _extract_utterances(text: str, segments):
    utterances = []
    for match in re.finditer(r"\"([^\"]+)\"", text):
        utterance_text = match.group(1).strip()
        start, end = match.start(1), match.end(1)
        clause_id = None
        for seg in segments:
            if seg["token_start"] <= start < seg["token_end"]:
                clause_id = seg["clause_id"]
                break
        speaker_guess = _guess_speaker(text[:start])
        speech_act = "question" if utterance_text.endswith("?") else "unknown"
        utterances.append(
            {
                "text": utterance_text,
                "speaker_guess": speaker_guess,
                "speech_act": speech_act,
                "clause_id": clause_id,
                "token_span": [start, end],
            }
        )
    return utterances


def _guess_speaker(prefix_text: str):
    window = prefix_text[-120:]
    for name in ["Jesus", "John", "Samaritan woman", "woman", "disciples"]:
        if re.search(rf"\b{name}\b", window):
            return (
                "woman_of_Samaria" if "woman" in name.lower() and "samar" in name.lower() else name
            )
    return "unknown"


def _build_characters(text: str, segments):
    meta = _entity_meta()
    patterns = _entity_patterns()
    mentions_by_id = {m["char_id"]: [] for m in meta.values()}
    for label, pattern in patterns:
        for match in re.finditer(pattern, text):
            entry = meta[label]
            clause_id = None
            for seg in segments:
                if seg["token_start"] <= match.start() < seg["token_end"]:
                    clause_id = seg["clause_id"]
                    break
            mentions_by_id[entry["char_id"]].append(
                {
                    "clause_id": clause_id,
                    "token_span": [match.start(), match.end()],
                    "surface": match.group(0),
                }
            )
    characters = []
    for label, entry in meta.items():
        mentions = mentions_by_id[entry["char_id"]]
        if mentions:
            characters.append(
                {
                    "char_id": entry["char_id"],
                    "label": entry["label"],
                    "mentions": sorted(mentions, key=lambda m: m["token_span"][0]),
                }
            )
    characters.sort(key=lambda c: (c["mentions"][0]["token_span"][0], c["label"]))
    return characters


def _build_coref_links(text: str, segments, characters):
    candidate_mentions = []
    for char in characters:
        gender = _entity_meta().get(char["label"], {}).get("gender")
        number = _entity_meta().get(char["label"], {}).get("number")
        for m in char["mentions"]:
            sentence_id = _sentence_for_span(segments, m["token_span"][0])
            candidate_mentions.append(
                {
                    "label": char["label"],
                    "gender": gender,
                    "number": number,
                    "sentence_id": sentence_id,
                    "token_start": m["token_span"][0],
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
            gender, number = PRONOUNS.get(pronoun.lower(), ("N", "S"))
            lookback = [
                c for c in candidate_mentions if 0 <= seg["sentence_id"] - c["sentence_id"] <= 2
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
                unknown_id = f"char_unknown_{gender}_{unknown_state[gender]}"
                coref_links.append(
                    {
                        "from": {
                            "clause_id": seg["clause_id"],
                            "token_span": [start, end],
                            "surface_pronoun": pronoun,
                        },
                        "to": unknown_id,
                        "rule": "lookback_limit",
                        "evidence": f"no match within lookback for {pronoun}",
                    }
                )
                continue
            filtered.sort(key=lambda c: (seg["sentence_id"] - c["sentence_id"], -c["token_start"]))
            chosen = filtered[0]
            coref_links.append(
                {
                    "from": {
                        "clause_id": seg["clause_id"],
                        "token_span": [start, end],
                        "surface_pronoun": pronoun,
                    },
                    "to": chosen["label"],
                    "rule": "recency",
                    "evidence": f"resolved {pronoun} to {chosen['label']} by recency",
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


def _frame_string(actor, verb, obj, indirect_object):
    if indirect_object:
        return f"{actor} {verb} to {indirect_object}"
    if obj:
        return f"{actor} {verb} {obj}"
    return f"{actor} {verb}"
