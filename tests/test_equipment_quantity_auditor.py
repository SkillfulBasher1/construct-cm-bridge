"""Tests for Equipment Quantity & Calculation-BOQ-Drawing 3-Way Auditor (Module 18)"""

import os
import pytest
from samwoo_cm_bridge.core.equipment_quantity_auditor import (
    EquipmentQuantityAuditor,
    audit_calculation_quantity_drawing_match,
)


def test_extract_pdf_equipment_tables():
    auditor = EquipmentQuantityAuditor()
    items = auditor.extract_pdf_equipment_tables("sample_소방_장비일람표_도면.pdf")
    assert len(items) >= 3
    assert any("주펌프" in item["equipment_name"] for item in items)
    assert any("충압펌프" in item["equipment_name"] for item in items)
    assert "source_anchor" in items[0]


def test_parse_excel_boq_and_detect_errors():
    auditor = EquipmentQuantityAuditor()
    items, errors = auditor.parse_excel_boq_items("sample_소방_수량산출서.xlsx")
    assert len(items) >= 4

    # Detect arithmetic calculation errors and negative value outliers
    assert len(errors) >= 2
    assert any("수식 불일치" in str(e) or "차액" in str(e) or "discrepancy_amount" in e for e in errors)
    assert any("음수" in str(e) or "이상치" in str(e) or "reason" in e for e in errors)


def test_audit_3way_match_end_to_end():
    res = audit_calculation_quantity_drawing_match(
        calc_file="sample_소방_소화수조및펌프계산서.xlsx",
        boq_file="sample_소방_수량산출서.xlsx",
        drawing_pdf_file="sample_소방_장비일람표_도면.pdf",
    )
    assert res["status"] == "SUCCESS"
    assert res["total_equipments_checked"] >= 3
    assert res["discrepancy_count"] >= 1
    assert res["boq_errors_count"] >= 2
    assert "보완 지시" in res["overall_verdict"] or "DISCREPANCY" in res["overall_verdict"]
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])
