"""Unit tests for Generic PDF Document Indexer and Search Engine."""

import pytest
import sqlite3
from pathlib import Path
from construct_cm_bridge.core.pdf_indexer import PdfDocumentIndexer
from construct_cm_bridge.core.semantic_standard_searcher import search_standards_by_keyword


def test_pdf_indexer_initialization(tmp_path):
    test_db = tmp_path / "test_knowledge.db"
    indexer = PdfDocumentIndexer(db_path=test_db)
    assert test_db.exists()

    with sqlite3.connect(test_db) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "pdf_documents" in tables
        assert "pdf_pages" in tables
        assert "pdf_fts" in tables


def test_pdf_indexer_search_fallback(tmp_path):
    test_db = tmp_path / "test_knowledge.db"
    indexer = PdfDocumentIndexer(db_path=test_db)

    # Insert test page manually to verify FTS search logic
    with sqlite3.connect(test_db) as conn:
        conn.execute("""
            INSERT INTO pdf_documents (id, filename, doc_title, total_pages, char_count, file_size)
            VALUES (1, 'spec_sample.pdf', '기계설비 시방서', 10, 500, 1024)
        """)
        conn.execute("""
            INSERT INTO pdf_pages (doc_id, filename, page_no, heading, content, char_length)
            VALUES (1, 'spec_sample.pdf', 5, '시스템에어컨 기밀시험', '시스템에어컨 냉매배관 질소 가압 4.15 MPa 기밀시험 기준', 40)
        """)
        conn.execute("""
            INSERT INTO pdf_fts (filename, heading, content, page_no)
            VALUES ('spec_sample.pdf', '시스템에어컨 기밀시험', '시스템에어컨 냉매배관 질소 가압 4.15 MPa 기밀시험 기준', 5)
        """)

    results = indexer.search("시스템에어컨", top_k=2)
    assert len(results) > 0
    assert results[0]["filename"] == "spec_sample.pdf"
    assert results[0]["page_no"] == 5


def test_semantic_standard_searcher_with_generic_pdf():
    # Verify semantic search returns success without relying on hardcoded strings
    res = search_standards_by_keyword("소화수조 유효수량", top_k=2)
    assert res["status"] == "SUCCESS"
    assert len(res["top_results"]) > 0
