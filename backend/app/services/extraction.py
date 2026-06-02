from __future__ import annotations

import io
import re
from pathlib import Path


ELECTRICAL_SCOPE_KEYWORDS = [
    "underground cable",
    "overhead",
    "pole line",
    "transmission",
    "distribution",
    "medium voltage",
    "high voltage",
    "conduit",
    "trenching",
    "transformer",
    "substation",
    "fiber",
    "data center",
    "hyperscale",
    "colocation",
    "critical power",
    "ai infrastructure",
    "artificial intelligence",
    "hpc",
    "high performance computing",
    "gpu",
    "compute campus",
    "server farm",
    "fire damage",
    "replacement",
    "emergency repair",
]

MATERIAL_TERMS = [
    "cable",
    "conductor",
    "conduit",
    "duct bank",
    "transformer",
    "switchgear",
    "switchboard",
    "ups",
    "uninterruptible power supply",
    "generator",
    "busduct",
    "busway",
    "power distribution unit",
    "pdu",
    "fiber",
    "pull box",
    "manhole",
    "splice",
    "termination",
    "pole",
    "crossarm",
    "recloser",
    "breaker",
    "substation steel",
]

INSTALLATION_TERMS = [
    "install",
    "installation",
    "replace",
    "replacement",
    "trench",
    "directional drill",
    "pull",
    "terminate",
    "splice",
    "test",
    "commission",
    "energize",
    "repair",
    "rebuild",
]

BONDING_TERMS = [
    "bid bond",
    "performance bond",
    "payment bond",
    "bonding",
    "insurance",
    "liability",
    "workers compensation",
]

SUBMISSION_TERMS = ["submit", "submission", "proposal", "sealed bid", "portal", "sam.gov", "email", "deadline"]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_attachment(file_bytes: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(file_bytes)
    return file_bytes.decode("utf-8", errors="ignore")


def parse_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return file_bytes.decode("utf-8", errors="ignore")

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages)


def find_sentences(text: str, terms: list[str], limit: int = 8) -> list[str]:
    sentence_candidates = re.split(r"(?<=[.!?])\s+|\n+", text)
    matches: list[str] = []
    for sentence in sentence_candidates:
        clean = normalize_text(sentence)
        if not clean:
            continue
        lower = clean.lower()
        if any(term in lower for term in terms):
            matches.append(clean[:500])
        if len(matches) >= limit:
            break
    return matches


def contains_term(text: str, term: str) -> bool:
    if term == "ups":
        return (
            re.search(
                r"\bups\b(?=.{0,64}\b(power|battery|distribution|system|room|electrical|critical|backup|busduct|switchgear|feeder|feeders|data center|infrastructure)\b)|"
                r"\b(power|battery|distribution|system|room|electrical|critical|backup|busduct|switchgear|feeder|feeders|data center|infrastructure)\b.{0,64}\bups\b",
                text,
            )
            is not None
        )
    if re.fullmatch(r"[a-z0-9]+", term):
        return re.search(rf"\b{re.escape(term)}\b", text) is not None
    return term in text


def extract_money(text: str) -> list[str]:
    values = re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", text)
    return values[:5]


def extract_deadlines(text: str) -> list[str]:
    patterns = [
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(matches))[:8]


def extract_specs(text: str) -> dict:
    clean_text = normalize_text(text)
    lower = clean_text.lower()

    keywords = [keyword for keyword in ELECTRICAL_SCOPE_KEYWORDS if contains_term(lower, keyword)]
    materials = [term for term in MATERIAL_TERMS if contains_term(lower, term)]

    return {
        "keywords": keywords,
        "required_materials": materials,
        "installation_scope": find_sentences(clean_text, INSTALLATION_TERMS),
        "deadlines": extract_deadlines(clean_text),
        "estimated_values_found": extract_money(clean_text),
        "bonding_insurance_requirements": find_sentences(clean_text, BONDING_TERMS, limit=5),
        "submission_instructions": find_sentences(clean_text, SUBMISSION_TERMS, limit=5),
        "source_text_preview": clean_text[:1200],
    }
