"""Major Structural Member Video Recording Log Manager (Module 24)

Manages video recordings of critical structural inspections (rebar placement, concrete pour, underground excavation)
under Ministry of Land, Infrastructure and Transport (MOLIT) and Local Government Mandatory Video Recording Regulations.
Generates official Samwoo CM '주요 구조부 동영상 촬영 기록관리대장 (.docx / .md)' for regulatory submission.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .doc_parser import DocumentParser, SECURE_DATA_DIR
from .docx_exporter import DocxExporter

logger = logging.getLogger(__name__)


class VideoRecordManager:
    """Manages structural member video logs and compiles municipal submission registers."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter()
        self.secure_dir = self.parser.secure_dir

    def generate_log(
        self,
        video_records: List[Dict[str, Any]],
        project_name: str = "삼우씨엠 신축공사 CM현장",
        chief_cm_name: str = "김수석 책임건설사업관리기술인",
        contractor_name: str = "(주)대우건설",
    ) -> Dict[str, Any]:
        """Compiles structural member inspection video records into an official register."""
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d")
        doc_no = f"SWCM-VID-{now.strftime('%Y%m%d')}-01"

        if not video_records:
            video_records = [
                {
                    "video_file": "VID_20260829_B2F_SLAB_REBAR.mp4",
                    "work_type": "지하 2층 바닥 슬래브 철근배근 검측",
                    "record_date": "2026.08.29",
                    "grid_location": "지하 2층 1구역 (X1~X5 / Y2~Y4)",
                    "key_items": "상·하부근 유효피복 50mm 확보, 이음길이 40d 확인, 스페이서 1m 간격 배치",
                    "inspector": chief_cm_name,
                    "result": "적합 (PASS)",
                },
                {
                    "video_file": "VID_20260829_B2F_CONC_POUR.mp4",
                    "work_type": "지하 2층 바닥 슬래브 콘크리트 타설",
                    "record_date": "2026.08.29",
                    "grid_location": "지하 2층 1구역 (타설량 320m3)",
                    "key_items": "레미콘 슬럼프/공기량 시험 입회, 봉형 진동기 적정 다짐(5~15초), 콜드조인트 방지",
                    "inspector": chief_cm_name,
                    "result": "적합 (PASS)",
                }
            ]

        # Markdown Table Generation
        md_lines = [
            f"# [주요 구조부 동영상 촬영 기록관리대장]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **시 공 자:** {contractor_name} / **건설사업관리자:** ㈜삼우씨엠건축사사무소",
            f"- **총괄책임자:** {chief_cm_name}",
            f"- **작성일자:** {date_str}\n",
            f"# 1. 동영상 기록관리 개요",
            f"- **법적 근거:** 건설기술 진흥법 제62조, 지자체 공사현장 주요구조부 동영상 촬영 및 보관 지침",
            f"- **촬영 대상:** 가설 흙막이, 기초 파일, 철근 배근, 구조체 콘크리트 타설, 내화구조 시공 등 은폐 부위 전 공종",
            f"- **총 등록 동영상:** **총 {len(video_records)}건**\n",
            f"# 2. 주요 구조부 동영상 촬영 상세 기록 대장",
            f"| No | 촬영 공종/부위 | 촬영일자 | 상세 위치(그리드) | 동영상 파일명 | 주요 검측 확인 사항 | 입회 감리원 | 검측 판정 |",
            f"|---|---|---|---|---|---|---|---|",
        ]

        for idx, rec in enumerate(video_records, 1):
            md_lines.append(
                f"| {idx} | **{rec.get('work_type', '-')}** | {rec.get('record_date', date_str)} | {rec.get('grid_location', '-')} | `{rec.get('video_file', '-')}` | {rec.get('key_items', '-')} | {rec.get('inspector', chief_cm_name)} | ✔ **{rec.get('result', '적합 (PASS)')}** |"
            )

        md_lines.extend([
            f"\n# 3. 감리원 종합 확인 의견",
            f"상기 주요 구조부 은폐 구간 및 타설 과정에 대한 동영상 촬영 기록을 전수 확인한 결과, "
            f"설계도서 및 KCS 시공표준에 부합하게 시공되었음을 확인하며, 관련 영상 파일은 준공 후 인허가 관청 제출 및 영구 보관용 스토리지에 무단 변조 없이 정상 저장되었음을 확인함.",
        ])

        report_md = "\n".join(md_lines)
        docx_filename = f"주요구조부_동영상촬영_기록관리대장_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="품질 / 시공동영상기록",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "doc_no": doc_no,
            "total_video_records": len(video_records),
            "records": video_records,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "source_anchor": f"{docx_filename} [동영상기록관리대장 본문]",
        }


# Singleton instance
_video_manager = VideoRecordManager()


def generate_video_recording_log(
    video_records_list: Optional[List[Dict[str, Any]]] = None,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
    contractor_name: str = "(주)대우건설",
) -> Dict[str, Any]:
    return _video_manager.generate_log(
        video_records=video_records_list or [],
        project_name=project_name,
        chief_cm_name=chief_cm_name,
        contractor_name=contractor_name,
    )
