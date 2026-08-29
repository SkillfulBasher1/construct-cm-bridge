"""Weather Condition Stop-Work Order Trigger (Module 25)

Automatically evaluates weather parameters (rainfall, wind speed, temperature) against:
1. KCS 14 20 10 (콘크리트공사 표준시방서 - 우천 시 타설 원칙적 금지)
2. Occupational Safety and Health Standards (산업안전보건기준에 관한 규칙 제37조 - 악천후 시 크레인 양중 작업중지)
3. Occupational Safety Rule (제567조 - 폭염/한파 시 옥외 고소작업 중지)
Generates official Samwoo CM '기상특보에 따른 작업중지 명령서 (.docx / .md)'.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .doc_parser import DocumentParser, SECURE_DATA_DIR
from .docx_exporter import DocxExporter

logger = logging.getLogger(__name__)


class WeatherStopWorkTrigger:
    """Evaluates weather severity and issues binding CM Stop-Work Orders."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter()
        self.secure_dir = self.parser.secure_dir

    def evaluate_and_issue_order(
        self,
        rain_mm: float,
        wind_speed_ms: float,
        planned_work: str = "3층 슬래브 콘크리트 타설 및 갱폼 양중",
        temp_c: Optional[float] = 22.0,
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
        contractor_name: str = "(주)대우건설 현장소장",
    ) -> Dict[str, Any]:
        """Evaluates weather conditions and determines mandatory stop-work actions."""
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d %H:%M")
        doc_no = f"SWCM-STOP-{now.strftime('%Y%m%d')}-01"

        stop_items: List[Dict[str, Any]] = []

        # 1. Rain Evaluation (우천 시 타설 및 도장/방수 금지)
        is_rain_pour = False
        if rain_mm >= 5.0 or (rain_mm > 0.5 and ("타설" in planned_work or "콘크리트" in planned_work)):
            is_rain_pour = True
            stop_items.append({
                "category": "우천 타설 및 옥외 방수 금지",
                "weather_metric": f"시간당 강우량 {rain_mm:.1f} mm/hr (강우 지속)",
                "legal_standard": "KCS 14 20 10 제3.3절 (강우·강설 시 콘크리트 타설 원칙적 금지)",
                "target_work": [w for w in ["콘크리트 타설", "옥외 도장", "아스팔트 방수"] if any(k in planned_work for k in ["타설", "콘크리트", "도장", "방수"])] or ["콘크리트 타설"],
                "stop_level": "전면 작업중지 (MANDATORY_STOP)",
                "order_details": "강우 중 콘크리트 타설 시 물-결합재비(W/B) 상승으로 인한 강도 저하 및 품질 불량 발생 위험 ➔ 타설 즉시 중단 및 콜드조인트 방지 마감 조치",
            })

        # 2. Wind Evaluation (강풍 시 크레인 양중 및 고소작업 중지)
        is_wind_stop = False
        if wind_speed_ms >= 10.0:
            is_wind_stop = True
            if wind_speed_ms >= 15.0:
                stop_action = "타워크레인 운전 전면 중단 및 지브 회전 고정 해제"
                stop_level = "타워크레인 운전 중단 (CRITICAL_STOP)"
            else:
                stop_action = "타워크레인/이동식크레인 자재 양중 및 인양 작업 중지"
                stop_level = "크레인 양중 중지 (WARNING_STOP)"

            stop_items.append({
                "category": "강풍 시 양중 및 고소작업 중지",
                "weather_metric": f"순간최대풍속 {wind_speed_ms:.1f} m/s (강풍 주의보/경보)",
                "legal_standard": "산업안전보건기준에 관한 규칙 제37조 (악천후 및 강풍 시 작업중지)",
                "target_work": ["타워크레인 양중", "갱폼 인양", "비계 설치/해체", "외부 도장"],
                "stop_level": stop_level,
                "order_details": f"순간풍속 {wind_speed_ms:.1f}m/s 도달에 따라 {stop_action} 실시. 하부 낙하물 위험구역 통제선 설치.",
            })

        # 3. Overall Verdict
        has_stop = len(stop_items) > 0
        status = "STOP_ORDER_ISSUED" if has_stop else "NORMAL"
        overall_verdict = (
            "【긴급 작업중지 명령 발령】 기상 악화(강우/강풍)에 따른 법적 작업중지권 행사"
            if has_stop
            else "기상 양호 - 정상 작업 가능 (PASS)"
        )

        # 4. Generate Document
        md_lines = [
            f"# [기상특보에 따른 우천타설금지 및 양중작업중지 명령서]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **발령일시:** {date_str}",
            f"- **수 신:** {contractor_name} / **발 신:** {chief_cm_name} (책임건설사업관리기술인)\n",
            f"# 1. 기상 현황 및 작업중지 발령 개요",
            f"- **현재 기상:** 강우량 **{rain_mm:.1f} mm/hr**, 풍속 **{wind_speed_ms:.1f} m/s**, 기온 **{temp_c:.1f} ℃**",
            f"- **당일 계획공종:** {planned_work}",
            f"- **감리단 종합 판정:** **{overall_verdict}**\n",
            f"# 2. 세부 작업중지 지시 내역",
            f"| No | 구분 | 기상 측정치 | 적용 기준 (법령/KCS) | 작업중지 대상 공종 | 작업중지 등급 | 감리단 세부 지시내용 |",
            f"|---|---|---|---|---|---|---|",
        ]

        if stop_items:
            for idx, item in enumerate(stop_items, 1):
                md_lines.append(
                    f"| {idx} | **{item['category']}** | {item['weather_metric']} | {item['legal_standard']} | {', '.join(item['target_work'])} | 🛑 **{item['stop_level']}** | {item['order_details']} |"
                )
        else:
            md_lines.append("| - | 정상 기상 | 기준치 이내 | 정상 | 없음 | 정상 (PASS) | 표준 안전수칙 준수 하에 시공 |")

        md_lines.extend([
            f"\n# 3. 시공사 필수 조치사항 및 해제 절차",
            f"1. **현장 즉시 전파:** 시공사는 본 작업중지 명령 즉시 현장 작업반장 및 근로자에게 전파하고 옥외 작업을 전면 중단할 것.",
            f"2. **작업 재개 승인:** 기상 상태 호전 후 시공사는 현장 안전점검 및 감리원 합동 육안 검측을 실시하여 이상이 없음을 확인받은 후 작업을 재개할 것.",
        ])

        report_md = "\n".join(md_lines)
        docx_filename = f"기상특보_작업중지명령서_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="안전 / 기상재해방지",
            doc_no=doc_no,
        )

        return {
            "status": status,
            "overall_verdict": overall_verdict,
            "rain_mm": rain_mm,
            "wind_speed_ms": wind_speed_ms,
            "temp_c": temp_c,
            "planned_work": planned_work,
            "stop_items_count": len(stop_items),
            "stop_items": stop_items,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "source_anchor": f"{docx_filename} [작업중지명령서 본문]",
        }


# Singleton instance
_weather_trigger = WeatherStopWorkTrigger()


def issue_weather_stop_work_order(
    rain_mm: float,
    wind_speed_ms: float,
    planned_work: str = "3층 슬래브 콘크리트 타설 및 갱폼 양중",
    temp_c: Optional[float] = 22.0,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
    contractor_name: str = "(주)대우건설 현장소장",
) -> Dict[str, Any]:
    return _weather_trigger.evaluate_and_issue_order(
        rain_mm=rain_mm,
        wind_speed_ms=wind_speed_ms,
        planned_work=planned_work,
        temp_c=temp_c,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
        contractor_name=contractor_name,
    )
