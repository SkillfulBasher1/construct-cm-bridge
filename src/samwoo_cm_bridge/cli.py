import sys
import json
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .server import run_server
from .core.openapi_client import fetch_national_law, fetch_kcsc_standard
from .core.doc_parser import read_local_project_file, list_secure_local_files, SECURE_DATA_DIR
from .core.formula_engine import verify_calculation_safety
from .core.docx_exporter import export_review_document
from .core.batch_cross_checker import batch_cross_check_documents, BatchCrossChecker
from .core.diff_audit_engine import audit_document_diff, DiffAuditEngine
from .core.adaptive_checklist_engine import generate_and_evaluate_checklist, AdaptiveChecklistEngine
from .core.semantic_standard_searcher import search_standards_by_keyword, SemanticStandardSearcher
from .core.project_memory_engine import index_project_instruction, search_project_memory
from .core.design_change_tracker import track_design_changes
from .core.cm_periodic_reporter import generate_weekly_cm_report
from .core.official_letter_generator import draft_official_notice
from .core.comprehensive_review_pipeline import run_comprehensive_review
from .core.ocr_parser import parse_scanned_material_cert
from .core.daily_log_generator import generate_daily_cm_log
from .core.flexible_schedule_analyzer import analyze_custom_schedule
from .core.safety_tbm_generator import generate_daily_tbm_safety
from .core.inspection_ncr_generator import (
    generate_inspection_sheet,
    draft_ncr_correction_order,
)


def cmd_serve(args):
    """Run FastMCP Server over stdio."""
    print("Starting Samwoo-CM-Bridge FastMCP Server (stdio)...", file=sys.stderr)
    run_server()


def cmd_list(args):
    """List files in secure_local_data/."""
    files = list_secure_local_files()
    print(f"\n[Secure Local Storage: {SECURE_DATA_DIR}]")
    print(f"Total files: {len(files)}")
    print("-" * 65)
    for f in files:
        print(f" - {f['filename']:<40} | {f['size_bytes']:>8} bytes | {f['extension']}")
    print("-" * 65)


def cmd_parse(args):
    """Parse local project file."""
    res = read_local_project_file(args.filename)
    print(f"\n=== [Parsed Document: {args.filename}] ===")
    print(res.get("markdown", ""))


