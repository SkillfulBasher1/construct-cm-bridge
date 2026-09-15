"""Tests for Batch Cross-Checker Module"""

import pytest
from construct_cm_bridge.core.batch_cross_checker import BatchCrossChecker, batch_cross_check_documents


def test_batch_cross_check_bundle():
    checker = BatchCrossChecker()
    files = ["sample_과업지시서_특기시방.hwpx", "sample_가설흙막이_구조계산서.xlsx"]
    res = checker.cross_check_bundle(files)

    assert res["status"] == "SUCCESS"
    assert len(res["inspected_files"]) == 2
    assert "FAIL" in res["overall_verdict"] or res["total_discrepancies"] > 0

    # The sheet's explicit FAIL must be surfaced without assuming a universal threshold.
    categories = [d["category"] for d in res["discrepancies"]]
    assert any("부적합" in cat for cat in categories)


def test_extract_numeric_entities_regex():
    checker = BatchCrossChecker()
    sample_text = """
    가설 흙막이 버팀보 규격은 H-300x300x10x15 및 H-350x350x12x19를 사용한다.
    콘크리트 설계기준강도 fck = 24MPa, 안전율 Fs = 1.25 이상 확보.
    작용응력 163.8 MPa, 허용응력 220.0 MPa.
    계측 주기는 주 2회 실시한다.
    """
    entities = checker._extract_numeric_entities(sample_text, "test_doc")

    assert "H-300X300X10X15" in entities["steel_sections"]
    assert "H-350X350X12X19" in entities["steel_sections"]
    assert 1.25 in entities["safety_factors"]
    assert 24 in entities["concrete_strength"]
    assert "주2회" in entities["monitoring_frequency"]
    assert 163.8 in entities["stresses"]
    assert 220.0 in entities["stresses"]
