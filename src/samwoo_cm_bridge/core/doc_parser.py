"""Local Multi-Format Document Parser with Secure Sandbox

Parses HWPX (Zip-XML), XLSX (Sheets & Formulas), DOCX, PPTX, PDF, and TXT files
strictly contained within the local 'secure_local_data/' directory.
Prevents directory traversal attacks and extracts structured Markdown + JSON metrics.
"""

import os
import zipfile
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

# Default secure working directory (supports environment variable override)
SECURE_DATA_DIR = Path(
    os.environ.get("SAMWOO_DATA_DIR")
    or os.environ.get("CONSTRUCT_MCP_DATA_DIR")
    or (Path(__file__).resolve().parent.parent.parent.parent / "secure_local_data")
)


class SecurityError(Exception):
    """Raised when an unauthorized path traversal or file access is attempted."""
    pass


class DocumentParser:
    """Secure multi-format document parser."""

    def __init__(self, secure_dir: Optional[Union[str, Path]] = None):
        self.secure_dir = Path(secure_dir).resolve() if secure_dir else SECURE_DATA_DIR.resolve()
        self.secure_dir.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, filename: str) -> Path:
        """Validates that the target file is strictly inside the secure sandbox directory."""
        # Detect explicit directory traversal attempt
        if ".." in filename or filename.startswith("/") or filename.startswith("\\") or (len(filename) > 1 and filename[1] == ":"):
            target_path = (self.secure_dir / filename).resolve()
            if not target_path.is_relative_to(self.secure_dir):
                raise SecurityError(f"Access Denied: Path traversal detected for '{filename}'.")

        target_path = (self.secure_dir / os.path.basename(filename)).resolve()

        if not target_path.is_relative_to(self.secure_dir):
            raise SecurityError(f"Access Denied: Path traversal detected for '{filename}'.")

        if not target_path.exists():
            raise FileNotFoundError(f"File '{filename}' not found in secure storage ({self.secure_dir}).")

        return target_path

    def list_files(self) -> List[Dict[str, Any]]:
        """Lists all files in the secure directory with metadata."""
        file_list = []
        for p in self.secure_dir.glob("*"):
            if p.is_file():
                file_list.append({
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                    "extension": p.suffix.lower(),
                    "last_modified": p.stat().st_mtime,
                })
        return file_list

    def parse_document(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
        """Parses a local project file into structured Markdown and metadata with SHA-256 caching."""
        from .doc_cache_manager import DocumentCacheManager
        cache_mgr = DocumentCacheManager(self.secure_dir)

        if use_cache and cache_mgr.is_cache_valid(filename):
            cached = cache_mgr.get_cached_document(filename)
            if cached:
                cached_data = cached.get("parsed_data", {})
                cached_data["from_cache"] = True
                cached_data["sha256"] = cached.get("sha256")
                return cached_data

        file_path = self._validate_path(filename)
        ext = file_path.suffix.lower()

        if ext == ".hwpx":
            res = self._parse_hwpx(file_path)
        elif ext in [".xlsx", ".xls"]:
            res = self._parse_xlsx(file_path)
        elif ext in [".docx"]:
            res = self._parse_docx(file_path)
        elif ext in [".pptx"]:
            res = self._parse_pptx(file_path)
        elif ext in [".pdf"]:
            res = self._parse_pdf(file_path)
        elif ext in [".txt", ".md", ".json"]:
            res = self._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}' for file '{filename}'.")

        res["from_cache"] = False
        if use_cache:
            cache_mgr.cache_document(filename, res, res.get("markdown"))

        return res

    def parse_file(self, filename: str) -> Dict[str, Any]:
        """Alias for parse_document."""
        return self.parse_document(filename)

    def _parse_hwpx(self, path: Path) -> Dict[str, Any]:
        """Extracts text and tables from HWPX (Hancom Office XML zip package)."""
        paragraphs: List[str] = []
        tables_markdown: List[str] = []
        structured_tables: List[List[List[str]]] = []

        try:
            with zipfile.ZipFile(path, "r") as z:
                # Find all section XML files in Contents/
                section_files = [f for f in z.namelist() if f.startswith("Contents/section") and f.endswith(".xml")]
                if not section_files:
                    # Fallback to any xml in archive
                    section_files = [f for f in z.namelist() if f.endswith(".xml") and "header" not in f]

                for sec_file in sorted(section_files):
                    xml_content = z.read(sec_file)
                    root = ET.fromstring(xml_content)

                    # Extract namespace map if present
                    # Hancom tags: hp:p, hp:run, hp:t, hp:tbl, hp:tr, hp:tc
                    # We use local-name xpath or direct search ignoring namespace
                    for elem in root.iter():
                        tag = elem.tag.split("}")[-1]

                        if tag == "tbl":
                            table_data = self._extract_hwpx_table(elem)
                            if table_data:
                                structured_tables.append(table_data)
                                tables_markdown.append(self._table_to_markdown(table_data))
                        elif tag == "p":
                            p_texts = []
                            for t in elem.iter():
                                if t.tag.split("}")[-1] == "t" and t.text:
                                    p_texts.append(t.text.strip())
                            if p_texts:
                                line = " ".join(p_texts).strip()
                                if line:
                                    paragraphs.append(line)

            # Build anchored chunks
            chunks: List[Dict[str, Any]] = []
            char_offset = 0
            line_counter = 1

            for p_idx, p in enumerate(paragraphs, 1):
                p_len = len(p)
                chunks.append({
                    "chunk_id": f"P-{p_idx:03d}",
                    "source_type": "PARAGRAPH",
                    "line_no": line_counter,
                    "char_start": char_offset,
                    "char_end": char_offset + p_len,
                    "section_title": "본문 단락",
                    "table_coord": None,
                    "text": p,
                    "source_anchor": f"{path.name} L{line_counter} (char {char_offset}-{char_offset + p_len})",
                })
                char_offset += p_len + 2
                line_counter += 1

            for t_idx, t_matrix in enumerate(structured_tables, 1):
                for r_idx, row in enumerate(t_matrix):
                    for c_idx, cell in enumerate(row):
                        if cell.strip():
                            cell_len = len(cell)
                            chunks.append({
                                "chunk_id": f"TBL-{t_idx}-R{r_idx}C{c_idx}",
                                "source_type": "TABLE_CELL",
                                "line_no": line_counter,
                                "char_start": char_offset,
                                "char_end": char_offset + cell_len,
                                "section_title": f"표 {t_idx}",
                                "table_coord": {"table": t_idx, "row": r_idx, "col": c_idx},
                                "text": cell,
                                "source_anchor": f"{path.name} Table {t_idx} [R{r_idx}, C{c_idx}]",
                            })
                            char_offset += cell_len + 1
                    line_counter += 1

            md_content = f"# [HWPX Document] {path.name}\n\n"
            if paragraphs:
                md_content += "## 1. 본문 단락 내용\n" + "\n\n".join(paragraphs) + "\n\n"
            if tables_markdown:
                md_content += "## 2. 문서 내 표 (Tables)\n" + "\n\n".join(tables_markdown)

            return {
                "status": "SUCCESS",
                "filename": path.name,
                "format": "HWPX",
                "markdown": md_content,
                "chunks": chunks,
                "metadata": {
                    "paragraph_count": len(paragraphs),
                    "table_count": len(structured_tables),
                    "tables": structured_tables,
                    "chunk_count": len(chunks),
                }
            }
        except Exception as e:
            logger.error(f"HWPX parse error: {e}")
            raise RuntimeError(f"Failed to parse HWPX file '{path.name}': {str(e)}")

    def _extract_hwpx_table(self, tbl_elem: ET.Element) -> List[List[str]]:
        """Helper to extract a 2D matrix from an HWPX hp:tbl element."""
        matrix: List[List[str]] = []
        for tr in tbl_elem.iter():
            if tr.tag.split("}")[-1] == "tr":
                row_cells = []
                for tc in tr.iter():
                    if tc.tag.split("}")[-1] == "tc":
                        cell_texts = []
                        for t in tc.iter():
                            if t.tag.split("}")[-1] == "t" and t.text:
                                cell_texts.append(t.text.strip())
                        row_cells.append(" ".join(cell_texts) if cell_texts else "")
                if row_cells:
                    matrix.append(row_cells)
        return matrix

    def _parse_xlsx(self, path: Path) -> Dict[str, Any]:
        """Parses Excel workbook sheets, cell values, and structures."""
        import openpyxl

        wb = openpyxl.load_workbook(path, data_only=True)
        sheets_data = {}
        md_sections = [f"# [Excel Calculation Sheet] {path.name}\n"]

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue

            # Filter out completely empty rows
            non_empty_rows = []
            for r in rows:
                if any(c is not None and str(c).strip() != "" for c in r):
                    row_vals = [str(c).strip() if c is not None else "" for c in r]
                    non_empty_rows.append(row_vals)

            if not non_empty_rows:
                continue

            # Normalize column width
            max_cols = max(len(r) for r in non_empty_rows)
            normalized_rows = [r + [""] * (max_cols - len(r)) for r in non_empty_rows]

            sheets_data[sheet_name] = normalized_rows
            md_sections.append(f"## 시트: {sheet_name}")
            md_sections.append(self._table_to_markdown(normalized_rows))
            md_sections.append("\n")

        # Build chunks for XLSX
        chunks: List[Dict[str, Any]] = []
        for s_name, s_rows in sheets_data.items():
            for r_idx, row in enumerate(s_rows, 1):
                row_str = " | ".join(row)
                chunks.append({
                    "chunk_id": f"{s_name}-R{r_idx}",
                    "source_type": "SHEET_ROW",
                    "line_no": r_idx,
                    "section_title": f"시트: {s_name}",
                    "table_coord": {"sheet": s_name, "row": r_idx},
                    "text": row_str,
                    "source_anchor": f"{path.name} [{s_name}!R{r_idx}]",
                })

        return {
            "status": "SUCCESS",
            "filename": path.name,
            "format": "XLSX",
            "markdown": "\n".join(md_sections),
            "chunks": chunks,
            "metadata": {
                "sheets": list(sheets_data.keys()),
                "data": sheets_data,
                "chunk_count": len(chunks),
            }
        }

    def _parse_docx(self, path: Path) -> Dict[str, Any]:
        """Parses Word .docx documents."""
        import docx

        doc = docx.Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        tables_data = []
        tables_md = []

        for table in doc.tables:
            t_rows = []
            for row in table.rows:
                row_cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                t_rows.append(row_cells)
            if t_rows:
                tables_data.append(t_rows)
                tables_md.append(self._table_to_markdown(t_rows))

        md_sections = [f"# [Word Document] {path.name}\n"]
        if paragraphs:
            md_sections.append("## 본문 내용\n" + "\n\n".join(paragraphs))
        if tables_md:
            md_sections.append("## 표 (Tables)\n" + "\n\n".join(tables_md))

        # Build chunks for DOCX
        chunks: List[Dict[str, Any]] = []
        char_offset = 0
        for p_idx, p in enumerate(paragraphs, 1):
            p_len = len(p)
            chunks.append({
                "chunk_id": f"P-{p_idx:03d}",
                "source_type": "PARAGRAPH",
                "line_no": p_idx,
                "char_start": char_offset,
                "char_end": char_offset + p_len,
                "section_title": "본문 단락",
                "table_coord": None,
                "text": p,
                "source_anchor": f"{path.name} L{p_idx} (char {char_offset}-{char_offset + p_len})",
            })
            char_offset += p_len + 2

        for t_idx, t_matrix in enumerate(tables_data, 1):
            for r_idx, row in enumerate(t_matrix):
                for c_idx, cell in enumerate(row):
                    if cell.strip():
                        chunks.append({
                            "chunk_id": f"TBL-{t_idx}-R{r_idx}C{c_idx}",
                            "source_type": "TABLE_CELL",
                            "line_no": p_idx + r_idx,
                            "section_title": f"표 {t_idx}",
                            "table_coord": {"table": t_idx, "row": r_idx, "col": c_idx},
                            "text": cell,
                            "source_anchor": f"{path.name} Table {t_idx} [R{r_idx}, C{c_idx}]",
                        })

        return {
            "status": "SUCCESS",
            "filename": path.name,
            "format": "DOCX",
            "markdown": "\n\n".join(md_sections),
            "chunks": chunks,
            "metadata": {
                "paragraph_count": len(paragraphs),
                "table_count": len(tables_data),
                "tables": tables_data,
                "chunk_count": len(chunks),
            }
        }

    def _parse_pptx(self, path: Path) -> Dict[str, Any]:
        """Parses PowerPoint .pptx slides."""
        from pptx import Presentation

        prs = Presentation(path)
        slide_texts = []

        for idx, slide in enumerate(prs.slides, start=1):
            s_lines = [f"### 슬라이드 {idx}"]
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        txt = paragraph.text.strip()
                        if txt:
                            s_lines.append(f"- {txt}")
                elif shape.has_table:
                    t_rows = []
                    for row in shape.table.rows:
                        row_cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                        t_rows.append(row_cells)
                    if t_rows:
                        s_lines.append(self._table_to_markdown(t_rows))
            slide_texts.append("\n".join(s_lines))

        return {
            "status": "SUCCESS",
            "filename": path.name,
            "format": "PPTX",
            "markdown": f"# [PowerPoint Presentation] {path.name}\n\n" + "\n\n".join(slide_texts),
            "metadata": {"slide_count": len(prs.slides)},
        }

    def _parse_pdf(self, path: Path) -> Dict[str, Any]:
        """Parses PDF pages."""
        from pypdf import PdfReader

        reader = PdfReader(path)
        pages_text = []

        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages_text.append(f"### 페이지 {idx}\n{text.strip()}")

        return {
            "status": "SUCCESS",
            "filename": path.name,
            "format": "PDF",
            "markdown": f"# [PDF Document] {path.name}\n\n" + "\n\n".join(pages_text),
            "metadata": {"page_count": len(reader.pages)},
        }

    def _parse_text(self, path: Path) -> Dict[str, Any]:
        """Parses TXT, CSV, JSON, MD raw texts."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return {
            "status": "SUCCESS",
            "filename": path.name,
            "format": path.suffix.upper().replace(".", ""),
            "markdown": content,
            "metadata": {"length_chars": len(content)},
        }

    def _table_to_markdown(self, rows: List[List[str]]) -> str:
        """Converts a 2D matrix of strings into a standard Markdown table."""
        if not rows:
            return ""

        headers = rows[0]
        # Clean header names
        clean_headers = [h if h else f"Col{i+1}" for i, h in enumerate(headers)]
        separator = ["---"] * len(clean_headers)

        lines = [
            "| " + " | ".join(clean_headers) + " |",
            "| " + " | ".join(separator) + " |",
        ]

        for row in rows[1:]:
            # Ensure row length matches header length
            padded = row + [""] * (len(clean_headers) - len(row))
            clean_row = [c.replace("\n", " ").replace("|", "/") for c in padded[:len(clean_headers)]]
            lines.append("| " + " | ".join(clean_row) + " |")

        return "\n".join(lines)


# Singleton instance
_parser = DocumentParser()


def read_local_project_file(filename: str) -> Dict[str, Any]:
    return _parser.parse_document(filename)


def list_secure_local_files() -> List[Dict[str, Any]]:
    return _parser.list_files()


def get_anchored_chunks(filename: str) -> List[Dict[str, Any]]:
    doc = _parser.parse_document(filename)
    return doc.get("chunks", [])
