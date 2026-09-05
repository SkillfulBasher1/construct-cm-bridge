"""CM Periodic Report Synthesizer (Module 7 - Periodic Reporter)

Synthesizes project memory, completed technical reviews, pay application audits,
and owner instruction tracking into Samwoo CM standard Weekly / Monthly CM Reports (.docx / .md).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .doc_parser import SECURE_DATA_DIR
from .docx_exporter import DocxExporter
from .project_memory_engine import get_all_project_instructions


class PeriodicReporter:
    """Generates official Samwoo CM Periodic (Weekly/Monthly) Reports."""

    def __init__(self, exporter: Optional[DocxExporter] = None):
        self.exporter = exporter or DocxExporter()

    def generate_weekly_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
    ) -> Dict[str, Any]:
        """Synthesizes weekly report from project memory and recent reviews."""
        now = datetime.now()
        s_date = start_date or now.strftime("%Y.%m.%d")
        e_date = end_date or now.strftime("%Y.%m.%d")
        try:
            start_dt = datetime.strptime(s_date, "%Y.%m.%d")
            end_dt = datetime.strptime(e_date, "%Y.%m.%d")
        except ValueError as e:
            raise ValueError("start_date와 end_date는 YYYY.MM.DD 형식이어야 합니다.") from e
        if start_dt > end_dt:
            raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
        doc_no = f"SWCM-WR-{now.strftime('%Y%m%d')}-01"

        # Fetch instructions and action items from project_memory
        instructions = get_all_project_instructions()

        # Build Markdown content
        md_lines = [
            "# 1. 주간 CM 업무 개요",
            f"- **사업명:** {project_name}",
            f"- **보고 기간:** {s_date} ~ {e_date}",
            f"- **작성자:** {chief_cm_name}",
            "- **금주 주요 공정:** 입력 자료 없음 (현장 실적 입력 필요)\n",
            "# 2. 주요 서류 기술검토 및 3자 교차검증 실적",
            "- 연동된 기술검토 실적 자료가 없습니다. 검토결과를 별도 확인·입력해야 합니다.\n",
            "# 3. 발주처 지시사항 조치 및 이행 현황 관리표",
            "| 문서번호 | 시행일자 | 발신처 | 핵심 지시내용 | 조치 기한 | 이행 상태 |",
            "|---|---|---|---|---|---|",
        ]

        if instructions:
            for inst in instructions:
                status_badge = "**이행 완료 (RESOLVED)**" if inst.get("status") == "RESOLVED" else "**조치 진행중 (PENDING)**"
                md_lines.append(
                    f"| {inst.get('doc_no')} | {inst.get('doc_date')} | {inst.get('issuer')} | {inst.get('subject')} | {inst.get('deadline')} | {status_badge} |"
                )
        else:
            md_lines.append("| - | - | - | 색인된 발주처 지시사항 없음 | - | **입력 필요 (REVIEW_REQUIRED)** |")

        md_lines.extend([
            "\n# 4. 설계변경 및 기성 관리 현황",
            "- 연동된 설계변경·기성 감사 자료 없음 (자료 입력 및 검토 필요).\n",
            "# 5. 차주 주요 감리업무 추진 계획",
            "- 입력된 추진 계획 없음 (책임기술인 확인 후 작성 필요).",
        ])

        report_md = "\n".join(md_lines)
        output_filename = f"주간감리보고서_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=output_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="건설사업관리(CM) 총괄",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "report_type": "WEEKLY_CM_REPORT",
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "doc_no": doc_no,
            "period": f"{s_date} ~ {e_date}",
            "project_name": project_name,
            "evidence_status": "PARTIAL" if instructions else "NO_LINKED_EVIDENCE",
        }


# Singleton instance
_periodic_reporter = PeriodicReporter()


def generate_weekly_cm_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_name: str = "미입력 프로젝트",
    chief_cm_name: str = "미입력 책임기술인",
) -> Dict[str, Any]:
    return _periodic_reporter.generate_weekly_report(start_date, end_date, project_name, chief_cm_name)
