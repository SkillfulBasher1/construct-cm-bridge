"""Weather screening that drafts a stop-work review sheet for responsible approval."""

import math
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from .doc_parser import DocumentParser
from .docx_exporter import DocxExporter

logger = logging.getLogger(__name__)


class WeatherStopWorkTrigger:
    """Flags weather-sensitive work without claiming a binding legal determination."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.secure_dir = self.parser.secure_dir

    def evaluate_and_issue_order(
        self,
        rain_mm: float,
        wind_speed_ms: float,
        rain_threshold_mm: Optional[float] = None,
        wind_threshold_ms: Optional[float] = None,
        planned_work: str = "미입력",
        temp_c: Optional[float] = None,
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
        contractor_name: str = "미입력 시공사 현장소장",
    ) -> Dict[str, Any]:
        """Screens weather-sensitive work against user-supplied project criteria."""
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d %H:%M")
        doc_no = f"SWCM-STOP-{now.strftime('%Y%m%d')}-01"

        for name, value in (
            ("rain_mm", rain_mm),
            ("wind_speed_ms", wind_speed_ms),
            ("rain_threshold_mm", rain_threshold_mm),
            ("wind_threshold_ms", wind_threshold_ms),
            ("temp_c", temp_c),
        ):
            if value is None and name in {"temp_c", "rain_threshold_mm", "wind_threshold_ms"}:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"{name}은 유한한 숫자여야 합니다.")
            if name != "temp_c" and value < 0:
                raise ValueError(f"{name}은 음수일 수 없습니다.")

        stop_items: List[Dict[str, Any]] = []

        # 1. Rain-sensitive work screening
        rain_targets = []
        if any(k in planned_work for k in ["타설", "콘크리트"]):
            rain_targets.append("콘크리트 타설")
        if "도장" in planned_work:
            rain_targets.append("옥외 도장")
        if "방수" in planned_work:
            rain_targets.append("옥외 방수")
        rain_candidate = bool(rain_targets) and rain_mm > 0 and (
            rain_threshold_mm is None or rain_mm >= rain_threshold_mm
        )
        if rain_candidate:
            criterion = (
                f"사용자 입력 현장 기준 {rain_threshold_mm:.1f} mm/hr"
                if rain_threshold_mm is not None
                else "현장 강우 기준 미입력"
            )
            stop_items.append({
                "category": "강우(우천) 민감 공종 검토",
                "weather_metric": f"입력 강우량 {rain_mm:.1f} mm/hr",
                "screening_criterion": criterion,
                "target_work": rain_targets,
                "stop_level": "현장 기준 확인 필요 (REVIEW_REQUIRED)",
                "order_details": "승인 시방서·타설계획·작업허가서와 실측값을 대조하여 작업 진행·보호·중지 조치를 책임자가 결정",
            })

        # 2. Wind-sensitive work screening
        wind_targets = [
            label for keyword, label in [
                ("타워크레인", "타워크레인 양중"), ("크레인", "크레인 양중"),
                ("양중", "자재 양중"), ("갱폼", "갱폼 인양"),
                ("비계", "비계 설치/해체"), ("고소", "고소작업"),
            ] if keyword in planned_work
        ]
        wind_candidate = bool(wind_targets) and wind_speed_ms > 0 and (
            wind_threshold_ms is None or wind_speed_ms >= wind_threshold_ms
        )
        if wind_candidate:
            criterion = (
                f"사용자 입력 현장 기준 {wind_threshold_ms:.1f} m/s"
                if wind_threshold_ms is not None
                else "장비·현장 풍속 기준 미입력"
            )
            stop_items.append({
                "category": "강풍·풍속 민감 공종 검토",
                "weather_metric": f"입력 풍속 {wind_speed_ms:.1f} m/s",
                "screening_criterion": criterion,
                "target_work": list(dict.fromkeys(wind_targets)),
                "stop_level": "장비·현장 기준 확인 필요 (REVIEW_REQUIRED)",
                "order_details": "장비 제조사 운용한계, 승인 양중계획, 작업허가서 및 실측 위치·평균시간을 확인하여 책임자가 조치를 결정",
            })

        # 3. Overall Verdict
        has_stop = len(stop_items) > 0
        status = "STOP_REVIEW_REQUIRED" if has_stop else "NORMAL"
        overall_verdict = (
            "【작업중지 검토대상 감지】 현장 승인기준 확인 및 책임기술인 판단 필요"
            if has_stop
            else "자동 작업중지 조건 미검출 (작업 승인 판정 아님)"
        )

        # 4. Generate Document
        md_lines = [
            f"# [기상조건 작업중지 검토서 (초안)]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **검토일시:** {date_str}",
            f"- **수 신:** {contractor_name} / **발 신:** {chief_cm_name} (책임건설사업관리기술인)\n",
            f"# 1. 기상 현황 및 작업중지 검토 개요",
            f"- **현재 기상:** 강우량 **{rain_mm:.1f} mm/hr**, 풍속 **{wind_speed_ms:.1f} m/s**, 기온 **{f'{temp_c:.1f} ℃' if temp_c is not None else '미입력'}**",
            f"- **당일 계획공종:** {planned_work}",
            f"- **감리단 종합 판정:** **{overall_verdict}**\n",
            f"# 2. 세부 작업중지 검토 내역",
            f"| No | 구분 | 기상 측정치 | 선별 기준 | 검토 공종 | 검토 등급 | 확인 조치 |",
            f"|---|---|---|---|---|---|---|",
        ]

        if stop_items:
            for idx, item in enumerate(stop_items, 1):
                md_lines.append(
                    f"| {idx} | **{item['category']}** | {item['weather_metric']} | {item['screening_criterion']} | {', '.join(item['target_work'])} | **{item['stop_level']}** | {item['order_details']} |"
                )
        else:
            md_lines.append("| - | 자동 중지조건 미검출 | 입력값 기준 | 승인기준 별도 확인 | 없음 | REVIEW_REQUIRED | 작업허가·장비기준·현장상태 별도 확인 |")

        md_lines.extend([
            f"\n# 3. 책임자 확인사항 및 재개 절차",
            f"1. **책임자 확인:** 현장 승인기준, 장비 제작사 기준, 작업허가서와 실측 기상값을 대조하여 중지 여부를 결정할 것.",
            f"2. **중지 시 재개 절차:** 기상 상태 호전 후 현장 안전점검과 책임자의 재개 승인을 거칠 것.",
        ])

        report_md = "\n".join(md_lines)
        docx_filename = f"기상조건_작업중지검토서_{now.strftime('%Y%m%d')}.docx"

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
            "rain_threshold_mm": rain_threshold_mm,
            "wind_threshold_ms": wind_threshold_ms,
            "temp_c": temp_c,
            "planned_work": planned_work,
            "stop_items_count": len(stop_items),
            "stop_items": stop_items,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "source_anchor": f"{docx_filename} [작업중지검토서 본문]",
        }


# Singleton instance
_weather_trigger = WeatherStopWorkTrigger()


def issue_weather_stop_work_order(
    rain_mm: float,
    wind_speed_ms: float,
    rain_threshold_mm: Optional[float] = None,
    wind_threshold_ms: Optional[float] = None,
    planned_work: str = "미입력",
    temp_c: Optional[float] = None,
    project_name: str = "미입력 프로젝트",
    chief_cm_name: str = "미입력 책임기술인",
    contractor_name: str = "미입력 시공사 현장소장",
) -> Dict[str, Any]:
    return _weather_trigger.evaluate_and_issue_order(
        rain_mm=rain_mm,
        wind_speed_ms=wind_speed_ms,
        rain_threshold_mm=rain_threshold_mm,
        wind_threshold_ms=wind_threshold_ms,
        planned_work=planned_work,
        temp_c=temp_c,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
        contractor_name=contractor_name,
    )
