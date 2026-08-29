"""Samwoo-CM-Bridge FastMCP Server Definition

Exposes CM 3-way Cross Verification Tools to Claude Desktop, Cursor, OpenClaw, and local agents.
"""

import json
import logging
from typing import Optional, Dict, Any

from fastmcp import FastMCP

from .core.openapi_client import fetch_national_law as _fetch_law, fetch_kcsc_standard as _fetch_kcsc
from .core.doc_parser import read_local_project_file as _read_file, list_secure_local_files as _list_files
from .core.formula_engine import verify_calculation_safety as _verify_math
from .core.docx_exporter import export_review_document as _export_doc
from .core.batch_cross_checker import batch_cross_check_documents as _batch_cross_check
from .core.diff_audit_engine import audit_document_diff as _audit_diff
from .core.adaptive_checklist_engine import generate_and_evaluate_checklist as _checklist_eval
from .core.semantic_standard_searcher import search_standards_by_keyword as _search_standards
from .core.cm_periodic_reporter import generate_weekly_cm_report as _gen_weekly_report
from .core.official_letter_generator import draft_official_notice as _draft_notice
from .core.comprehensive_review_pipeline import run_comprehensive_review as _auto_review
from .core.ocr_parser import parse_scanned_material_cert as _parse_cert
from .core.daily_log_generator import generate_daily_cm_log as _gen_daily_log
from .core.flexible_schedule_analyzer import analyze_custom_schedule as _analyze_schedule
from .core.safety_tbm_generator import generate_daily_tbm_safety as _gen_tbm
from .core.inspection_ncr_generator import (
    generate_inspection_sheet as _gen_inspection,
    draft_ncr_correction_order as _draft_ncr,
)
from .core.custom_requirement_auditor import audit_custom_spec_requirements as _audit_spec_reqs
from .core.equipment_quantity_auditor import (
    audit_calculation_quantity_drawing_match as _audit_3way_match,
)

logger = logging.getLogger("samwoo_cm_bridge")

# Initialize FastMCP Server
mcp = FastMCP(
    name="Samwoo-CM-Bridge",
    instructions=(
        "Samwoo-CM-Bridge는 삼우씨엠 건설사업관리(CM) 3자 교차 검토(국가법령-KCSC기준-시공사제출서류) "
        "엔진입니다. 로컬 보안 격리 폴더 내 문서를 읽고, 국가법령/KCSC 기준을 조회하며, "
        "파이썬 기반의 엄밀한 수치 검산(Zero-Hallucination)을 거쳐 삼우씨엠 표준 감리의견서를 자동 생성합니다."
    ),
)


@mcp.tool()
def fetch_national_law(law_name: str, article_no: str = "") -> str:
    """국가법령정보센터(law.go.kr) REST API를 호출하여 최신 개정 법률·시행령·시행규칙 조문을 실시간 검색합니다.
    API 키 미설정 또는 오프라인 환경에서는 정밀 로컬 캐시/Mock 데이터를 자동으로 반환합니다.

    Args:
        law_name: 검색할 법령명 (예: '건설기술 진흥법', '건축법', '주택법', '소방시설 설치 및 관리에 관한 법률', '전기사업법')
        article_no: 특정 조문 번호 (선택 사항, 예: '62', '53', '12')
    """
    res = _fetch_law(law_name=law_name, article_no=article_no if article_no else None)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def fetch_kcsc_standard(standard_code: str) -> str:
    """국가건설기준센터(kcsc.re.kr)로부터 KDS(설계기준) 및 KCS(표준시방서) 최신 규격 본문과 허용 기준치를 호출합니다.
    API 키 미설정 또는 오프라인 환경에서는 정밀 로컬 캐시/Mock 데이터를 자동으로 반환합니다.

    Args:
        standard_code: 검색할 건설기준 코드 (예: 'KDS 21 30 00', 'KCS 14 31 25', 'KCS 31 10 00', 'KEC 232', 'KDS 41 10 00')
    """
    res = _fetch_kcsc(standard_code=standard_code)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def read_local_project_file(filename: str) -> str:
    """로컬 보안 격리 폴더(secure_local_data/) 내의 프로젝트 파일(HWPX, XLSX, DOCX, PPTX, PDF, TXT)을 읽어
    구조화된 마크다운 본문 및 수치 테이블 메타데이터로 변환합니다. 외부 유출 없이 로컬에서만 격리 파싱됩니다.

    Args:
        filename: 읽을 파일명 (예: '과업지시서_특기시방.hwpx', '가설구조계산서.xlsx', '시공계획서.docx')
    """
    try:
        res = _read_file(filename=filename)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "filename": filename, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def list_secure_local_files() -> str:
    """로컬 보안 격리 작업 폴더(secure_local_data/)에 존재하는 검토 대상 파일 목록과 메타데이터(크기, 확장자 등)를 조회합니다."""
    files = _list_files()
    return json.dumps({"status": "SUCCESS", "count": len(files), "files": files}, ensure_ascii=False, indent=2)


