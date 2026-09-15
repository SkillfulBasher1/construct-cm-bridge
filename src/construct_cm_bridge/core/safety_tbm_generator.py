"""Daily TBM (Tool Box Meeting) & Safety Risk Assessment Generator (Module 14 - Safety TBM)

Generates preliminary daily TBM safety meeting checklists and hazard candidates:
- Site-specific laws, approved plans, permits, and manufacturer instructions must be checked separately
- Maps daily tasks (굴착, 비계, 양중, 용접, 콘크리트 타설, 밀폐공간) to:
  * Hazard categories (추락, 협착, 붕괴, 화재, 낙하비래, 감전)
  * Risk Level (상/중/하)
  * Candidate pre-work safety measures & inspection checkpoints
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
                    "measures": "승인 굴착계획의 사면·지보 기준 확인, 상부 추가하중 통제, 굴착 저면 배수계획 확인",
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
                    "hazard": "고소 작업 중 작업자 추락",
                    "risk_level": "상 (HIGH)",
                    "measures": "현행 기준과 승인 안전계획에 맞는 안전난간·작업발판·추락방호 및 안전대 걸이시설 확인",
                    "checkpoint": "안전대 체결 상태와 작업발판 고정·틈새·하중조건 확인",
                },
                {
                    "hazard": "비계 조립/해체 자재 낙하·비래",
                    "risk_level": "중 (MEDIUM)",
                    "measures": "승인 안전계획에 맞는 낙하물 방지시설과 하부 출입통제 구획 설치, 자재 투하 금지",
                    "checkpoint": "자재 인양용 달줄/달포대 사용 및 하부 신호수 배치",
                },
            ],
            "양중": [
                {
                    "hazard": "크레인 양중 중 와이어로프 파단 및 중량물 낙하",
                    "risk_level": "상 (HIGH)",
                    "measures": "와이어로프·샤클·슬링의 손상과 폐기기준을 제조사 지침 및 현행 기준에 따라 사전 확인",
                    "checkpoint": "2줄 걸이 체결 및 인양 하중계 지침 확인, 인양 경로 하부 통제",
                },
                {
                    "hazard": "크레인 아웃트리거 지반 침하에 의한 전도",
                    "risk_level": "상 (HIGH)",
                    "measures": "장비 매뉴얼과 지반 검토에 따른 아웃트리거 전개·받침·지내력 확보",
                    "checkpoint": "아웃트리거 수평계 확인 및 연약지반 치환 상태",
                },
            ],
            "용접": [
                {
                    "hazard": "용접 불티 비산에 의한 화재 및 가연물 폭발",
                    "risk_level": "상 (HIGH)",
                    "measures": "화기작업허가서의 이격·가연물 제거·불티 방호·소화설비 조건을 현장 확인",
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
                    "measures": "타설 전 동바리·연결재와 승인 타설순서·속도·높이·편심 방지 대책 확인",
                    "checkpoint": "타설 중 동바리 변형 감시원 상시 배치",
                },
            ],
        }

    def generate_tbm_sheet(
        self,
        today_tasks_list: List[str],
        date_str: Optional[str] = None,
        project_name: str = "미입력 프로젝트",
        tbm_leader: str = "미입력 TBM 주관자",
    ) -> Dict[str, Any]:
        """Generates TBM safety meeting checklist for today's specific task list."""
        now = datetime.now()
        cur_date = date_str or now.strftime("%Y.%m.%d")
        try:
            datetime.strptime(cur_date, "%Y.%m.%d")
        except ValueError as e:
            raise ValueError("date_str은 YYYY.MM.DD 형식이어야 합니다.") from e
        if not today_tasks_list or not all(isinstance(task, str) and task.strip() for task in today_tasks_list):
            raise ValueError("today_tasks_list에는 하나 이상의 작업명이 필요합니다.")

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
            f"- **주의:** 아래 위험등급과 대책은 키워드 기반 후보이며, 현장 위험성평가와 승인 문서로 확정해야 합니다. **REVIEW_REQUIRED**\n",
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
            f"\n# 2. 작업 시작 전 기본안전 확인 후보",
            f"1. 작업별 개인보호구 선정·착용과 추락방호 체결 상태 확인",
            f"2. 적법한 절차에 따른 작업 적합성·건강상태 확인 및 고위험 작업 배치 검토",
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
            "evidence_status": "REVIEW_REQUIRED",
            "evaluated_risks": evaluated_risks,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
        }


# Singleton instance
_safety_tbm_gen = SafetyTBMGenerator()


def generate_daily_tbm_safety(
    today_tasks_list: List[str],
    date_str: Optional[str] = None,
    project_name: str = "미입력 프로젝트",
) -> Dict[str, Any]:
    return _safety_tbm_gen.generate_tbm_sheet(
        today_tasks_list=today_tasks_list,
        date_str=date_str,
        project_name=project_name,
    )
