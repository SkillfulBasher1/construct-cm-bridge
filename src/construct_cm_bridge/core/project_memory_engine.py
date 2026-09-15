"""Local Project Memory and Directive Tracking Engine (Module 6 - Memory)

Persists and indexes:
- Owner official directives, meeting minutes, and design change notices (HWPX/DOCX/PDF)
- Extracts: [문서번호, 발행일자, 발신처, 수신처, 핵심 지시내용, 변경수치, 적용기한, 관련공종, 조치상태]
- Stores into lightweight local SQLite database (`secure_local_data/project_memory.db`)
- Provides natural language semantic search and action-item status tracking.
"""

import os
import re
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .doc_parser import DocumentParser, SECURE_DATA_DIR

logger = logging.getLogger(__name__)

DB_PATH = SECURE_DATA_DIR / "project_memory.db"


class ProjectMemoryEngine:
    """Manages project context memory, directives, and action items in SQLite."""

    def __init__(self, db_path: Optional[Path] = None, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()
        self.db_path = Path(db_path).resolve() if db_path else self.parser.secure_dir / "project_memory.db"
        self._init_db()

    def _init_db(self):
        """Initializes database schema if not present."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_instructions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    doc_no TEXT,
                    doc_date TEXT,
                    issuer TEXT,
                    recipient TEXT,
                    subject TEXT,
                    summary TEXT,
                    discipline TEXT,
                    deadline TEXT,
                    status TEXT DEFAULT 'PENDING',
                    raw_text TEXT,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instruction_id INTEGER,
                    item_title TEXT,
                    target_spec TEXT,
                    contractor_action TEXT,
                    status TEXT DEFAULT 'PENDING',
                    resolved_date TEXT,
                    FOREIGN KEY (instruction_id) REFERENCES project_instructions(id)
                )
            """)
            conn.commit()

    def index_document(self, filename: str) -> Dict[str, Any]:
        """Parses an official letter / directive document and indexes it into project memory."""
        parsed = self.parser.parse_document(filename)
        text = parsed.get("markdown", "")

        # 1. Extract metadata via regex
        doc_no_m = re.search(r'(?:문서번호|문서\s*No|번호)\s*[:=~]?\s*([A-Za-z0-9-_]+)', text)
        doc_no = doc_no_m.group(1).strip() if doc_no_m else "미확인"

        date_m = re.search(r'(?:시행일자|발행일자|일자|Date)\s*[:=~]?\s*([0-9]{4}[.-][0-9]{1,2}[.-][0-9]{1,2})', text)
        doc_date = date_m.group(1).strip() if date_m else "미확인"

        issuer_m = re.search(r'(?:발신|발신처|시행청|발주처)\s*[:=~]?\s*([^\n|]+)', text)
        issuer = issuer_m.group(1).strip() if issuer_m else "미확인"

        recipient_m = re.search(r'(?:수신|수신처)\s*[:=~]?\s*([^\n|]+)', text)
        recipient = recipient_m.group(1).strip() if recipient_m else "미확인"

        subject_m = re.search(r'(?:제목|건명|Subject)\s*[:=~]?\s*([^\n|]+)', text)
        subject = subject_m.group(1).strip() if subject_m else parsed.get("filename", "")

        deadline_m = re.search(r'(?:조치기한|적용기한|제출기한|기한)\s*[:=~]?\s*([0-9]{4}[.-년 ]*[0-9]{1,2}[.-월 ]*[0-9]{1,2}[일]?)', text)
        deadline = deadline_m.group(1).strip() if deadline_m else "미확인"

        # Determine discipline
        discipline = "토목/가설" if any(k in text for k in ["토목", "흙막이", "버팀보", "굴착", "앵커"]) else (
            "골조/구조" if any(k in text for k in ["콘크리트", "철근", "거푸집", "골조"]) else (
                "기계/소방" if any(k in text for k in ["소화", "소방", "펌프", "배관", "설비"]) else (
                    "전기/통신" if any(k in text for k in ["전기", "변압기", "전압", "간선"]) else "일반/공통"
                )
            )
        )

        # Generate summary
        summary_lines = []
        for line in text.splitlines():
            line_str = line.strip()
            if any(k in line_str for k in ["지시", "요청", "변경", "상향", "강화", "조치", "확보"]):
                if len(line_str) > 10 and not line_str.startswith("#"):
                    summary_lines.append(line_str)
        summary = " / ".join(summary_lines[:3]) if summary_lines else subject

        # Store in SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO project_instructions
                (filename, doc_no, doc_date, issuer, recipient, subject, summary, discipline, deadline, status, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                ON CONFLICT(filename) DO UPDATE SET
                    doc_no = excluded.doc_no,
                    doc_date = excluded.doc_date,
                    issuer = excluded.issuer,
                    recipient = excluded.recipient,
                    subject = excluded.subject,
                    summary = excluded.summary,
                    discipline = excluded.discipline,
                    deadline = excluded.deadline,
                    status = 'PENDING',
                    raw_text = excluded.raw_text,
                    indexed_at = CURRENT_TIMESTAMP
            """, (filename, doc_no, doc_date, issuer, recipient, subject, summary, discipline, deadline, text))
            cursor.execute("SELECT id FROM project_instructions WHERE filename = ?", (filename,))
            inst_id = cursor.fetchone()[0]

            # Extract specific action items (from table or bullet points)
            cursor.execute("DELETE FROM action_items WHERE instruction_id = ?", (inst_id,))
            for line in text.splitlines():
                if "단면 증대" in line or "규격 상향" in line or "계측" in line:
                    cursor.execute("""
                        INSERT INTO action_items (instruction_id, item_title, target_spec, status)
                        VALUES (?, ?, ?, 'PENDING')
                    """, (inst_id, line[:50], line[:100]))

            conn.commit()

        return {
            "status": "SUCCESS",
            "message": f"성공적으로 프로젝트 메모리에 인덱싱되었습니다: {doc_no}",
            "indexed_data": {
                "filename": filename,
                "doc_no": doc_no,
                "doc_date": doc_date,
                "issuer": issuer,
                "subject": subject,
                "summary": summary,
                "discipline": discipline,
                "deadline": deadline,
                "status": "PENDING (조치 대기)",
            }
        }

    def search_memory(self, query: str, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """Searches past instructions, meeting minutes, and project directives using token matching."""
        if not isinstance(query, str) or not query.strip():
            return {
                "status": "ERROR",
                "query": query,
                "total_found": 0,
                "results": [],
                "error": "검색어는 비어 있을 수 없습니다.",
            }
        tokens = [t.strip() for t in query.strip().split() if len(t.strip()) >= 2]
        if not tokens:
            tokens = [query.strip()]

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Match any or all tokens with weighted relevance
            cursor.execute("""
                SELECT id, filename, doc_no, doc_date, issuer, recipient, subject, summary, discipline, deadline, status, raw_text
                FROM project_instructions
            """)
            rows = cursor.fetchall()

            results = []
            for r in rows:
                searchable_text = f"{r['doc_no']} {r['subject']} {r['summary']} {r['raw_text']} {r['discipline']} {r['issuer']}".lower()

                matched_tokens = [t for t in tokens if t.lower() in searchable_text]
                if matched_tokens:
                    score = len(matched_tokens) / len(tokens) * 100.0

                    if status_filter and r["status"] != status_filter:
                        continue

                    results.append({
                        "score": round(score, 1),
                        "id": r["id"],
                        "filename": r["filename"],
                        "doc_no": r["doc_no"],
                        "doc_date": r["doc_date"],
                        "issuer": r["issuer"],
                        "subject": r["subject"],
                        "summary": r["summary"],
                        "discipline": r["discipline"],
                        "deadline": r["deadline"],
                        "status": r["status"],
                        "matched_tokens": matched_tokens,
                    })

            # Sort by score descending
            results.sort(key=lambda x: x["score"], reverse=True)

        return {
            "status": "SUCCESS",
            "query": query,
            "total_found": len(results),
            "results": results,
        }

    def get_action_items_status(self) -> List[Dict[str, Any]]:
        """Retrieves all pending and resolved action items for periodic report synthesis."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.doc_no, p.doc_date, p.issuer, p.subject, p.deadline, p.status, p.summary
                FROM project_instructions p
                ORDER BY p.doc_date DESC
            """)
            return [dict(r) for r in cursor.fetchall()]


# Singleton instance
_memory_engine = ProjectMemoryEngine()


def index_project_instruction(filename: str) -> Dict[str, Any]:
    return _memory_engine.index_document(filename)


def search_project_memory(query: str, status_filter: Optional[str] = None) -> Dict[str, Any]:
    return _memory_engine.search_memory(query, status_filter)


def get_all_project_instructions() -> List[Dict[str, Any]]:
    return _memory_engine.get_action_items_status()
