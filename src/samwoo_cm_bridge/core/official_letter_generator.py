"""CM Letter & Outward Notice Draft Generator (Module 8)

Generates review-required CM outward notification drafts to Contractor or Owner:
- [수신: 시공사 현장소장, 참조: 발주처 감독관, 제목: OO 시공계획서 검토결과 통보 및 보완 지시의 건]
- Formats document numbers and review signature placeholders in Word (.docx) and Markdown (.md).
"""

from datetime import datetime
from typing import Dict, Any, List, Optional

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from .doc_parser import DocumentParser
from .docx_exporter import choose_output_stem, set_cell_background, set_cell_margins


class OfficialLetterGenerator:
    """Generates review-required CM outward notification drafts."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()
        self.output_dir = self.parser.secure_dir

    def draft_notice(
        self,
        doc_title: str,
        recipient: str = "미입력 시공사 현장소장",
        reference: str = "발주처 감독관, 품질관리팀장",
        review_result_file: Optional[str] = None,
        action_items: Optional[List[str]] = None,
        project_name: str = "미입력 프로젝트",
        chief_cm_name: str = "미입력 책임기술인",
    ) -> Dict[str, Any]:
        """Generates a CM notice draft that requires authorized review before sending."""
        now = datetime.now()
        date_str = now.strftime("%Y년 %m월 %d일")
        doc_no = f"SWCM-NOTI-{now.strftime('%Y%m%d')}-01"

        # If review_result_file is provided, extract summary
        review_summary = ""
        if review_result_file:
            parsed = self.parser.parse_document(review_result_file)
            review_text = parsed.get("markdown", "")
            relevant_lines = [
                line.strip()
                for line in review_text.splitlines()
                if any(key in line for key in ["종합 판정", "최종 판정", "검토 결과", "overall_verdict", "PASS", "FAIL"])
            ]
            verdict_evidence = " / ".join(relevant_lines[:5])
            review_summary = verdict_evidence or review_text[:400].strip()
        else:
            verdict_evidence = ""
            review_summary = "검토결과 근거파일 미제공"

        evidence_upper = verdict_evidence.upper()
        if "FAIL" in evidence_upper or "부적합" in verdict_evidence or "반려" in verdict_evidence:
            notice_verdict = "보완 요청 초안 (FAIL 근거 확인)"
            result_sentence = "근거 검토결과에 보완 또는 부적합 표현이 있습니다. 원문 확인 후 보완 요청 여부를 확정해야 합니다."
        elif "PASS" in evidence_upper or "적합" in verdict_evidence or "승인" in verdict_evidence:
            notice_verdict = "PASS 표현 확인 (승인 여부 검토 필요)"
            result_sentence = "근거 검토결과에 PASS·적합·승인 표현이 있습니다. 원문과 승인권자를 확인한 후 발송해야 합니다."
        else:
            notice_verdict = "판정 확인 필요 (REVIEW_REQUIRED)"
            result_sentence = "근거자료에서 확정 판정을 확인하지 못했으므로 책임기술인의 검토 후 발송해야 합니다."

        # Build Markdown content
        actions = list(action_items or [])
        if not actions:
            actions = ["세부 조치사항과 발송 여부는 첨부 원문을 확인하여 책임기술인이 확정할 것"]

        md_content = f"""# 주식회사 삼우씨엠건축사사무소
**{project_name} 건설사업관리단**

---
- **문서번호:** {doc_no}
- **시행일자:** {date_str}
- **수　　신:** {recipient}
- **참　　조:** {reference}
- **제　　목:** {doc_title}

---

### 1. 관련 근거
1. 제출된 검토대상 도서 및 검토결과 파일
2. 해당 공종의 승인 설계도서, 계약조건 및 특기시방서

### 2. 검토 결과 요약
**판정:** {notice_verdict}

{result_sentence}

**근거 발췌:** {review_summary or '검토결과 본문 없음'}

### 3. 감리단 시정 및 조치 요구사항
아래 조치사항은 입력된 내용에 한하여 통보하며, 미입력 사항은 임의로 생성하지 않습니다.

"""
        for a in actions:
            md_content += f"- {a}\n"

        md_content += f"""
### 4. 제출 기한
- **조치 기한:** {date_str}로부터 7일 이내 (별도 협의 시 조정 가능)

