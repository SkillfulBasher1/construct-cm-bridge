"""Tests for End-to-End Comprehensive Review Pipeline"""

import os
import pytest
from samwoo_cm_bridge.core.comprehensive_review_pipeline import (
    ComprehensiveReviewPipeline,
    run_comprehensive_review,
)


def test_run_comprehensive_review_end_to_end():
    pipeline = ComprehensiveReviewPipeline()
    res = pipeline.run_auto_review(
        target_plan_file="sample_과업지시서_특기시방.hwpx",
        calc_file="sample_가설흙막이_구조계산서.xlsx",
        output_report_name="테스트_종합_CM기술검토의견서.docx",
    )

    assert res["status"] == "SUCCESS"
    assert "cross_comparison_table" in res
    assert len(res["cross_comparison_table"]) >= 3
    assert len(res["referenced_laws_and_standards"]) >= 1
    assert os.path.exists(res["generated_docx_file"])
    assert os.path.exists(res["generated_md_file"])


def test_run_comprehensive_review_helper():
    res = run_comprehensive_review(
        target_plan_file="sample_건축_단열및시공계획서.docx",
        spec_file="sample_과업지시서_특기시방.hwpx",
        output_report_name="테스트_건축_종합검토의견서.docx",
    )
    assert res["status"] == "SUCCESS"
    assert res["pipeline"] == "ComprehensiveReviewPipeline"
    assert os.path.exists(res["generated_docx_file"])
