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
from .core.custom_requirement_auditor import audit_custom_spec_requirements
from .core.equipment_quantity_auditor import audit_calculation_quantity_drawing_match
from .core.concrete_qc_tracker import register_concrete_pour
from .core.ncr_action_sheet_builder import generate_before_after_sheet
from .core.subcontract_auditor import audit_subcontract_agreement
from .core.cm_final_report_assembler import assemble_cm_final_report
from .core.fire_hazard_conflict_detector import check_concurrent_work_fire_hazard
from .core.video_record_manager import generate_video_recording_log
from .core.weather_stop_work_trigger import issue_weather_stop_work_order


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
    """Run an evidence-based review with the bundled sample documents."""
    result = run_comprehensive_review(
        target_plan_file="sample_건축_단열및시공계획서.docx",
        spec_file="sample_과업지시서_특기시방.hwpx",
        calc_file="sample_가설흙막이_구조계산서.xlsx",
        output_report_name="샘플_근거기반_CM기술검토의견서.docx",
        project_name="샘플 데이터 검토",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

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
        print("=== [추출된 근거 및 일치 후보] ===")
        for m in result["verified_matches"]:
            print(f" ✔ {m}")
        print()


def cmd_audit_diff(args):
    """Compare document revisions and payment-sheet values."""
    res = audit_document_diff(args.base_file, args.target_file, args.category)
    print("\n" + "=" * 70)
    print(f"[도서/내역서 Diff 및 수치 비교 결과] 최종 판정: {res.get('overall_verdict')}")
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
            print(f"- ⚠️ 재계산 불일치 금액: +{fin.get('unauthorized_overbilling_amount', 0):,.0f}원 (원본 확인 필요)")
        print()

        print(f"=== [발견된 변경 및 불일치 항목: {res.get('total_findings_count', 0)}건 (CRITICAL: {res.get('critical_count', 0)}건)] ===")
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
    print(f"[현장 맞춤형 CM 체크리스트 & 시공계획서 근거 스캔] 최종 결과: {res.get('overall_verdict')}")
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
        sym = "⚠️" if "EVIDENCE_FOUND" in item["status"] else "✖"
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
    print(f"[자재 시험성적서/밀시트 OCR 추출] 문서 기재 판정: {res.get('ks_compliance_verdict')}")
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
    tasks = [t.strip() for t in args.tasks.split(";") if t.strip()]
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
        recipient=args.recipient,
    )
    print("\n" + "=" * 70)
    print(f"[부적합 시정지시서 (NCR) 초안 생성 완료]")
    print("=" * 70)
    print(f"- 관리번호: {res.get('doc_no')}")
    print(f"- 부적합 분류: {res.get('defect_category')} | 위치: {res.get('location')}")
    print(f"- 시정기한: {res.get('deadline')}")
    print(f"- Word 공문서: {res.get('docx_path')}")
    print(f"- Markdown 공문서: {res.get('md_path')}\n")



