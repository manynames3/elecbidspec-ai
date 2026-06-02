from app.services.extraction import extract_specs


def test_extract_specs_finds_electrical_scope_and_requirements():
    text = """
    Contractor shall furnish medium voltage underground cable, conduit, transformers, and fiber.
    Scope includes trenching, pulling cable, terminations, testing, and commissioning by 07/15/2026.
    A bid bond, performance bond, and insurance certificate are required. Submit via portal.
    """

    specs = extract_specs(text)

    assert "underground cable" in specs["keywords"]
    assert "medium voltage" in specs["keywords"]
    assert "conduit" in specs["required_materials"]
    assert specs["bonding_insurance_requirements"]
    assert specs["submission_instructions"]


def test_extract_specs_finds_ai_data_center_power_terms():
    specs = extract_specs(
        "AI infrastructure data center requires UPS, busduct, switchgear, GPU compute campus feeders, "
        "and utility interconnection work."
    )

    assert "ai infrastructure" in specs["keywords"]
    assert "data center" in specs["keywords"]
    assert "ups" in specs["required_materials"]
    assert "busduct" in specs["required_materials"]


def test_extract_specs_does_not_treat_delivery_ups_as_power_equipment():
    specs = extract_specs("Bid packages may be sent by FedEx, UPS, USPS, or hand delivery.")

    assert "ups" not in specs["required_materials"]


def test_extract_specs_does_not_treat_hpc_concrete_as_compute():
    specs = extract_specs("Relevant bid items: CL C CONC (CAP)(HPC), CONDT PVC conduit, and illumination fixtures.")

    assert "hpc" not in specs["keywords"]
