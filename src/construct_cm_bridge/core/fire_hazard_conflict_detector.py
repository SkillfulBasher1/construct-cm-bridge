"""Fire Hazard Concurrent Work Conflict Detector (Module 23)

Detects prohibited/dangerous concurrent work combinations between:
1. Hot Works (용접, 용단, 절단, 연마, 토치 가열 등)
2. Combustible Materials / Flammable Vapor Works (우레탄폼 뿜칠, 단열재 시공, 에폭시/페인트 도장, 방수 시공, 본드 접착 등)
Screens spatial overlap and drafts a review sheet (.docx / .md). It does not issue
a legal stop-work order or determine which regulation applies to the project.
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .doc_parser import DocumentParser, SECURE_DATA_DIR
from .docx_exporter import DocxExporter

logger = logging.getLogger(__name__)

# Keyword sets for Hot Works vs Combustible Works
HOT_WORK_KEYWORDS = [
    "용접", "아크", "가스절단", "용단", "절단", "토치", "열풍", "그라인더", "연마", "화기", "불꽃", "화염"
]

COMBUSTIBLE_KEYWORDS = [
    "단열재", "우레탄", "우레탄폼", "스티로폼", "뿜칠", "도장", "페인트", "에폭시", "방수", "아스팔트", "유성", "신너", "접착", "본드", "인화", "가연"
]


class FireHazardConflictDetector:
    """Screens concurrent-work conflicts and drafts a review-required worksheet."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.secure_dir = self.parser.secure_dir

    def detect_conflicts(
        self,
        tasks_list: Union[List[str], str],
        date_str: str = "",
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
        contractor_name: str = "미입력 시공사 현장소장",
    ) -> Dict[str, Any]:
        """Analyzes daily tasks list and detects hot work & combustible work conflicts in same space."""
        if isinstance(tasks_list, str):
            raw_tasks = [t.strip() for t in re.split(r"[\n;,]+", tasks_list) if t.strip()]
        else:
            raw_tasks = list(tasks_list)

        now = datetime.now()
        cur_date = date_str if date_str else now.strftime("%Y.%m.%d")
        try:
            datetime.strptime(cur_date, "%Y.%m.%d")
        except ValueError as e:
            raise ValueError("date_str은 YYYY.MM.DD 형식이어야 합니다.") from e
        doc_no = f"SWCM-FIRE-{now.strftime('%Y%m%d')}-01"

        hot_works: List[Dict[str, Any]] = []
        combustible_works: List[Dict[str, Any]] = []

        for idx, task in enumerate(raw_tasks, 1):
            is_hot = any(k in task for k in HOT_WORK_KEYWORDS)
            is_comb = any(k in task for k in COMBUSTIBLE_KEYWORDS)

            # Location extraction (e.g. 지하 1층, 101동, 기계실 등)
            loc_match = re.search(r"((?:지하\s*\d+층|지상\s*\d+층|\d+층|\d+동|기계실|전기실|주차장|옥상|피트|램프)[\w\s~]*)", task)
            loc = loc_match.group(1).strip() if loc_match else "구역 미상"

            if is_hot:
                hot_works.append({"no": idx, "task": task, "location": loc, "type": "화기/용접작업"})
            if is_comb:
                combustible_works.append({"no": idx, "task": task, "location": loc, "type": "가연성물질/도장작업"})

        conflicts: List[Dict[str, Any]] = []
        # Check overlaps
        for h in hot_works:
            for c in combustible_works:
                # Compare locations
                h_loc, c_loc = h["location"], c["location"]
                overlap = False
                confidence = "CONFIRMED_LOCATION_MATCH"
                if h_loc == "구역 미상" or c_loc == "구역 미상":
                    overlap = True
                    confidence = "POTENTIAL_UNKNOWN_LOCATION"
                elif h_loc == c_loc:
                    overlap = True
                elif any(k in c_loc for k in h_loc.split() if len(k) > 1) or any(k in h_loc for k in c_loc.split() if len(k) > 1):
                    overlap = True

                if overlap:
                    confirmed = confidence == "CONFIRMED_LOCATION_MATCH"
                    conflicts.append({
                        "hot_work": h["task"],
                        "combustible_work": c["task"],
                        "conflict_location": h_loc if h_loc != "구역 미상" else c_loc,
                        "confidence": confidence,
                        "risk_level": "CRITICAL (즉시 작업중지 및 분리)" if confirmed else "POTENTIAL (위치 확인 필요)",
                        "legal_basis": "화재위험작업 관련 현행 규정과 현장 화기작업 절차 원문 확인 필요",
                        "mandatory_action": "화기작업과 가연성물질 취급작업의 위치·시간을 즉시 확인하고, 중첩이 확인되면 작업 분리와 방호조치 완료 전까지 중지",
                    })

        confirmed_conflicts = [c for c in conflicts if c["confidence"] == "CONFIRMED_LOCATION_MATCH"]
        if confirmed_conflicts:
            status = "CRITICAL_ALERT"
            overall_verdict = "【위험 경보】 동일 위치 화재위험 동시작업 키워드 감지 ➔ 현장 확인 및 작업 분리 필요"
        elif conflicts:
            status = "REVIEW_REQUIRED"
            overall_verdict = "화재위험 작업 조합 감지, 위치 미상으로 현장 확인 필요 (REVIEW_REQUIRED)"
        elif raw_tasks:
            status = "NORMAL"
            overall_verdict = "키워드 기반 화재 동시작업 충돌 미검출 (작업 승인 판정 아님)"
        else:
            status = "REVIEW_REQUIRED"
            overall_verdict = "작업 목록 미입력 (REVIEW_REQUIRED)"

        # Generate DOCX and MD reports
        md_lines = [
            f"# [화재위험 동시작업 충돌 검토서]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **점검일자:** {cur_date}",
            f"- **수 신:** {contractor_name} / **발 신:** {chief_cm_name}\n",
            f"# 1. 종합 판정 결과",
            f"- **총 작업 계획:** {len(raw_tasks)}건 (화기작업 {len(hot_works)}건 / 가연성작업 {len(combustible_works)}건)",
            f"- **동시작업 충돌 건수:** **{len(conflicts)}건 검출**",
            f"- **감리단 조치사항:** **{overall_verdict}**\n",
            f"# 2. 화재위험 동시작업 충돌 상세 내역",
            f"| No | 화기 작업 (점화원) | 가연성 물질 취급 (연소원) | 충돌 위치 | 위험도 | 확인 및 권고 조치 |",
            f"|---|---|---|---|---|---|",
        ]

        if conflicts:
            for idx, conf in enumerate(conflicts, 1):
                md_lines.append(
                    f"| {idx} | {conf['hot_work']} | {conf['combustible_work']} | **{conf['conflict_location']}** | 🚨 **{conf['risk_level']}** | {conf['mandatory_action']} |"
                )
        else:
            md_lines.append("| - | 자동 검출 없음 | 자동 검출 없음 | 위치 근거 없음 | REVIEW_REQUIRED | 작업허가서와 실제 공간·시간 중첩 여부 확인 |")

        md_lines.extend([
            f"\n# 3. 적용 기준 및 확인사항",
            f"1. **적용 기준:** 화재위험작업 관련 현행 규정, 현장 화기작업허가 절차 및 작업계획서 원문을 확인할 것.",
            f"2. **조치 요구사항:** 검출된 충돌 공종은 공간·시간 분리와 방호조치를 확인한 후 책임자의 재개 승인을 받을 것.",
        ])

        report_md = "\n".join(md_lines)
        docx_filename = f"동시작업_화재위험_검토서_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="안전 / 화재예방관리",
            doc_no=doc_no,
        )

        return {
            "status": status,
            "overall_verdict": overall_verdict,
            "total_tasks_evaluated": len(raw_tasks),
            "hot_works_count": len(hot_works),
            "combustible_works_count": len(combustible_works),
            "conflicts_count": len(conflicts),
            "conflicts": conflicts,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "source_anchor": f"{docx_filename} [화재동시작업 대조표]",
        }


# Singleton instance
_fire_detector = FireHazardConflictDetector()


def check_concurrent_work_fire_hazard(
    tasks_list: Union[List[str], str],
    date_str: str = "",
    project_name: str = "미입력 프로젝트",
    chief_cm_name: str = "미입력 책임기술인",
    contractor_name: str = "미입력 시공사 현장소장",
) -> Dict[str, Any]:
    return _fire_detector.detect_conflicts(
        tasks_list=tasks_list,
        date_str=date_str,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
        contractor_name=contractor_name,
    )
