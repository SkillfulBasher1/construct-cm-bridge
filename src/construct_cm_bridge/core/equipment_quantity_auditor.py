"""Calculation - Quantity Takeoff (BOQ) - Drawing PDF 3-Way Equipment Outlier & Discrepancy Auditor (Module 18 - Equipment Quantity Auditor)

Extracts equipment schedule tables from PDF drawings (via pdfplumber/PyMuPDF),
cross-checks specs, capacities, and quantities against Calculation sheets (XLSX) and BOQ sheets (XLSX),
detects arithmetic formula errors in BOQ (Quantity * Unit Price != Amount) and calculation outliers (negative numbers),
and generates a comprehensive 3-way discrepancy report with precision source coordinates.
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import openpyxl
import pdfplumber

from .doc_parser import DocumentParser
from .docx_exporter import DocxExporter

logger = logging.getLogger(__name__)


class EquipmentQuantityAuditor:
    """3-Way Equipment & Quantity Discrepancy Auditor."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.secure_dir = self.parser.secure_dir

    def extract_pdf_equipment_tables(self, pdf_file: str) -> List[Dict[str, Any]]:
        """Extracts equipment schedule table items from a PDF drawing."""
        pdf_path = self.parser._validate_path(pdf_file)
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError("도면 입력은 PDF 파일이어야 합니다.")

        items: List[Dict[str, Any]] = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    for t_idx, table in enumerate(tables, 1):
                        if not table or len(table) < 2:
                            continue

                        # Header identification
                        headers = [str(c).replace("\n", " ").strip() if c else "" for c in table[0]]
                        name_col = self._find_col_idx(headers, ["장비명", "EQUIPMENT", "품명", "기기명"])
                        spec_col = self._find_col_idx(headers, ["규격", "SPEC", "사양", "용량"])
                        flow_col = self._find_col_idx(headers, ["토출량", "유량", "Q", "FLOW"])
                        head_col = self._find_col_idx(headers, ["양정", "전양정", "H", "HEAD"])
                        power_col = self._find_col_idx(headers, ["동력", "모터", "KW", "POWER"])
                        qty_col = self._find_col_idx(headers, ["수량", "QTY", "설치수량", "대수"])

                        for r_idx, row in enumerate(table[1:], 2):
                            if not row or not any(row):
                                continue
                            row_clean = [str(c).replace("\n", " ").strip() if c else "" for c in row]

                            eq_name = row_clean[name_col] if name_col is not None and name_col < len(row_clean) else ""
                            if not eq_name and len(row_clean) > 1:
                                eq_name = row_clean[1]  # fallback to col 1

                            if not eq_name or eq_name in ["장비명", "소계", "합계"]:
                                continue

                            spec = row_clean[spec_col] if spec_col is not None and spec_col < len(row_clean) else ""
                            flow = row_clean[flow_col] if flow_col is not None and flow_col < len(row_clean) else ""
                            head = row_clean[head_col] if head_col is not None and head_col < len(row_clean) else ""
                            power = row_clean[power_col] if power_col is not None and power_col < len(row_clean) else ""
                            qty_str = row_clean[qty_col] if qty_col is not None and qty_col < len(row_clean) else "1"

                            qty_match = re.search(r"(\d+)", qty_str)
                            qty = int(qty_match.group(1)) if qty_match else 1

                            full_spec = f"{spec} {flow} {head} {power}".strip()

                            items.append({
                                "equipment_name": eq_name,
                                "raw_spec": full_spec,
                                "flow": flow,
                                "head": head,
                                "power": power,
                                "quantity": qty,
                                "source_anchor": f"{pdf_path.name} [Page {page_idx} Table {t_idx} Row {r_idx}]",
                            })
        except Exception as e:
            logger.error(f"Failed to parse PDF tables from {pdf_file}: {e}")
            raise RuntimeError(f"PDF 장비표 파싱에 실패했습니다: {e}") from e

        if not items:
            raise ValueError(f"'{pdf_file}'에서 검증 가능한 장비 일람표를 추출하지 못했습니다.")

        return items

    def parse_excel_boq_items(self, boq_file: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parses BOQ (수량산출서) Excel lines and audits arithmetic formulas (Qty * UnitPrice == Amount)."""
        boq_path = self.parser._validate_path(boq_file)

        wb = openpyxl.load_workbook(boq_path, data_only=True)
        items: List[Dict[str, Any]] = []
        arithmetic_errors: List[Dict[str, Any]] = []
        outliers: List[Dict[str, Any]] = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))
            if not rows or len(rows) < 2:
                continue

            headers = [str(c).strip() if c else "" for c in rows[0]]
            name_col = self._find_col_idx(headers, ["품명", "공종", "장비명", "내역", "항목"])
            spec_col = self._find_col_idx(headers, ["규격", "사양", "규격 및 사양", "SPEC"])
            qty_col = self._find_col_idx(headers, ["수량", "QTY"])
            price_col = self._find_col_idx(headers, ["단가", "단가(원)", "PRICE"])
            amount_col = self._find_col_idx(headers, ["금액", "금액(원)", "합계", "AMOUNT"])

            for r_idx, row in enumerate(rows[1:], start=2):
                if not row or not any(row):
                    continue

                name = str(row[name_col]).strip() if name_col is not None and name_col < len(row) and row[name_col] is not None else ""
                if not name or name in ["소계", "합계", "순번"]:
                    continue

                spec = str(row[spec_col]).strip() if spec_col is not None and spec_col < len(row) and row[spec_col] is not None else ""
                
                # Qty
                raw_qty = row[qty_col] if qty_col is not None and qty_col < len(row) else 0
                try:
                    qty = float(raw_qty) if raw_qty is not None else 0.0
                except (ValueError, TypeError):
                    qty = 0.0

                # Unit price
                raw_price = row[price_col] if price_col is not None and price_col < len(row) else 0
                try:
                    price = float(raw_price) if raw_price is not None else 0.0
                except (ValueError, TypeError):
                    price = 0.0

                # Stated amount
                raw_amt = row[amount_col] if amount_col is not None and amount_col < len(row) else 0
                try:
                    stated_amount = float(raw_amt) if raw_amt is not None else 0.0
                except (ValueError, TypeError):
                    stated_amount = 0.0

                anchor = f"{boq_path.name} [{sheet_name}!R{r_idx}]"

                # 1. Check for negative or outlier quantities
                if qty < 0:
                    outliers.append({
                        "item_name": name,
                        "abnormal_value": f"수량 {qty} (음수)",
                        "reason": "산출서 내 음수(-) 수량 무단 입력 오류",
                        "source_anchor": anchor,
                    })

                # 2. Check arithmetic: Qty * Price == Stated Amount
                expected_amount = round(qty * price)
                diff = abs(stated_amount - expected_amount)
                if diff > 10.0 and qty > 0 and price > 0:
                    arithmetic_errors.append({
                        "item_name": name,
                        "quantity": qty,
                        "unit_price": price,
                        "stated_amount": stated_amount,
                        "calculated_amount": expected_amount,
                        "discrepancy_amount": stated_amount - expected_amount,
                        "source_anchor": anchor,
                    })

                items.append({
                    "item_name": name,
                    "spec": spec,
                    "quantity": qty,
                    "unit_price": price,
                    "stated_amount": stated_amount,
                    "source_anchor": anchor,
                })

        return items, arithmetic_errors + outliers

    def parse_excel_calculation_items(self, calc_file: str) -> List[Dict[str, Any]]:
        """Parses Calculation Sheet (계산서) and extracts design specs and parameters."""
        calc_path = self.parser._validate_path(calc_file)

        wb = openpyxl.load_workbook(calc_path, data_only=True)
        items: List[Dict[str, Any]] = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                if not row or not any(row):
                    continue
                row_str = " ".join([str(c) for c in row if c is not None])
                
                # Check for capacity, flow, head
                for term in ["토출량", "유효수량", "전양정", "용량", "안전율", "수조"]:
                    if term in row_str:
                        items.append({
                            "keyword": term,
                            "raw_text": row_str,
                            "source_anchor": f"{calc_path.name} [{sheet_name}!R{r_idx}]",
                        })
                        break

        return items

    def audit_3way_match(
        self,
        calc_file: str,
        boq_file: str,
        drawing_pdf_file: str,
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
    ) -> Dict[str, Any]:
        """Cross-audits Calculation Sheet vs BOQ vs Drawing PDF."""
        # 1. Parse all 3 sources
        drawing_items = self.extract_pdf_equipment_tables(drawing_pdf_file)
        boq_items, boq_errors = self.parse_excel_boq_items(boq_file)
        calc_items = self.parse_excel_calculation_items(calc_file)

        # 2. 3-Way Match Matrix
        match_matrix: List[Dict[str, Any]] = []
        discrepancy_count = 0

        for d_eq in drawing_items:
            eq_name = d_eq["equipment_name"]
            d_spec = d_eq["raw_spec"]
            d_qty = d_eq["quantity"]
            d_anchor = d_eq["source_anchor"]

            # Match in BOQ by highest word overlap score
            best_boq = None
            best_b_score = 0
            eq_words = set(w for w in re.findall(r'[가-힣a-zA-Z0-9]+', eq_name) if len(w) > 1)
            for b in boq_items:
                b_words = set(w for w in re.findall(r'[가-힣a-zA-Z0-9]+', b["item_name"]) if len(w) > 1)
                common = len(eq_words & b_words)
                if common > best_b_score:
                    best_b_score = common
                    best_boq = b

            matched_boq = best_boq if best_b_score > 0 else None
            b_spec = matched_boq["spec"] if matched_boq else "산출서 누락"
            b_qty = matched_boq["quantity"] if matched_boq else 0
            b_anchor = matched_boq["source_anchor"] if matched_boq else "-"

            # Match in Calc by highest word overlap score
            best_calc = None
            best_c_score = 0
            for c in calc_items:
                c_words = set(w for w in re.findall(r'[가-힣a-zA-Z0-9]+', c["raw_text"]) if len(w) > 1)
                common = len(eq_words & c_words)
                if common > best_c_score:
                    best_c_score = common
                    best_calc = c

            matched_calc = best_calc if best_c_score > 0 else None
            c_spec = matched_calc["raw_text"] if matched_calc else "계산서 근거 없음"
            c_anchor = matched_calc["source_anchor"] if matched_calc else "-"

            # Verify Spec & Quantity match
            issues = []
            status = "근거 발견 (REVIEW_REQUIRED)"

            if not matched_boq:
                status = "불일치 (DISCREPANCY)"
                issues.append("도면 표기 장비가 산출서에서 누락됨")
            else:
                # Check quantity
                if d_qty != b_qty:
                    status = "불일치 (DISCREPANCY)"
                    issues.append(f"수량 불일치: 도면 {d_qty}대 vs 산출서 {int(b_qty)}대 (과다/과소)")

                # Check spec / flow
                flow_d_match = re.search(r"(\d[\d,]*)\s*(?:L/min|lpm|m3)", d_spec, re.I)
                flow_b_match = re.search(r"(\d[\d,]*)\s*(?:L/min|lpm|m3)", b_spec, re.I)
                if flow_d_match and flow_b_match:
                    f_d = int(flow_d_match.group(1).replace(",", ""))
                    f_b = int(flow_b_match.group(1).replace(",", ""))
                    if f_d != f_b:
                        status = "불일치 (DISCREPANCY)"
                        issues.append(f"용량/토출량 불일치: 도면 {f_d} vs 산출서 {f_b}")

            if not matched_calc:
                status = "불일치 (DISCREPANCY)"
                issues.append("도면 장비에 대응하는 계산서 근거를 확인하지 못함")

            if "DISCREPANCY" in status:
                discrepancy_count += 1

            match_matrix.append({
                "equipment_name": eq_name,
                "drawing_spec_qty": f"{d_spec} ({d_qty}대)",
                "boq_spec_qty": f"{b_spec} ({int(b_qty)}대)" if matched_boq else "누락",
                "calc_ref": c_spec[:30] + "..." if len(c_spec) > 30 else c_spec,
                "status": status,
                "discrepancy_details": "; ".join(issues) if issues else "자동 추출 범위 내 대응 근거 발견, 원본 수동 대조 필요",
                "source_anchors": f"도면: {d_anchor} | 산출서: {b_anchor} | 계산서: {c_anchor}",
            })

        total_issues = discrepancy_count + len(boq_errors)
        overall_verdict = (
            "수치 불일치 및 산출 오류 보완 지시 (DISCREPANCY_DETECTED)"
            if total_issues > 0
            else "자동 추출 범위 내 대응 근거 발견 (REVIEW_REQUIRED)"
        )

        # 3. Generate Word Document (.docx) & Markdown (.md)
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d")
        doc_no = f"SWCM-AUD-MATCH-{now.strftime('%Y%m%d')}-01"

        md_lines = [
            f"# [계산서-수량산출서-도면(PDF) 3자 수치 교차검토 보고서]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **검토 도서:** 계산서({calc_file}), 산출서({boq_file}), 도면PDF({drawing_pdf_file})",
            f"- **점검 일자:** {date_str}",
            f"- **총괄 감리원:** {chief_cm_name}\n",
            f"# 1. 3자 수치 교차 검증 종합 요약",
            f"- **검증 대상 장비:** **{len(drawing_items)}종**",
            f"- **도면 vs 산출서 수치 불일치:** **{discrepancy_count}건**",
            f"- **산출서 수식/단가 산출 오류 및 이상치:** **{len(boq_errors)}건**",
            f"- **최종 종합 판정:** **{overall_verdict}**\n",
            f"# 2. 장비 규격 및 수량 3자 대조표",
            f"| No | 대상 장비명 | 도면 PDF 사양/수량 | 수량산출서(XLSX) 사양/수량 | 계산서 근거 | 일치 여부 | 불일치 상세 및 감리 조치사항 | 출처 좌표 (Source Anchor) |",
            f"|---|---|---|---|---|---|---|---|",
        ]

        for idx, m in enumerate(match_matrix, 1):
            sym = "✖" if "DISCREPANCY" in m["status"] else "⚠️"
            md_lines.append(
                f"| {idx} | {m['equipment_name']} | {m['drawing_spec_qty']} | {m['boq_spec_qty']} | {m['calc_ref']} | {sym} **{m['status']}** | {m['discrepancy_details']} | `{m['source_anchors']}` |"
            )

        if boq_errors:
            md_lines.append(f"\n# 3. 수량산출서 수식 오류 및 비정상 이상치 적발 내역")
            md_lines.append(f"| No | 항목명 | 적발 사유 / 오차 금액 | 정밀 출처 좌표 | 감리 조치 요구 |")
            md_lines.append(f"|---|---|---|---|---|")
            for e_idx, err in enumerate(boq_errors, 1):
                if "discrepancy_amount" in err:
                    reason = f"수식 불일치: {err['quantity']} * {err['unit_price']:,.0f}원 = {err['calculated_amount']:,.0f}원이나 기재금액 {err['stated_amount']:,.0f}원 (차액: {err['discrepancy_amount']:+,.0f}원)"
                else:
                    reason = f"{err['reason']} ({err['abnormal_value']})"
                md_lines.append(
                    f"| {e_idx} | {err['item_name']} | {reason} | `{err['source_anchor']}` | 산출 내역서 수정 및 공사비 재정산 요구 |"
                )

        report_md = "\n".join(md_lines)
        docx_filename = f"수치교차검토의견서_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="기계 / 소방 / 적산",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "overall_verdict": overall_verdict,
            "total_equipments_checked": len(drawing_items),
            "discrepancy_count": discrepancy_count,
            "boq_errors_count": len(boq_errors),
            "3way_match_matrix": match_matrix,
            "boq_errors_list": boq_errors,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
        }

    def _find_col_idx(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        """Finds matching column index in headers with ASCII word boundary safety."""
        for idx, h in enumerate(headers):
            for k in keywords:
                if k.isascii() and len(k) <= 2:
                    pattern = rf"(?:^|[\s\(_/-]){re.escape(k)}(?:$|[\s\)_/-])"
                    if re.search(pattern, h, re.I):
                        return idx
                else:
                    if k.lower() in h.lower():
                        return idx
        return None


# Singleton instance
_auditor = EquipmentQuantityAuditor()


def audit_calculation_quantity_drawing_match(
    calc_file: str,
    boq_file: str,
    drawing_pdf_file: str,
    project_name: str = "미입력 프로젝트",
) -> Dict[str, Any]:
    return _auditor.audit_3way_match(
        calc_file=calc_file,
        boq_file=boq_file,
        drawing_pdf_file=drawing_pdf_file,
        project_name=project_name,
    )
