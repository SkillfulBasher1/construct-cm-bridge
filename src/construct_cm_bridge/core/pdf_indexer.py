"""Generic PDF Document Indexing & FTS5 Full-Text Search Engine

Extracts and indexes text content from PDF documents (manuals, guidelines, engineering specs):
- Direct digital text extraction via pypdf / pdfplumber
- Automatic table of contents / outline extraction
- Local SQLite + FTS5 full-text search indexing
- Fast keyword search with rank scoring and page-anchoring
- Neutral, reusable architecture free of proprietary hardcoded data
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("secure_local_data") / "pdf_knowledge.db"


class PdfDocumentIndexer:
    """Generic indexing and full-text search engine for local PDF engineering documents."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path:
            self.db_path = Path(db_path).resolve()
        else:
            self.db_path = Path(os.environ.get("PDF_KNOWLEDGE_DB", DEFAULT_DB_PATH)).resolve()
        self._init_db()

    def _init_db(self):
        """Initializes SQLite schema with FTS5 full-text indexing."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS pdf_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    doc_title TEXT,
                    total_pages INTEGER,
                    char_count INTEGER,
                    file_size INTEGER,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS pdf_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER,
                    filename TEXT,
                    page_no INTEGER,
                    heading TEXT,
                    content TEXT,
                    char_length INTEGER,
                    FOREIGN KEY (doc_id) REFERENCES pdf_documents(id) ON DELETE CASCADE
                )
            """)
            c.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS pdf_fts USING fts5(
                    filename,
                    heading,
                    content,
                    page_no UNINDEXED
                )
            """)
            conn.commit()

    def index_pdf_file(self, pdf_path: str, doc_title: Optional[str] = None) -> Dict[str, Any]:
        """Parses a PDF file and indexes all page text into the SQLite FTS5 database."""
        path = Path(pdf_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"PDF file not found: {path}")

        filename = path.name
        title = doc_title or path.stem
        file_size = path.stat().st_size

        from pypdf import PdfReader
        reader = PdfReader(str(path))
        total_pages = len(reader.pages)

        # Extract bookmarks / outlines if available
        outline_map: Dict[int, str] = {}
        try:
            def extract_outline(items, prefix=""):
                for it in items:
                    if isinstance(it, list):
                        extract_outline(it, prefix + "  ")
                    else:
                        item_title = getattr(it, "title", str(it))
                        try:
                            p_num = reader.get_destination_page_number(it)
                            outline_map[p_num + 1] = item_title
                        except Exception:
                            pass
            if reader.outline:
                extract_outline(reader.outline)
        except Exception:
            pass

        # Extract text per page
        pages_data = []
        total_chars = 0
        current_heading = title

        for idx, page in enumerate(reader.pages):
            p_no = idx + 1
            if p_no in outline_map:
                current_heading = outline_map[p_no]

            text = page.extract_text() or ""
            text_clean = text.strip()
            total_chars += len(text_clean)

            pages_data.append((
                filename,
                p_no,
                current_heading,
                text_clean,
                len(text_clean)
            ))

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO pdf_documents (filename, doc_title, total_pages, char_count, file_size)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(filename) DO UPDATE SET
                    doc_title = excluded.doc_title,
                    total_pages = excluded.total_pages,
                    char_count = excluded.char_count,
                    file_size = excluded.file_size,
                    indexed_at = CURRENT_TIMESTAMP
            """, (filename, title, total_pages, total_chars, file_size))

            c.execute("SELECT id FROM pdf_documents WHERE filename = ?", (filename,))
            doc_id = c.fetchone()[0]

            # Clear old pages for this doc
            c.execute("DELETE FROM pdf_pages WHERE doc_id = ?", (doc_id,))
            c.execute("DELETE FROM pdf_fts WHERE filename = ?", (filename,))

            for f_name, p_no, heading, content, clen in pages_data:
                c.execute("""
                    INSERT INTO pdf_pages (doc_id, filename, page_no, heading, content, char_length)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (doc_id, f_name, p_no, heading, content, clen))

                if content:
                    c.execute("""
                        INSERT INTO pdf_fts (filename, heading, content, page_no)
                        VALUES (?, ?, ?, ?)
                    """, (f_name, heading, content, p_no))

            conn.commit()

        return {
            "status": "SUCCESS",
            "filename": filename,
            "doc_title": title,
            "total_pages": total_pages,
            "total_characters": total_chars,
            "pages_with_text": sum(1 for p in pages_data if p[4] > 0),
            "db_path": str(self.db_path)
        }

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Searches indexed PDF content with FTS5 full-text matching."""
        if not query or not query.strip():
            return []

        clean_q = query.strip()
        results = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # 1. Exact FTS query
            rows = c.execute("""
                SELECT filename, heading, content, page_no, rank
                FROM pdf_fts
                WHERE pdf_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (clean_q, top_k)).fetchall()

            # 2. Wildcard fallback if empty
            if not rows:
                tokens = clean_q.split()
                wildcard_q = " ".join(f"{t}*" for t in tokens)
                rows = c.execute("""
                    SELECT filename, heading, content, page_no, rank
                    FROM pdf_fts
                    WHERE pdf_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (wildcard_q, top_k)).fetchall()

            for r in rows:
                snippet = r["content"][:200].replace("\n", " ") if r["content"] else ""
                results.append({
                    "filename": r["filename"],
                    "heading": r["heading"],
                    "page_no": r["page_no"],
                    "score": round(-float(r["rank"]), 2) if r["rank"] is not None else 0.0,
                    "excerpt": snippet
                })

        return results