def cmd_law(args):
    """Query national law."""
    res = fetch_national_law(args.law_name, args.article_no)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_kcsc(args):
    """Query KCSC standard."""
    res = fetch_kcsc_standard(args.code)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def cmd_demo(args):
    """Run comprehensive 3-way cross examination CM demo across 3 scenarios."""
    print("\n" + "=" * 70)
    print(" 🚀 Samwoo-CM-Bridge: 3자 교차 검토(Law-KCSC-Local) 종합 데모 시작")
    print("=" * 70)

    # -------------------------------------------------------------
    # Scenario 1: 토목/가설 흙막이 구조안전성 검토 (KDS 21 30 00)
    # -------------------------------------------------------------
    print("\n[시나리오 1: 토목/가설 흙막이 버팀보 및 안전율 3자 검토]")
    law1 = fetch_national_law("건설기술 진흥법", "62")
    kcsc1 = fetch_kcsc_standard("KDS 21 30 00")
    print(f" ✔ [국가법령] {law1.get('law_name')} 제{law1.get('article_no')}조 ({law1.get('title')}) 연동 완료")
    print(f" ✔ [KCSC기준] {kcsc1.get('standard_code')} ({kcsc1.get('standard_name')}) 수신 완료 (요구안전율 Fs >= 1.25)")

    # Math Verification
    math1 = verify_calculation_safety(
        item_name="1단 버팀보(Strut H-300x300x10x15)",
        domain="토목/구조",
        design_val=205.4,
        allowable_val=220.0,
        req_sf=1.25,
        formula_type="civil_safety_factor",
    )
    print(f" ✔ [수치검산] 작용응력: 205.4 MPa, 허용응력: 220.0 MPa -> 계산 Fs: {math1.get('calculated_value')} (판정: {math1.get('judgement')})")

    report1_md = f"""# 1. 검토 개요
- **검토 대상:** 가설 흙막이 지보공 1단 버팀보(H-300x300x10x15) 단면 적정성
- **근거 기준:** {law1.get('law_name')} 제{law1.get('article_no')}조 및 {kcsc1.get('standard_code')}

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 국가법령 및 KDS 기준 | 발주처 시방조건 | 시공사 제출값 | 판정 결과 | 비고 / 조치사항 |
|---|---|---|---|---|---|
| 버팀보 안전율(Fs) | KDS 21 30 00 (Fs >= 1.25) | 특기시방 4.1조 (Fs >= 1.25) | Fs = 1.07 (작용 205.4 / 허용 220.0) | **FAIL (부적합)** | 단면 증대(H-350계열) 또는 설치간격 축소 필요 |
| 강재 품질 규격 | KCS 14 31 25 (SS275/SM355) | KS 정품 및 밀시트 제출 | KS D 3503 SS275 제출 | **PASS (적합)** | 공장 성적서 일치 확인 |
| 안전관리계획 대상 | 건진법 제62조 (10m 이상 굴착) | 굴착깊이 12.5m 승인필요 | 안전관리계획서 초안 제출 | **PASS (적합)** | 인허가청 승인 절차 진행 |

# 3. 세부 수치 검산 내역
- **연산 공식:** $F_s = \\frac{{\\sigma_{{allowable}}}}{{\\sigma_{{design}}}} = \\frac{{220.0}}{{205.4}} = 1.071$
- **요구 안전율:** $1.25$
- **검토 판정:** 기준 안전율 대비 -14.3% 부족으로 **부적합(FAIL)** 판정.

# 4. 종합 감리의견 및 조치 지시사항
- 본 가설 흙막이 1단 버팀보는 시공 중 토압 증가 시 좌굴 위험이 상존하므로 **[반려 및 보완]** 조치함.
- 시공사는 버팀보 부재 규격을 상향(H-350x350x12x19 등)하거나 수평 지지간격을 재조정하여 구조계산서를 재작성 후 제출할 것.
"""
    doc1 = export_review_document(
        output_filename="가설흙막이_CM검토의견서.docx",
        report_text=report1_md,
        project_name="삼우씨엠 강남 복합빌딩 신축공사",
        reviewer_name="김수석 건설사업관리기술인 (토목/구조)",
        discipline="토목 / 가설구조",
    )
    print(f" ✔ [의견서생성] 삼우씨엠 표준 Word 문서 생성 완료: {doc1.get('docx_path')}")

    # -------------------------------------------------------------
    # Scenario 2: 소방/기계 소화수조 및 펌프 검토 (KCS 31 10 00)
    # -------------------------------------------------------------
    print("\n[시나리오 2: 소방/기계 소화수조 유효수량 및 펌프 용량 3자 검토]")
    law2 = fetch_national_law("소방시설 설치 및 관리에 관한 법률", "12")
    kcsc2 = fetch_kcsc_standard("KCS 31 10 00")
    print(f" ✔ [국가법령] {law2.get('law_name')} 제{law2.get('article_no')}조 ({law2.get('title')}) 연동 완료")
    print(f" ✔ [KCSC기준] {kcsc2.get('standard_code')} ({kcsc2.get('standard_name')}) 수신 완료")

    math2 = verify_calculation_safety(
        item_name="옥내소화전 소화수조 유효저수량",
        domain="소방",
        formula_type="fire_reservoir_hydrant",
        variables={"actual_reservoir_vol": 15.0, "hydrant_count": 5},
    )
    print(f" ✔ [수치검산] 소화수조 유효용량 검토: {math2.get('judgement')} (실제 15.0 m³ >= 요구 13.0 m³)")

    report2_md = f"""# 1. 검토 개요
- **검토 대상:** 지하 2층 기계실 옥내소화전 소화수조 용량 및 가압송수펌프 양정
- **근거 기준:** {law2.get('law_name')} 제{law2.get('article_no')}조 및 {kcsc2.get('standard_code')}

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 법령 및 KCSC 기준 | 발주처 요구조건 | 시공사 제출 설계치 | 판정 결과 | 비고 / 조치사항 |
|---|---|---|---|---|---|
| 소화수조 유효수량 | KCS 31 10 00 (V >= 5 x 2.6 = 13.0 m³) | 유효용량 15.0 m³ 이상 | 설계용량 15.0 m³ | **PASS (적합)** | 기준 대비 +15.4% 여유 확보 |
| 소화펌프 방수압력 | 소방시설법 (P >= 0.17 MPa) | 최상층 방수압 0.25 MPa | 정격토출압 0.32 MPa | **PASS (적합)** | 규격 적정 |
| 펌프 정격 토출량 | KCS 31 10 00 (Q >= 650 L/min) | 토출량 700 L/min | 설계 토출량 700 L/min | **PASS (적합)** | 적정 |

# 3. 세부 수치 검산 내역
- **소화수조 용량 산정식:** $V = N \\times 2.6 = 5 \\times 2.6 = 13.0\\text{{ m}}^3$
- **설계 저수량:** $15.0\\text{{ m}}^3$ (여유율 $+15.38\\%$) -> **적합(PASS)**

# 4. 종합 감리의견
- 소방 수조 및 펌프 용량 계산 결과 관련 법령 및 발주처 시방기준을 모두 만족하므로 **[원안 승인]**함.
"""
    doc2 = export_review_document(
        output_filename="소방설비_CM검토의견서.docx",
        report_text=report2_md,
        project_name="삼우씨엠 판교 데이터센터 신축공사",
        reviewer_name="박수석 건설사업관리기술인 (기계/소방)",
        discipline="기계 / 소방",
    )
    print(f" ✔ [의견서생성] 삼우씨엠 표준 Word 문서 생성 완료: {doc2.get('docx_path')}")

    # -------------------------------------------------------------
    # Scenario 3: 전기/건축 전압강하 및 외벽 열관류율 검토 (KEC 232 / KDS 41 10 00)
    # -------------------------------------------------------------
    print("\n[시나리오 3: 전기/건축 전압강하율 및 외벽 열관류율 3자 검토]")
    law3 = fetch_national_law("전기사업법", "67")
    kcsc3 = fetch_kcsc_standard("KEC 232")
    print(f" ✔ [국가법령] {law3.get('law_name')} 제{law3.get('article_no')}조 ({law3.get('title')}) 연동 완료")
    print(f" ✔ [KCSC기준] {kcsc3.get('standard_code')} ({kcsc3.get('standard_name')}) 수신 완료")

    math3 = verify_calculation_safety(
        item_name="지하주차장 동력 간선 전압강하율",
        domain="전기/통신",
        formula_type="elec_voltage_drop_pct",
        variables={"length_m": 85, "current_a": 150, "wire_area_sqmm": 50, "nominal_voltage": 380, "max_drop_pct": 3.0},
    )
    print(f" ✔ [수치검산] 선로 전압강하율 검토: {math3.get('calculated_value')}% (허용: 3.0%, 판정: {math3.get('judgement')})")

    report3_md = f"""# 1. 검토 개요
- **검토 대상:** 지하주차장 동력 배선 간선 전압강하율 및 외벽 단열 성능
- **근거 기준:** {law3.get('law_name')} 제{law3.get('article_no')}조 및 {kcsc3.get('standard_code')}

# 2. 3자 교차 검토 종합 대조표
| 검토 항목 | 기준 및 KEC 규정 | 발주처 요구조건 | 시공사 제출 설계치 | 판정 결과 | 비고 / 조치사항 |
|---|---|---|---|---|---|
| 간선 전압강하율 | KEC 232 (허용강하율 <= 3.0%) | 조명/동력 공통 2.5% 이하 | e = 1.19% (CV 50sq, 85m) | **PASS (적합)** | 허용치(3.0%) 대비 충분한 여유 |
| 외벽 열관류율(U) | KDS 41 10 00 (U <= 0.170 W/m²K) | 특기시방 0.160 이하 | U = 0.155 (압출보온판 160mm) | **PASS (적합)** | 단열성능 만족 |

# 3. 세부 수치 검산 내역
- **3상 4선식 전압강하율 산정식:**
  $$e(\\%) = \\frac{{17.8 \\times L \\times I}}{{1000 \\times A \\times V}} \\times 100 = \\frac{{17.8 \\times 85 \\times 150}}{{1000 \\times 50 \\times 380}} \\times 100 = 1.194\\%$$
- **판정:** 규격 기준 $3.0\\%$ 이하 만족 -> **PASS (적합)**

# 4. 종합 감리의견
- 전기 간선 굵기 산정 및 단열재 열관류율 계산 결과 기준치를 충분히 만족하므로 **[원안 승인]**함.
"""
    doc3 = export_review_document(
        output_filename="전기및건축_CM검토의견서.docx",
        report_text=report3_md,
        project_name="삼우씨엠 마곡 R&D센터 신축공사",
        reviewer_name="이수석 건설사업관리기술인 (전기/건축)",
        discipline="전기 / 건축",
    )
    print(f" ✔ [의견서생성] 삼우씨엠 표준 Word 문서 생성 완료: {doc3.get('docx_path')}")

    print("\n" + "=" * 70)
    print(" 🎉 3대 시나리오 3자 교차 검토 및 감리의견서 자동 생성 데모 완료!")
    print(f" 📂 결과 문서 저장소: {SECURE_DATA_DIR}")
    print("=" * 70 + "\n")


