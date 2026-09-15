"""Owner Special Specification & Statutory Submission Requirement Auditor (Module 17 - Custom Requirement Auditor)

Extracts mandatory submission requirements from Owner RFP / Special Specs (HWPX/DOCX) or KCS standards:
- Automatically parses sentences with:
  * "제출하여야 한다", "승인을 득할 것", "제출물", "계산서 첨부", "성적서 제출", "밀시트", "계측계획"
- Maps extracted requirements against files present in local storage (`secure_local_data/`)
- Evaluates submission status:
  * [접수완료 (RECEIVED) / 미접수·누락 (MISSING) / 보완필요 (MODIFY)]
- Generates official Construct CM "제출도서 접수 및 검토현황표 (.docx / .md)"
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .doc_parser import DocumentParser, SECURE_DATA_DIR
from .docx_exporter import DocxExporter

logger = logging.getLogger(__name__)


class CustomRequirementAuditor:
    """Audits owner submission requirements against submitted local project files."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        exporter: Optional[DocxExporter] = None,
    ):
        self.parser = parser or DocumentParser()
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.secure_dir = self.parser.secure_dir

    def audit_spec_requirements(
        self,
        spec_file: str,
        target_work_type: Optional[str] = None,
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
    ) -> Dict[str, Any]:
        """Parses spec_file for mandatory submission clauses and cross-checks with local files."""
        parsed = self.parser.parse_document(spec_file)
        spec_text = parsed.get("markdown", "")
        chunks = parsed.get("chunks", [])

        # Get list of existing local files
        local_files = [f["filename"] for f in self.parser.list_files() if f["filename"] != spec_file]

        # 1. Extract requirement sentences
        requirements: List[Dict[str, Any]] = []
        req_patterns = [
            r'([^.\n]*?(?:제출하여야\s*한다|승인을\s*득하여야\s*한다|첨부하여야\s*한다|사전\s*승인을\s*득할\s*것|제출물)[^.\n]*\.)',
            r'([^.\n]*?(?:밀시트|성적서|계산서|계획서|배합설계|안전관리계획서)(?:를|을)?\s*(?:제출|첨부|제시)[^.\n]*\.)',
        ]

        raw_candidates = []
        for pat in req_patterns:
            for m in re.finditer(pat, spec_text):
                c_text = m.group(1).strip()
                if len(c_text) > 15 and c_text not in raw_candidates:
                    raw_candidates.append(c_text)

        # 2. Map requirements to existing files and evaluate status
        received_count = 0
        missing_count = 0
        modify_count = 0

        for idx, sentence in enumerate(raw_candidates, 1):
            # Determine expected submission document type
            doc_type = "시공계획서"
            expected_keywords = []

            if any(k in sentence for k in ["안전관리계획", "건진법"]):
                doc_type = "안전관리계획서"
                expected_keywords = ["안전관리계획", "safety_plan"]
            elif any(k in sentence for k in ["구조계산서", "계산서", "안전율"]):
                doc_type = "구조/수치계산서"
                expected_keywords = ["계산서", "calc"]
            elif any(k in sentence for k in ["밀시트", "성적서", "Mill Sheet", "KS"]):
                doc_type = "자재 시험성적서/밀시트"
                expected_keywords = ["밀시트", "성적서", "cert"]
            elif any(k in sentence for k in ["계측", "수위계", "경사계"]):
                doc_type = "계측관리계획서"
                expected_keywords = ["계측"]
            elif any(k in sentence for k in ["배합설계", "레미콘"]):
                doc_type = "레미콘 공장 배합표"
                expected_keywords = ["배합", "콘크리트", "성적서"]
            else:
                doc_type = "세부 시공계획서"
                expected_keywords = ["시공계획서", "단열", "마감", "방수"]

            # Search in local files
            matched_file = None
            for lf in local_files:
                if any(kw.lower() in lf.lower() for kw in expected_keywords):
                    matched_file = lf
                    break

            # Find precision source anchor in spec chunks
            source_anchor = f"{spec_file} (본문 요건)"
            for ch in chunks:
                if any(w in ch.get("text", "") for w in sentence.split()[:2]):
                    source_anchor = ch.get("source_anchor", source_anchor)
                    break

            if matched_file:
                status = "접수확인 (RECEIVED_REVIEW_REQUIRED)"
                received_count += 1
                remark = f"파일명 기준 제출 후보({matched_file}) 확인. 내용·최신본·승인 여부는 별도 검토 필요"
            else:
                status = "미접수·누락 (MISSING)"
                missing_count += 1
                remark = f"특기시방 명시 서류({doc_type}) 미제출 ➔ 시공사 긴급 제출 촉구"

            requirements.append({
                "no": idx,
                "clause_excerpt": sentence,
                "required_doc_type": doc_type,
                "status": status,
                "matched_local_file": matched_file or "미제출",
                "source_anchor": source_anchor,
                "cm_action": remark,
            })

        total_reqs = len(requirements)
        if not requirements:
            overall_verdict = "시방서에서 제출 요건을 추출하지 못함 (REVIEW_REQUIRED)"
        elif missing_count > 0:
            overall_verdict = "제출도서 누락 및 보완 지시 (REVISE_REQUIRED)"
        else:
            overall_verdict = "파일 접수 후보 확인, 내용 검토 필요 (REVIEW_REQUIRED)"

        # 3. Generate Word Document (.docx) & Markdown (.md)
        now = datetime.now()
        date_str = now.strftime("%Y.%m.%d")
        doc_no = f"SWCM-SUBM-{now.strftime('%Y%m%d')}-01"

        md_lines = [
            f"# [발주처 특기시방 요구 제출도서 접수 및 검토현황표]",
            f"- **문서번호:** {doc_no}",
            f"- **공 사 명:** {project_name}",
            f"- **기준 시방서:** {spec_file}",
            f"- **점검 일자:** {date_str}",
            f"- **총괄 감리원:** {chief_cm_name}\n",
            f"# 1. 제출도서 접수 현황 집계",
            f"- **총 요구 제출물:** **{total_reqs}건**",
            f"- **정상 접수:** {received_count}건 / **미접수(누락):** {missing_count}건 / **보완 필요:** {modify_count}건",
            f"- **종합 판정:** **{overall_verdict}**\n",
            f"# 2. 세부 시방 조항별 제출도서 대조표",
            f"| No | 시방 요구 조항 및 제출물 요건 | 대상 도서명 | 접수 상태 | 매핑 파일 | 출처 좌표 (Source Anchor) | 감리 조치 사항 |",
            f"|---|---|---|---|---|---|---|",
        ]

        for r in requirements:
            sym = "✔" if "RECEIVED" in r["status"] else ("⚠️" if "MODIFY" in r["status"] else "✖")
            md_lines.append(
                f"| {r['no']} | {r['clause_excerpt'][:45]}... | {r['required_doc_type']} | {sym} **{r['status']}** | {r['matched_local_file']} | `{r['source_anchor']}` | {r['cm_action']} |"
            )

        report_md = "\n".join(md_lines)
        docx_filename = f"제출도서_검토현황표_{now.strftime('%Y%m%d')}.docx"

        res = self.exporter.export(
            output_filename=docx_filename,
            report_text=report_md,
            project_name=project_name,
            reviewer_name=chief_cm_name,
            discipline="제출도서 관리",
            doc_no=doc_no,
        )

        return {
            "status": "SUCCESS",
            "spec_file": spec_file,
            "overall_verdict": overall_verdict,
            "total_requirements": total_reqs,
            "received_count": received_count,
            "missing_count": missing_count,
            "modify_count": modify_count,
            "requirements_matrix": requirements,
            "docx_path": res.get("docx_path"),
            "md_path": res.get("md_path"),
        }


# Singleton instance
_req_auditor = CustomRequirementAuditor()


def audit_custom_spec_requirements(
    spec_file: str,
    target_work_type: Optional[str] = None,
    project_name: str = "미입력 프로젝트",
) -> Dict[str, Any]:
    return _req_auditor.audit_spec_requirements(
        spec_file=spec_file,
        target_work_type=target_work_type,
        project_name=project_name,
    )
