"""Tests for Periodic Reporting and Official Notice Drafter"""

import os
import pytest
from samwoo_cm_bridge.core.cm_periodic_reporter import (
    PeriodicReporter,
    generate_weekly_cm_report,
)
from samwoo_cm_bridge.core.official_letter_generator import (
    OfficialLetterGenerator,
    draft_official_notice,
)


def test_generate_weekly_cm_report():
    res = generate_weekly_cm_report(
        start_date="2026.08.15",
        end_date="2026.08.22",
        project_name="한국건설 신축공사 CM현장",
    )
    assert res["status"] == "SUCCESS"
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])


def test_draft_official_notice():
    res = draft_official_notice(
        doc_title="가설 흙막이 시공계획서 검토결과 통보 및 보완 지시의 건",
        recipient="(주)대우건설 현장소장",
        reference="발주처 감독관",
        review_result_file="sample_건축_단열및시공계획서.docx",
    )
    assert res["status"] == "SUCCESS"
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])
