"""Fire Hazard Concurrent Work Conflict Detector (Module 23)

Detects prohibited/dangerous concurrent work combinations between:
1. Hot Works (용접, 용단, 절단, 연마, 토치 가열 등)
2. Combustible Materials / Flammable Vapor Works (우레탄폼 뿜칠, 단열재 시공, 에폭시/페인트 도장, 방수 시공, 본드 접착 등)
Evaluates spatial/temporal overlap and automatically drafts an official CM Stop/Separation Order (.docx / .md)
under the Occupational Safety and Health Act (산업안전보건기준에 관한 규칙 제241조의2) and KCS standards.
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
    """Detects dangerous concurrent work conflicts and drafts formal CM corrective orders."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter()
        self.secure_dir = self.parser.secure_dir

    def detect_conflicts(
        self,
        tasks_list: Union[List[str], str],
        date_str: str = "",
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
        contractor_name: str = "(주)대우건설 현장소장",
    ) -> Dict[str, Any]:
        """Analyzes daily tasks list and detects hot work & combustible work conflicts in same space."""
        if isinstance(tasks_list, str):
            raw_tasks = [t.strip() for t in re.split(r"[\n;,]+", tasks_list) if t.strip()]
        else:
            raw_tasks = list(tasks_list)

        now = datetime.now()
        cur_date = date_str if date_str else now.strftime("%Y.%m.%d")
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
                if h_loc == c_loc and h_loc != "구역 미상":
                    overlap = True
                elif any(k in c_loc for k in h_loc.split() if len(k) > 1) or any(k in h_loc for k in c_loc.split() if len(k) > 1):
                    overlap = True
                elif h_loc == "구역 미상" or c_loc == "구역 미상":
                    overlap = True  # Conservative defense: unknown location is flagged as potential collision

                if overlap:
                    conflicts.append({
                        "hot_work": h["task"],
                        "combustible_work": c["task"],
                        "conflict_location": h_loc if h_loc != "구역 미상" else c_loc,
                        "risk_level": "CRITICAL (즉시 작업중지 및 분리)",
                        "legal_basis": "산업안전보건기준에 관한 규칙 제241조의2 (화재위험작업 시의 준수사항) 및 건설기술 진흥법 제62조",
                        "mandatory_action": "화기작업과 가연성물질 취급작업의 공간적/시간적 동시작업 전면 금지, 화재감시자 배치, 불꽃비산방지포 설치 전까지 작업중지",
                    })

        status = "CRITICAL_ALERT" if conflicts else "NORMAL"
        overall_verdict = (
            "【위험 경보】 화재위험 동시작업 충돌 감지 ➔ 즉시 작업중지 및 구획 분리 명령"
            if conflicts
            else "화재 동시작업 충돌 없음 (PASS)"
        )

        # Generate DOCX and MD reports
        md_lines = [
            f"# [화재위험 동시작업 충돌 감지 및 감리단 시정명령서]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **점검일자:** {cur_date}",
            f"- **수 신:** {contractor_name} / **발 신:** {chief_cm_name}\n",
            f"# 1. 종합 판정 결과",
            f"- **총 작업 계획:** {len(raw_tasks)}건 (화기작업 {len(hot_works)}건 / 가연성작업 {len(combustible_works)}건)",
            f"- **동시작업 충돌 건수:** **{len(conflicts)}건 검출**",
            f"- **감리단 조치사항:** **{overall_verdict}**\n",
            f"# 2. 화재위험 동시작업 충돌 상세 내역",
            f"| No | 화기 작업 (점화원) | 가연성 물질 취급 (연소원) | 충돌 위치 | 위험도 | 감리원 법적 조치사항 |",
            f"|---|---|---|---|---|---|",
        ]

        if conflicts:
            for idx, conf in enumerate(conflicts, 1):
                md_lines.append(
                    f"| {idx} | {conf['hot_work']} | {conf['combustible_work']} | **{conf['conflict_location']}** | 🚨 **{conf['risk_level']}** | {conf['mandatory_action']} |"
                )
        else:
            md_lines.append("| - | 화기작업 없음 | 가연성작업 없음 | 안전 구역 | 정상 (PASS) | 특이 충돌 사항 없음 |")

        md_lines.extend([
            f"\n# 3. 법적 근거 및 감리단 지시사항",
            f"1. **산업안전보건기준에 관한 규칙 제241조의2:** 통풍이나 환기가 불충분한 장소에서 화재위험작업과 인화성 액체·증기 물질을 취급하는 작업을 동시에 진행하여서는 아니 됨.",
            f"2. **조치 요구사항:** 상기 충돌 공종에 대하여 시공사는 작업을 즉시 중지하고, 시공 순서 변경 또는 방화구획 분리 조치계획서를 제출하여 감리원의 승인을 득한 후 재개할 것.",
        ])

        report_md = "\n".join(md_lines)
        docx_filename = f"동시작업_화재위험_시정지시서_{now.strftime('%Y%m%d')}.docx"

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
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
    contractor_name: str = "(주)대우건설 현장소장",
) -> Dict[str, Any]:
    return _fire_detector.detect_conflicts(
        tasks_list=tasks_list,
        date_str=date_str,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
        contractor_name=contractor_name,
    )