def cmd_check_bundle(args):
    """Run batch cross-check across multiple submitted documents."""
    files = args.files
    if not files:
        print("Error: Please provide at least one filename to check.", file=sys.stderr)
        return

    checker = BatchCrossChecker()
    result = checker.cross_check_bundle(list(files))

    is_fail = "FAIL" in result["overall_verdict"] or result["total_discrepancies"] > 0
    verdict_str = f"보완 후 재제출 (FAIL)" if is_fail else f"적합 (PASS)"

    print("\n" + "=" * 65)
    print(f"[일괄 전수검사 결과] 최종 판정: {verdict_str}")
    print("=" * 65)
    print(f"- 검토 대상 파일: {', '.join(result['inspected_files'])}")
    print(f"- 검출된 불일치/미달 건수: {result['total_discrepancies']}건\n")

    if result["discrepancies"]:
        print("=== [발견된 불일치 및 결함 항목] ===")
        for idx, item in enumerate(result["discrepancies"], 1):
            print(f"{idx}. [{item['category']}] (심각도: {item['severity']})")
            print(f"   - 내용: {item['description']}")
            print(f"   - 조치사항: {item['action']}")
        print()

    if result["verified_matches"]:
        print("=== [검증된 일치/충족 항목] ===")
        for m in result["verified_matches"]:
            print(f" ✔ {m}")
        print()


