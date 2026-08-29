"""Daily CM Supervision Log Generator with Session Memory (Module 12)

Generates official Samwoo CM Daily Supervision Log (.docx / .md) with smart daily session appending:
- Maintains a real-time daily session buffer (`secure_local_data/summaries/DAILY_LOG_YYYY-MM-DD.json`)
- If log entries (morning inspection, afternoon concrete pour) are entered multiple times on the same day:
  automatically merges activities, inspections, workers, and equipment without overwriting or duplicating.
- Compiles a unified, single Daily Work Log (.docx) at the end of the day.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from .doc_parser import SECURE_DATA_DIR
from .docx_exporter import DocxExporter, set_cell_background, set_cell_margins

logger = logging.getLogger(__name__)

SUMMARIES_DIR_NAME = "summaries"


class DailyLogGenerator:
    """Generates official Samwoo CM Daily Supervision Work Log with Session Append/Update."""

    def __init__(self, exporter: Optional[DocxExporter] = None, secure_dir: Optional[Union[str, Path]] = None):
        self.secure_dir = Path(secure_dir).resolve() if secure_dir else SECURE_DATA_DIR.resolve()
        self.summaries_dir = self.secure_dir / SUMMARIES_DIR_NAME
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.exporter = exporter or DocxExporter(self.secure_dir)

    def _get_session_file_paths(self, clean_date_tag: str):
        """Returns JSON and MD file paths for today's session buffer."""
        json_path = self.summaries_dir / f"DAILY_LOG_{clean_date_tag}.json"
        md_path = self.summaries_dir / f"DAILY_LOG_{clean_date_tag}.md"
        return json_path, md_path

    def _load_session_buffer(self, clean_date_tag: str) -> Optional[Dict[str, Any]]:
        """Loads existing session buffer for the given date if present."""
        json_path, _ = self._get_session_file_paths(clean_date_tag)
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read daily log session buffer: {e}")
        return None

    def _save_session_buffer(self, clean_date_tag: str, session_data: Dict[str, Any]):
        """Saves session buffer in JSON and MD."""
        json_path, md_path = self._get_session_file_paths(clean_date_tag)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        # Build Markdown summary for the session
        md_lines = [
            f"# [일일 감리업무일보 세션 버퍼] {session_data.get('date')}",
            f"- **문서번호:** {session_data.get('doc_no')}",
            f"- **기상상태:** {session_data.get('weather')}",
            f"- **최종 갱신:** {datetime.now().strftime('%Y.%m.%d %H:%M:%S')}\n",
            f"## 1. 금일 시공사 주요 작업내용 ({len(session_data.get('activities', []))}건)",
        ]
        for a in session_data.get("activities", []):
            md_lines.append(f"- {a}")

        md_lines.append(f"\n## 2. 감리단 검측 및 품질/안전 실적 ({len(session_data.get('inspections', []))}건)")
        for insp in session_data.get("inspections", []):
            md_lines.append(f"- [{insp.get('time', '-')}] {insp.get('item', '')} ➔ **{insp.get('result', 'PASS')}** ({insp.get('remark', '')})")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

    def generate_daily_log(
        self,
        date_str: Optional[str] = None,
        weather: str = "맑음 (기온: 24.5℃, 강수량: 0mm)",
        activities: Optional[List[str]] = None,
        inspections: Optional[List[Dict[str, str]]] = None,
        workers_count: Optional[Dict[str, int]] = None,
        equipment_count: Optional[Dict[str, int]] = None,
        key_directives: Optional[List[str]] = None,
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
        force_overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Generates or appends to standard Daily CM Log in DOCX and Markdown."""
        now = datetime.now()
        cur_date = date_str or now.strftime("%Y.%m.%d")
        clean_date_tag = cur_date.replace(".", "").replace("-", "").replace(" ", "")
        doc_no = f"SWCM-DL-{clean_date_tag}-01"

        # Check existing session buffer
        existing_session = self._load_session_buffer(clean_date_tag) if not force_overwrite else None
        session_merged = False

        if existing_session:
            # 1. Merge Activities
            merged_acts = list(existing_session.get("activities", []))
            if activities:
                for act in activities:
                    if act not in merged_acts:
                        merged_acts.append(act)

            # 2. Merge Inspections
            merged_insps = list(existing_session.get("inspections", []))
            if inspections:
                for insp in inspections:
                    if insp not in merged_insps:
                        merged_insps.append(insp)

            # 3. Merge Workers Count
            merged_workers = dict(existing_session.get("workers", {}))
            if workers_count:
                merged_workers.update(workers_count)

            # 4. Merge Equipment Count
            merged_equip = dict(existing_session.get("equipment", {}))
            if equipment_count:
                merged_equip.update(equipment_count)

            # 5. Merge Directives
            merged_directives = list(existing_session.get("directives", []))
            if key_directives:
                for d in key_directives:
                    if d not in merged_directives:
                        merged_directives.append(d)

            # 6. Update Weather if non-default provided
            merged_weather = weather if "맑음 (기온: 24.5℃, 강수량: 0mm)" != weather else existing_session.get("weather", weather)

            acts = merged_acts
            insps = merged_insps
            workers = merged_workers
            equip = merged_equip
            directives = merged_directives
            weather = merged_weather
            session_merged = True
        else:
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
            equip = equipment_count or {
                "백호 (0.8m³)": 2, "덤프트럭 (15t)": 8, "크레인 (50t)": 1, "펌프카 (36m)": 1
            }
            directives = key_directives or [
                "지하 2층 2구역 굴착 시 과굴착 금지 및 안전관리계획 절차 엄수",
                "익일 오전 09:00 레미콘 타설 전 슬럼프/공기량/염화물 전수 입회검사 실시 예정",
                "인접 도로변 경사계 데이터 일일 보고서 제출 확인",
            ]

        total_workers = sum(workers.values())
        total_equip = sum(equip.values())

        # Save merged session state
        session_data = {
            "doc_no": doc_no,
            "date": cur_date,
            "weather": weather,
            "project_name": project_name,
            "chief_cm_name": chief_cm_name,
            "activities": acts,
            "inspections": insps,
            "workers": workers,
            "equipment": equip,
            "directives": directives,
            "updated_at": now.isoformat(),
        }
        self._save_session_buffer(clean_date_tag, session_data)

        # Build Markdown content
        md_lines = [
            f"# [일일 감리업무일보] {cur_date}",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **기상상태:** {weather}",
            f"- **작 성 자:** {chief_cm_name} (총괄감리원)",
            f"- **누적 상태:** {'[오전/오후 일괄 병합 완료]' if session_merged else '[신규 작성]'}\n",
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
        ])
        for idx, d in enumerate(directives, 1):
            md_lines.append(f"{idx}. {d}")

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
            "session_merged": session_merged,
            "doc_no": doc_no,
            "date": cur_date,
            "weather": weather,
            "total_activities": len(acts),
            "total_workers": total_workers,
            "total_equipment": total_equip,
            "inspection_count": len(insps),
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "session_buffer_path": str(self.summaries_dir / f"DAILY_LOG_{clean_date_tag}.json"),
            "source_anchor": f"{docx_filename} [일일감리업무일보 본문]",
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
    key_directives: Optional[List[str]] = None,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
    force_overwrite: bool = False,
) -> Dict[str, Any]:
    return _daily_log_gen.generate_daily_log(
        date_str=date_str,
        weather=weather,
        activities=activities,
        inspections=inspections,
        workers_count=workers_count,
        equipment_count=equipment_count,
        key_directives=key_directives,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
        force_overwrite=force_overwrite,
    )
