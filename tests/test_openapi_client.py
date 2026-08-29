"""Tests for OpenAPI Client (Module 1)"""

import pytest
from samwoo_cm_bridge.core.openapi_client import OpenApiClient, fetch_national_law, fetch_kcsc_standard


def test_fetch_national_law_mock_fallback():
    client = OpenApiClient()
    res = client.fetch_national_law("건설기술 진흥법", "62")
    assert res["status"] == "SUCCESS"
    assert "안전관리계획" in res["title"] or "안전관리계획" in res["content"]
    assert "62" in str(res["article_no"])


def test_fetch_national_law_all_articles():
    res = fetch_national_law("건축법")
    assert res["status"] == "SUCCESS"
    assert "건축법" in res["law_name"]


def test_fetch_national_law_not_found():
    res = fetch_national_law("존재하지않는법률명12345")
    assert res["status"] == "NOT_FOUND"


def test_fetch_kcsc_standard_mock_fallback():
    res = fetch_kcsc_standard("KDS 21 30 00")
    assert res["status"] == "SUCCESS"
    assert "가설 흙막이" in res["standard_name"]
    assert "1.25" in res["content"]


def test_fetch_kcsc_standard_not_found():
    res = fetch_kcsc_standard("KDS 99 99 99")
    assert res["status"] == "NOT_FOUND"
