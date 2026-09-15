"""Evidence-based end-to-end CM review pipeline."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .batch_cross_checker import BatchCrossChecker
from .doc_parser import DocumentParser
from .docx_exporter import DocxExporter
from .formula_engine import FormulaEngine
from .semantic_standard_searcher import SemanticStandardSearcher


class ComprehensiveReviewPipeline:
    """Parses supplied documents and reports only evidence found in them."""

    def __init__(
        self,
        parser: Optional[DocumentParser] = None,
        searcher: Optional[SemanticStandardSearcher] = None,
        formula_engine: Optional[FormulaEngine] = None,
        exporter: Optional[DocxExporter] = None,
        cross_checker: Optional[BatchCrossChecker] = None,
    ):
        self.parser = parser or DocumentParser()
        self.searcher = searcher or SemanticStandardSearcher()
        self.formula_engine = formula_engine or FormulaEngine()
        self.exporter = exporter or DocxExporter(self.parser.secure_dir)
        self.cross_checker = cross_checker or BatchCrossChecker(self.parser)

    @staticmethod
    def _extract_labeled_number(text: str, labels: List[str]) -> Optional[float]:
        label_pattern = "|".join(re.escape(label) for label in labels)
        match = re.search(rf"(?:{label_pattern})[^\d-]{{0,50}}(-?\d+(?:\.\d+)?)", text, re.I)
        return float(match.group(1)) if match else None

    def run_auto_review(
        self,
        target_plan_file: str,
        spec_file: Optional[str] = None,
        calc_file: Optional[str] = None,
        output_report_name: str = "종합_CM기술검토의견서.docx",
        project_name: str = "미입력 프로젝트",
        reviewer_name: str = "미입력 책임기술인",
        contractor_name: str = "미입력 시공사",
    ) -> Dict[str, Any]:
        plan_doc = self.parser.parse_document(target_plan_file)
        plan_text = plan_doc.get("markdown", "")
        plan_entities = self.cross_checker._extract_numeric_entities(plan_text, target_plan_file)

        spec_text = ""
        spec_entities: Dict[str, Any] = {}
        if spec_file:
            spec_doc = self.parser.parse_document(spec_file)
            spec_text = spec_doc.get("markdown", "")
            spec_entities = self.cross_checker._extract_numeric_entities(spec_text, spec_file)

        calc_text = ""
        calc_entities: Dict[str, Any] = {}
        if calc_file:
            calc_doc = self.parser.parse_document(calc_file)
            calc_text = calc_doc.get("markdown", "")
            calc_entities = self.cross_checker._extract_numeric_entities(calc_text, calc_file)

        search_query = f"{plan_text[:500]} {spec_text[:500]} {calc_text[:500]}"
        search_res = self.searcher.search_standards(search_query, top_k=3)
        referenced_standards: List[Dict[str, Any]] = []
        for result in search_res.get("top_results", []):
            code = result["code"]
            if result.get("category") == "국가법령":
                law_match = re.match(r"(.+?)\s+제(\d+)조", code)
                source = self.searcher.client.fetch_national_law(
                    law_match.group(1) if law_match else result.get("discipline", code),
                    law_match.group(2) if law_match else None,
                )
            else:
                source = self.searcher.client.fetch_kcsc_standard(code)
            referenced_standards.append({
                "code": code,
                "title": result.get("title", ""),
                "category": result.get("category", ""),
                "source": source.get("source", "NOT_FOUND"),
                "content_summary": source.get("content", result.get("excerpt", ""))[:200],
            })

        combined_calc_text = calc_text or plan_text
        design_val = self._extract_labeled_number(combined_calc_text, ["작용응력", "설계응력", "작용치"])
        allowable_val = self._extract_labeled_number(combined_calc_text, ["허용응력", "허용치"])
        req_sf = self._extract_labeled_number(
            f"{spec_text}\n{combined_calc_text}",
            ["요구안전율", "기준안전율", "최소안전율"],
        )

        math_evaluations: List[Dict[str, Any]] = []
        if design_val is not None and allowable_val is not None and req_sf is not None:
            math_evaluations.append(self.formula_engine.verify(
                item_name="문서에서 추출한 허용응력 안전율",
                domain="토목/구조",
                design_val=design_val,
                allowable_val=allowable_val,
                req_sf=req_sf,
                formula_type="civil_safety_factor",
            ))

        cross_table: List[Dict[str, Any]] = []
        if math_evaluations:
            math_result = math_evaluations[0]
            numeric_submission = (
                f"작용응력 {design_val}, 허용응력 {allowable_val}, 요구안전율 {req_sf}; "
                f"계산 Fs={math_result.get('calculated_value')}"
            )
            numeric_verdict = math_result.get("judgement", "ERROR")
            numeric_notes = math_result.get("action_required", "검산 결과 확인 필요")
        else:
            numeric_submission = "작용응력·허용응력·요구안전율의 완전한 조합을 추출하지 못함"
            numeric_verdict = "REVIEW_REQUIRED"
            numeric_notes = "원 계산서의 단위와 라벨을 수동 확인"
        cross_table.append({
            "item": "수치 안전율 검산",
            "standard_basis": "검색된 기준 원문 및 승인 설계기준 확인 필요",
            "client_requirement": f"특기시방 파일: {spec_file or '미제공'}",
            "contractor_submission": numeric_submission,
            "verdict": numeric_verdict,
            "notes": numeric_notes,
        })

        steel_specs = calc_entities.get("steel_sections", []) or plan_entities.get("steel_sections", [])
        cross_table.append({
            "item": "강재·부재 규격",
            "standard_basis": "승인 도면·시방·자재성적서 대조 필요",
            "client_requirement": "특기시방 원문 확인 필요" if spec_file else "특기시방 미제공",
            "contractor_submission": ", ".join(steel_specs) if steel_specs else "관련 규격을 추출하지 못함",
            "verdict": "EVIDENCE_FOUND (REVIEW_REQUIRED)" if steel_specs else "REVIEW_REQUIRED",
            "notes": "규격 문자열 발견은 자재 적합 또는 밀시트 확인을 의미하지 않음",
        })

        safety_plan_found = "안전관리계획" in plan_text
        cross_table.append({
            "item": "안전관리계획 근거",
            "standard_basis": "해당 사업의 적용 법령과 승인 요건 확인 필요",
            "client_requirement": "특기시방 원문 확인 필요" if spec_file else "특기시방 미제공",
            "contractor_submission": "관련 문구 발견" if safety_plan_found else "관련 문구 미발견",
            "verdict": "EVIDENCE_FOUND (REVIEW_REQUIRED)" if safety_plan_found else "REVIEW_REQUIRED",
            "notes": "문구 존재만으로 작성·승인 완료를 판정하지 않음",
        })

        spec_freq = spec_entities.get("monitoring_frequency", [])
        plan_freq = plan_entities.get("monitoring_frequency", [])
        if spec_freq and plan_freq:
            frequency_match = bool(set(spec_freq) & set(plan_freq))
            frequency_verdict = "EVIDENCE_MATCH" if frequency_match else "DISCREPANCY"
        else:
            frequency_match = False
            frequency_verdict = "REVIEW_REQUIRED"
        cross_table.append({
            "item": "계측 주기",
            "standard_basis": "제공된 특기시방/지시 원문",
            "client_requirement": ", ".join(spec_freq) if spec_freq else "추출 근거 없음",
            "contractor_submission": ", ".join(plan_freq) if plan_freq else "추출 근거 없음",
            "verdict": frequency_verdict,
            "notes": "문서 간 동일 표기 확인" if frequency_match else "원문과 적용 위치를 수동 확인",
        })

        has_fail = any(
            "FAIL" in row["verdict"] or "부적합" in row["verdict"] or "DISCREPANCY" in row["verdict"]
            for row in cross_table
        )
        overall_verdict = "보완 후 재제출 (FAIL/REVISE)" if has_fail else "근거 확인 후 최종 판정 필요 (REVIEW_REQUIRED)"

        md_body_lines = [
            "# 1. 검토 개요",
            f"- **사업명:** {project_name}",
            f"- **검토 대상 도서:** {target_plan_file} (계산서: {calc_file or '미제공'}, 특기시방: {spec_file or '미제공'})",
            f"- **시공사:** {contractor_name}",
            f"- **검토 일자:** {datetime.now().strftime('%Y.%m.%d')}",
            f"- **책임 감리원:** {reviewer_name}\n",
            "# 2. 관련 법령 및 국가건설기준 검색 내역",
        ]
        if referenced_standards:
            for standard in referenced_standards:
                md_body_lines.append(
                    f"- **[{standard['code']}] {standard['title']}** ({standard['source']}): {standard['content_summary']}"
                )
        else:
            md_body_lines.append("- 문서 내용과 매칭된 로컬 기준 없음 (REVIEW_REQUIRED)")

        md_body_lines.extend([
            "\n# 3. 근거 기반 교차 검토표",
            "| 검토 항목 | 기준 근거 | 발주처 요구조건 | 시공사 제출 근거 | 판정 결과 | 비고 |",
            "|---|---|---|---|---|---|",
        ])
        for row in cross_table:
            md_body_lines.append(
                f"| {row['item']} | {row['standard_basis']} | {row['client_requirement']} | {row['contractor_submission']} | **{row['verdict']}** | {row['notes']} |"
            )

        if math_evaluations:
            md_body_lines.append("\n# 4. 결정론적 수치 검산")
            for result in math_evaluations:
                md_body_lines.append(
                    f"- 공식: `{result.get('formula')}` / 계산값: {result.get('calculated_value')} / "
                    f"기준값: {result.get('threshold_value')} / 판정: **{result.get('judgement')}**"
                )

        md_body_lines.extend([
            "\n# 5. 종합 검토의견",
            f"- **총괄 판정:** {overall_verdict}",
            "- 자동 검토는 제공 문서에서 확인된 근거만 표시합니다. 미제공 자료, 승인 여부, 현장 시공 상태는 책임기술인이 확인해야 합니다.",
        ])

        export_res = self.exporter.export(
            output_filename=output_report_name,
            report_text="\n".join(md_body_lines),
            project_name=project_name,
            reviewer_name=reviewer_name,
            discipline="건설사업관리(CM) 종합",
        )

        return {
            "status": "SUCCESS",
            "pipeline": "ComprehensiveReviewPipeline",
            "target_document": target_plan_file,
            "overall_verdict": overall_verdict,
            "referenced_laws_and_standards": referenced_standards,
            "cross_comparison_table": cross_table,
            "math_verifications": math_evaluations,
            "generated_docx_file": export_res.get("docx_path"),
            "generated_md_file": export_res.get("md_path"),
            "summary_opinion": overall_verdict,
        }


_comprehensive_pipeline = ComprehensiveReviewPipeline()


def run_comprehensive_review(
    target_plan_file: str,
    spec_file: Optional[str] = None,
    calc_file: Optional[str] = None,
    output_report_name: str = "종합_CM기술검토의견서.docx",
    project_name: str = "미입력 프로젝트",
    reviewer_name: str = "미입력 책임기술인",
) -> Dict[str, Any]:
    return _comprehensive_pipeline.run_auto_review(
        target_plan_file=target_plan_file,
        spec_file=spec_file,
        calc_file=calc_file,
        output_report_name=output_report_name,
        project_name=project_name,
        reviewer_name=reviewer_name,
    )
