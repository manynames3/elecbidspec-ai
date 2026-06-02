from __future__ import annotations

from collections.abc import Mapping
import re


CLASSIFICATION_KEYWORDS = {
    "data_center_power": [
        "data center",
        "hyperscale",
        "colocation",
        "server",
        "server farm",
        "compute campus",
        "ai infrastructure",
        "artificial intelligence",
        "hpc",
        "high performance computing",
        "gpu",
        "gpu cluster",
        "ups",
        "uninterruptible power supply",
        "generator",
        "switchgear",
        "critical power",
        "pdu",
        "power distribution unit",
        "busduct",
        "busway",
        "utility interconnection",
        "campus power",
    ],
    "utility_replacement": [
        "utility",
        "replacement",
        "grid",
        "feeder",
        "reconduct",
        "storm hardening",
        "distribution",
    ],
    "fire_damage_rebuild": ["fire damage", "wildfire", "burned", "rebuild", "emergency repair", "restoration"],
    "underground_installation": ["underground", "trenching", "duct bank", "conduit", "directional drill", "manhole"],
    "pole_overhead_installation": ["overhead", "pole", "aerial", "crossarm", "pole line", "recloser"],
    "substation_related": ["substation", "transformer", "switchyard", "breaker", "relay", "bus work"],
}

DATA_CENTER_STRONG_TERMS = {
    "data center",
    "hyperscale",
    "colocation",
    "server farm",
    "compute campus",
    "ai infrastructure",
    "artificial intelligence",
    "hpc",
    "high performance computing",
    "gpu",
    "gpu cluster",
    "critical power",
    "utility interconnection",
    "campus power",
}


def _contains_term(text: str, term: str) -> bool:
    if term == "hpc":
        return (
            "high performance computing" in text
            or re.search(
                r"\bhpc\b(?=.{0,80}\b(ai|compute|computing|gpu|server|data center|datacenter|hyperscale)\b)|"
                r"\b(ai|compute|computing|gpu|server|data center|datacenter|hyperscale)\b.{0,80}\bhpc\b",
                text,
            )
            is not None
        )
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


def classify_bid(title: str, description: str = "", extracted_specs: Mapping | None = None) -> dict:
    extracted_specs = extracted_specs or {}
    keywords = " ".join(extracted_specs.get("keywords", []))
    materials = " ".join(extracted_specs.get("required_materials", []))
    scope = " ".join(extracted_specs.get("installation_scope", []))
    text = f"{title} {description} {keywords} {materials} {scope}".lower()

    scores: dict[str, int] = {}
    hits_by_type: dict[str, list[str]] = {}
    for project_type, terms in CLASSIFICATION_KEYWORDS.items():
        hits = [term for term in terms if _contains_term(text, term)]
        if project_type == "data_center_power" and hits and not any(hit in DATA_CENTER_STRONG_TERMS for hit in hits):
            hits = []
        hits_by_type[project_type] = hits
        scores[project_type] = len(hits)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    if best_score == 0:
        return {
            "project_type": "general_electrical",
            "confidence_score": 0.45,
            "explanation": "No dominant specialized electrical infrastructure pattern was found, so this is classified as general electrical.",
        }

    total_possible = max(len(CLASSIFICATION_KEYWORDS[best_type]), 1)
    confidence = min(0.95, 0.55 + (best_score / total_possible) * 0.4)
    hits_text = ", ".join(hits_by_type[best_type][:5])
    return {
        "project_type": best_type,
        "confidence_score": round(confidence, 2),
        "explanation": f"Matched {best_type.replace('_', ' ')} indicators: {hits_text}.",
    }
