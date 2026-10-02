from app.worker import _gabungkan_hasil_banding


def test_pair_comparison_adds_duplicate_and_pasted_region_findings():
    findings = []
    comparison = {
        "kemiripan": 0.98,
        "sama": True,
        "kalimat": "Isi berkas 98% sama dengan berkas pembanding.",
        "region_a": [[85, 540, 1070, 782]],
        "region_b": [[85, 540, 1070, 782]],
        "tempelan": [
            {
                "bagian": "ttd-1",
                "region_a": [900, 582, 250, 80],
                "region_b": [900, 582, 250, 80],
                "kemiripan": 0.99,
            }
        ],
    }

    _gabungkan_hasil_banding(findings, comparison, "b_asal")

    assert [finding["cek"] for finding in findings] == ["berkas_kembar", "tempelan"]
    assert all(finding["pasangan"] == "b_asal" for finding in findings)
    assert findings[1]["area"] == [[900, 582, 250, 80]]


def test_pair_comparison_does_not_add_findings_when_documents_differ():
    findings = []

    _gabungkan_hasil_banding(
        findings,
        {"sama": False, "kemiripan": 0.4, "kalimat": "Berbeda."},
        "b_lain",
    )

    assert findings == []