def cmd_audit_req(args):
    """Audit custom spec submission requirements against local files."""
    res = audit_custom_spec_requirements(
        spec_file=args.spec,
        target_work_type=args.work_type,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[특기시방 요구 제출도서 점검 완료] 종합 결과: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 기준 시방서: {res.get('spec_file')}")
    print(f"- 총 요구 제출물: {res.get('total_requirements')}건 (파일명 후보: {res.get('received_count')}건 / 미발견: {res.get('missing_count')}건 / 보완: {res.get('modify_count')}건)")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")

    print("=== [세부 시방 조항별 제출도서 대조표] ===")
    for r in res.get("requirements_matrix", []):
        sym = "✔" if "RECEIVED" in r["status"] else ("⚠️" if "MODIFY" in r["status"] else "✖")
        print(f"{r['no']}. [{r['required_doc_type']}] ➔ {sym} {r['status']}")
        print(f"   - 시방 조항: {r['clause_excerpt']}")
        print(f"   - 매핑 파일: {r['matched_local_file']}")
        print(f"   - 출처 좌표: {r['source_anchor']}")
        print(f"   - 감리 조치: {r['cm_action']}")
    print()


def cmd_audit_match(args):
    """Audit 3-way calculation vs BOQ vs drawing PDF match."""
    res = audit_calculation_quantity_drawing_match(
        calc_file=args.calc,
        boq_file=args.boq,
        drawing_pdf_file=args.pdf,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[계산서-산출서-도면(PDF) 3자 수치 교차검증 완료] 종합 판정: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 검증 대상 장비: 총 {res.get('total_equipments_checked')}종")
    print(f"- 도면 vs 산출서 불일치: {res.get('discrepancy_count')}건")
    print(f"- 산출서 수식오류/이상치: {res.get('boq_errors_count')}건")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")

    print("=== [장비 규격 및 수량 3자 대조표] ===")
    for idx, m in enumerate(res.get("3way_match_matrix", []), 1):
        sym = "✔" if "PASS" in m["status"] else "✖"
        print(f"{idx}. {m['equipment_name']} ➔ {sym} {m['status']}")
        print(f"   - 도면 PDF: {m['drawing_spec_qty']}")
        print(f"   - 산출서(XLSX): {m['boq_spec_qty']}")
        print(f"   - 계산서 근거: {m['calc_ref']}")
        print(f"   - 불일치 상세: {m['discrepancy_details']}")
        print(f"   - 출처 좌표: {m['source_anchors']}")
    print()

    if res.get("boq_errors_list"):
        print("=== [수량산출서 수식 오류 및 비정상 이상치] ===")
        for e_idx, err in enumerate(res.get("boq_errors_list", []), 1):
            if "discrepancy_amount" in err:
                print(f"{e_idx}. [{err['item_name']}] 수식 불일치 (기재금액 {err['stated_amount']:,.0f}원 vs 정산금액 {err['calculated_amount']:,.0f}원, 오차: {err['discrepancy_amount']:+,.0f}원)")
            else:
                print(f"{e_idx}. [{err['item_name']}] {err['reason']} ({err['abnormal_value']})")
            print(f"   - 출처: {err['source_anchor']}")
        print()


def cmd_qc_concrete(args):
    """Register concrete pour and track strength."""
    res = register_concrete_pour(
        date_str=args.date,
        location=args.location,
        spec_fck=args.fck,
        volume_m3=args.volume,
        remicon_spec=args.spec,
        measured_7d_mpa=args.m7d,
        measured_28d_mpa=args.m28d,
        project_name=args.project,
    )
    r7_str = f"{res.get('rate_7d_pct'):.1f}%" if res.get("rate_7d_pct") is not None else "-"
    r28_str = f"{res.get('rate_28d_pct'):.1f}%" if res.get("rate_28d_pct") is not None else "-"

    print("\n" + "=" * 70)
    print(f"[콘크리트 타설 등록 및 품질시험 관리] 최종 판정: {res.get('verdict')}")
    print("=" * 70)
    print(f"- 관리번호: {res.get('pour_no')} | 타설일자: {res.get('pour_date')}")
    print(f"- 타설부위: {res.get('location')} | 타설량: {res.get('volume_m3'):,.0f} m3 (규격: {res.get('remicon_spec')})")
    print(f"- 설계기준강도(fck): {res.get('spec_fck_mpa')} MPa")
    print(f"- 7일 강도 시험일: {res.get('test_7d_date')} (D{res.get('days_until_7d_test'):+d}일) ➔ 측정: {res.get('measured_7d_mpa') or '-'} MPa ({r7_str})")
    print(f"- 28일 강도 시험일: {res.get('test_28d_date')} (D{res.get('days_until_28d_test'):+d}일) ➔ 측정: {res.get('measured_28d_mpa') or '-'} MPa ({r28_str})")
    print(f"- 품질관리대장(XLSX): {res.get('ledger_path')}\n")


def cmd_sheet_ba(args):
    """Generate Before / After photo verification sheet."""
    res = generate_before_after_sheet(
        issue_title=args.title,
        before_img=args.before,
        after_img=args.after,
        description=args.desc,
        location=args.location,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[시정조치 확인서 (Before/After) 카드 생성 완료]")
    print("=" * 70)
    print(f"- 문서번호: {res.get('doc_no')} (관련 NCR: {res.get('ncr_no')})")
    print(f"- 지적건명: {res.get('issue_title')} | 위치: {res.get('location')}")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")


def cmd_audit_subcon(args):
    """Audit subcontract agreement and legal compliance."""
    res = audit_subcontract_agreement(
        subcontract_excel_file=args.file,
        contractor_name=args.contractor,
        subcontractor_name=args.subcontractor,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[하도급계약 적정성 검토 완료] 최종 판정: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 공종명: {res.get('contract_work_name')}")
    print(f"- 도급액: {res.get('original_contract_amount'):,.0f}원 vs 하도급액: {res.get('subcontract_amount'):,.0f}원")
    print(f"- 하도급 비율: {res.get('subcontract_ratio_pct'):.2f}% (법정 기준: 82.0% 이상)")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")

    print("=== [법정 심사기준별 세부 검토 대조표] ===")
    for item in res.get("review_matrix", []):
        sym = "✔" if "PASS" in item["status"] or "적정" in item["status"] or "적합" in item["status"] else "⚠️"
        print(f"{item['no']}. {item['review_topic']} ➔ {sym} {item['status']}")
        print(f"   - 기준: {item['legal_criteria']}")
        print(f"   - 제출: {item['submitted_value']}")
        print(f"   - 의견: {item['action']}")
    print()


def cmd_assemble_report(args):
    """Assemble final completion report from cumulative project records."""
    res = assemble_cm_final_report(
        project_name=args.project,
        report_type=args.type,
    )
    print("\n" + "=" * 70)
    print(f"[{res.get('report_type')} 자동 일괄 조립 완료]")
    print("=" * 70)
    print(f"- 문서번호: {res.get('doc_no')} | 공사명: {res.get('project_name')}")
    print(f"- 종합 공정률: {res.get('final_progress_pct')}% (준공 달성)")
    print(f"- 취합된 발주처/설계변경 지시: {res.get('assembled_instructions_count')}건")
    print(f"- 스캔된 감리 산출물 도서: 총 {res.get('scanned_artifacts_count')}건")
    print(f"- Word 완성본: {res.get('docx_path')}")
    print(f"- Markdown 완성본: {res.get('md_path')}\n")


def cmd_fire_conflict(args):
    """Detect hot work & combustible material concurrent work conflicts."""
    res = check_concurrent_work_fire_hazard(
        tasks_list=args.tasks,
        date_str=args.date,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[화재위험 동시작업 충돌 감지] 최종 판정: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 평가 작업 수: 총 {res.get('total_tasks_evaluated')}건 (화기 {res.get('hot_works_count')}건 / 가연성 {res.get('combustible_works_count')}건)")
    print(f"- 동시작업 충돌: {res.get('conflicts_count')}건 검출")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")

    if res.get("conflicts"):
        print("=== [동시작업 충돌 상세 내역] ===")
        for idx, conf in enumerate(res["conflicts"], 1):
            print(f"{idx}. 위치: {conf['conflict_location']} ➔ 🚨 {conf['risk_level']}")
            print(f"   - 화기작업 (점화원): {conf['hot_work']}")
            print(f"   - 가연성물질 (연소원): {conf['combustible_work']}")
            print(f"   - 조치요구: {conf['mandatory_action']}")
    print()


def cmd_video_log(args):
    """Generate structural member video recording register."""
    res = generate_video_recording_log(
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[주요 구조부 동영상 촬영 기록관리대장 조립 완료]")
    print("=" * 70)
    print(f"- 문서번호: {res.get('doc_no')}")
    print(f"- 등록된 검측 동영상: 총 {res.get('total_video_records')}건")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")


def cmd_weather_stop(args):
    """Screen weather-sensitive work for responsible review."""
    res = issue_weather_stop_work_order(
        rain_mm=args.rain,
        wind_speed_ms=args.wind,
        rain_threshold_mm=args.rain_threshold,
        wind_threshold_ms=args.wind_threshold,
        planned_work=args.work,
        temp_c=args.temp,
        project_name=args.project,
    )
    print("\n" + "=" * 70)
    print(f"[기상조건 작업중지 검토] 종합 결과: {res.get('overall_verdict')}")
    print("=" * 70)
    print(f"- 기상 조건: 강우량 {res.get('rain_mm')} mm/hr, 풍속 {res.get('wind_speed_ms')} m/s, 기온 {res.get('temp_c')} ℃")
    print(f"- 작업중지 검토 후보: 총 {res.get('stop_items_count')}건")
    print(f"- Word 파일: {res.get('docx_path')}")
    print(f"- Markdown 파일: {res.get('md_path')}\n")

    if res.get("stop_items"):
        print("=== [작업중지 검토 상세 내역] ===")
        for idx, item in enumerate(res["stop_items"], 1):
            print(f"{idx}. 구분: {item['category']} ➔ 🛑 {item['stop_level']}")
            print(f"   - 기상 측정: {item['weather_metric']}")
            print(f"   - 선별 기준: {item['screening_criterion']}")
            print(f"   - 중지 대상: {', '.join(item['target_work'])}")
            print(f"   - 지시 사항: {item['order_details']}")
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
    p_diff = subparsers.add_parser("audit-diff", help="Review document changes and arithmetic discrepancies")
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
    p_rep.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # draft-notice
    p_not = subparsers.add_parser("draft-notice", help="Draft official CM notice letter")
    p_not.add_argument("title", help="Letter subject / title")
    p_not.add_argument("--recipient", "-r", default="미입력 시공사 현장소장", help="Recipient")
    p_not.add_argument("--ref", default="발주처 감독관, 품질관리팀장", help="Reference")
    p_not.add_argument("--file", "-f", default="", help="Attached review result file")
    p_not.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # review-auto
    p_rev = subparsers.add_parser("review-auto", help="End-to-end one-click comprehensive review pipeline")
    p_rev.add_argument("target_plan_file", help="Contractor construction plan file")
    p_rev.add_argument("--spec", "-s", default="", help="Specification file")
    p_rev.add_argument("--calc", "-c", default="", help="Calculation spreadsheet file")
    p_rev.add_argument("--output", "-o", default="종합_CM기술검토의견서.docx", help="Output Word report filename")
    p_rev.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # daily-log
    p_dlog = subparsers.add_parser("daily-log", help="Generate daily CM supervision log")
    p_dlog.add_argument("--date", "-d", default="", help="Date (YYYY.MM.DD)")
    p_dlog.add_argument("--weather", "-w", default="미입력", help="Weather")
    p_dlog.add_argument("--activities", "-a", default="", help="Activities separated by semicolon (;)")
    p_dlog.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # ocr-cert
    p_ocr = subparsers.add_parser("ocr-cert", help="OCR test certificate / Mill Sheet parser")
    p_ocr.add_argument("file", help="Certificate image/pdf file")

    # schedule-diff
    p_sch = subparsers.add_parser("schedule-diff", help="Analyze custom schedule progress & delay")
    p_sch.add_argument("file", help="Schedule Excel file (XLSX)")

    # tbm-safe
    p_tbm = subparsers.add_parser("tbm-safe", help="Generate daily TBM safety checklist")
    p_tbm.add_argument("--tasks", "-t", required=True, help="Tasks separated by semicolon (;)")
    p_tbm.add_argument("--date", "-d", default="", help="Date (YYYY.MM.DD)")
    p_tbm.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # inspect-sheet
    p_insp = subparsers.add_parser("inspect-sheet", help="Generate inspection sheet & result")
    p_insp.add_argument("work_type", help="Work type (e.g. '가설 흙막이 지보공')")
    p_insp.add_argument("location", help="Location (e.g. '지하 2층 1구역')")
    p_insp.add_argument("--spec", "-s", default="", help="Specification")

    # draft-ncr
    p_ncr = subparsers.add_parser("draft-ncr", help="Draft Non-Conformance Report (NCR)")
    p_ncr.add_argument("issue", help="Defect / non-conformance description")
    p_ncr.add_argument("location", help="Defect location")
    p_ncr.add_argument("--category", "-c", default="미분류", help="Defect category")
    p_ncr.add_argument("--photo", "-p", default="미첨부", help="Photo evidence")
    p_ncr.add_argument("--deadline", "-d", default="", help="Corrective deadline")
    p_ncr.add_argument("--recipient", "-r", default="미입력 시공사 현장소장", help="Draft recipient")

    # audit-req
    p_req = subparsers.add_parser("audit-req", help="Audit custom spec submission requirements")
    p_req.add_argument("--spec", "-s", required=True, help="Special specification file (HWPX/DOCX)")
    p_req.add_argument("--work-type", "-w", default="", help="Target work type filter")
    p_req.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # audit-match
    p_match = subparsers.add_parser("audit-match", help="Audit 3-way calculation vs BOQ vs drawing PDF match")
    p_match.add_argument("--calc", "-c", required=True, help="Calculation spreadsheet file (XLSX)")
    p_match.add_argument("--boq", "-b", required=True, help="Quantity takeoff / BOQ file (XLSX)")
    p_match.add_argument("--pdf", "-p", required=True, help="Drawing equipment schedule file (PDF)")
    p_match.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # qc-concrete
    p_conc = subparsers.add_parser("qc-concrete", help="Register concrete pour and track strength")
    p_conc.add_argument("--date", "-d", required=True, help="Pour date (YYYY.MM.DD)")
    p_conc.add_argument("--location", "-l", required=True, help="Pour location")
    p_conc.add_argument("--fck", "-f", type=float, required=True, help="Design fck (MPa)")
    p_conc.add_argument("--volume", "-v", type=float, required=True, help="Pour volume (m3)")
    p_conc.add_argument("--spec", "-s", default="미입력", help="Remicon spec")
    p_conc.add_argument("--m7d", type=float, default=None, help="Measured 7-day strength (MPa)")
    p_conc.add_argument("--m28d", type=float, default=None, help="Measured 28-day strength (MPa)")
    p_conc.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # sheet-ba
    p_ba = subparsers.add_parser("sheet-ba", help="Generate Before/After photo sheet")
    p_ba.add_argument("title", help="Issue title")
    p_ba.add_argument("before", help="Before photo filename")
    p_ba.add_argument("after", help="After photo filename")
    p_ba.add_argument("--desc", "-d", required=True, help="Action description")
    p_ba.add_argument("--location", "-l", default="미입력", help="Location")
    p_ba.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # audit-subcon
    p_sub = subparsers.add_parser("audit-subcon", help="Audit subcontract agreement")
    p_sub.add_argument("file", help="Subcontract agreement Excel file (XLSX)")
    p_sub.add_argument("--contractor", "-c", default="미입력 시공사", help="Contractor name")
    p_sub.add_argument("--subcontractor", "-s", default="미입력 하수급인", help="Subcontractor name")
    p_sub.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # assemble-report
    p_ass = subparsers.add_parser("assemble-report", help="Assemble final CM completion report")
    p_ass.add_argument("--project", default="미입력 프로젝트", help="Project name")
    p_ass.add_argument("--type", "-t", default="준공 감리완료보고서", help="Report type")

    # fire-conflict
    p_fire = subparsers.add_parser("fire-conflict", help="Detect hot work & combustible material conflicts")
    p_fire.add_argument("--tasks", "-t", required=True, help="Tasks list separated by semicolon (;)")
    p_fire.add_argument("--date", "-d", default="", help="Inspection date")
    p_fire.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # video-log
    p_vid = subparsers.add_parser("video-log", help="Generate video recording register")
    p_vid.add_argument("--project", default="미입력 프로젝트", help="Project name")

    # weather-stop
    p_wea = subparsers.add_parser("weather-stop", help="Screen weather-sensitive work for review")
    p_wea.add_argument("--rain", "-r", type=float, required=True, help="Rainfall (mm/hr)")
    p_wea.add_argument("--wind", "-w", type=float, required=True, help="Wind speed (m/s)")
    p_wea.add_argument("--rain-threshold", type=float, default=None, help="Project-approved rainfall screening threshold (mm/hr)")
    p_wea.add_argument("--wind-threshold", type=float, default=None, help="Equipment/project wind screening threshold (m/s)")
    p_wea.add_argument("--work", default="미입력", help="Planned work")
    p_wea.add_argument("--temp", type=float, default=None, help="Temperature (℃)")
    p_wea.add_argument("--project", default="미입력 프로젝트", help="Project name")

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
    elif args.command == "audit-req":
        cmd_audit_req(args)
    elif args.command == "audit-match":
        cmd_audit_match(args)
    elif args.command == "qc-concrete":
        cmd_qc_concrete(args)
    elif args.command == "sheet-ba":
        cmd_sheet_ba(args)
    elif args.command == "audit-subcon":
        cmd_audit_subcon(args)
    elif args.command == "assemble-report":
        cmd_assemble_report(args)
    elif args.command == "fire-conflict":
        cmd_fire_conflict(args)
    elif args.command == "video-log":
        cmd_video_log(args)
    elif args.command == "weather-stop":
        cmd_weather_stop(args)
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
