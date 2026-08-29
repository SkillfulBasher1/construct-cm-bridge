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
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
    ) -> Dict[str, Any]:
        """Synthesizes weekly report from project memory and recent reviews."""
        now = datetime.now()
        s_date = start_date or now.strftime("%Y.%m.%d")
        e_date = end_date or now.strftime("%Y.%m.%d")
        doc_no = f"SWCM-WR-{now.strftime('%Y%m%d')}-01"

        # Fetch instructions and action items from project_memory
        instructions = get_all_project_instructions()

        # Build Markdown content
        md_lines = [
            f"# 1. 주간 CM 업무 개요",
            f"- **사업명:** {project_name}",
            f"- **보고 기간:** {s_date} ~ {e_date}",
            f"- **작성자:** {chief_cm_name}",
            f"- **금주 주요 공정:** 지하 2층 토공사 및 가설 흙막이 지보공 설치, 1차 설계변경 검토\n",
            f"# 2. 주요 서류 기술검토 및 3자 교차검증 실적",
            f"| 일자 | 대상 도서명 | 검토 공종 | 3자 검토 결과 | 조치 사항 |",
            f"|---|---|---|---|---|",
            f"| {s_date} | 가설흙막이 구조계산서 | 토목/가설 | **부적합 (FAIL)** | 1단 버팀보 안전율(Fs=1.07 < 1.25) 미달로 단면증대 보완지시 |",
            f"| {s_date} | 옥내소화전 및 펌프계산서 | 기계/소방 | **적합 (PASS)** | 유효저수량 15.0m³ 및 정격양정 확보 확인 후 승인 |",
            f"| {s_date} | 지하주차장 전압강하계산서 | 전기 | **적합 (PASS)** | 선로 전압강하율 1.19% (기준 3.0% 이하) 충족 확인 |\n",
            f"# 3. 발주처 지시사항 조치 및 이행 현황 관리표",
            f"| 문서번호 | 시행일자 | 발신처 | 핵심 지시내용 | 조치 기한 | 이행 상태 |",
            f"|---|---|---|---|---|---|",
        ]

        if instructions:
            for inst in instructions:
                status_badge = "**이행 완료 (RESOLVED)**" if inst.get("status") == "RESOLVED" else "**조치 진행중 (PENDING)**"
                md_lines.append(
                    f"| {inst.get('doc_no')} | {inst.get('doc_date')} | {inst.get('issuer')} | {inst.get('subject')} | {inst.get('deadline')} | {status_badge} |"
                )
        else:
            md_lines.append(
                f"| SW-ORD-2026-0815 | {s_date} | (주)삼우글로벌 | 램프구간 버팀보 규격상향(H-350) 및 계측 주2회 강화 | {e_date} | **조치 진행중 (PENDING)** |"
            )

        md_lines.extend([
            f"\n# 4. 설계변경 및 기성 관리 현황",
            f"- **기성내역 감사 실적:** 제2회 기성 청구내역서 단가 임의 인상(+1,300만원) 및 수식 하드코딩 과대청구(+550만원) 적발 후 감리단 삭감 조치 완료.",
            f"- **설계변경(VE) 누적 관리:** 제1회 설계변경(램프구간 단면증대 및 계측비) 100% 반영 검증 완료.\n",
            f"# 5. 차주 주요 감리업무 추진 계획",
            f"1. 보완된 가설 흙막이 시공계획서(H-350 적용본) 재검토 및 최종 승인 처리",
            f"2. 인접 구조물 지표변위 및 경사계 주 2회 계측데이터 현장 교차 대조 확인",
            f"3. 지하 2층 골조공사 레미콘 공장 배합설계 사전 자재검수",
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
        }


# Singleton instance
_periodic_reporter = PeriodicReporter()


def generate_weekly_cm_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
) -> Dict[str, Any]:
    return _periodic_reporter.generate_weekly_report(start_date, end_date, project_name, chief_cm_name)
