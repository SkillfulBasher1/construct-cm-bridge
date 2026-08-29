"""Tests for Semantic Standard Searcher Module"""

import pytest
from samwoo_cm_bridge.core.semantic_standard_searcher import (
    SemanticStandardSearcher,
    search_standards_by_keyword,
)


def test_search_standards_strut_safety():
    res = search_standards_by_keyword("버팀보 허용응력 및 안전율")
    assert res["status"] == "SUCCESS"
    assert res["total_matches"] > 0

    top_code = res["top_results"][0]["code"]
    assert "KDS 21 30 00" in top_code or "건설기술 진흥법" in top_code


def test_search_standards_fire_reservoir():
    res = search_standards_by_keyword("소화수조 유효수량 계산")
    assert res["status"] == "SUCCESS"
    top_code = res["top_results"][0]["code"]
    assert "KCS 31 10 00" in top_code or "소방" in top_code


def test_search_standards_voltage_drop():
    res = search_standards_by_keyword("간선 전압강하율")
    assert res["status"] == "SUCCESS"
    top_code = res["top_results"][0]["code"]
    assert "KEC 232" in top_code or "전기" in top_code
