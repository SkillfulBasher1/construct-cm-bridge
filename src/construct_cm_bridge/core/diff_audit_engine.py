"""Document Revision & Pay Application Change Review Engine

Performs:
1. Pay Application (기성내역서 / XLSX) Audit:
   - Cell coordinates, unit price changes, billing amounts, cumulative quantity caps
   - Detection of price/quantity changes and arithmetic discrepancies for human review
2. Document Revision (도서 HWPX/DOCX) Diff:
   - Clause-by-clause similarity comparison
   - Extraction of added, deleted, and modified specifications
   - Automatic risk assessment (e.g. relaxation of safety factors or specs flagged as CRITICAL)
"""

import os
import re
import difflib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import openpyxl

from .doc_parser import DocumentParser, SECURE_DATA_DIR

logger = logging.getLogger(__name__)


class DiffAuditEngine:
    """Audits differences between document revisions and pay application spreadsheets."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()

    def audit_document_diff(
        self,
        base_file: str,
        target_file: str,
        file_category: str = "AUTO",
    ) -> Dict[str, Any]:
        """Audits differences between two files. Auto-detects Excel vs Text/Word/HWPX."""
        base_ext = os.path.splitext(base_file)[1].lower()
        target_ext = os.path.splitext(target_file)[1].lower()

        is_excel = (base_ext in [".xlsx", ".xlsm"]) or (target_ext in [".xlsx", ".xlsm"]) or (file_category.upper() == "EXCEL")

        if is_excel:
            return self.audit_excel_diff(base_file, target_file)
        else:
            return self.audit_text_diff(base_file, target_file)

    def audit_excel_diff(self, base_file: str, target_file: str) -> Dict[str, Any]:
        """Audits two versions of Pay Applications (기성내역서 / 공사비내역서)."""
        base_path = self.parser._validate_path(base_file)
        target_path = self.parser._validate_path(target_file)

        wb_base = openpyxl.load_workbook(base_path, data_only=True)
        wb_target = openpyxl.load_workbook(target_path, data_only=True)

        ws_base = wb_base.active
        ws_target = wb_target.active

        base_rows = list(ws_base.iter_rows(values_only=True))
        target_rows = list(ws_target.iter_rows(values_only=True))

        # Parse tables into structured records
        base_records, base_headers = self._parse_pay_table(base_rows)
        target_records, target_headers = self._parse_pay_table(target_rows)
        if not base_records or not target_records:
            return {
                "status": "ERROR",
                "error": "두 파일 모두에서 검증 가능한 기성 내역 행을 추출해야 합니다.",
            }

        findings: List[Dict[str, Any]] = []
        verified_items: List[Dict[str, Any]] = []

        total_base_claim = sum(r.get("claim_amount", 0) for r in base_records.values())
        total_target_claim = sum(r.get("claim_amount", 0) for r in target_records.values())
        total_recalculated_claim = 0

        # Compare target records against base records
        for key, t_rec in target_records.items():
            item_name = t_rec.get("name", key)
            spec = t_rec.get("spec", "")
            t_price = t_rec.get("unit_price", 0.0)
            t_qty = t_rec.get("claim_qty", 0.0)
            t_claim = t_rec.get("claim_amount", 0.0)
            contract_qty = t_rec.get("contract_qty", 0.0)
            prev_qty = t_rec.get("prev_qty", 0.0)

            # Recalculate the amount represented by the extracted quantity and unit price.
            recalculated_claim = t_price * t_qty
            total_recalculated_claim += recalculated_claim

            if abs(t_claim - recalculated_claim) > 1.0:
                diff_amount = t_claim - recalculated_claim
                findings.append({
                    "category": "수량×단가와 기재금액 불일치",
                    "item": f"{item_name} ({spec})",
                    "severity": "CRITICAL",
                    "description": (
                        f"기재된 청구금액({t_claim:,.0f}원)이 수량({t_qty:,.1f}) x 단가({t_price:,.0f}원) = "
                        f"{recalculated_claim:,.0f}원과 불일치 (차액: {diff_amount:+,.0f}원)"
                    ),
                    "action": f"당회 청구금액과 원 수식을 확인하고 재계산값({recalculated_claim:,.0f}원)과 대조",
                })

            # Check against base record
            if key in base_records:
                b_rec = base_records[key]
                b_price = b_rec.get("unit_price", 0.0)

                if t_price > b_price:
                    findings.append({
                        "category": "기준본 대비 단가 상승 변경",
                        "item": f"{item_name} ({spec})",
                        "severity": "HIGH",
                        "description": f"기준본 단가({b_price:,.0f}원) 대비 대상본 단가({t_price:,.0f}원) 상승 (+{t_price - b_price:,.0f}원/단위)",
                        "action": "설계변경·계약변경 승인 근거와 적용 시점을 확인",
                    })
                elif t_price < b_price:
                    findings.append({
                        "category": "단가 하향 변경",
                        "item": f"{item_name} ({spec})",
                        "severity": "INFO",
                        "description": f"단가 인하 적용 ({b_price:,.0f}원 -> {t_price:,.0f}원)",
                        "action": "단가 변경 사유 확인",
                    })

                cumulative_qty = prev_qty + t_qty
                if contract_qty > 0 and cumulative_qty > contract_qty:
                    excess_qty = cumulative_qty - contract_qty
                    findings.append({
                        "category": "기재 도급수량 초과 후보",
                        "item": f"{item_name} ({spec})",
                        "severity": "HIGH",
                        "description": f"누계 기성수량({cumulative_qty:,.1f})이 도급수량({contract_qty:,.1f}) 초과 (초과량: {excess_qty:,.1f})",
                        "action": "설계변경·물량변경 승인 근거와 누계 산식을 확인",
                    })

                if not findings or not any(f["item"].startswith(item_name) for f in findings):
                    verified_items.append({
                        "item": f"{item_name} ({spec})",
                        "status": "자동 대조상 항목별 변경 미검출 (REVIEW_REQUIRED)",
                        "amount": t_claim,
                    })
            else:
                findings.append({
                    "category": "기준본에 없는 신규 비목 추가",
                    "item": f"{item_name} ({spec})",
                    "severity": "MEDIUM",
                    "description": f"기준본에 존재하지 않는 신규 비목 (기재금액: {t_claim:,.0f}원)",
                    "action": "설계변경·계약변경 승인 여부와 증빙서류 확인",
                })

        # Check for Deleted/Omitted items
        for key, b_rec in base_records.items():
            if key not in target_records:
                findings.append({
                    "category": "기존 비목 누락",
                    "item": f"{b_rec.get('name')} ({b_rec.get('spec')})",
                    "severity": "LOW",
                    "description": f"이전 회차 비목이 당회차 내역서에서 누락됨",
                    "action": "비목 누락 사유 확인",
                })

        # Total amount discrepancy
        amount_difference = total_target_claim - total_base_claim
        audit_discrepancy = total_target_claim - total_recalculated_claim

        has_critical = any(f["severity"] == "CRITICAL" for f in findings)
        verdict = (
            "산술 불일치 수정 및 원본 검토 필요 (REVISE_REQUIRED)"
            if has_critical
            else ("변경·이상 항목 확인 필요 (REVIEW_REQUIRED)" if findings else "자동 대조 범위 내 이상 미검출 (REVIEW_REQUIRED)")
        )

        return {
            "status": "SUCCESS",
            "audit_type": "PAY_APPLICATION_XLSX",
            "base_file": base_file,
            "target_file": target_file,
            "overall_verdict": verdict,
            "total_findings_count": len(findings),
            "critical_count": sum(1 for f in findings if f["severity"] == "CRITICAL"),
            "financial_summary": {
                "base_claim_total": total_base_claim,
                "target_claim_total": total_target_claim,
                "recalculated_true_total": total_recalculated_claim,
                "claimed_increase_vs_base": amount_difference,
                "arithmetic_discrepancy_amount": audit_discrepancy,
                "unauthorized_overbilling_amount": audit_discrepancy,
            },
            "findings": findings,
            "verified_normal_items": verified_items,
        }

    def _parse_pay_table(self, rows: List[Tuple]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """Parses spreadsheet rows into standardized Pay Item records."""
        if not rows:
            return {}, []

        # Find header row
        header_idx = 0
        headers = []
        for idx, row in enumerate(rows):
            row_str = " ".join([str(c) for c in row if c is not None])
            if any(k in row_str for k in ["품명", "공종", "항목", "비목"]) and any(k in row_str for k in ["단가", "수량", "금액"]):
                header_idx = idx
                headers = [str(c).strip() if c is not None else f"col_{j}" for j, c in enumerate(row)]
                break

        if not headers and rows:
            headers = [f"col_{j}" for j in range(len(rows[0]))]

        # Map column positions
        col_map = {
            "name": -1, "spec": -1, "unit": -1, "contract_qty": -1,
            "unit_price": -1, "prev_qty": -1, "claim_qty": -1, "claim_amount": -1
        }

        for idx, h in enumerate(headers):
            h_clean = h.replace(" ", "")
            if any(k in h_clean for k in ["품명", "공종", "항목명", "명칭"]):
                col_map["name"] = idx
            elif any(k in h_clean for k in ["규격", "사양"]):
                col_map["spec"] = idx
            elif any(k in h_clean for k in ["단위"]):
                col_map["unit"] = idx
            elif any(k in h_clean for k in ["도급수량", "총수량", "설계수량"]):
                col_map["contract_qty"] = idx
            elif any(k in h_clean for k in ["단가"]):
                col_map["unit_price"] = idx
            elif any(k in h_clean for k in ["전회기성", "전회수량", "전월수량"]):
                col_map["prev_qty"] = idx
            elif any(k in h_clean for k in ["당회청구수량", "당회수량", "금회수량", "기성수량"]):
                col_map["claim_qty"] = idx
            elif any(k in h_clean for k in ["당회청구금액", "당회금액", "금회금액", "청구금액", "금액"]):
                col_map["claim_amount"] = idx

        records: Dict[str, Dict[str, Any]] = {}

        for row in rows[header_idx + 1:]:
            if not row or all(c is None for c in row):
                continue

            name = str(row[col_map["name"]]).strip() if col_map["name"] != -1 and row[col_map["name"]] is not None else ""
            if not name or name in ["합계", "총계", "소계"]:
                continue

            spec = str(row[col_map["spec"]]).strip() if col_map["spec"] != -1 and row[col_map["spec"]] is not None else ""
            unit = str(row[col_map["unit"]]).strip() if col_map["unit"] != -1 and row[col_map["unit"]] is not None else ""

            def to_num(val):
                if val is None:
                    return 0.0
                if isinstance(val, (int, float)):
                    return float(val)
                clean = re.sub(r'[^0-9.-]', '', str(val))
                try:
                    return float(clean)
                except ValueError:
                    return 0.0

            contract_qty = to_num(row[col_map["contract_qty"]]) if col_map["contract_qty"] != -1 else 0.0
            unit_price = to_num(row[col_map["unit_price"]]) if col_map["unit_price"] != -1 else 0.0
            prev_qty = to_num(row[col_map["prev_qty"]]) if col_map["prev_qty"] != -1 else 0.0
            claim_qty = to_num(row[col_map["claim_qty"]]) if col_map["claim_qty"] != -1 else 0.0
            claim_amount = to_num(row[col_map["claim_amount"]]) if col_map["claim_amount"] != -1 else (unit_price * claim_qty)

            item_key = f"{name}___{spec}"
            records[item_key] = {
                "name": name,
                "spec": spec,
                "unit": unit,
                "contract_qty": contract_qty,
                "unit_price": unit_price,
                "prev_qty": prev_qty,
                "claim_qty": claim_qty,
                "claim_amount": claim_amount,
            }

        return records, headers

    def audit_text_diff(self, base_file: str, target_file: str) -> Dict[str, Any]:
        """Audits revision differences between HWPX, DOCX, or text documents."""
        parsed_base = self.parser.parse_document(base_file)
        parsed_target = self.parser.parse_document(target_file)

        base_text = parsed_base.get("markdown", "")
        target_text = parsed_target.get("markdown", "")

        base_lines = [l.strip() for l in base_text.splitlines() if l.strip()]
        target_lines = [l.strip() for l in target_text.splitlines() if l.strip()]

        matcher = difflib.SequenceMatcher(None, base_lines, target_lines)
        diff_entries: List[Dict[str, Any]] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            elif tag == "replace":
                paired_count = min(i2 - i1, j2 - j1)
                for offset in range(paired_count):
                    b_idx = i1 + offset
                    t_idx = j1 + offset
                    b_line = base_lines[b_idx]
                    t_line = target_lines[t_idx]

                    # Extract numbers to check for specification relaxation
                    b_nums = re.findall(r'([0-9]+\.?[0-9]*)', b_line)
                    t_nums = re.findall(r'([0-9]+\.?[0-9]*)', t_line)

                    # Assess severity
                    severity = "MEDIUM"
                    risk_desc = "단락 내용 수정"

                    if any(k in b_line for k in ["안전율", "Fs", "허용", "강도", "두께"]):
                        severity = "HIGH"
                        risk_desc = "주요 공학적 기준/수치 수정"
                        # If safety factor or requirement was reduced
                        if b_nums and t_nums:
                            try:
                                if float(t_nums[0]) < float(b_nums[0]) and ("안전율" in b_line or "Fs" in b_line or "두께" in b_line):
                                    severity = "CRITICAL"
                                    risk_desc = f"설계 기준 수치 하향 가능성 ({b_nums[0]} -> {t_nums[0]})"
                            except Exception:
                                pass

                    diff_entries.append({
                        "change_type": "MODIFIED",
                        "severity": severity,
                        "description": risk_desc,
                        "base_excerpt": b_line,
                        "target_excerpt": t_line,
                    })
                for b_idx in range(i1 + paired_count, i2):
                    diff_entries.append({
                        "change_type": "DELETED",
                        "severity": "HIGH" if any(k in base_lines[b_idx] for k in ["안전", "시방", "기준", "품질"]) else "MEDIUM",
                        "description": "치환 과정에서 기존 문구 삭제",
                        "base_excerpt": base_lines[b_idx],
                        "target_excerpt": "",
                    })
                for t_idx in range(j1 + paired_count, j2):
                    diff_entries.append({
                        "change_type": "ADDED",
                        "severity": "MEDIUM",
                        "description": "치환 과정에서 신규 문구 추가",
                        "base_excerpt": "",
                        "target_excerpt": target_lines[t_idx],
                    })
            elif tag == "delete":
                for b_idx in range(i1, i2):
                    diff_entries.append({
                        "change_type": "DELETED",
                        "severity": "HIGH" if any(k in base_lines[b_idx] for k in ["안전", "시방", "기준", "품질"]) else "MEDIUM",
                        "description": "기존 시방/관리 기준 삭제",
                        "base_excerpt": base_lines[b_idx],
                        "target_excerpt": "",
                    })
            elif tag == "insert":
                for t_idx in range(j1, j2):
                    diff_entries.append({
                        "change_type": "ADDED",
                        "severity": "MEDIUM",
                        "description": "신규 조항/문구 추가",
                        "base_excerpt": "",
                        "target_excerpt": target_lines[t_idx],
                    })

        has_critical = any(d["severity"] == "CRITICAL" for d in diff_entries)
        verdict = "기준 수치 하향 가능성 검토 필요 (REVISE_REQUIRED)" if has_critical else "문서 변경점 추출 완료 (REVIEW_REQUIRED)"

        return {
            "status": "SUCCESS",
            "audit_type": "DOCUMENT_REVISION_TEXT",
            "base_file": base_file,
            "target_file": target_file,
            "overall_verdict": verdict,
            "total_changes": len(diff_entries),
            "critical_changes": sum(1 for d in diff_entries if d["severity"] == "CRITICAL"),
            "changes": diff_entries,
        }


# Singleton instance
_diff_auditor = DiffAuditEngine()


def audit_document_diff(base_file: str, target_file: str, file_category: str = "AUTO") -> Dict[str, Any]:
    return _diff_auditor.audit_document_diff(base_file, target_file, file_category)
