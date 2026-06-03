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

PROJECT_STAGE_QUERY_MAP = {
    "early signal": "early_signal",
    "early signals": "early_signal",
    "capital plan": "early_signal",
    "capital project": "early_signal",
    "capital projects": "early_signal",
    "puc": "early_signal",
    "rate case": "early_signal",
    "docket": "early_signal",
    "regulatory filing": "early_signal",
    "transmission plan": "early_signal",
    "transmission planning": "early_signal",
    "interconnection queue": "early_signal",
    "large load": "early_signal",
    "zoning": "early_signal",
    "permitting": "early_signal",
    "before rfp": "early_signal",
    "before bidding": "early_signal",
    "long before bidding": "early_signal",
    "ahead of bidding": "early_signal",
    "future project": "early_signal",
    "future projects": "early_signal",
    "upcoming project": "early_signal",
    "upcoming projects": "early_signal",
    "planning signal": "early_signal",
    "planning signals": "early_signal",
    "pre rfp": "pre_rfp",
    "pre-rfp": "pre_rfp",
    "pre solicitation": "pre_rfp",
    "pre-solicitation": "pre_rfp",
    "sources sought": "pre_rfp",
    "prequalification": "pre_rfp",
    "approved vendor list": "pre_rfp",
    "avl": "pre_rfp",
    "posted bid": "active_bid",
    "active bid": "active_bid",
    "active bids": "active_bid",
    "open bid": "active_bid",
    "open bids": "active_bid",
    "rfp": "active_bid",
    "solicitation": "active_bid",
    "awarded": "awarded",
    "award": "awarded",
}

OWNER_QUERY_MAP = {
    "investor-owned": "investor_owned_utility",
    "investor owned": "investor_owned_utility",
    "iou": "investor_owned_utility",
    "private utility": "investor_owned_utility",
    "private investor owned utility": "investor_owned_utility",
    "dominion": "investor_owned_utility",
    "duke energy": "investor_owned_utility",
    "aep": "investor_owned_utility",
    "xcel": "investor_owned_utility",
    "pg&e": "investor_owned_utility",
    "pge": "investor_owned_utility",
    "southern california edison": "investor_owned_utility",
    "sce": "investor_owned_utility",
    "oncor": "investor_owned_utility",
    "centerpoint": "investor_owned_utility",
    "nextera": "investor_owned_utility",
    "fpl": "investor_owned_utility",
    "public agency": "public_agency",
    "public utility": "public_power_or_utility",
    "public power": "public_power_or_utility",
    "private developer": "private_developer",
    "data center developer": "private_developer",
}

STATE_QUERY_MAP = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}


def contains_term(text: str, term: str) -> bool:
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


def parse_due_before(query: str) -> date | None:
    next_days_match = re.search(r"next\s+(\d+)\s+days", query.lower())
    return date.today() + timedelta(days=int(next_days_match.group(1))) if next_days_match else None


def parse_state_filter(query: str) -> str | None:
    lower_query = query.lower()
    for state_name, abbreviation in STATE_QUERY_MAP.items():
        if re.search(rf"\b{re.escape(state_name)}\b", lower_query):
            return abbreviation

    abbreviation_match = re.search(
        r"\b(?:in|for|near|within|across)\s+([A-Z]{2})\b|\b([A-Z]{2})\s+(?:bids|opportunities|projects|rfps)\b",
        query,
    )
    if abbreviation_match:
        abbreviation = (abbreviation_match.group(1) or abbreviation_match.group(2) or "").upper()
        if abbreviation in set(STATE_QUERY_MAP.values()):
            return abbreviation
    return None


def parse_project_stage(query: str) -> str | None:
    lower_query = query.lower()
    for phrase, stage in PROJECT_STAGE_QUERY_MAP.items():
        if re.search(rf"\b{re.escape(phrase)}\b", lower_query):
            return stage
    return None


def parse_owner_type(query: str) -> str | None:
    lower_query = query.lower()
    for phrase, owner_type in OWNER_QUERY_MAP.items():
        if re.search(rf"\b{re.escape(phrase)}\b", lower_query):
            return owner_type
    return None


def search_opportunities(query: str, opportunities: Iterable[Mapping]) -> list[dict]:
    lower_query = query.lower()
    desired_project_type = next((ptype for phrase, ptype in PROJECT_QUERY_MAP.items() if phrase in lower_query), None)
    desired_state = parse_state_filter(query)
    desired_project_stage = parse_project_stage(query)
    desired_owner_type = parse_owner_type(query)
    value_threshold = parse_value_threshold(query)
    due_before = parse_due_before(query)
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
                str(opp.get("project_stage") or ""),
                str(opp.get("signal_type") or ""),
                str(opp.get("owner_type") or ""),
                str(opp.get("forecast_rfp_date") or ""),
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

        if desired_project_stage and opp.get("project_stage") == desired_project_stage:
            score += 26
            reasons.append(f"Stage matches {desired_project_stage.replace('_', ' ')}.")
        elif desired_project_stage:
            score -= 10

        if desired_owner_type and opp.get("owner_type") == desired_owner_type:
            score += 24
            reasons.append(f"Owner type matches {desired_owner_type.replace('_', ' ')}.")
        elif desired_owner_type:
            score -= 10

        if due_before and opp.get("due_date") and opp["due_date"] <= due_before:
            score += 20
            reasons.append(f"Due by {due_before.isoformat()}.")
        elif due_before:
            score -= 10

        if desired_state and str(opp.get("state") or "").upper() == desired_state:
            score += 20
            reasons.append(f"Located in {desired_state}.")
        elif desired_state:
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

        ai_relevance_confirmed = False
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
                    ai_relevance_confirmed = True
                    score += min(30, 10 + len(ai_matches) * 4)
                    reasons.append(f"AI/data center infrastructure indicators: {', '.join(ai_matches[:5])}.")
                elif len(support_matches) >= 2:
                    ai_relevance_confirmed = True
                    score += min(14, len(support_matches) * 4)
                    reasons.append(f"Power-infrastructure support terms: {', '.join(support_matches[:5])}.")
        if wants_ai_infra and opp.get("project_type") != "data_center_power" and not ai_relevance_confirmed:
            continue

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
