"""Tests for Precision Source Coordinate Anchoring (HWPX, XLSX, DOCX, Law/KCSC)"""

import pytest
from samwoo_cm_bridge.core.doc_parser import DocumentParser, get_anchored_chunks
from samwoo_cm_bridge.core.openapi_client import OpenApiClient


def test_hwpx_source_anchoring():
    parser = DocumentParser()
    doc = parser.parse_document("sample_과업지시서_특기시방.hwpx")
    assert doc["status"] == "SUCCESS"
    assert "chunks" in doc
    assert len(doc["chunks"]) > 0

    first_chunk = doc["chunks"][0]
    assert "line_no" in first_chunk
    assert "char_start" in first_chunk
    assert "char_end" in first_chunk
    assert "source_anchor" in first_chunk
    assert "sample_과업지시서_특기시방.hwpx" in first_chunk["source_anchor"]


def test_xlsx_source_anchoring():
    parser = DocumentParser()
    doc = parser.parse_document("sample_가설흙막이_구조계산서.xlsx")
    assert doc["status"] == "SUCCESS"
    assert "chunks" in doc
    assert len(doc["chunks"]) > 0

    first_chunk = doc["chunks"][0]
    assert "table_coord" in first_chunk
    assert "source_anchor" in first_chunk
    assert "!" in first_chunk["source_anchor"]


def test_docx_source_anchoring():
    parser = DocumentParser()
    doc = parser.parse_document("sample_건축_단열및시공계획서.docx")
    assert doc["status"] == "SUCCESS"
    assert "chunks" in doc
    assert len(doc["chunks"]) > 0

    first_chunk = doc["chunks"][0]
    assert "source_anchor" in first_chunk
    assert "sample_건축_단열및시공계획서.docx" in first_chunk["source_anchor"]


def test_openapi_law_kcsc_anchoring():
    client = OpenApiClient()
    law_res = client.fetch_national_law("건설기술 진흥법", "62")
    assert law_res["status"] == "SUCCESS"
    assert "source_anchor" in law_res
    assert "건설기술 진흥법 제62조" in law_res["source_anchor"]

    kcsc_res = client.fetch_kcsc_standard("KDS 21 30 00")
    assert kcsc_res["status"] == "SUCCESS"
    assert "source_anchor" in kcsc_res
    assert "KDS 21 30 00" in kcsc_res["source_anchor"]
