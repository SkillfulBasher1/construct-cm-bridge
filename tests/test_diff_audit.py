"""Tests for Diff and Tampering Audit Engine"""

import pytest
from samwoo_cm_bridge.core.diff_audit_engine import (
    DiffAuditEngine,
    audit_document_diff,
)


def test_audit_excel_pay_application_tampering():
    engine = DiffAuditEngine()
    res = engine.audit_excel_diff(
        base_file="sample_기성내역서_Rev0.xlsx",
        target_file="sample_기성내역서_Rev1.xlsx",
    )

    assert res["status"] == "SUCCESS"
    assert res["audit_type"] == "PAY_APPLICATION_XLSX"
    assert res["critical_count"] >= 2
    assert "REJECT" in res["overall_verdict"] or "FAIL" in res["overall_verdict"]

    categories = [f["category"] for f in res["findings"]]
    assert any("단가 임의 인상" in c for c in categories)
    assert any("과대청구" in c or "수식" in c for c in categories)


def test_audit_text_revision_diff(tmp_path):
    engine = DiffAuditEngine()
    # Test comparing two sample docs or text
    res = engine.audit_text_diff(
        base_file="sample_과업지시서_특기시방.hwpx",
        target_file="sample_과업지시서_특기시방.hwpx",
    )
    assert res["status"] == "SUCCESS"
    assert res["total_changes"] == 0