---
**주식회사 삼우씨엠건축사사무소 책임건설사업관리기술인 (직인생략)**
"""

        # Generate Word (.docx)
        output_stem = choose_output_stem(self.output_dir, f"공문_{doc_no}")
        docx_filename = f"{output_stem}.docx"
        md_filename = f"{output_stem}.md"
        docx_path = self.output_dir / docx_filename
        md_path = self.output_dir / md_filename

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        doc = docx.Document()
        for s in doc.sections:
            s.top_margin = Inches(0.8)
            s.bottom_margin = Inches(0.8)
            s.left_margin = Inches(0.8)
            s.right_margin = Inches(0.8)

        # Header Title
        h_p = doc.add_paragraph()
        h_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h_run = h_p.add_run("주식회사 삼우씨엠건축사사무소")
        h_run.font.name = "맑은 고딕"
        h_run.font.size = Pt(18)
        h_run.font.bold = True
        h_run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

        sub_p = doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = sub_p.add_run(f"{project_name} 건설사업관리단")
        sub_run.font.name = "맑은 고딕"
        sub_run.font.size = Pt(12)
        sub_run.font.bold = True
        sub_run.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

        # Meta table
        meta_table = doc.add_table(rows=4, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_data = [
            ("문서번호", doc_no),
            ("시행일자", date_str),
            ("수　　신", recipient),
            ("참　　조", reference),
        ]
        for r_idx, (lbl, val) in enumerate(meta_data):
            c0 = meta_table.cell(r_idx, 0)
            c1 = meta_table.cell(r_idx, 1)
            c0.text = lbl
            c1.text = val
            set_cell_background(c0, "EDF2F7")
            set_cell_margins(c0, 60, 60, 80, 80)
            set_cell_margins(c1, 60, 60, 80, 80)
            c0.paragraphs[0].runs[0].font.bold = True

        doc.add_paragraph()

        # Subject line
        subj_p = doc.add_paragraph()
        subj_run = subj_p.add_run(f"제　　목 : {doc_title}")
        subj_run.font.name = "맑은 고딕"
        subj_run.font.size = Pt(12)
        subj_run.font.bold = True
        subj_run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

        doc.add_paragraph("─" * 45)

        # Body paragraphs
        p1 = doc.add_paragraph()
        p1.add_run("1. 관련 근거\n   가. 제출된 검토대상 도서 및 검토결과 파일\n   나. 해당 공종의 승인 설계도서, 계약조건 및 특기시방서")

        p2 = doc.add_paragraph()
        p2.add_run(f"2. 검토 결과 요약\n   판정: {notice_verdict}\n   {result_sentence}\n   근거 발췌: {review_summary or '검토결과 본문 없음'}")

        p3 = doc.add_paragraph()
        p3.add_run("3. 감리단 시정 및 조치 요구사항\n   아래 조치사항은 입력된 내용에 한하여 통보하며, 미입력 사항은 임의로 생성하지 않습니다.\n")
        for a in actions:
            ap = doc.add_paragraph(style="List Bullet")
            ap.add_run(a).font.bold = True

        p4 = doc.add_paragraph()
        p4.add_run("4. 제출 기한: 본 공문 수신일로부터 7일 이내 제출 요망.")

        doc.add_paragraph()
        sig_p = doc.add_paragraph()
        sig_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sig_run = sig_p.add_run(f"주식회사 삼우씨엠건축사사무소\n책임건설사업관리기술인 {chief_cm_name} (직인생략)")
        sig_run.font.name = "맑은 고딕"
        sig_run.font.size = Pt(13)
        sig_run.font.bold = True
        sig_run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

        doc.save(str(docx_path))

        return {
            "status": "SUCCESS",
            "doc_no": doc_no,
            "doc_title": doc_title,
            "recipient": recipient,
            "notice_verdict": notice_verdict,
            "review_source": review_result_file,
            "docx_path": str(docx_path),
            "md_path": str(md_path),
        }


# Singleton instance
_letter_generator = OfficialLetterGenerator()


def draft_official_notice(
    doc_title: str,
    recipient: str = "미입력 시공사 현장소장",
    reference: str = "발주처 감독관, 품질관리팀장",
    review_result_file: Optional[str] = None,
    action_items: Optional[List[str]] = None,
    project_name: str = "미입력 프로젝트",
    chief_cm_name: str = "미입력 책임기술인",
) -> Dict[str, Any]:
    return _letter_generator.draft_notice(
        doc_title=doc_title,
        recipient=recipient,
        reference=reference,
        review_result_file=review_result_file,
        action_items=action_items,
        project_name=project_name,
        chief_cm_name=chief_cm_name,
    )
