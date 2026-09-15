"""Tests for Docx and Markdown Exporter (Module 3)"""

import os
from pathlib import Path
from construct_cm_bridge.core.docx_exporter import export_review_document


def test_export_review_document(tmp_path):
    report_text = """# 1. 검토 개요
- 가설 흙막이 지보공 검토

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 법령 기준 | 발주처 시방 | 시공사 제출 | 판정 |
|---|---|---|---|---|
| 버팀보 안전율 | Fs >= 1.25 | Fs >= 1.25 | Fs = 1.07 | FAIL |

# 3. 종합 의견
- 단면 증대 보완 지시
"""
    res = export_review_document(
        output_filename="test_cm_report.docx",
        report_text=report_text,
        project_name="테스트 신축공사",
        reviewer_name="홍길동 기술인",
        discipline="토목",
    )
    assert res["status"] == "SUCCESS"
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])

    # Clean up test output
    if os.path.exists(res["docx_path"]):
        os.remove(res["docx_path"])
    if os.path.exists(res["md_path"]):
        os.remove(res["md_path"])
