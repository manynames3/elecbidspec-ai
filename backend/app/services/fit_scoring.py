from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal


PROJECT_CAPABILITY_MAP = {
    "data_center_power": ["medium_voltage", "high_voltage", "data_center", "switchgear"],
    "utility_replacement": ["distribution", "medium_voltage", "overhead", "underground"],
    "fire_damage_rebuild": ["emergency_repair", "overhead", "underground"],
    "underground_installation": ["underground", "trenching", "conduit"],
    "pole_overhead_installation": ["overhead", "pole_line"],
    "substation_related": ["substation", "transformer", "high_voltage"],
    "general_electrical": ["medium_voltage", "low_voltage"],
}


def _as_set(values) -> set[str]:
    return {str(value).lower().replace(" ", "_") for value in (values or [])}


def score_fit(opportunity: Mapping, profile: Mapping) -> dict:
    score = 0
    positives: list[str] = []
    negatives: list[str] = []

    state = (opportunity.get("state") or "").upper()
    states_served = {str(item).upper() for item in profile.get("states_served", [])}
    nationwide = bool(states_served & {"ALL", "US", "USA", "NATIONWIDE"})
    if state and (state in states_served or nationwide):
        score += 20
        positives.append(f"Serves project state {state}.")
    elif state:
        negatives.append(f"Project state {state} is outside the served-state profile.")
    else:
        score += 8
        positives.append("State is not specified, so no location penalty was applied.")

    estimated_value = opportunity.get("estimated_value")
    bonding_capacity = profile.get("bonding_capacity")
    if estimated_value and bonding_capacity:
        estimated_decimal = Decimal(str(estimated_value))
        bonding_decimal = Decimal(str(bonding_capacity))
        if estimated_decimal <= bonding_decimal:
            score += 20
            positives.append("Estimated value appears within bonding capacity.")
        elif estimated_decimal <= bonding_decimal * Decimal("1.25"):
            score += 10
            negatives.append("Estimated value is slightly above stated bonding capacity.")
        else:
            negatives.append("Estimated value materially exceeds stated bonding capacity.")
    else:
        score += 8
        negatives.append("Estimated value or bonding capacity is missing.")

    project_type = opportunity.get("project_type", "general_electrical")
    required_caps = set(PROJECT_CAPABILITY_MAP.get(project_type, []))
    company_caps = _as_set(profile.get("installation_capabilities")) | _as_set(profile.get("cable_types_supplied"))
    matched_caps = required_caps & company_caps
    if required_caps:
        capability_score = int((len(matched_caps) / len(required_caps)) * 25)
        score += capability_score
        if matched_caps:
            positives.append(f"Matches capabilities: {', '.join(sorted(matched_caps))}.")
        missing_caps = required_caps - matched_caps
        if missing_caps:
            negatives.append(f"Missing or unstated capabilities: {', '.join(sorted(missing_caps))}.")

    extracted_specs = opportunity.get("extracted_specs") or {}
    keyword_set = _as_set(extracted_specs.get("keywords", []))
    material_set = _as_set(extracted_specs.get("required_materials", []))
    supplied = _as_set(profile.get("cable_types_supplied"))
    if keyword_set & company_caps or material_set & supplied:
        score += 15
        positives.append("Extracted scope and materials overlap with company profile.")
    else:
        negatives.append("No strong material/scope overlap was found in extracted specs.")

    experience = profile.get("experience") or {}
    if experience.get(project_type) or any(experience.get(cap) for cap in matched_caps):
        score += 15
        positives.append("Profile lists relevant project experience.")
    else:
        negatives.append("Relevant experience is not documented in the profile.")

    labor_type = (profile.get("labor_type") or "").lower()
    description = f"{opportunity.get('description') or ''} {opportunity.get('title') or ''}".lower()
    if "union" in description:
        if labor_type == "union":
            score += 5
            positives.append("Labor profile matches union language.")
        elif labor_type:
            negatives.append("Bid references union labor, but the profile is not union.")
    else:
        score += 3

    bounded_score = max(0, min(100, score))
    explanation = " ".join(positives + negatives)
    return {"fit_score": bounded_score, "fit_explanation": explanation}
