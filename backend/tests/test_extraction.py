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