@mcp.tool()
def verify_calculation_safety(
    item_name: str,
    domain: str = "토목/구조",
    design_val: float = 0.0,
    allowable_val: float = 0.0,
    req_sf: float = 1.25,
    formula_type: str = "civil_safety_factor",
    custom_formula: str = "",
    variables_json: str = "{}",
) -> str:
    """AI의 임의 추론(환각)을 배제하고 파이썬 코드로 안전율 및 공학 수식을 직접 연산하여 PASS/FAIL 및 여유율을 판정합니다.
    5대 공종(구조·토목, 기계·설비, 소방, 전기·통신, 건축) 표준 공식 및 AST 기반 커스텀 수식을 지원합니다.

    Args:
        item_name: 검토 대상 부재 또는 장비명 (예: '1단 버팀보(H-300x300)', '소화펌프 주펌프', '간선 케이블')
        domain: 공학 분야 ('토목/구조', '기계/설비', '소방', '전기/통신', '건축')
        design_val: 시공사 설계 작용치 / 작용응력
        allowable_val: 허용치 / 허용응력
        req_sf: 요구 안전율 또는 기준 임계치 (예: 1.25, 1.5, 3.0)
        formula_type: 내장 공식 키 ('civil_safety_factor', 'civil_strut_buckling', 'mep_pump_head_margin', 'fire_reservoir_hydrant', 'elec_voltage_drop_pct', 'arch_u_value' 등)
        custom_formula: 커스텀 수식 문자열 (선택 사항)
        variables_json: 추가 수식 변수 JSON 문자열 (선택 사항, 예: '{"length_m": 50, "current_a": 120, "wire_area_sqmm": 70, "nominal_voltage": 380, "max_drop_pct": 3.0}')
    """
    try:
        vars_dict = json.loads(variables_json) if variables_json and variables_json.strip() != "{}" else {}
    except Exception:
        vars_dict = {}

    res = _verify_math(
        item_name=item_name,
        domain=domain,
        design_val=design_val if design_val != 0.0 else None,
        allowable_val=allowable_val if allowable_val != 0.0 else None,
        req_sf=req_sf if req_sf != 0.0 else None,
        formula_type=formula_type if formula_type else None,
        custom_formula=custom_formula if custom_formula else None,
        variables=vars_dict,
    )
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def export_review_document(
    output_filename: str,
    report_text: str,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    reviewer_name: str = "수석 건설사업관리기술인",
    discipline: str = "토목 / 구조 / 기계 / 소방 / 전기",
    doc_no: str = "",
) -> str:
    """3자 대조 및 수치 검산이 완료된 최종 마크다운 검토 의견을 삼우씨엠 표준 서식의 Word(.docx) 및 Markdown(.md) 문서로 로컬 저장합니다.

    Args:
        output_filename: 저장할 파일명 (예: '가설흙막이_CM검토의견서.docx')
        report_text: 마크다운 형식의 전체 검토의견서 본문 (4단 3자 교차 대조표, 수치 검산 상세, 종합 조치 의견 포함)
        project_name: 프로젝트명
        reviewer_name: 검토자(건설사업관리기술인) 이름
        discipline: 검토 공종 분야
        doc_no: 문서번호 (미지정 시 자동 채번)
    """
    try:
        res = _export_doc(
            output_filename=output_filename,
            report_text=report_text,
            project_name=project_name,
            reviewer_name=reviewer_name,
            discipline=discipline,
            doc_no=doc_no if doc_no else None,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def batch_cross_check_documents(filenames: list[str]) -> str:
    """로컬 보안 격리 폴더(secure_local_data/) 내 여러 문서(시공계획서 HWPX, 계산서 XLSX, 특기시방서 DOCX 등)를
    동시에 스캔하여 부재 규격, 안전율(Fs), 설계 하중, 허용응력, 콘크리트 강도, 계측 주기의 수치 상충 및 기준 미달을 일괄 전수 검사합니다.

    Args:
        filenames: 검사할 파일명 목록 (예: ['sample_과업지시서_특기시방.hwpx', 'sample_가설흙막이_구조계산서.xlsx'])
    """
    try:
        res = _batch_cross_check(filenames=filenames)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def audit_document_diff(base_file: str, target_file: str, file_category: str = "AUTO") -> str:
    """기성내역서(XLSX) 단가/수량/금액 변조 및 도서(HWPX/DOCX) 개정본(Revision) 변경점 전수 감사 도구입니다.
    - 기성내역서: 전회 승인단가 대비 임의 인상, 수식 하드코딩 과대청구, 도급수량 초과, 미승인 비목 자동 탐지
    - 설계도서/시방서: 삭제/추가/수정 조항 추출 및 설계 안전율/기준 완화(CRITICAL) 감지

    Args:
        base_file: 기준 파일명 (예: 'sample_기성내역서_Rev0.xlsx', '특기시방서_Rev0.hwpx')
        target_file: 변경/검토 대상 파일명 (예: 'sample_기성내역서_Rev1.xlsx', '특기시방서_Rev1.hwpx')
        file_category: 파일 구분 ('AUTO', 'EXCEL', 'TEXT')
    """
    try:
        res = _audit_diff(base_file=base_file, target_file=target_file, file_category=file_category)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def generate_and_evaluate_checklist(
    work_type: str,
    site_conditions: str = "",
    spec_file: str = "",
    plan_file: str = "",
) -> str:
    """현장 특성(도심지, 고지하수위, 암반, 동절기 등) 및 특기시방서 기반으로 15~20개 맞춤형 CM 체크리스트를
    동적으로 생성하고, 시공사 제출 시공계획서(HWPX/DOCX)를 자동 스캔하여 적합/보완 판정 및 근거를 매핑합니다.

    Args:
        work_type: 대상 공종 ('토공/가설', '골조/콘크리트', '기계/소방', '전기/통신', '마감/방수')
        site_conditions: 현장 특수 조건 (예: '도심지 인접, 고지하수위, 암반발파, 동절기')
        spec_file: 발주처 특기시방서 파일명 (선택 사항, 예: 'sample_과업지시서_특기시방.hwpx')
        plan_file: 시공사 제출 시공계획서 파일명 (선택 사항, 예: 'sample_건축_단열및시공계획서.docx')
    """
    try:
        res = _checklist_eval(
            work_type=work_type,
            site_conditions=site_conditions,
            spec_file=spec_file if spec_file else None,
            plan_file=plan_file if plan_file else None,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def search_standards_by_keyword(query: str, domain: str = "", top_k: int = 3) -> str:
    """자연어 공학 질의(예: '버팀보 허용응력', '피난계단 보행거리', '소화수조 유효수량', '간선 전압강하율')를 분석하여
    관련 국가건설기준(KDS/KCS) 및 법령 조항을 연관도 순으로 역추적 검색하고 수치 검산 공식 힌트를 제공합니다.

    Args:
        query: 자연어 검색 질의어 (예: '버팀보 안전율 기준', '소화수조 용량 계산', '저압 간선 전압강하')
        domain: 공종 분야 필터 (선택 사항, 예: '토목/구조', '기계/소방', '전기/통신', '건축')
        top_k: 반환할 상위 결과 개수 (기본값: 3)
    """
    try:
        res = _search_standards(query=query, domain=domain if domain else None, top_k=top_k)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def index_project_instruction(filename: str) -> str:
    """발주처 공문, 설계변경 지시서, 회의록(HWPX/DOCX/PDF)을 읽어 핵심 지시내용, 수치, 조치기한을
    로컬 SQLite DB(project_memory.db)에 영구 색인(Indexing)합니다.

    Args:
        filename: 인덱싱할 공문/지시서 파일명 (예: 'sample_발주처_설계변경지시공문.hwpx')
    """
    try:
        res = _index_instruction(filename=filename)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def search_project_memory(query: str, status_filter: str = "") -> str:
    """과거 발주처 지시사항, 회의록 결정사항, 설계변경 히스토리를 자연어로 검색합니다.
    (예: "지하 주차장 램프 지시내용", "계측 주기 변경 공문")

    Args:
        query: 자연어 검색어
        status_filter: 조치 상태 필터 ('PENDING', 'RESOLVED' 등, 선택 사항)
    """
    try:
        res = _search_memory(query=query, status_filter=status_filter if status_filter else None)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def track_design_changes(change_log_file: str, target_plan_file: str) -> str:
    """누적 설계변경(VE) 내역서(XLSX)의 회차별 변경 사양이 시공사가 제출한 신규 시공계획서(HWPX/DOCX)에
    누락 없이 100% 반영되었는지 역추적 검증합니다.

    Args:
        change_log_file: 누적 설계변경 총괄내역서 (예: 'sample_설계변경_총괄내역서.xlsx')
        target_plan_file: 검증 대상 시공계획서 (예: 'sample_건축_단열및시공계획서.docx')
    """
    try:
        res = _track_changes(change_log_file=change_log_file, target_plan_file=target_plan_file)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def generate_weekly_cm_report(
    start_date: str = "",
    end_date: str = "",
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
) -> str:
    """프로젝트 메모리(지시사항, 검토 이력, 설계변경 현황)를 취합하여 삼우씨엠 표준 주간/월간 감리보고서(.docx)를 자동 생성합니다.

    Args:
        start_date: 보고 시작일자 (예: '2026.08.15')
        end_date: 보고 종료일자 (예: '2026.08.22')
        project_name: 프로젝트명
        chief_cm_name: 책임건설사업관리기술인 성명
    """
    try:
        res = _gen_weekly_report(
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            project_name=project_name,
            chief_cm_name=chief_cm_name,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def draft_official_notice(
    doc_title: str,
    recipient: str = "(주)대우건설 현장소장",
    reference: str = "발주처 감독관, 품질관리팀장",
    review_result_file: str = "",
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
) -> str:
    """시공계획서 검토결과(FAIL/보완필요)를 기반으로 시공사/발주처 발송용 정식 감리단 대외 공문(.docx/.md)을 자동 기안합니다.

    Args:
        doc_title: 공문 제목 (예: '가설 흙막이 시공계획서 검토결과 통보 및 시정 조치 지시의 건')
        recipient: 수신처 (예: '(주)대우건설 현장소장')
        reference: 참조처 (예: '발주처 개발사업팀 감독관')
        review_result_file: 첨부/근거 검토의견서 파일명 (선택 사항)
        project_name: 현장 사업명
        chief_cm_name: 책임건설사업관리기술인 성명
    """
    try:
        res = _draft_notice(
            doc_title=doc_title,
            recipient=recipient,
            reference=reference,
            review_result_file=review_result_file if review_result_file else None,
            project_name=project_name,
            chief_cm_name=chief_cm_name,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def run_comprehensive_review(
    target_plan_file: str,
    spec_file: str = "",
    calc_file: str = "",
    output_report_name: str = "종합_CM기술검토의견서.docx",
    project_name: str = "삼우씨엠 신축공사 CM현장",
    reviewer_name: str = "김수석 책임건설사업관리기술인",
) -> str:
    """[원클릭 통합 자료 검토 파이프라인]
    시공사 제출 시공계획서/계산서 파일명만 입력하면 [로컬 문서 파싱 ➔ 실시간 법령/KCSC 자동 호출 ➔
    수치 검산 ➔ 3자 교차 대조표 ➔ 삼우씨엠 표준 Word 감리의견서(.docx) 생성]을 한 번에 원스톱으로 실행합니다.

    Args:
        target_plan_file: 검토 대상 시공계획서 (예: 'sample_과업지시서_특기시방.hwpx', 'sample_건축_단열및시공계획서.docx')
        spec_file: 발주처 특기시방서 파일명 (선택 사항, 예: 'sample_과업지시서_특기시방.hwpx')
        calc_file: 구조/수치 계산서 파일명 (선택 사항, 예: 'sample_가설흙막이_구조계산서.xlsx')
        output_report_name: 저장할 감리의견서 파일명 (기본값: '종합_CM기술검토의견서.docx')
        project_name: 프로젝트 현장명
        reviewer_name: 책임건설사업관리기술인 성명
    """
    try:
        res = _auto_review(
            target_plan_file=target_plan_file,
            spec_file=spec_file if spec_file else None,
            calc_file=calc_file if calc_file else None,
            output_report_name=output_report_name,
            project_name=project_name,
            reviewer_name=reviewer_name,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def parse_scanned_material_cert(image_or_pdf_file: str) -> str:
    """스캔된 자재 시험성적서/공장 밀시트(PDF, JPG, PNG)에서 로컬 OCR을 통해 항복강도, 인장강도,
    압축강도, 열전도율 수치를 자동 추출하고 KS 기준 합격 여부를 판정합니다.

    Args:
        image_or_pdf_file: 스캔 성적서 파일명 (예: 'sample_밀시트_SS275.jpg', 'sample_콘크리트성적서.pdf')
    """
    try:
        res = _parse_cert(image_or_pdf_file=image_or_pdf_file)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def generate_daily_cm_log(
    date_str: str = "",
    weather: str = "맑음 (기온: 24.5℃, 강수량: 0mm)",
    activities: list[str] = None,
    inspections: list[dict] = None,
    workers_count: dict = None,
    equipment_count: dict = None,
    project_name: str = "삼우씨엠 신축공사 CM현장",
    chief_cm_name: str = "김수석 책임건설사업관리기술인",
) -> str:
    """금일 시공사 작업내용, 검측 실적, 투입 인원 및 중장비 데이터를 취합하여
    삼우씨엠 표준 '일일 감리업무일보(.docx)'를 자동 생성합니다.

    Args:
        date_str: 업무일자 (예: '2026.08.29')
        weather: 기상 상태 및 기온/강수량
        activities: 금일 시공사 주요 공종 작업내용 목록
        inspections: 감리단 검측 및 안전점검 실적 목록
        workers_count: 직종별 투입 인원수 딕셔너리
        equipment_count: 투입 장비 대수 딕셔너리
        project_name: 현장 사업명
        chief_cm_name: 책임건설사업관리기술인 성명
    """
    try:
        res = _gen_daily_log(
            date_str=date_str if date_str else None,
            weather=weather,
            activities=activities,
            inspections=inspections,
            workers_count=workers_count,
            equipment_count=equipment_count,
            project_name=project_name,
            chief_cm_name=chief_cm_name,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def analyze_custom_schedule(excel_file: str) -> str:
    """다양한 양식의 시공사 엑셀 공정표(XLSX)를 동적으로 스캔하여 계획 대비 실적 지연율(%p)을 분석하고
    주공정선(Critical Path) 부진 시 공정만회대책 요구서를 자동 작성합니다.

    Args:
        excel_file: 공정표 엑셀 파일명 (예: 'sample_공정표_진도현황.xlsx')
    """
    try:
        res = _analyze_schedule(excel_file=excel_file)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def generate_daily_tbm_safety(
    today_tasks_list: list[str],
    date_str: str = "",
    project_name: str = "삼우씨엠 신축공사 CM현장",
) -> str:
    """당일 예정된 공종명(굴착, 비계, 양중, 용접, 콘크리트 타설 등)을 입력받아 산안법 및 KCS 기준에 따른
    맞춤형 '일일 TBM 안전점검표 및 위험성평가표(.docx)'를 자동 생성합니다.

    Args:
        today_tasks_list: 금일 예정 작업 공종 목록 (예: ['지하 10m 토사 굴착', '가설 비계 설치', '크레인 양중'])
        date_str: 일자 (예: '2026.08.29')
        project_name: 현장 사업명
    """
    try:
        res = _gen_tbm(
            today_tasks_list=today_tasks_list,
            date_str=date_str if date_str else None,
            project_name=project_name,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def generate_inspection_sheet(
    work_type: str,
    location: str,
    contractor_spec: str = "",
    inspection_items: list[dict] = None,
) -> str:
    """현장 시공 부위에 대한 공종별 표준 '검측요청서 및 결과통보서(.docx)'를 자동 기안합니다.

    Args:
        work_type: 검측 대상 공종 (예: '가설 흙막이 지보공', '철근 배근', '배관 수압시험')
        location: 검측 위치 (예: '지하 2층 1구역 (X1~X5 열)')
        contractor_spec: 시공사 제출 규격/도면 사양
        inspection_items: 세부 검측 체크항목 리스트 (선택 사항)
    """
    try:
        res = _gen_inspection(
            work_type=work_type,
            location=location,
            contractor_spec=contractor_spec,
            inspection_items=inspection_items,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def draft_ncr_correction_order(
    issue_description: str,
    location: str,
    defect_category: str = "시공품질 불량",
    photo_attached: str = "현장 결함 사진 첨부",
    corrective_deadline: str = "",
) -> str:
    """현장 부적합/결함 적발 시 시공사 대상 정식 '부적합 시정지시서(NCR: Non-Conformance Report .docx)'를 즉시 발급합니다.

    Args:
        issue_description: 지적 사항 및 결함 내용 (예: '1단 버팀보 볼트 조임 불량 및 안전율 미달 부재 무단 설치')
        location: 결함 발생 위치 (예: '지하 2층 램프 구간')
        defect_category: 부적합 분류 ('시공품질 불량', '안전관리 미흡', '도면/시방 위반')
        photo_attached: 사진 증빙 설명
        corrective_deadline: 시정조치 완료 기한 (예: '2026년 09월 05일까지')
    """
    try:
        res = _draft_ncr(
            issue_description=issue_description,
            location=location,
            defect_category=defect_category,
            photo_attached=photo_attached,
            corrective_deadline=corrective_deadline,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def audit_custom_spec_requirements(
    spec_file: str,
    target_work_type: str = "",
    project_name: str = "삼우씨엠 신축공사 CM현장",
) -> str:
    """발주처 과업지시서/특기시방서(HWPX/DOCX)에서 필수 제출도서 요건을 추출하고
    로컬 파일 목록과 매핑하여 [접수완료 / 미접수(누락) / 보완필요] 판정표 및 제출현황표(.docx)를 자동 생성합니다.

    Args:
        spec_file: 발주처 특기시방서 파일명 (예: 'sample_과업지시서_특기시방.hwpx')
        target_work_type: 특정 공종 필터 (선택 사항, 예: '토공/가설')
        project_name: 현장 사업명
    """
    try:
        res = _audit_spec_reqs(
            spec_file=spec_file,
            target_work_type=target_work_type if target_work_type else None,
            project_name=project_name,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def audit_calculation_quantity_drawing_match(
    calc_file: str,
    boq_file: str,
    drawing_pdf_file: str,
    project_name: str = "삼우씨엠 신축공사 CM현장",
) -> str:
    """계산서(XLSX), 수량산출서(XLSX), 도면 PDF(장비일람표) 간 장비 규격, 용량, 수량 상호 불일치,
    산출서 수식 오류(수량*단가!=금액) 및 비정상 이상치(음수값 등)를 전수 교차 검증합니다.

    Args:
        calc_file: 계산서 엑셀 파일명 (예: 'sample_소방_소화수조및펌프계산서.xlsx')
        boq_file: 수량산출서 엑셀 파일명 (예: 'sample_소방_수량산출서.xlsx')
        drawing_pdf_file: 도면 장비일람표 PDF 파일명 (예: 'sample_소방_장비일람표_도면.pdf')
        project_name: 현장 사업명
    """
    try:
        res = _audit_3way_match(
            calc_file=calc_file,
            boq_file=boq_file,
            drawing_pdf_file=drawing_pdf_file,
            project_name=project_name,
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": str(e)}, ensure_ascii=False)


def run_server():
    """Starts the FastMCP Stdio Server."""
    mcp.run()


if __name__ == "__main__":
    run_server()