def cmd_audit_diff(args):
    """Run document revision diff & pay application tampering audit."""
    res = audit_document_diff(args.base_file, args.target_file, args.category)
    print("\n" + "=" * 70)
    print(f"[도서/내역서 Diff & 변조 감사 결과] 최종 판정: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 기준 파일: {res.get('base_file')}  <--->  검토 대상: {res.get('target_file')}")
    print(f"- 감사 유형: {res.get('audit_type')}\n")

    if res.get("audit_type") == "PAY_APPLICATION_XLSX":
        fin = res.get("financial_summary", {})
        print("=== [공사비/기성 청구 금액 분석] ===")
        print(f"- 전회 승인액: {fin.get('base_claim_total', 0):,.0f}원")
        print(f"- 당회 청구액: {fin.get('target_claim_total', 0):,.0f}원 (증감: {fin.get('claimed_increase_vs_base', 0):+,.0f}원)")
        print(f"- 수학적 재검증액: {fin.get('recalculated_true_total', 0):,.0f}원")
        if fin.get("unauthorized_overbilling_amount", 0) > 0:
            print(f"- ⚠️ 불일치/과대청구 금액: +{fin.get('unauthorized_overbilling_amount', 0):,.0f}원 (삭감 대상)")
        print()

        print(f"=== [발견된 변조 및 불일치 항목: {res.get('total_findings_count', 0)}건 (CRITICAL: {res.get('critical_count', 0)}건)] ===")
        for idx, f in enumerate(res.get("findings", []), 1):
            print(f"{idx}. [{f['category']}] (심각도: {f['severity']}) - {f['item']}")
            print(f"   - 내용: {f['description']}")
            print(f"   - 조치: {f['action']}")
        print()
    else:
        print(f"=== [도서 개정 변경점: 총 {res.get('total_changes', 0)}건 (CRITICAL: {res.get('critical_changes', 0)}건)] ===")
        for idx, c in enumerate(res.get("changes", []), 1):
            print(f"{idx}. [{c['change_type']}] (심각도: {c['severity']}) - {c['description']}")
            if c.get("base_excerpt"):
                print(f"   - [기존 Rev0]: {c['base_excerpt']}")
            if c.get("target_excerpt"):
                print(f"   - [변경 Rev1]: {c['target_excerpt']}")
        print()


def cmd_checklist(args):
    """Generate dynamic checklist and evaluate contractor plan."""
    res = generate_and_evaluate_checklist(
        work_type=args.work_type,
        site_conditions=args.conditions,
        spec_file=args.spec,
        plan_file=args.plan,
    )
    print("\n" + "=" * 70)
    print(f"[현장 맞춤형 CM 체크리스트 & 시공계획서 판정] 최종 결과: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 대상 공종: {res.get('work_type')} | 현장 특성: {res.get('site_conditions')}")
    print(f"- 시공계획서 적합도 점수: {res.get('compliance_score_pct')}% (적합: {res.get('pass_count')}건 / 보완: {res.get('modify_count')}건 / 총: {res.get('total_items')}문항)\n")

    print("=== [세부 항목별 판정 및 매핑 근거] ===")
    for item in res.get("checklist_results", []):
        status_symbol = "✔" if "PASS" in item["status"] else "✖"
        print(f"{item['no']:02d}. [{item['id']}] {item['item']}")
        print(f"    - 판정: {status_symbol} {item['status']}")
        print(f"    - 근거 문구: {item['evidence']}")
        if "MODIFY" in item["status"]:
            print(f"    - 조치 지시: {item['action_required']}")
    print()


def cmd_search_std(args):
    """Semantic backtracking search for KDS/KCS/Laws."""
    res = search_standards_by_keyword(query=args.query, domain=args.domain, top_k=args.top)
    print("\n" + "=" * 70)
    print(f"[건설기준 & 법령 시맨틱 역추적 검색] 질의어: '{res.get('query')}' (결과: {res.get('total_matches')}건)")
    print("=" * 70)

    for idx, r in enumerate(res.get("top_results", []), 1):
        print(f"\n{idx}. [{r['code']}] {r['title']} (유사도: {r['score']}점 | 분류: {r['category']} - {r['discipline']})")
        print(f"   - 핵심 기준 본문: {r['excerpt']}")
        if r.get("formula_hint"):
            print(f"   - 💡 파이프라인 연계 공식: {r['formula_hint']}")
    print()


def cmd_memo_index(args):
    """Index an official document into project memory."""
    res = index_project_instruction(args.filename)
    print("\n" + "=" * 70)
    print(f"[프로젝트 메모리 색인 완료] {res.get('message')}")
    print("=" * 70)
    idx_data = res.get("indexed_data", {})
    print(f"- 문서번호: {idx_data.get('doc_no')}")
    print(f"- 시행일자: {idx_data.get('doc_date')}")
    print(f"- 발신처: {idx_data.get('issuer')}")
    print(f"- 건명: {idx_data.get('subject')}")
    print(f"- 핵심 지시사항: {idx_data.get('summary')}")
    print(f"- 조치 기한: {idx_data.get('deadline')}")
    print(f"- 관리 상태: {idx_data.get('status')}\n")


