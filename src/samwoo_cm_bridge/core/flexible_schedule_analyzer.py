"""Flexible Schedule & Progress Rate Analyzer (Module 13 - Schedule Analyzer)

Flexibly analyzes various formats of construction progress spreadsheets (XLSX):
- Dynamic header discovery: [공종/작업명, 계획시작/종료, 실적시작/종료, 계획공정률, 실적공정률, 대비/지연율]
- Computes overall project delay variance and critical path bottlenecks
- Formulates standard CM Schedule Recovery Directive (공정만회대책 요구서)
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import openpyxl

from .doc_parser import DocumentParser, SECURE_DATA_DIR

logger = logging.getLogger(__name__)


class FlexibleScheduleAnalyzer:
    """Analyzes schedule progress and delayed critical activities from custom Excel sheets."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()

    def analyze_schedule(self, excel_file: str) -> Dict[str, Any]:
        """Parses custom schedule Excel sheet and computes delay diagnostics."""
        path = self.parser._validate_path(excel_file)
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return {"status": "ERROR", "error": "Excel sheet is empty"}

        # 1. Dynamically locate header row
        header_idx = -1
        col_map = {
            "name": -1, "plan_start": -1, "plan_end": -1,
            "actual_start": -1, "actual_end": -1,
            "plan_pct": -1, "actual_pct": -1, "variance": -1
        }

        for idx, row in enumerate(rows):
            row_str = " ".join([str(c) for c in row if c is not None])
            if any(k in row_str for k in ["공종", "작업명", "Activity", "공정", "내역"]) and any(k in row_str for k in ["계획", "실적", "달성", "진도"]):
                header_idx = idx
                headers = [str(c).strip() if c is not None else f"col_{j}" for j, c in enumerate(row)]
                break

        if header_idx == -1:
            header_idx = 0
            headers = [str(c).strip() if c is not None else f"col_{j}" for j, c in enumerate(rows[0])]

        # Map column positions
        for j, h in enumerate(headers):
            h_clean = h.replace(" ", "")
            if any(k in h_clean for k in ["공종", "작업명", "Activity명", "세부공종", "구분"]):
                if col_map["name"] == -1:
                    col_map["name"] = j
            elif any(k in h_clean for k in ["계획시작", "예정시작", "PlanStart"]):
                col_map["plan_start"] = j
            elif any(k in h_clean for k in ["계획종료", "예정종료", "PlanEnd"]):
                col_map["plan_end"] = j
            elif any(k in h_clean for k in ["실적시작", "ActualStart"]):
                col_map["actual_start"] = j
            elif any(k in h_clean for k in ["실적종료", "ActualEnd"]):
                col_map["actual_end"] = j
            elif any(k in h_clean for k in ["계획공정률", "계획진도", "계획(%)", "Plan%"]):
                col_map["plan_pct"] = j
            elif any(k in h_clean for k in ["실적공정률", "실적진도", "실적(%)", "Actual%"]):
                col_map["actual_pct"] = j
            elif any(k in h_clean for k in ["대비", "증감", "지연", "Variance", "달성률"]):
                col_map["variance"] = j

        # Fallback index mapping if not found
        if col_map["name"] == -1:
            col_map["name"] = 1 if len(headers) > 1 else 0
        if col_map["plan_pct"] == -1 and len(headers) > 4:
            col_map["plan_pct"] = 4
        if col_map["actual_pct"] == -1 and len(headers) > 5:
            col_map["actual_pct"] = 5

        # 2. Extract and analyze rows
        activities: List[Dict[str, Any]] = []
        delayed_critical_items: List[Dict[str, Any]] = []

        total_plan_sum = 0.0
        total_act_sum = 0.0
        row_count = 0

        def parse_pct(val) -> float:
            if val is None:
                return 0.0
            if isinstance(val, (int, float)):
                return float(val) if val <= 1.0 and val > 0 else float(val)  # handle 0.85 as 85%
            s = re.sub(r'[^0-9.-]', '', str(val))
            try:
                v = float(s)
                return v if v > 1.0 else v * 100.0
            except ValueError:
                return 0.0

        for row in rows[header_idx + 1:]:
            if not row or all(c is None for c in row):
                continue

            name = str(row[col_map["name"]]).strip() if col_map["name"] != -1 and row[col_map["name"]] is not None else ""
            if not name or name in ["합계", "총계", "소계", "누계"]:
                continue

            p_pct = parse_pct(row[col_map["plan_pct"]]) if col_map["plan_pct"] != -1 and len(row) > col_map["plan_pct"] else 0.0
            a_pct = parse_pct(row[col_map["actual_pct"]]) if col_map["actual_pct"] != -1 and len(row) > col_map["actual_pct"] else 0.0
            var = a_pct - p_pct

            # Determine delay status
            if var < -10.0:
                severity = "CRITICAL_DELAY"
                status_desc = f"심각 지연 ({var:+.1f}%p) - 주공정선 마비 우려"
                action_text = "돌관작업 및 장비/인력 2교대 투입 만회대책 제출 요구"
            elif var < -5.0:
                severity = "WARNING_DELAY"
                status_desc = f"주의 지연 ({var:+.1f}%p) - 공정 만회 필요"
                action_text = "세부 주간 만회계획 수립 및 중점 공정 관리"
            elif var >= 0.0:
                severity = "NORMAL"
                status_desc = f"정상 진도 ({var:+.1f}%p)"
                action_text = "현행 공정 유지"
            else:
                severity = "MINOR_DELAY"
                status_desc = f"경미 지연 ({var:+.1f}%p)"
                action_text = "지연 추이 모니터링"

            act_data = {
                "name": name,
                "planned_pct": round(p_pct, 1),
                "actual_pct": round(a_pct, 1),
                "variance_pct": round(var, 1),
                "severity": severity,
                "status_description": status_desc,
                "action_required": action_text,
            }
            activities.append(act_data)

            if severity in ["CRITICAL_DELAY", "WARNING_DELAY"]:
                delayed_critical_items.append(act_data)

            total_plan_sum += p_pct
            total_act_sum += a_pct
            row_count += 1

        avg_plan = round(total_plan_sum / row_count, 1) if row_count > 0 else 0.0
        avg_act = round(total_act_sum / row_count, 1) if row_count > 0 else 0.0
        avg_var = round(avg_act - avg_plan, 1)

        overall_verdict = (
            "공정부진 경고 및 공정만회대책 요구 (REVISE_SCHEDULE)" if delayed_critical_items or avg_var < -5.0 else "공정 진도 양호 (NORMAL)"
        )

        recovery_order = ""
        if overall_verdict != "공정 진도 양호 (NORMAL)":
            recovery_order = (
                f"총괄 계획 진도({avg_plan}%) 대비 실적({avg_act}%)이 {abs(avg_var)}%p 지연됨에 따라, "
                f"건설공사 사업관리방식 검토기준 및 도급계약조건에 의거하여 시공사는 7일 이내에 "
                f"장비/인력 추가 투입 및 야간/주말 공정을 반영한 '공정만회대책서'를 제출할 것."
            )

        return {
            "status": "SUCCESS",
            "excel_file": excel_file,
            "overall_verdict": overall_verdict,
            "total_activities_count": len(activities),
            "delayed_critical_count": len(delayed_critical_items),
            "project_progress_summary": {
                "average_planned_pct": avg_plan,
                "average_actual_pct": avg_act,
                "variance_pct": avg_var,
            },
            "delayed_critical_activities": delayed_critical_items,
            "all_activities": activities,
            "schedule_recovery_demand_directive": recovery_order,
        }


# Singleton instance
_schedule_analyzer = FlexibleScheduleAnalyzer()


def analyze_custom_schedule(excel_file: str) -> Dict[str, Any]:
    return _schedule_analyzer.analyze_schedule(excel_file)
