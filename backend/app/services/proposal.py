from collections.abc import Mapping


def generate_proposal_package(opportunity: Mapping) -> dict:
    specs = opportunity.get("extracted_specs") or {}
    title = opportunity.get("title") or "the opportunity"
    agency = opportunity.get("agency") or "the issuing agency"
    project_type = (opportunity.get("project_type") or "general_electrical").replace("_", " ")
    due_date = opportunity.get("due_date") or "the posted due date"
    fit_score = opportunity.get("fit_score")

    materials = specs.get("required_materials") or ["Confirm cable, conduit, equipment, and accessory requirements."]
    scope_items = specs.get("installation_scope") or ["Confirm supply, installation, testing, commissioning, and closeout scope."]
    bonding = specs.get("bonding_insurance_requirements") or ["Verify bid bond, performance bond, payment bond, and insurance requirements."]
    submission = specs.get("submission_instructions") or ["Confirm portal, format, delivery address, and submission deadline."]

    risk_flags = []
    if not opportunity.get("estimated_value"):
        risk_flags.append("Estimated value is missing; validate bonding and pricing exposure before pursuing.")
    if fit_score is not None and fit_score < 60:
        risk_flags.append("Fit score is below target; consider teaming or no-bid review.")
    if opportunity.get("value_confidence") in {"unknown", "likely"}:
        risk_flags.append("Estimated value needs validation before committing bid resources.")
    if opportunity.get("bid_status") != "open":
        risk_flags.append("Opportunity is not marked open; confirm bidding status before outreach.")
    if not specs.get("deadlines"):
        risk_flags.append("Intermediate deadlines were not extracted; review the full solicitation manually.")
    if not bonding:
        risk_flags.append("Bonding and insurance requirements need manual confirmation.")

    bid_summary = (
        f"{agency} is seeking bids for {title}, classified as {project_type}. "
        f"The response is due by {due_date}. Key extracted keywords include "
        f"{', '.join(specs.get('keywords', []) or ['general electrical scope'])}."
    )

    return {
        "bid_summary": bid_summary,
        "scope_checklist": [
            f"Review and price material requirement: {item}." for item in materials[:8]
        ]
        + [f"Validate field scope: {item}" for item in scope_items[:5]],
        "missing_information_checklist": [
            "Confirm final drawings, one-line diagrams, cable schedules, and addenda.",
            "Confirm site access, outage windows, phasing, and owner-furnished equipment.",
            "Confirm liquidated damages, warranty terms, wage rules, and permitting responsibilities.",
        ],
        "required_documents_checklist": [
            "Completed bid form and pricing schedule.",
            "Bid bond and bonding letter.",
            "Certificate of insurance and safety record.",
            "Relevant project references and resumes.",
            "Manufacturer cut sheets or material compliance documentation.",
        ],
        "risk_flags": risk_flags,
        "draft_executive_summary": (
            f"Our team understands that {agency} requires a responsive electrical infrastructure partner for {title}. "
            "We will combine compliant material sourcing, experienced field execution, disciplined safety practices, "
            "and schedule-focused project management to deliver the work with minimal operational disruption."
        ),
        "partner_email_template": (
            "Subject: Partner review requested - "
            f"{title}\n\n"
            "Hi team,\n\n"
            f"We are reviewing {title} for {agency}. The opportunity appears to involve {project_type} work and is due {due_date}. "
            "Please review the attached scope, confirm whether your team can support pricing, labor, schedule, and any specialty equipment, "
            "and send exclusions or clarifications we should include in the proposal.\n\n"
            "Thanks,"
        ),
    }
