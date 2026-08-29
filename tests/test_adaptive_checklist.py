"""Tests for Adaptive Checklist Generator and Plan Evaluator"""

import pytest
from samwoo_cm_bridge.core.adaptive_checklist_engine import (
    AdaptiveChecklistEngine,
    generate_and_evaluate_checklist,
)


def test_generate_dynamic_checklist_with_site_conditions():
    engine = AdaptiveChecklistEngine()
    checklist = engine.generate_checklist(
        work_type="토공/가설",
        site_conditions="도심지 인접, 지하수위, 동절기",
    )

    assert len(checklist) >= 10
    items_text = " ".join([c["item"] for c in checklist])
    assert "도심지" in items_text
    assert "지하수" in items_text
    assert "동절기" in items_text


def test_evaluate_plan_against_checklist():
    res = generate_and_evaluate_checklist(
        work_type="토공/가설",
        site_conditions="도심지",
        spec_file="sample_과업지시서_특기시방.hwpx",
        plan_file="sample_건축_단열및시공계획서.docx",
    )

    assert res["status"] == "SUCCESS"
    assert res["total_items"] > 0
    assert "checklist_results" in res
    assert 0 <= res["compliance_score_pct"] <= 100