def cmd_memo_search(args):
    """Search past project memory instructions."""
    res = search_project_memory(query=args.query, status_filter=args.status)
    print("\n" + "=" * 70)
    print(f"[프로젝트 메모리 검색 결과] 질의어: '{res.get('query')}' (총 {res.get('total_found')}건 검색)")
    print("=" * 70)

    for idx, r in enumerate(res.get("results", []), 1):
        print(f"{idx}. [{r['doc_no']}] {r['subject']} ({r['doc_date']} | {r['issuer']})")
        print(f"   - 핵심 지시: {r['summary']}")
        print(f"   - 조치기한: {r['deadline']} | 상태: {r['status']}")
    print()


def cmd_change_track(args):
    """Track design changes across cumulative change log and construction plan."""
    res = track_design_changes(args.change_log, args.plan)
    print("\n" + "=" * 70)
    print(f"[설계변경(VE) 누적 추적 & 반영 검증] 최종 결과: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 내역서: {res.get('change_log_file')} <---> 검증 도서: {res.get('target_plan_file')}")
    print(f"- 변경 항목 총 {res.get('total_change_items')}건 (반영 확인: {res.get('matched_count')}건 / 누락: {res.get('omission_count')}건)\n")

    print("=== [설계변경 항목별 반영 검증표] ===")
    for idx, item in enumerate(res.get("change_tracking_matrix", []), 1):
        sym = "✔" if "MATCH" in item["status"] else "✖"
        print(f"{idx}. {item['item_name']} (승인 변경사양: {item['approved_change_spec']})")
        print(f"   - 판정: {sym} {item['status']} (사유: {item['change_reason']})")
        print(f"   - 근거: {item['evidence_in_plan']}")
        if "OMISSION" in item["status"]:
            print(f"   - 조치: {item['action_required']}")
    print()


