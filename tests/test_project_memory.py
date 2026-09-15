"""Tests for Project Memory Engine and Design Change Tracker"""

import pytest
from construct_cm_bridge.core.project_memory_engine import (
    ProjectMemoryEngine,
    index_project_instruction,
    search_project_memory,
)
from construct_cm_bridge.core.design_change_tracker import (
    DesignChangeTracker,
    track_design_changes,
)


def test_index_and_search_project_memory():
    # 1. Index sample directive
    res = index_project_instruction("sample_발주처_설계변경지시공문.hwpx")
    assert res["status"] == "SUCCESS"
    assert "SW-ORD-2026-0815" in res["indexed_data"]["doc_no"]
    assert "H-350" in res["indexed_data"]["summary"] or "버팀보" in res["indexed_data"]["summary"]

    # 2. Search project memory by natural language
    search_res = search_project_memory("지하 주차장 램프 구간 버팀보")
    assert search_res["status"] == "SUCCESS"
    assert search_res["total_found"] >= 1
    assert "SW-ORD-2026-0815" in search_res["results"][0]["doc_no"]


def test_track_design_changes():
    res = track_design_changes(
        change_log_file="sample_설계변경_총괄내역서.xlsx",
        target_plan_file="sample_건축_단열및시공계획서.docx",
    )
    assert res["status"] == "SUCCESS"
    assert res["total_change_items"] >= 3
    assert "change_tracking_matrix" in res
