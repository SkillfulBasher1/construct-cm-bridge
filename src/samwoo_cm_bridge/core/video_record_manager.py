"""Major Structural Member Video Recording Log Manager (Module 24)

Manages user-supplied video recording metadata for structural inspections and drafts
a review register. Project-specific recording and submission requirements must be verified separately.
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
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.secure_dir = self.parser.secure_dir

    def generate_log(
        self,
        video_records: List[Dict[str, Any]],
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
        contractor_name: str = "미입력 시공사",
    ) -> Dict[str, Any]:
        """Compiles supplied video metadata into a review-required register draft."""
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d")
        doc_no = f"SWCM-VID-{now.strftime('%Y%m%d')}-01"

        normalized_records: List[Dict[str, Any]] = []
        missing_files = 0
        allowed_video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
        for record in video_records:
            normalized = dict(record)
            video_name = str(normalized.get("video_file", "")).strip()
            if not video_name or video_name != os.path.basename(video_name) or "/" in video_name or "\\" in video_name:
                normalized["file_status"] = "INVALID_OR_MISSING"
                missing_files += 1
            elif Path(video_name).suffix.lower() not in allowed_video_exts:
                normalized["file_status"] = "INVALID_TYPE"
                missing_files += 1
            elif not (self.secure_dir / video_name).is_file():
                normalized["file_status"] = "MISSING"
                missing_files += 1
            else:
                normalized["file_status"] = "FOUND"
            normalized_records.append(normalized)
        video_records = normalized_records

        # Markdown Table Generation
        md_lines = [
            f"# [주요 구조부 동영상 촬영 기록관리대장]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **시 공 자:** {contractor_name} / **건설사업관리자:** ㈜삼우씨엠건축사사무소",
            f"- **총괄책임자:** {chief_cm_name}",
            f"- **작성일자:** {date_str}\n",
            f"# 1. 동영상 기록관리 개요",
            f"- **적용 근거:** 해당 사업의 발주조건·인허가조건·승인 촬영계획 확인 필요",
            f"- **촬영 대상:** 승인 촬영계획에 기재된 대상 공종",
            f"- **총 등록 동영상:** **총 {len(video_records)}건**\n",
            f"# 2. 주요 구조부 동영상 촬영 상세 기록 대장",
            f"| No | 촬영 공종/부위 | 촬영일자 | 상세 위치(그리드) | 동영상 파일명 | 주요 검측 확인 사항 | 입회 감리원 | 검측 판정 |",
            f"|---|---|---|---|---|---|---|---|",
        ]

        for idx, rec in enumerate(video_records, 1):
            md_lines.append(
                f"| {idx} | **{rec.get('work_type', '-')}** | {rec.get('record_date', '미입력')} | {rec.get('grid_location', '-')} | `{rec.get('video_file', '-')}` ({rec.get('file_status')}) | {rec.get('key_items', '-')} | {rec.get('inspector', '미입력')} | **{rec.get('result', '미입력 (REVIEW_REQUIRED)')}** |"
            )

        if not video_records:
            md_lines.append("| - | 입력 기록 없음 | - | - | - | - | - | **REVIEW_REQUIRED** |")

        source_file_status = "ALL_FOUND" if video_records and missing_files == 0 else "MISSING_OR_INVALID"
        evidence_status = "REVIEW_REQUIRED"
        md_lines.extend([
            f"\n# 3. 감리원 종합 확인 의견",
            f"입력 기록 {len(video_records)}건 중 원본 파일 확인 실패 {missing_files}건. "
            f"영상 내용의 적합성은 이 목록만으로 자동 판정하지 않으며 책임기술인의 원본 확인이 필요함. **{evidence_status}**",
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
            "missing_video_files": missing_files,
            "source_file_status": source_file_status,
            "evidence_status": evidence_status,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "source_anchor": f"{docx_filename} [동영상기록관리대장 본문]",
        }


# Singleton instance
_video_manager = VideoRecordManager()


def generate_video_recording_log(
    video_records_list: Optional[List[Dict[str, Any]]] = None,
    project_name: str = "미입력 프로젝트",
    chief_cm_name: str = "미입력 책임기술인",
    contractor_name: str = "미입력 시공사",
) -> Dict[str, Any]:
    return _video_manager.generate_log(
        video_records=video_records_list or [],
        project_name=project_name,
        chief_cm_name=chief_cm_name,
        contractor_name=contractor_name,
    )
