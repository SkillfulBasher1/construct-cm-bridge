"""Tests for Final Practical CM Engineering Tools (Modules 19-22)

1. Concrete Pouring & 28-day Strength Tracker (concrete_qc_tracker.py)
2. NCR Before/After Photo Verification Sheet Builder (ncr_action_sheet_builder.py)
3. Subcontract Appropriateness & Compliance Auditor (subcontract_auditor.py)
4. Comprehensive Final Completion Report Assembler (cm_final_report_assembler.py)
"""

import os
import pytest
from samwoo_cm_bridge.core.concrete_qc_tracker import (
    ConcreteQCTracker,
    register_concrete_pour,
)
from samwoo_cm_bridge.core.ncr_action_sheet_builder import (
    NCRActionSheetBuilder,
    generate_before_after_sheet,
)
from samwoo_cm_bridge.core.subcontract_auditor import (
    SubcontractAuditor,
    audit_subcontract_agreement,
)
from samwoo_cm_bridge.core.cm_final_report_assembler import (
    CMFinalReportAssembler,
    assemble_cm_final_report,
)


def test_concrete_qc_tracker():
    res = register_concrete_pour(
        date_str="2026.08.29",
        location="지하 2층 바닥 슬래브 1구역",
        spec_fck=24.0,
        volume_m3=320.0,
        remicon_spec="25-24-150",
        measured_7d_mpa=18.5,
        measured_28d_mpa=26.2,
    )
    assert res["status"] == "SUCCESS"
    assert "CONC-" in res["pour_no"]
    assert res["spec_fck_mpa"] == 24.0
    assert res["measured_28d_mpa"] == 26.2
    assert "28일 강도 적합" in res["verdict"]
    assert os.path.exists(res["ledger_path"])


def test_ncr_action_sheet_builder():
    res = generate_before_after_sheet(
        issue_title="1단 버팀보 볼트 체결 불량 및 유격 발생",
        before_img="sample_조치전사진.jpg",
        after_img="sample_조치후사진.jpg",
        description="규정 토크치(1200 N.m) 체결 완료 및 KCS 기준 적합 확인",
        location="지하 2층 1구역 (X3~X5 열)",
    )
    assert res["status"] == "SUCCESS"
    assert "SWCM-ACT-" in res["doc_no"]
    assert "REVIEW_REQUIRED" in res["verification_status"]
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])


def test_subcontract_auditor():
    res = audit_subcontract_agreement(
        subcontract_excel_file="sample_하도급내역서.xlsx",
        contractor_name="(주)대우건설",
        subcontractor_name="(주)한국토건",
    )
    assert res["status"] == "SUCCESS"
    assert res["subcontract_ratio_pct"] >= 82.0
    assert "REVIEW_REQUIRED" in res["overall_verdict"]
    assert len(res["review_matrix"]) >= 3
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])


def test_cm_final_report_assembler():
    res = assemble_cm_final_report(
        project_name="한국건설 신축공사 CM현장",
        report_type="준공 감리완료보고서",
    )
    assert res["status"] == "SUCCESS"
    assert res["final_progress_pct"] is None
    assert res["final_verdict"] == "REVIEW_REQUIRED"
    assert res["scanned_artifacts_count"] >= 10
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])
