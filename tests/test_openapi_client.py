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


def test_fetch_national_law_rejects_empty_and_missing_article():
    client = OpenApiClient()
    assert client.fetch_national_law("   ")["status"] == "ERROR"
    assert client.fetch_national_law("건설기술 진흥법", "99999")["status"] == "NOT_FOUND"


def test_fetch_kcsc_standard_mock_fallback():
    res = fetch_kcsc_standard("KDS 21 30 00")
    assert res["status"] == "SUCCESS"
    assert "가설 흙막이" in res["standard_name"]
    assert "1.25" in res["content"]


def test_fetch_kcsc_standard_not_found():
    res = fetch_kcsc_standard("KDS 99 99 99")
    assert res["status"] == "NOT_FOUND"


def test_fetch_kcsc_standard_rejects_empty_or_partial_code():
    client = OpenApiClient()
    assert client.fetch_kcsc_standard(" ")["status"] == "ERROR"
    assert client.fetch_kcsc_standard("KDS")["status"] == "NOT_FOUND"


class _FakeResponse:
    def __init__(self, *, content=b"", payload=None):
        self.content = content
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_national_law_live_api_uses_search_then_body_endpoint(monkeypatch, tmp_path):
    search_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <LawSearch><law><법령명한글>건설기술 진흥법</법령명한글>
    <법령일련번호>12345</법령일련번호></law></LawSearch>""".encode()
    body_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <법령><조문><조문단위><조문번호>62</조문번호><조문제목>안전관리계획</조문제목>
    <조문내용>안전관리계획을 수립하여야 한다.</조문내용></조문단위></조문></법령>""".encode()
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        if url.endswith("lawSearch.do"):
            return _FakeResponse(content=search_xml)
        return _FakeResponse(content=body_xml)

    monkeypatch.setattr("requests.get", fake_get)
    client = OpenApiClient(law_oc="tester", cache_dir=tmp_path)
    result = client.fetch_national_law("건설기술 진흥법", "62")

    assert result["status"] == "SUCCESS"
    assert result["source"] == "REAL_OPENAPI"
    assert calls[0][0].endswith("lawSearch.do")
    assert calls[1][0].endswith("lawService.do")
    assert calls[1][1]["MST"] == "12345"
    assert calls[1][1]["JO"] == "006200"


def test_kcsc_live_api_uses_documented_route_and_shape(monkeypatch, tmp_path):
    payload = [
        {
            "codeType": "KDS",
            "code": "213000",
            "name": "가설 흙막이 설계기준",
            "version": "2024",
            "updateDate": "2024-01-01",
            "list": [{"title": "1.1 적용범위", "contents": "<p>기준 본문</p>"}],
        }
    ]
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return _FakeResponse(payload=payload)

    monkeypatch.setattr("requests.get", fake_get)
    client = OpenApiClient(kcsc_key="secret", cache_dir=tmp_path)
    result = client.fetch_kcsc_standard("KDS 21 30 00")

    assert result["status"] == "SUCCESS"
    assert result["source"] == "REAL_KCSC_API"
    assert calls[0][0].endswith("/OpenApi/CodeViewer/KDS/213000")
    assert calls[0][1] == {"key": "secret"}
    assert result["content"] == "### 1.1 적용범위\n기준 본문"
