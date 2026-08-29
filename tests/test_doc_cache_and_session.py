"""Tests for SHA-256 Content-Hash Caching & Daily Session Memory (Modules 26 & 12)

1. Document SHA-256 Cache Manager (doc_cache_manager.py)
   - Cache hit on unchanged files (0.05s)
   - Cache invalidation on file modification
2. Daily Log Session Append / Merge (daily_log_generator.py)
   - Morning & Afternoon session merging into single daily log (.docx / .md)
"""

import os
import time
import pytest
from pathlib import Path
from samwoo_cm_bridge.core.doc_cache_manager import (
    DocumentCacheManager,
    get_cached_doc_summary,
)
from samwoo_cm_bridge.core.doc_parser import DocumentParser, SECURE_DATA_DIR
from samwoo_cm_bridge.core.daily_log_generator import (
    DailyLogGenerator,
    generate_daily_cm_log,
)


def test_sha256_cache_hit_and_reuse():
    parser = DocumentParser()
    cache_mgr = DocumentCacheManager()
    target_file = "sample_과업지시서_특기시방.hwpx"

    # 1. Clear any prior cache for clean test
    cache_mgr.clear_cache()

    # 2. First Parse (Cold Start)
    res1 = parser.parse_document(target_file, use_cache=True)
    assert res1.get("from_cache") is False
    assert "markdown" in res1
    assert "chunks" in res1

    # Verify registry entry created
    meta = cache_mgr.get_file_metadata(target_file)
    assert meta is not None
    assert len(meta["sha256"]) == 64
    assert cache_mgr.is_cache_valid(target_file) is True

    # 3. Second Parse (Warm Cache Hit)
    res2 = parser.parse_document(target_file, use_cache=True)
    assert res2.get("from_cache") is True
    assert res2.get("sha256") == meta["sha256"]
    assert "markdown" in res2
    assert "chunks" in res2


def test_sha256_cache_invalidation_on_file_change():
    cache_mgr = DocumentCacheManager()
    parser = DocumentParser()

    dummy_filename = "test_cache_dummy.txt"
    dummy_path = SECURE_DATA_DIR / dummy_filename

    # Create dummy file
    with open(dummy_path, "w", encoding="utf-8") as f:
        f.write("Initial version 1.0")

    try:
        # First parse
        res1 = parser.parse_document(dummy_filename, use_cache=True)
        assert res1.get("from_cache") is False

        # Verify cached
        cached = cache_mgr.get_cached_document(dummy_filename)
        assert cached is not None

        # Modify file
        time.sleep(0.01)
        with open(dummy_path, "w", encoding="utf-8") as f:
            f.write("Modified version 2.0 with different content!")

        # Cache should now be invalid
        assert cache_mgr.is_cache_valid(dummy_filename) is False

        # Re-parse should detect modification
        res2 = parser.parse_document(dummy_filename, use_cache=True)
        assert res2.get("from_cache") is False
        assert "Modified version 2.0" in res2.get("markdown", "")

    finally:
        if dummy_path.exists():
            dummy_path.unlink()


def test_daily_log_session_smart_append():
    test_date = "2026.08.30"
    clean_tag = "20260830"
    gen = DailyLogGenerator()

    # Ensure clean session start
    json_path, md_path = gen._get_session_file_paths(clean_tag)
    if json_path.exists():
        json_path.unlink()
    if md_path.exists():
        md_path.unlink()

    # 1. Morning 11:00 AM Input
    morning_acts = [
        "[오전 09:00] 지하 2층 1구역 토사 굴착 120m3 진행",
        "[오전 10:30] 3층 바닥 슬래브 철근 배근 감리원 입회 검측 (합격)",
    ]
    morning_insps = [
        {"time": "10:30", "item": "3층 바닥 슬래브 철근 배근 검측", "result": "적합 (PASS)", "remark": "피복두께 50mm 확인"}
    ]
    morning_workers = {"보통인부": 5, "철근공": 8}

    res_am = generate_daily_cm_log(
        date_str=test_date,
        weather="맑음 (24.0℃)",
        activities=morning_acts,
        inspections=morning_insps,
        workers_count=morning_workers,
        project_name="삼우씨엠 신축공사 CM현장",
    )
    assert res_am["status"] == "SUCCESS"
    assert res_am["session_merged"] is False
    assert res_am["total_activities"] == 2
    assert res_am["inspection_count"] == 1
    assert os.path.exists(res_am["docx_path"])

    # 2. Afternoon 17:00 PM Input (Smart Append)
    afternoon_acts = [
        "[오후 14:00] 3층 바닥 매트 콘크리트 타설 180m3 완료 (레미콘 30대, 펌프카 1대)",
        "[오후 16:30] 당일 TBM 안전순찰 및 계측기 이상유무 확인",
    ]
    afternoon_insps = [
        {"time": "14:00", "item": "3층 콘크리트 타설 전 슬럼프/공기량 시험", "result": "적합 (PASS)", "remark": "슬럼프 150mm, 공기량 4.5%"}
    ]
    afternoon_workers = {"보통인부": 8, "철근공": 8, "타설공": 6}

    res_pm = generate_daily_cm_log(
        date_str=test_date,
        weather="맑음 (최고 28.5℃)",
        activities=afternoon_acts,
        inspections=afternoon_insps,
        workers_count=afternoon_workers,
        project_name="삼우씨엠 신축공사 CM현장",
    )
    assert res_pm["status"] == "SUCCESS"
    assert res_pm["session_merged"] is True
    # 2 morning + 2 afternoon = 4 activities merged into single report!
    assert res_pm["total_activities"] == 4
    assert res_pm["inspection_count"] == 2
    assert res_pm["total_workers"] == (8 + 8 + 6)
    assert os.path.exists(res_pm["docx_path"])
    assert os.path.exists(res_pm["md_path"])

    # Verify Markdown file contains both morning and afternoon items
    with open(res_pm["md_path"], "r", encoding="utf-8") as f:
        md_content = f.read()
        assert "지하 2층 1구역 토사 굴착" in md_content
        assert "3층 바닥 매트 콘크리트 타설" in md_content
        assert "슬럼프/공기량 시험" in md_content
