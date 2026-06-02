from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, timedelta
import re


PROJECT_QUERY_MAP = {
    "data center": "data_center_power",
    "datacenter": "data_center_power",
    "ai infrastructure": "data_center_power",
    "artificial intelligence": "data_center_power",
    "hyperscale": "data_center_power",
    "colocation": "data_center_power",
    "hpc": "data_center_power",
    "gpu": "data_center_power",
    "critical power": "data_center_power",
    "compute campus": "data_center_power",
    "utility": "utility_replacement",
    "fire": "fire_damage_rebuild",
    "underground": "underground_installation",
    "pole": "pole_overhead_installation",
    "overhead": "pole_overhead_installation",
    "substation": "substation_related",
}


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


def parse_value_threshold(query: str) -> int | None:
    match = re.search(
        r"(?:over|above|greater than|at least|minimum|min)\s+(?:minimum\s+)?\$?(\d+(?:\.\d+)?)\s*(m|mil|million|k|thousand)?",
        query,
        re.I,
    )
    if not match:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit in {"m", "mil", "million"}:
        amount *= 1_000_000
    elif unit in {"k", "thousand"}:
        amount *= 1_000
    return int(amount)


def search_opportunities(query: str, opportunities: Iterable[Mapping]) -> list[dict]:
    lower_query = query.lower()
    desired_project_type = next((ptype for phrase, ptype in PROJECT_QUERY_MAP.items() if phrase in lower_query), None)
    value_threshold = parse_value_threshold(query)
    next_days_match = re.search(r"next\s+(\d+)\s+days", lower_query)
    due_before = date.today() + timedelta(days=int(next_days_match.group(1))) if next_days_match else None
    wants_supply_and_install = "supply and installation" in lower_query or "supply and install" in lower_query or "both cable supply and installation" in lower_query
    wants_open = any(term in lower_query for term in ["open", "active", "bidding", "solicitation"])
    wants_public = any(term in lower_query for term in ["public", "publicly notified", "nationwide"])
    wants_ai_infra = any(
        term in lower_query
        for term in [
            "ai infrastructure",
            "artificial intelligence",
            "hyperscale",
            "colocation",
            "data center",
            "datacenter",
            "hpc",
            "gpu",
            "critical power",
            "compute campus",
        ]
    )

    ranked: list[dict] = []
    query_terms = {term for term in re.findall(r"[a-z0-9]+", lower_query) if len(term) > 2}
    for opp in opportunities:
        reasons: list[str] = []
        score = 0
        haystack = " ".join(
            [
                str(opp.get("title") or ""),
                str(opp.get("description") or ""),
                str(opp.get("source_type") or ""),
                str(opp.get("bid_status") or ""),
                str(opp.get("value_confidence") or ""),
                " ".join((opp.get("extracted_specs") or {}).get("keywords", [])),
                " ".join((opp.get("extracted_specs") or {}).get("required_materials", [])),
                str(opp.get("project_type") or ""),
            ]
        ).lower()
        text_matches = query_terms & set(re.findall(r"[a-z0-9]+", haystack))
        if text_matches:
            score += min(25, len(text_matches) * 5)
            reasons.append(f"Text matched: {', '.join(sorted(list(text_matches))[:5])}.")

        if desired_project_type and opp.get("project_type") == desired_project_type:
            score += 30
            reasons.append(f"Project type matches {desired_project_type.replace('_', ' ')}.")
        elif desired_project_type:
            score -= 10

        if due_before and opp.get("due_date") and opp["due_date"] <= due_before:
            score += 20
            reasons.append(f"Due by {due_before.isoformat()}.")
        elif due_before:
            score -= 10

        estimated_value = opp.get("estimated_value")
        if value_threshold and estimated_value and float(estimated_value) >= value_threshold:
            score += 20
            reasons.append(f"Estimated value is at or above ${value_threshold:,.0f}.")
        elif value_threshold and value_threshold <= 5_000_000 and opp.get("minimum_value_match"):
            score += 15
            reasons.append(f"Value is {opp.get('value_confidence')} for the $5M+ target.")
        elif value_threshold:
            score -= 10

        if wants_open and opp.get("bid_status") == "open":
            score += 15
            reasons.append("Bid status is open.")
        elif wants_open:
            score -= 10

        if wants_public and opp.get("source_type") != "manual":
            score += 10
            reasons.append(f"Source is categorized as {opp.get('source_type')}.")

        if wants_ai_infra:
            strong_ai_terms = {
                "ai infrastructure",
                "artificial intelligence",
                "hyperscale",
                "colocation",
                "data center",
                "datacenter",
                "hpc",
                "gpu",
                "critical power",
                "compute campus",
            }
            supporting_power_terms = {
                "ups",
                "switchgear",
                "generator",
                "substation",
                "high voltage",
                "medium voltage",
                "utility interconnection",
            }
            strong_matches = sorted(term for term in strong_ai_terms if contains_term(haystack, term))
            support_matches = sorted(term for term in supporting_power_terms if contains_term(haystack, term))
            ai_matches = strong_matches + support_matches
            if ai_matches:
                if strong_matches:
                    score += min(30, 10 + len(ai_matches) * 4)
                    reasons.append(f"AI/data center infrastructure indicators: {', '.join(ai_matches[:5])}.")
                elif len(support_matches) >= 2:
                    score += min(14, len(support_matches) * 4)
                    reasons.append(f"Power-infrastructure support terms: {', '.join(support_matches[:5])}.")

        specs = opp.get("extracted_specs") or {}
        scope_text = " ".join(specs.get("installation_scope", [])).lower()
        materials_text = " ".join(specs.get("required_materials", [])).lower()
        if wants_supply_and_install and ("install" in scope_text or "installation" in scope_text) and ("cable" in materials_text or "conduit" in materials_text):
            score += 25
            reasons.append("Requires both material supply and installation scope.")
        elif wants_supply_and_install:
            score -= 10

        fit_score = opp.get("fit_score")
        if fit_score:
            score += min(20, int(fit_score) // 5)

        if score > 0:
            ranked.append({"opportunity": opp, "rank_score": score, "search_explanation": " ".join(reasons)})

    return sorted(ranked, key=lambda item: item["rank_score"], reverse=True)
