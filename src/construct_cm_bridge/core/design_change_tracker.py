"""Cumulative Design Change (VE) and Implementation Tracker (Module 6 - Change Tracker)

Tracks:
1. Multi-round design changes (당초, 1차 변경, 2차 변경) from cumulative change logs (XLSX).
2. Cross-verifies whether submitted contractor plans (HWPX/DOCX) faithfully reflect
   all approved design changes without omitting critical structural/cost modifications.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import openpyxl

from .doc_parser import DocumentParser

logger = logging.getLogger(__name__)


class DesignChangeTracker:
    """Tracks cumulative VE / Design Changes and validates implementation in construction plans."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()

    def parse_change_log(self, change_log_file: str) -> List[Dict[str, Any]]:
        """Parses multi-round design change log spreadsheet (XLSX)."""
        path = self.parser._validate_path(change_log_file)
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        # Find header
        header_idx = 0
        for idx, row in enumerate(rows):
            row_str = " ".join([str(c) for c in row if c is not None])
            if "품명" in row_str or "공종" in row_str or "변경" in row_str:
                header_idx = idx
                break

        headers = [str(c).strip() if c is not None else f"col_{j}" for j, c in enumerate(rows[header_idx])]

        items: List[Dict[str, Any]] = []
        for row in rows[header_idx + 1:]:
            if not row or all(c is None for c in row):
                continue

            # Extract fields
            name = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            if not name or name in ["합계", "총계"]:
                continue

            spec = str(row[2]).strip() if len(row) > 2 and row[2] else ""
            unit = str(row[3]).strip() if len(row) > 3 and row[3] else ""

            orig_qty = row[4] if len(row) > 4 else 0
            orig_amt = row[5] if len(row) > 5 else 0

            # 1st and 2nd change quantities and amounts
            rev1_qty = row[6] if len(row) > 6 else 0
            rev1_diff = row[7] if len(row) > 7 else 0

            rev2_qty = row[8] if len(row) > 8 else 0
            rev2_diff = row[9] if len(row) > 9 else 0

            final_amt = row[10] if len(row) > 10 else 0
            reason = str(row[11]).strip() if len(row) > 11 and row[11] else "설계변경"

            items.append({
                "name": name,
                "spec": spec,
                "unit": unit,
                "original_spec": f"{name} ({spec})",
                "latest_approved_spec": spec,
                "original_amount": orig_amt,
                "final_cumulative_amount": final_amt,
                "change_reason": reason,
            })

        return items

    def track_and_verify_plan(
        self,
        change_log_file: str,
        target_plan_file: str,
    ) -> Dict[str, Any]:
        """Cross-checks whether all approved design change items are implemented in the plan."""
        change_items = self.parse_change_log(change_log_file)
        parsed_plan = self.parser.parse_document(target_plan_file)
        plan_text = parsed_plan.get("markdown", "")

        verification_results: List[Dict[str, Any]] = []
        omission_count = 0
        match_count = 0

        for item in change_items:
            name = item["name"]
            spec = item["spec"]
            reason = item["change_reason"]

            # Key terms to look for in plan
            spec_keywords = [w for w in re.findall(r'[a-zA-Z0-9-xX]{3,}|[가-힣]{2,}', f"{name} {spec}") if len(w) >= 2]

            matched = False
            evidence_line = ""

            for line in plan_text.splitlines():
                if any(kw.lower() in line.lower() for kw in spec_keywords[:2]):
                    # Check if spec is specifically mentioned
                    if spec.lower().replace(" ", "") in line.lower().replace(" ", "") or name[:4] in line:
                        matched = True
                        evidence_line = line.strip()[:100]
                        break

            if matched:
                status = "EVIDENCE_FOUND (REVIEW_REQUIRED)"
                match_count += 1
                action = "관련 문구 발견, 승인도서·수치 최종 대조 필요"
            else:
                status = "OMISSION (설계변경 미반영 누락)"
                omission_count += 1
                action = f"승인된 변경 사양({spec})으로 시공계획서 보완 지시"
                evidence_line = "계획서 내 승인된 최신 변경 규격 미기재"

            verification_results.append({
                "item_name": name,
                "approved_change_spec": spec,
                "change_reason": reason,
                "status": status,
                "evidence_in_plan": evidence_line,
                "action_required": action,
            })

        has_omission = omission_count > 0
        if not change_items:
            overall_verdict = "설계변경 항목을 추출하지 못함 (REVIEW_REQUIRED)"
        elif has_omission:
            overall_verdict = "설계변경 사항 누락 보완 지시 (FAIL/REVISE)"
        else:
            overall_verdict = "관련 문구 발견, 도면·수치 최종 대조 필요 (REVIEW_REQUIRED)"

        return {
            "status": "SUCCESS",
            "change_log_file": change_log_file,
            "target_plan_file": target_plan_file,
            "overall_verdict": overall_verdict,
            "total_change_items": len(change_items),
            "matched_count": match_count,
            "omission_count": omission_count,
            "change_tracking_matrix": verification_results,
        }


# Singleton instance
_tracker = DesignChangeTracker()


def track_design_changes(change_log_file: str, target_plan_file: str) -> Dict[str, Any]:
    return _tracker.track_and_verify_plan(change_log_file, target_plan_file)
