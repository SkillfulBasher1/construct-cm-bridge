"""Daily CM Supervision Log Generator (Module 12 - Daily Log Generator)

Generates official Samwoo CM Daily Supervision Log (.docx / .md):
- Weather & temperature records
- Daily contractor work activities by discipline
- CM inspection & QA/QC patrol records
- Manpower & heavy equipment deployment tally
- Key CM instructions & tomorrow's plan
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from .doc_parser import SECURE_DATA_DIR
from .docx_exporter import DocxExporter, set_cell_background, set_cell_margins


class DailyLogGenerator:
    """Generates official Samwoo CM Daily Supervision Work Log."""

    def __init__(self, exporter: Optional[DocxExporter] = None):
        self.exporter = exporter or DocxExporter()
        self.output_dir = SECURE_DATA_DIR

    def generate_daily_log(
        self,
        date_str: Optional[str] = None,
        weather: str = "맑음 (기온: 24.5℃, 강수량: 0mm)",
        activities: Optional[List[str]] = None,
        inspections: Optional[List[Dict[str, str]]] = None,
        workers_count: Optional[Dict[str, int]] = None,
        equipment_count: Optional[Dict[str, int]] = None,
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
    ) -> Dict[str, Any]:
        """Generates standard Daily CM Log in DOCX and Markdown."""
        now = datetime.now()
        cur_date = date_str or now.strftime("%Y.%m.%d")
        clean_date_tag = cur_date.replace(".", "").replace("-", "").replace(" ", "")
        doc_no = f"SWCM-DL-{clean_date_tag}-01"

        # Default sample data if not provided
        acts = activities or [
            "지하 2층 1구역 토사 굴착 및 반출 (백호 0.8m³ 2대, 덤프 15t 8대)",
            "지하 2층 가설 흙막이 1단 버팀보(H-350x350) 설치 및 프리스트레스 긴장 작업",
            "지하 1층 코어부 벽체 철근 배근 및 스페이서 설치",
            "레미콘 타설용 펌프카 셋업 및 현장 품질시험 준비",
        ]

        insps = inspections or [
            {"time": "10:30", "item": "지하 2층 1단 버팀보 설치 검측", "result": "적합 (PASS)", "remark": "H-350 규격 및 볼트 조임 토크 확인"},
            {"time": "14:00", "item": "지하 1층 벽체 철근 배근 검측", "result": "조건부 적합", "remark": "피복두께 미달 부위 스페이서 추가 설치 지시"},
            {"time": "16:30", "item": "일일 안전 TBM 순찰 및 계측기 확인", "result": "양호", "remark": "경사계 변위 정상 범위 (1/1200)"},
        ]

        workers = workers_count or {
            "보통인부": 8, "형틀목공": 12, "철근공": 10, "비계공": 4, "용접공": 2, "장비운전원": 6
        }
        total_workers = sum(workers.values())

        equip = equipment_count or {
            "백호 (0.8m³)": 2, "덤프트럭 (15t)": 8, "크레인 (50t)": 1, "펌프카 (36m)": 1
        }
        total_equip = sum(equip.values())

        # Build Markdown content
        md_lines = [
            f"# [일일 감리업무일보] {cur_date}",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **기상상태:** {weather}",
            f"- **작 성 자:** {chief_cm_name} (총괄감리원)\n",
            f"# 1. 금일 시공사 주요 작업사항",
        ]
        for a in acts:
            md_lines.append(f"- {a}")

        md_lines.extend([
            f"\n# 2. 감리단 검측 및 품질/안전 점검 실적",
            f"| 점검시간 | 점검/검측 대상 항목 | 판정 결과 | 비고 및 감리 조치사항 |",
            f"|---|---|---|---|",
        ])
        for insp in insps:
            md_lines.append(f"| {insp.get('time', '-')} | {insp.get('item', '')} | **{insp.get('result', 'PASS')}** | {insp.get('remark', '')} |")

        md_lines.extend([
            f"\n# 3. 금일 현장 투입 인원 및 장비 집계",
            f"- **총 투입 인원:** **{total_workers}명** ({', '.join([f'{k} {v}명' for k, v in workers.items()])})",
            f"- **총 투입 장비:** **{total_equip}대** ({', '.join([f'{k} {v}대' for k, v in equip.items()])})\n",
            f"# 4. 주요 감리 지시사항 및 명일 계획",
            f"1. 지하 2층 2구역 굴착 시 과굴착 금지 및 안전관리계획 절차 엄수",
            f"2. 익일 오전 09:00 레미콘 타설 전 슬럼프/공기량/염화물 전수 입회검사 실시 예정",
            f"3. 인접 도로변 경사계 데이터 일일 보고서 제출 확인",
        ])

        report_md = "\n".join(md_lines)
        docx_filename = f"감리업무일보_{clean_date_tag}.docx"
        md_filename = f"감리업무일보_{clean_date_tag}.md"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="건설사업관리(CM) 일일업무",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "doc_no": doc_no,
            "date": cur_date,
            "weather": weather,
            "total_workers": total_workers,
            "total_equipment": total_equip,
            "inspection_count": len(insps),
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
        }


# Singleton instance
_daily_log_gen = DailyLogGenerator()


def generate_daily_cm_log(
    date_str: Optional[str] = None,
    weather: str = "맑음 (기온: 24.5℃, 강수량: 0mm)",
    activities: Optional[List[str]] = None,
    inspections: Optional[List[Dict[str, str]]] = None,
    workers_count: Optional[Dict[str, int]] = None,
    equipment_count: Optional[Dict[str, int]] = None,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
) -> Dict[str, Any]:
    return _daily_log_gen.generate_daily_log(
        date_str=date_str,
        weather=weather,
        activities=activities,
        inspections=inspections,
        workers_count=workers_count,
        equipment_count=equipment_count,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
    )
