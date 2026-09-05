"""Tests for Field Engineering Modules (OCR, Daily Log, Schedule, TBM, Inspection/NCR)"""

import os
import pytest
from samwoo_cm_bridge.core.ocr_parser import (
    MaterialCertOCRParser,
    parse_scanned_material_cert,
)
from samwoo_cm_bridge.core.daily_log_generator import (
    DailyLogGenerator,
    generate_daily_cm_log,
)
from samwoo_cm_bridge.core.flexible_schedule_analyzer import (
    FlexibleScheduleAnalyzer,
    analyze_custom_schedule,
)
from samwoo_cm_bridge.core.safety_tbm_generator import (
    SafetyTBMGenerator,
    generate_daily_tbm_safety,
)
from samwoo_cm_bridge.core.inspection_ncr_generator import (
    InspectionNCRGenerator,
    generate_inspection_sheet,
    draft_ncr_correction_order,
)


def test_ocr_material_cert():
    res = parse_scanned_material_cert("sample_밀시트_SS275.jpg")
    assert res["status"] == "REVIEW_REQUIRED"
    assert res["certificate_metadata"]["report_no"] is None
    assert res["test_results"] == {}
    assert "REVIEW_REQUIRED" in res["ks_compliance_verdict"]


def test_daily_cm_log_generation():
    res = generate_daily_cm_log(
        date_str="2026.08.29",
        weather="맑음 (기온: 25.0℃)",
        activities=["지하 2층 토사 굴착", "가설 흙막이 지보공 설치"],
    )
    assert res["status"] == "SUCCESS"
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])


def test_flexible_schedule_analyzer():
    res = analyze_custom_schedule("sample_공정표_진도현황.xlsx")
    assert res["status"] == "SUCCESS"
    assert res["total_activities_count"] >= 3
    assert res["delayed_critical_count"] >= 1
    assert "공정만회대책" in res["overall_verdict"] or "REVISE" in res["overall_verdict"]


def test_daily_tbm_safety_generator():
    res = generate_daily_tbm_safety(
        today_tasks_list=["지하 10m 토사 굴착", "가설 비계 설치 및 해체", "50톤 크레인 양중 작업"],
        date_str="2026.08.29",
    )
    assert res["status"] == "SUCCESS"
    assert res["total_risk_factors"] >= 3
    assert res["high_risk_count"] >= 2
    assert os.path.exists(res["docx_path"])


def test_inspection_sheet_generator():
    res = generate_inspection_sheet(
        work_type="가설 흙막이 지보공",
        location="지하 2층 1구역 (X1~X5 열)",
        contractor_spec="H-350x350x12x19 강재",
    )
    assert res["status"] == "SUCCESS"
    assert "REVIEW_REQUIRED" in res["final_verdict"]
    assert os.path.exists(res["docx_path"])


def test_draft_ncr_order():
    res = draft_ncr_correction_order(
        issue_description="1단 버팀보 볼트 조임 토크치 미달 및 일부 접합부 유격 발생",
        location="지하 2층 램프 구간 버팀보 1열",
        defect_category="시공품질 불량",
        photo_attached="현장 토크렌치 실측 사진 첨부",
        corrective_deadline="2026년 09월 05일까지",
    )
    assert res["status"] == "SUCCESS"
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])
