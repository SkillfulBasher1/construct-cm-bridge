"""Tests for Document Parser (Module 2)"""

import pytest
from samwoo_cm_bridge.core.doc_parser import (
    DocumentParser,
    read_local_project_file,
    list_secure_local_files,
    SecurityError,
)


def test_list_secure_local_files():
    files = list_secure_local_files()
    assert len(files) >= 5
    filenames = [f["filename"] for f in files]
    assert "sample_과업지시서_특기시방.hwpx" in filenames
    assert "sample_가설흙막이_구조계산서.xlsx" in filenames


def test_parse_hwpx():
    res = read_local_project_file("sample_과업지시서_특기시방.hwpx")
    assert res["status"] == "SUCCESS"
    assert res["format"] == "HWPX"
    assert "특기시방서" in res["markdown"]
    assert "KDS 21 30 00" in res["markdown"]


def test_parse_xlsx():
    res = read_local_project_file("sample_가설흙막이_구조계산서.xlsx")
    assert res["status"] == "SUCCESS"
    assert res["format"] == "XLSX"
    assert "1단 버팀보" in res["markdown"]
    assert "FAIL" in res["markdown"]


def test_parse_docx():
    res = read_local_project_file("sample_건축_단열및시공계획서.docx")
    assert res["status"] == "SUCCESS"
    assert res["format"] == "DOCX"
    assert "단열" in res["markdown"]


def test_path_traversal_security_defense():
    parser = DocumentParser()
    with pytest.raises(SecurityError):
        parser.parse_document("../../../windows/system32/cmd.exe")
