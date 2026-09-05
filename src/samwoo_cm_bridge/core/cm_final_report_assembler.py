"""Comprehensive CM Completion & Regulatory Final Report Assembler (Module 22)

Aggregates all project records from SQLite Memory DB (`project_memory.db`) and local audit artifacts:
- Compiles Section 1: Executive Summary & CM Organization
- Compiles Section 2: Progress & Schedule Milestones
- Compiles Section 3: Quality Control & Material Test Reports (Concrete Strength, Mill Sheets)
- Compiles Section 4: Safety Management & Daily TBM History
- Compiles Section 5: Corrective Actions (NCR) & Design Changes / VE History
- Compiles Section 6: Final Chief CM Completion Opinion
Generates official Samwoo CM '준공 감리완료보고서 (.docx / .md)'.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .doc_parser import DocumentParser
from .docx_exporter import DocxExporter
from .project_memory_engine import ProjectMemoryEngine

logger = logging.getLogger(__name__)


class CMFinalReportAssembler:
    """Assembles all cumulative CM supervision records into a comprehensive Final Completion Report."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
        db_path: Optional[Path] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.db_path = Path(db_path).resolve() if db_path else self.parser.secure_dir / "project_memory.db"
        self.secure_dir = self.parser.secure_dir

    def assemble_report(
        self,
        project_name: str = "미입력 프로젝트",
        report_type: str = "준공 감리완료보고서",
        chief_cm_name: str = "미입력 책임기술인",
        client_name: str = "미입력 발주자",
        contractor_name: str = "미입력 시공사",
    ) -> Dict[str, Any]:
        """Scans project DB and local artifacts to assemble a complete Final CM Report."""
        now = datetime.now()
        date_str = now.strftime("%Y년 %m월 %d일")
        doc_no = f"SWCM-FINAL-{now.strftime('%Y%m%d')}-01"

        # 1. Fetch instructions from Project Memory DB
        memory_engine = ProjectMemoryEngine(db_path=self.db_path, parser=self.parser)
        instructions = memory_engine.get_action_items_status()

        # 2. Scan generated artifacts in secure_dir
        local_files = [f["filename"] for f in self.parser.list_files()]
        ncr_files = [f for f in local_files if "NCR" in f or "시정지시" in f]
        tbm_files = [f for f in local_files if "TBM" in f or "안전" in f]
        review_files = [f for f in local_files if "검토의견서" in f or "검측" in f]
        daily_files = [f for f in local_files if "일보" in f or "일지" in f]

        # 3. Build Structured Final Report Content
        md_lines = [
            f"# [{report_type}] {project_name}",
            f"- **문서번호:** {doc_no}",
            f"- **발 주 자:** {client_name}",
            f"- **시 공 자:** {contractor_name}",
            "- **건설사업관리자:** ㈜삼우씨엠건축사사무소",
            f"- **책임건설사업관리기술인:** {chief_cm_name}",
            f"- **보고일자:** {date_str}\n",
            "# 1. 자동 집계 범위",
            f"- 보안 저장소 파일: {len(local_files)}건",
            f"- 지시사항 DB 기록: {len(instructions)}건",
            f"- NCR 관련 파일명 후보: {len(ncr_files)}건",
            f"- TBM/안전 관련 파일명 후보: {len(tbm_files)}건",
            f"- 검토/검측 관련 파일명 후보: {len(review_files)}건",
            f"- 일일 기록 관련 파일명 후보: {len(daily_files)}건\n",
            "# 2. 공정관리 실적",
            "- 계획·실적 공정률 원자료가 연동되지 않아 자동 확정할 수 없습니다. (REVIEW_REQUIRED)\n",
            "# 3. 품질·시험·검측 실적",
            "- 위 파일 수는 파일명 기준 후보 건수이며, 적합 판정·시험 통과·중복 제거를 의미하지 않습니다.",
            "- 원본 대장과 승인 서명을 책임기술인이 대조해야 합니다. (REVIEW_REQUIRED)\n",
            "# 4. 안전·환경관리 실적",
            "- 재해 건수와 법정 점검 이행 여부를 판단할 원자료가 연동되지 않았습니다. (REVIEW_REQUIRED)\n",
            "# 5. NCR·설계변경·발주처 지시",
            f"- 색인 지시사항 {len(instructions)}건과 NCR 파일명 후보 {len(ncr_files)}건이 확인되었습니다.",
            "- 조치 완료 및 설계 반영 여부는 원본 증빙을 대조해야 합니다. (REVIEW_REQUIRED)\n",
            "# 6. 종합 준공검사 의견",
            "자동 집계 자료만으로 준공 적합·사용승인 가능 여부를 확정할 수 없습니다. 책임기술인이 필수 원본과 현장 상태를 검토한 후 최종 의견을 작성해야 합니다. **REVIEW_REQUIRED**",
        ]

        report_md = "\n".join(md_lines)
        docx_filename = f"준공_감리완료보고서_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="건설사업관리 종합 (준공)",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "project_name": project_name,
            "report_type": report_type,
            "doc_no": doc_no,
            "assembled_instructions_count": len(instructions),
            "scanned_artifacts_count": len(local_files),
            "final_progress_pct": None,
            "final_verdict": "REVIEW_REQUIRED",
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
            "source_anchor": f"{docx_filename} [준공완료보고서 본문]",
        }


# Singleton instance
_report_assembler = CMFinalReportAssembler()


def assemble_cm_final_report(
    project_name: str = "미입력 프로젝트",
    report_type: str = "준공 감리완료보고서",
    chief_cm_name: str = "미입력 책임기술인",
    client_name: str = "미입력 발주자",
    contractor_name: str = "미입력 시공사",
) -> Dict[str, Any]:
    return _report_assembler.assemble_report(
        project_name=project_name,
        report_type=report_type,
        chief_cm_name=chief_cm_name,
        client_name=client_name,
        contractor_name=contractor_name,
    )