def cmd_report_weekly(args):
    """Generate weekly CM report."""
    res = generate_weekly_cm_report(
        start_date=args.start,
        end_date=args.end,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[주간 감리업무 보고서 자동 생성 완료]")
    print("=" * 70)
    print(f"- 문서번호: {res.get('doc_no')}")
    print(f"- 보고기간: {res.get('period')}")
    print(f"- 사업명: {res.get('project_name')}")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")


def cmd_draft_notice(args):
    """Draft official outward CM notice letter."""
    res = draft_official_notice(
        doc_title=args.title,
        recipient=args.recipient,
        reference=args.ref,
        review_result_file=args.file,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[감리단 대외 정식 공문 기안 완료]")
    print("=" * 70)
    print(f"- 문서번호: {res.get('doc_no')}")
    print(f"- 공문 건명: {res.get('doc_title')}")
    print(f"- 수신처: {res.get('recipient')}")
    print(f"- Word 공문서: {res.get('docx_path')}")
    print(f"- Markdown 공문서: {res.get('md_path')}\n")


def cmd_review_auto(args):
    """Run full automated 3-way comprehensive review pipeline."""
    res = run_comprehensive_review(
        target_plan_file=args.target_plan_file,
        spec_file=args.spec,
        calc_file=args.calc,
        output_report_name=args.output,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[원클릭 종합 CM 기술검토 파이프라인 완료] 최종 판정: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 대상 시공계획서: {res.get('target_document')}")
    print(f"- 검토 요약: {res.get('summary_opinion')}")
    print(f"- Word 감리의견서: {res.get('generated_docx_file')}")
    print(f"- Markdown 감리의견서: {res.get('generated_md_file')}\n")

    print("=== [3자 교차 검토 종합 대조표] ===")
    for idx, r in enumerate(res.get("cross_comparison_table", []), 1):
        sym = "✔" if "PASS" in r["verdict"] or "적합" in r["verdict"] else "✖"
        print(f"{idx}. {r['item']} ➔ {sym} {r['verdict']}")
        print(f"   - 법령/KCSC 기준: {r['standard_basis']}")
        print(f"   - 시방 요구조건: {r['client_requirement']}")
        print(f"   - 시공사 제출값: {r['contractor_submission']}")
        print(f"   - 조치 사항: {r['notes']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Samwoo-CM-Bridge CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # serve
    subparsers.add_parser("serve", help="Run FastMCP stdio server")

    # list
    subparsers.add_parser("list", help="List files in secure_local_data/")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse a local project file")
    p_parse.add_argument("filename", help="Name of file in secure_local_data/")

    # check-bundle
    p_bundle = subparsers.add_parser("check-bundle", help="Batch cross-check multiple documents")
    p_bundle.add_argument("files", nargs="+", help="Filenames to cross-check")

    # audit-diff
    p_diff = subparsers.add_parser("audit-diff", help="Audit doc diff & pay application tampering")
    p_diff.add_argument("base_file", help="Baseline document / Rev0")
    p_diff.add_argument("target_file", help="Target document / Rev1")
    p_diff.add_argument("--category", "-c", default="AUTO", help="File category (AUTO, EXCEL, TEXT)")

    # checklist
    p_chk = subparsers.add_parser("checklist", help="Dynamic checklist & plan evaluator")
    p_chk.add_argument("work_type", help="Work type (e.g. '토공/가설', '골조/콘크리트', '기계/소방', '전기/통신')")
    p_chk.add_argument("--conditions", "-c", default="", help="Site conditions (e.g. '도심지, 지하수위, 동절기')")
    p_chk.add_argument("--spec", "-s", default="", help="Specification file")
    p_chk.add_argument("--plan", "-p", default="", help="Construction plan file")

    # search-std
    p_search = subparsers.add_parser("search-std", help="Semantic search for standards & laws")
    p_search.add_argument("query", help="Natural language query")
    p_search.add_argument("--domain", "-d", default="", help="Domain filter")
    p_search.add_argument("--top", "-t", type=int, default=3, help="Top K results")

    # memo-index
    p_m_idx = subparsers.add_parser("memo-index", help="Index document into project memory")
    p_m_idx.add_argument("filename", help="Document filename to index")

    # memo-search
    p_m_search = subparsers.add_parser("memo-search", help="Search project context memory")
    p_m_search.add_argument("query", help="Search query")
    p_m_search.add_argument("--status", "-s", default="", help="Status filter (PENDING, RESOLVED)")

    # change-track
    p_chg = subparsers.add_parser("change-track", help="Track design changes across log and plan")
    p_chg.add_argument("change_log", help="Change log spreadsheet (XLSX)")
    p_chg.add_argument("plan", help="Target construction plan file")

    # report-weekly
    p_rep = subparsers.add_parser("report-weekly", help="Generate weekly CM report")
    p_rep.add_argument("--start", default="", help="Start date (YYYY.MM.DD)")
    p_rep.add_argument("--end", default="", help="End date (YYYY.MM.DD)")
def cmd_daily_log(args):
    """Generate daily CM supervision log."""
    acts = [a.strip() for a in args.activities.split(";")] if args.activities else None
    res = generate_daily_cm_log(
        date_str=args.date,
        weather=args.weather,
        activities=acts,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[일일 감리업무일보 자동 생성 완료]")
    print("=" * 70)
    print(f"- 문서번호: {res.get('doc_no')} | 일자: {res.get('date')}")
    print(f"- 기상정보: {res.get('weather')}")
    print(f"- 투입인원: 총 {res.get('total_workers')}명 | 투입장비: 총 {res.get('total_equipment')}대")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")


def cmd_ocr_cert(args):
    """Run OCR and validate material test certificate."""
    res = parse_scanned_material_cert(args.file)
    print("\n" + "=" * 70)
    print(f"[자재 시험성적서/밀시트 OCR 판정] 최종 결과: {res.get('ks_compliance_verdict')}")
    print("=" * 70)
    meta = res.get("certificate_metadata", {})
    print(f"- 성적서 번호: {meta.get('report_no')} | 발행처: {meta.get('test_agency')}")
    print(f"- 강종/규격: {meta.get('material_grade')} | 용강/로트: {meta.get('heat_or_lot_no')}")
    print(f"- 시험 일자: {meta.get('issue_date')}\n")

    print("=== [추출된 역학/물리 시험 수치] ===")
    for k, v in res.get("test_results", {}).items():
        print(f" • {k}: {v}")
    print()

    if res.get("compliance_details"):
        print("=== [KS 규격 검증 상세] ===")
        for d in res.get("compliance_details", []):
            print(f" ✔ {d}")
        print()


def cmd_schedule_diff(args):
    """Analyze custom schedule spreadsheet progress and delays."""
    res = analyze_custom_schedule(args.file)
    print("\n" + "=" * 70)
    print(f"[공정표 진도율 및 지연 분석] 종합 판정: {res.get('overall_verdict')}")
    print("=" * 70)
    summary = res.get("project_progress_summary", {})
    print(f"- 평균 계획진도: {summary.get('average_planned_pct')}%")
    print(f"- 평균 실적진도: {summary.get('average_actual_pct')}% (대비: {summary.get('variance_pct'):+.1f}%p)")
    print(f"- 총 관리 액티비티: {res.get('total_activities_count')}건 (주의/심각 지연: {res.get('delayed_critical_count')}건)\n")

    if res.get("delayed_critical_activities"):
        print("=== [지연 중점 관리 공종 (Critical Path)] ===")
        for idx, act in enumerate(res.get("delayed_critical_activities", []), 1):
            print(f"{idx}. {act['name']} ➔ 계획 {act['planned_pct']}% vs 실적 {act['actual_pct']}% ({act['variance_pct']:+.1f}%p)")
            print(f"   - 상태: {act['status_description']}")
            print(f"   - 조치: {act['action_required']}")
        print()

    if res.get("schedule_recovery_demand_directive"):
        print("=== [감리단 공정만회대책 요구 명령서] ===")
        print(res.get("schedule_recovery_demand_directive"))
        print()


def cmd_tbm_safe(args):
    """Generate daily TBM safety checklist."""
    tasks = [t.strip() for t in args.tasks.split(";")] if args.tasks else ["지하 굴착", "가설 비계 설치"]
    res = generate_daily_tbm_safety(
        today_tasks_list=tasks,
        date_str=args.date,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[일일 TBM 안전점검표 및 위험성평가표 자동 생성 완료]")
    print("=" * 70)
    print(f"- 점검일자: {res.get('date')} | 분석 대상 공종: {', '.join(res.get('tasks_analyzed', []))}")
    print(f"- 도출된 유해위험요인: 총 {res.get('total_risk_factors')}건 (고위험 HIGH: {res.get('high_risk_count')}건)")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")

    print("=== [금일 중점 안전관리 대책 요약] ===")
    for idx, r in enumerate(res.get("evaluated_risks", []), 1):
        print(f"{idx}. [{r['task']}] {r['hazard']} (위험도: {r['risk_level']})")
        print(f"   - 대책: {r['safety_measures']}")
        print(f"   - 점검: {r['inspection_checkpoint']}")
    print()


def cmd_inspect_sheet(args):
    """Generate inspection request and result sheet."""
    res = generate_inspection_sheet(
        work_type=args.work_type,
        location=args.location,
        contractor_spec=args.spec,
    )
    print("\n" + "=" * 70)
    print(f"[검측요청서 및 결과통보서 자동 생성 완료] 최종 판정: {res.get('final_verdict')}")
    print("=" * 70)
    print(f"- 문서번호: {res.get('doc_no')}")
    print(f"- 검측공종: {res.get('work_type')} | 위치: {res.get('location')}")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")


def cmd_draft_ncr(args):
    """Draft formal Non-Conformance Report (NCR)."""
    res = draft_ncr_correction_order(
        issue_description=args.issue,
        location=args.location,
        defect_category=args.category,
        photo_attached=args.photo,
        corrective_deadline=args.deadline,
    )
    print("\n" + "=" * 70)
    print(f"[부적합 시정지시서 (NCR) 정식 발급 완료]")
    print("=" * 70)
    print(f"- 관리번호: {res.get('doc_no')}")
    print(f"- 부적합 분류: {res.get('defect_category')} | 위치: {res.get('location')}")
    print(f"- 시정기한: {res.get('deadline')}")
    print(f"- Word 공문서: {res.get('docx_path')}")
    print(f"- Markdown 공문서: {res.get('md_path')}\n")


def main():
    parser = argparse.ArgumentParser(description="Samwoo-CM-Bridge CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # serve
    subparsers.add_parser("serve", help="Run FastMCP stdio server")

    # list
    subparsers.add_parser("list", help="List files in secure_local_data/")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse a local project file")
    p_parse.add_argument("filename", help="Name of file in secure_local_data/")

    # check-bundle
    p_bundle = subparsers.add_parser("check-bundle", help="Batch cross-check multiple documents")
    p_bundle.add_argument("files", nargs="+", help="Filenames to cross-check")

    # audit-diff
    p_diff = subparsers.add_parser("audit-diff", help="Audit doc diff & pay application tampering")
    p_diff.add_argument("base_file", help="Baseline document / Rev0")
    p_diff.add_argument("target_file", help="Target document / Rev1")
    p_diff.add_argument("--category", "-c", default="AUTO", help="File category (AUTO, EXCEL, TEXT)")

    # checklist
    p_chk = subparsers.add_parser("checklist", help="Dynamic checklist & plan evaluator")
    p_chk.add_argument("work_type", help="Work type (e.g. '토공/가설', '골조/콘크리트', '기계/소방', '전기/통신')")
    p_chk.add_argument("--conditions", "-c", default="", help="Site conditions (e.g. '도심지, 지하수위, 동절기')")
    p_chk.add_argument("--spec", "-s", default="", help="Specification file")
    p_chk.add_argument("--plan", "-p", default="", help="Construction plan file")

    # search-std
    p_search = subparsers.add_parser("search-std", help="Semantic search for standards & laws")
    p_search.add_argument("query", help="Natural language query")
    p_search.add_argument("--domain", "-d", default="", help="Domain filter")
    p_search.add_argument("--top", "-t", type=int, default=3, help="Top K results")

    # memo-index
    p_m_idx = subparsers.add_parser("memo-index", help="Index document into project memory")
    p_m_idx.add_argument("filename", help="Document filename to index")

    # memo-search
    p_m_search = subparsers.add_parser("memo-search", help="Search project context memory")
    p_m_search.add_argument("query", help="Search query")
    p_m_search.add_argument("--status", "-s", default="", help="Status filter (PENDING, RESOLVED)")

    # change-track
    p_chg = subparsers.add_parser("change-track", help="Track design changes across log and plan")
    p_chg.add_argument("change_log", help="Change log spreadsheet (XLSX)")
    p_chg.add_argument("plan", help="Target construction plan file")

    # report-weekly
    p_rep = subparsers.add_parser("report-weekly", help="Generate weekly CM report")
    p_rep.add_argument("--start", default="", help="Start date (YYYY.MM.DD)")
    p_rep.add_argument("--end", default="", help="End date (YYYY.MM.DD)")
    p_rep.add_argument("--project", default="삼우씨엠 신축공사 CM현장", help="Project name")

    # draft-notice
    p_not = subparsers.add_parser("draft-notice", help="Draft official CM notice letter")
    p_not.add_argument("title", help="Letter subject / title")
    p_not.add_argument("--recipient", "-r", default="(주)대우건설 현장소장", help="Recipient")
    p_not.add_argument("--ref", default="발주처 감독관, 품질관리팀장", help="Reference")
    p_not.add_argument("--file", "-f", default="", help="Attached review result file")
    p_not.add_argument("--project", default="삼우씨엠 신축공사 CM현장", help="Project name")

    # review-auto
    p_rev = subparsers.add_parser("review-auto", help="End-to-end one-click comprehensive review pipeline")
    p_rev.add_argument("target_plan_file", help="Contractor construction plan file")
    p_rev.add_argument("--spec", "-s", default="", help="Specification file")
    p_rev.add_argument("--calc", "-c", default="", help="Calculation spreadsheet file")
    p_rev.add_argument("--output", "-o", default="종합_CM기술검토의견서.docx", help="Output Word report filename")
    p_rev.add_argument("--project", default="삼우씨엠 신축공사 CM현장", help="Project name")

    # daily-log
    p_dlog = subparsers.add_parser("daily-log", help="Generate daily CM supervision log")
    p_dlog.add_argument("--date", "-d", default="", help="Date (YYYY.MM.DD)")
    p_dlog.add_argument("--weather", "-w", default="맑음 (기온: 24.5℃, 강수량: 0mm)", help="Weather")
    p_dlog.add_argument("--activities", "-a", default="", help="Activities separated by semicolon (;)")
    p_dlog.add_argument("--project", default="삼우씨엠 신축공사 CM현장", help="Project name")

    # ocr-cert
    p_ocr = subparsers.add_parser("ocr-cert", help="OCR test certificate / Mill Sheet parser")
    p_ocr.add_argument("file", help="Certificate image/pdf file")

    # schedule-diff
    p_sch = subparsers.add_parser("schedule-diff", help="Analyze custom schedule progress & delay")
    p_sch.add_argument("file", help="Schedule Excel file (XLSX)")

    # tbm-safe
    p_tbm = subparsers.add_parser("tbm-safe", help="Generate daily TBM safety checklist")
    p_tbm.add_argument("--tasks", "-t", default="지하 토사 굴착; 가설 비계 설치; 크레인 양중", help="Tasks separated by semicolon (;)")
    p_tbm.add_argument("--date", "-d", default="", help="Date (YYYY.MM.DD)")
    p_tbm.add_argument("--project", default="삼우씨엠 신축공사 CM현장", help="Project name")

    # inspect-sheet
    p_insp = subparsers.add_parser("inspect-sheet", help="Generate inspection sheet & result")
    p_insp.add_argument("work_type", help="Work type (e.g. '가설 흙막이 지보공')")
    p_insp.add_argument("location", help="Location (e.g. '지하 2층 1구역')")
    p_insp.add_argument("--spec", "-s", default="", help="Specification")

    # draft-ncr
    p_ncr = subparsers.add_parser("draft-ncr", help="Draft Non-Conformance Report (NCR)")
    p_ncr.add_argument("issue", help="Defect / non-conformance description")
    p_ncr.add_argument("location", help="Defect location")
    p_ncr.add_argument("--category", "-c", default="시공품질 불량", help="Defect category")
    p_ncr.add_argument("--photo", "-p", default="현장 사진 첨부", help="Photo evidence")
    p_ncr.add_argument("--deadline", "-d", default="", help="Corrective deadline")

    # law
    p_law = subparsers.add_parser("law", help="Query national law article")
    p_law.add_argument("law_name", help="Name of law")
    p_law.add_argument("--article", "-a", dest="article_no", default="", help="Article number")

    # kcsc
    p_kcsc = subparsers.add_parser("kcsc", help="Query KCSC standard")
    p_kcsc.add_argument("code", help="Standard code (e.g. 'KDS 21 30 00')")

    # demo
    subparsers.add_parser("demo", help="Run full 3-way CM review demo")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "parse":
        cmd_parse(args)
    elif args.command == "check-bundle":
        cmd_check_bundle(args)
    elif args.command == "audit-diff":
        cmd_audit_diff(args)
    elif args.command == "checklist":
        cmd_checklist(args)
    elif args.command == "search-std":
        cmd_search_std(args)
    elif args.command == "memo-index":
        cmd_memo_index(args)
    elif args.command == "memo-search":
        cmd_memo_search(args)
    elif args.command == "change-track":
        cmd_change_track(args)
    elif args.command == "report-weekly":
        cmd_report_weekly(args)
    elif args.command == "draft-notice":
        cmd_draft_notice(args)
    elif args.command == "review-auto":
        cmd_review_auto(args)
    elif args.command == "daily-log":
        cmd_daily_log(args)
    elif args.command == "ocr-cert":
        cmd_ocr_cert(args)
    elif args.command == "schedule-diff":
        cmd_schedule_diff(args)
    elif args.command == "tbm-safe":
        cmd_tbm_safe(args)
    elif args.command == "inspect-sheet":
        cmd_inspect_sheet(args)
    elif args.command == "draft-ncr":
        cmd_draft_ncr(args)
    elif args.command == "law":
        cmd_law(args)
    elif args.command == "kcsc":
        cmd_kcsc(args)
    elif args.command == "demo":
        cmd_demo(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
