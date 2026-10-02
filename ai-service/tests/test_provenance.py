from vedika_ai.provenance import inspect_provenance, inspect_template_text


def checks(metadata):
    return {finding.cek for finding in inspect_provenance(metadata)}


def test_image_editor_metadata_is_supporting_edit_evidence():
    assert checks({"Creator": "Adobe Photoshop 25.0"}) == {"suntingan"}
    assert checks({"Creator": "GIMP 2.10"}) == {"suntingan"}


def test_canva_metadata_is_design_provenance_evidence():
    assert checks({"Producer": "Canva", "Creator": "Canva"}) == {"tanda_ai"}


def test_scanner_camera_and_acrobat_metadata_are_not_flagged():
    assert checks({"Creator": "Canon iR-ADV C3826"}) == set()
    assert checks({"Creator": "Galaxy A15 Kamera"}) == set()
    assert checks({"Producer": "Adobe Acrobat Pro (64-bit) 24.2"}) == set()


def test_static_template_text_mismatch_is_weak_supporting_evidence():
    finding = inspect_template_text(
        "RS MELATI SEHAT Jl. Kenagna Rya No. 41",
        0.64,
        "melati-v1",
    )

    assert len(finding) == 1
    assert finding[0].cek == "tanda_ai"
    assert finding[0].kekuatan == "lemah"


def test_static_template_text_accepts_match_and_ignores_uncertain_ocr():
    assert (
        inspect_template_text(
            "RS MELATI SEHAT Jl. Kenanga Raya No. 41",
            0.6,
            "melati-v1",
        )
        == []
    )
    assert inspect_template_text("teks tidak terbaca", 0.2, "melati-v1") == []
