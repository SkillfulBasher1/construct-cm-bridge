"""Tests for Owner Specification Requirement Auditor (Module 17)"""

import os
import pytest
from samwoo_cm_bridge.core.custom_requirement_auditor import (
    CustomRequirementAuditor,
    audit_custom_spec_requirements,
)


def test_audit_spec_requirements():
    res = audit_custom_spec_requirements("sample_과업지시서_특기시방.hwpx")
    assert res["status"] == "SUCCESS"
    assert res["total_requirements"] >= 3
    assert res["received_count"] >= 1
    assert "requirements_matrix" in res
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])

    # Verify source anchors are populated
    for r in res["requirements_matrix"]:
        assert "source_anchor" in r
        assert len(r["source_anchor"]) > 0
