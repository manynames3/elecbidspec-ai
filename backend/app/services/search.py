from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, timedelta
import re


PROJECT_QUERY_MAP = {
    "data center": "data_center_power",
    "utility": "utility_replacement",
    "fire": "fire_damage_rebuild",
    "underground": "underground_installation",
    "pole": "pole_overhead_installation",
    "overhead": "pole_overhead_installation",
    "substation": "substation_related",
}


def parse_value_threshold(query: str) -> int | None:
    match = re.search(r"(?:over|above|greater than)\s+\$?(\d+(?:\.\d+)?)\s*(m|million|k|thousand)?", query, re.I)
    if not match:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit in {"m", "million"}:
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

    ranked: list[dict] = []
    query_terms = {term for term in re.findall(r"[a-z0-9]+", lower_query) if len(term) > 2}
    for opp in opportunities:
        reasons: list[str] = []
        score = 0
        haystack = " ".join(
            [
                str(opp.get("title") or ""),
                str(opp.get("description") or ""),
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
        elif value_threshold:
            score -= 10

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

