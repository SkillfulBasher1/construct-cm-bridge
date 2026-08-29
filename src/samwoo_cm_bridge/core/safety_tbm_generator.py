"""Daily TBM (Tool Box Meeting) & Safety Risk Assessment Generator (Module 14 - Safety TBM)

Generates daily TBM safety meeting checklists and risk assessment tables:
- Based on Industrial Safety and Health Act (산업안전보건법 제36조) & KCS Safety Standards
- Maps daily tasks (굴착, 비계, 양중, 용접, 콘크리트 타설, 밀폐공간) to:
  * Hazard categories (추락, 협착, 붕괴, 화재, 낙하비래, 감전)
  * Risk Level (상/중/하)
  * Mandatory pre-work safety measures & inspection checkpoints
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .doc_parser import SECURE_DATA_DIR
from .docx_exporter import DocxExporter


class SafetyTBMGenerator:
    """Generates customized daily TBM Safety Checklists based on work activities."""

    def __init__(self, exporter: Optional[DocxExporter] = None):
        self.exporter = exporter or DocxExporter()
        self._init_hazard_matrix()

    def _init_hazard_matrix(self):
        """Initializes knowledge base for task-specific hazards and countermeasures."""
        self.hazard_kb = {
            "굴착": [
                {
                    "hazard": "굴착 사면 토사 붕괴 및 낙하",
                    "risk_level": "상 (HIGH)",
                    "measures": "사면 기준 구배(1:1.0~1.5) 준수, 상부 토사 하중 재하 금지, 굴착 저면 배수로 확보",
                    "checkpoint": "사면 균열/용수 여부 및 버팀보 선행 설치 확인",
                },
                {
                    "hazard": "백호/덤프 장비 선회 반경 내 작업자 협착",
                    "risk_level": "상 (HIGH)",
                    "measures": "장비 작업구역 내 전담 신호수 배치 및 통제 휀스 설치, 후방감지기 점검",
                    "checkpoint": "신호수 신호봉/무전기 소지 및 장비 유도 일치 여부",
                },
            ],
            "비계": [
                {
                    "hazard": "고소 작업 중 작업자 추락 (2m 이상)",
                    "risk_level": "상 (HIGH)",
                    "measures": "안전난간(상부 90~120cm, 중간 45~60cm) 설치, 안전대 걸이시설 체결, 2개고리 죔줄 착용",
                    "checkpoint": "안전대 체결 상태 및 작업발판 틈새 3cm 이하 밀실 설치",
                },
                {
                    "hazard": "비계 조립/해체 자재 낙하·비래",
                    "risk_level": "중 (MEDIUM)",
                    "measures": "낙하물 방지망(10m 이내) 설치, 하부 출입통제 구획 설정, 자재 투하 금지",
                    "checkpoint": "자재 인양용 달줄/달포대 사용 및 하부 신호수 배치",
                },
            ],
            "양중": [
                {
                    "hazard": "크레인 양중 중 와이어로프 파단 및 중량물 낙하",
                    "risk_level": "상 (HIGH)",
                    "measures": "와이어로프 꼬임/단선(10% 미만) 사전 검사, 샤클/슬링벨트 안전하중 준수",
                    "checkpoint": "2줄 걸이 체결 및 인양 하중계 지침 확인, 인양 경로 하부 통제",
                },
                {
                    "hazard": "크레인 아웃트리거 지반 침하에 의한 전도",
                    "risk_level": "상 (HIGH)",
                    "measures": "아웃트리거 최대 인출 및 두께 50mm 이상 받침목(철판) 전면 포설",
                    "checkpoint": "아웃트리거 수평계 확인 및 연약지반 치환 상태",
                },
            ],
            "용접": [
                {
                    "hazard": "용접 불티 비산에 의한 화재 및 가연물 폭발",
                    "risk_level": "상 (HIGH)",
                    "measures": "작업 반경 11m 이내 가연물 제거, 불티 비산방지포 설치, 소화기 2대 전면 비치",
                    "checkpoint": "전담 화재감시자 배치 및 화기작업허가서 승인 확인",
                },
                {
                    "hazard": "용접봉 접촉에 의한 감전 및 유해가스 흡입",
                    "risk_level": "중 (MEDIUM)",
                    "measures": "자동전격방지기 작동 확인, 절연장갑/방진마스크 착용, 환기팬 가동",
                    "checkpoint": "전격방지기 램프 정상 점등 및 케이블 피복 손상 여부",
                },
            ],
            "타설": [
                {
                    "hazard": "콘크리트 펌프카 붐대 파손 및 배관 요동 타격",
                    "risk_level": "중 (MEDIUM)",
                    "measures": "펌프카 배관 연결부 클램프 체결 확인, 붐대 하부 작업자 접근 금지",
                    "checkpoint": "호스맨 안전모/보안경 착용 및 펌프카 무선리모컨 오작동 방지",
                },
                {
                    "hazard": "타설 하중에 의한 거푸집·동바리 붕괴",
                    "risk_level": "상 (HIGH)",
                    "measures": "타설 전 동바리 수직도/수평연결재 검측 승인, 편심 타설 금지 및 1회 타설 높이 50cm 제한",
                    "checkpoint": "타설 중 동바리 변형 감시원 상시 배치",
                },
            ],
        }

    def generate_tbm_sheet(
        self,
        today_tasks_list: List[str],
        date_str: Optional[str] = None,
        project_name: str = "삼우씨엠 신축공사 CM현장",
        tbm_leader: str = "현장 안전책임자 / 감리원 입회",
    ) -> Dict[str, Any]:
        """Generates TBM safety meeting checklist for today's specific task list."""
        now = datetime.now()
        cur_date = date_str or now.strftime("%Y.%m.%d")

        evaluated_risks: List[Dict[str, Any]] = []

        for task in today_tasks_list:
            matched_key = None
            for k in self.hazard_kb:
                if k in task:
                    matched_key = k
                    break

            if matched_key:
                hazards = self.hazard_kb[matched_key]
                for h in hazards:
                    evaluated_risks.append({
                        "task": task,
                        "hazard": h["hazard"],
                        "risk_level": h["risk_level"],
                        "safety_measures": h["measures"],
                        "inspection_checkpoint": h["checkpoint"],
                    })
            else:
                # Generic construction safety risk
                evaluated_risks.append({
                    "task": task,
                    "hazard": "작업자 부주의에 의한 전도/충돌 및 개인보호구 미착용",
                    "risk_level": "중 (MEDIUM)",
                    "measures": "보호구(안전모, 안전화, 각반) 전원 착용 확인 및 작업 전 스트레칭",
                    "checkpoint": "개인 보호구 착용 상태 전수 점검",
                })

        high_risk_count = sum(1 for r in evaluated_risks if "상" in r["risk_level"])

        # Build Markdown content
        md_lines = [
            f"# [일일 TBM 안전보건활동 및 위험성평가표] {cur_date}",
            f"- **현장명:** {project_name}",
            f"- **TBM 주관:** {tbm_leader}",
            f"- **금일 예정 공종:** {', '.join(today_tasks_list)}",
            f"- **중점 고위험(HIGH) 항목:** {high_risk_count}건 도출\n",
            f"# 1. 작업별 유해·위험요인 및 안전대책 대비표",
            f"| 작업 공종 | 주요 유해·위험요인 | 위험등급 | 중점 안전관리대책 | TBM 점검 포인트 |",
            f"|---|---|---|---|---|",
        ]

        for r in evaluated_risks:
            r_badge = f"**{r['risk_level']}**"
            md_lines.append(
                f"| {r['task']} | {r['hazard']} | {r_badge} | {r['safety_measures']} | {r['inspection_checkpoint']} |"
            )

        md_lines.extend([
            f"\n# 2. 작업 시작 전 10대 기본안전수칙 확인 서명",
            f"1. 안전모 턱끈 조임 및 안전대 2개고리 체결 100% 이행",
            f"2. 음주 작업자 및 고혈압 등 건강 이상자 당일 고소작업 투입 절대 금지",
            f"3. 중장비 작업반경 내 신호수 외 일반 근로자 접근 금지",
        ])

        report_md = "\n".join(md_lines)
        clean_date = cur_date.replace(".", "").replace("-", "").replace(" ", "")
        output_filename = f"TBM_안전점검표_{clean_date}.docx"

        res = self.exporter.export(
            output_filename=output_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=tbm_leader,
            discipline="안전보건관리",
        )

        return {
            "status": "SUCCESS",
            "date": cur_date,
            "tasks_analyzed": today_tasks_list,
            "total_risk_factors": len(evaluated_risks),
            "high_risk_count": high_risk_count,
            "evaluated_risks": evaluated_risks,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
        }


# Singleton instance
_safety_tbm_gen = SafetyTBMGenerator()


def generate_daily_tbm_safety(
    today_tasks_list: List[str],
    date_str: Optional[str] = None,
    project_name: str = "삼우씨엠 신축공사 CM현장",
) -> Dict[str, Any]:
    return _safety_tbm_gen.generate_tbm_sheet(
        today_tasks_list=today_tasks_list,
        date_str=date_str,
        project_name=project_name,
    )
