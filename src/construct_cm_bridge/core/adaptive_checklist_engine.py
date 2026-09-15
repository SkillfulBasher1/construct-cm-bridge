"""Adaptive CM Checklist Generator and Automatic Plan Evaluator (Module 2)

Dynamically generates tailored 15~20 inspection checklist items based on:
1. Work Discipline (토공/가설, 골조/철근콘크리트, 철골, 기계/소방, 전기, 마감/방수 등)
2. Site Conditions (도심지 인접, 고지하수위/연약지반, 암반파쇄, 동절기/서중 등)
3. Owner Specifications (특기시방서 HWPX/DOCX)

Scans contractor plans for candidate evidence. Keyword matches are not approvals,
and embedded checklist thresholds must be checked against current project criteria.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .doc_parser import DocumentParser

logger = logging.getLogger(__name__)


class AdaptiveChecklistEngine:
    """Generates dynamic CM checklists and evaluates construction plans."""

    def __init__(self, parser: Optional[DocumentParser] = None):
        self.parser = parser or DocumentParser()
        self._init_checklist_bank()

    def _init_checklist_bank(self):
        """Initializes the master checklist criteria database."""
        self.work_type_bank = {
            "토공/가설": [
                {"id": "TC-01", "item": "굴착 안전관리계획의 적용·제출·승인 요건 확인", "req": "현행 적용 법령, 인허가조건 및 승인 안전관리계획 원문 확인", "keywords": ["안전관리계획", "굴착", "제출", "승인"]},
                {"id": "TC-02", "item": "가설 흙막이 버팀보(Strut) 좌굴 및 축력 안전율 검토", "req": "승인 구조계산서와 현행 적용 기준의 안전율·하중조합 확인", "keywords": ["버팀보", "Strut", "안전율", "좌굴"]},
                {"id": "TC-03", "item": "엄지말뚝(H-Pile) 근입깊이 및 천공홀 그라우팅 충진성", "req": "설계 근입깊이 확보 및 토사 유실 방지 그라우팅", "keywords": ["엄지말뚝", "H-Pile", "근입", "천공", "그라우팅"]},
                {"id": "TC-04", "item": "지반 앵커(Ground Anchor) 인장시험 및 인장력 안전율 검토", "req": "승인 설계도서·시방서의 시험빈도, 시험하중 및 긴장력 관리기준 확인", "keywords": ["앵커", "인장시험", "긴장", "안전율"]},
                {"id": "TC-05", "item": "토사 굴착 단계별 사면 구배 및 버팀보 선행 설치 절차", "req": "과굴착 금지 및 1단 굴착 후 즉시 지보공 설치", "keywords": ["굴착", "과굴착", "단계별", "사면", "선행"]},
                {"id": "TC-06", "item": "가설 강재 품질 규격 및 밀시트(Mill Sheet) 제출", "req": "승인 설계도서의 강종·규격과 자재 성적서 원문 대조", "keywords": ["강재", "강종", "규격", "밀시트", "성적서"]},
            ],
            "골조/콘크리트": [
                {"id": "RC-01", "item": "거푸집 및 동바리 구조안전성 계산서 및 조립도 검토", "req": "승인 구조계산서와 현행 적용 기준의 하중·허용응력·안전율 대조", "keywords": ["동바리", "거푸집", "구조계산", "조립도", "안전율"]},
                {"id": "RC-02", "item": "철근 배근 간격, 이음길이 및 피복두께 유지 계획", "req": "승인 구조도와 시방서의 이음·정착·피복 기준 및 스페이서 배치 확인", "keywords": ["철근", "배근", "피복두께", "이음길이", "스페이서"]},
                {"id": "RC-03", "item": "레미콘 공장 배합설계 승인 및 슬럼프/공기량/염화물 검사", "req": "공장 배합표 승인 및 반입 차량별 품질검사(슬럼프, 염화물)", "keywords": ["배합설계", "슬럼프", "공기량", "염화물", "품질검사"]},
                {"id": "RC-04", "item": "콘크리트 타설 구획 및 이어치기(콜드조인트 방지) 계획", "req": "승인 시공계획의 타설 속도·구획과 기온별 이어치기 시간 한도 확인", "keywords": ["이어치기", "콜드조인트", "타설구획", "타설속도"]},
                {"id": "RC-05", "item": "타설 후 습윤·보온 양생 및 거푸집 탈형 압축강도 관리", "req": "승인 시방서의 양생조건과 부위별 탈형강도 기준 확인", "keywords": ["양생", "습윤", "탈형", "압축강도", "강도확인"]},
            ],
            "기계/소방": [
                {"id": "MEP-01", "item": "옥내소화전설비 소화수조 유효수량 검토", "req": "현행 적용 법령, 소방 설계도서 및 특기시방의 유효수량 산식 확인", "keywords": ["소화수조", "유효수량", "저수량", "수원"]},
                {"id": "MEP-02", "item": "가압송수펌프 정격토출압력 및 토출량 선정 검토", "req": "승인 소방 설계도서의 방수압력·토출량·양정과 장비 성능곡선 대조", "keywords": ["가압송수장치", "소화펌프", "방수압력", "토출량", "양정"]},
                {"id": "MEP-03", "item": "배관 수압시험 및 누수 방지 계획", "req": "승인 시방서의 시험압력·유지시간·입회 및 합격 기준 확인", "keywords": ["수압시험", "내압시험", "누수", "가압", "기밀"]},
                {"id": "MEP-04", "item": "방화구획 관통부 내화채움구조 시공 및 성적서 검토", "req": "현행 적용 법령과 승인도서의 내화채움 인정·성적서 요건 확인", "keywords": ["방화구획", "내화채움", "관통부", "시험성적서"]},
            ],
            "전기/통신": [
                {"id": "EL-01", "item": "수전설비 인입구부터 최종 부하까지 전압강하율 검토", "req": "현행 전기설비 기준과 승인 설계도서의 회로별 허용 전압강하율 확인", "keywords": ["전압강하", "KEC", "간선", "케이블"]},
                {"id": "EL-02", "item": "변압기 용량 산정 시 수용률, 부하율 및 여유율 검토", "req": "승인 부하표의 수용률·부하율·피크 부하 및 설계 여유율 대조", "keywords": ["변압기", "수용률", "부하율", "용량", "여유율"]},
                {"id": "EL-03", "item": "통합 접지공사 및 접지저항값 기준 만족 여부", "req": "KEC 규정 기준 공통/통합접지 전위간섭 방지 및 등전위본딩", "keywords": ["접지", "접지저항", "등전위본딩", "접지극"]},
            ],
            "마감/방수": [
                {"id": "FIN-01", "item": "방수 바탕면 처리와 공정별 품질관리 계획", "req": "승인 설계도서와 특기시방서의 방수 공법 및 바탕면 기준 확인", "keywords": ["방수", "바탕면", "품질관리", "시방"]},
                {"id": "FIN-02", "item": "방수층 두께·겹침·단부 상세 및 담수시험 계획", "req": "승인 상세도와 제품 시방에 따른 시공 및 시험 계획 확인", "keywords": ["두께", "겹침", "단부", "담수시험"]},
                {"id": "FIN-03", "item": "마감재 시험성적서·색상·시공 견본 승인 계획", "req": "자재 반입 전 승인 자료와 시공 견본 확인", "keywords": ["시험성적서", "색상", "견본", "승인"]},
            ],
        }

        self.site_condition_modifiers = {
            "도심지": [
                {"id": "SITE-URB-01", "item": "[도심지 특화] 인접 건물 경사계 및 지표 침하계 계측 계획", "req": "승인 계측계획의 빈도·관리기준·보고 및 비상조치 기준 확인", "keywords": ["인접건물", "경사계", "침하계", "계측", "변위"]},
                {"id": "SITE-URB-02", "item": "[도심지 특화] 굴착·항타 공사 소음·진동 방지 대책", "req": "사업장 위치·시간대별 적용 기준, 신고조건 및 승인 관리기준 확인", "keywords": ["소음", "진동", "방음벽", "저소음", "소음진동"]},
                {"id": "SITE-URB-03", "item": "[도심지 특화] 보행자 안전통로, 낙하물 방지망 및 교통정리원 배치 계획", "req": "승인 교통처리·안전관리계획의 인원·위치·동선 분리 기준 확인", "keywords": ["보행자", "안전통로", "신호수", "낙하물", "교통정리"]},
            ],
            "지하수위": [
                {"id": "SITE-GW-01", "item": "[지하수 특화] 흙막이 배면 차수 그라우팅 연속성 및 차수성 검증", "req": "승인 설계도서의 투수계수·시공범위·품질확인 방법 대조", "keywords": ["차수", "그라우팅", "JSP", "SGR", "투수계수", "지하수"]},
                {"id": "SITE-GW-02", "item": "[지하수 특화] 굴착 저면 히빙 및 보일링 안전성 검토", "req": "승인 구조·지반 계산서의 수두조건·안전율과 양수계획 대조", "keywords": ["히빙", "보일링", "안전율", "디프웰", "웰포인트", "양수"]},
                {"id": "SITE-GW-03", "item": "[지하수 특화] 지하수위계(Water Level Meter) 매일 자동계측 및 일일 수위 보고", "req": "수위 급변 시 즉시 공사 중단 및 비상 차수대책 가동", "keywords": ["수위계", "지하수위", "일일계측", "수위변화"]},
            ],
            "암반": [
                {"id": "SITE-RK-01", "item": "[암반 특화] 암파쇄 공법 적용 및 발파진동 제어 계획", "req": "보안물건·이격거리·인허가조건별 승인 진동 관리기준 확인", "keywords": ["암반", "암파쇄", "무진동", "발파", "진동제어"]},
            ],
            "동절기": [
                {"id": "SITE-COLD-01", "item": "[동절기 특화] 한중 콘크리트 보온양생 및 초기동해 방지 계획", "req": "승인 시방서의 배합·타설·보온 온도와 양생 종료강도 기준 확인", "keywords": ["한중", "동절기", "보온", "열풍기", "초기동해", "온도기록"]},
            ],
            "서중": [
                {"id": "SITE-HOT-01", "item": "[서중 특화] 서중 콘크리트 타설 온도 제어 및 급결 방지 계획", "req": "승인 시방서의 재료·타설 온도와 운반·양생 관리기준 확인", "keywords": ["서중", "타설온도", "수화열", "급결방지", "양생"]},
            ],
        }

    def generate_checklist(
        self,
        work_type: str,
        site_conditions: str = "",
        spec_file: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generates dynamic checklist items tailored for the given work type, site conditions, and spec."""
        checklist: List[Dict[str, Any]] = []

        # 1. Base Work Type Items
        matched_work_key = None
        for key in self.work_type_bank:
            if any(k in work_type for k in key.split("/")):
                matched_work_key = key
                break

        if matched_work_key:
            checklist.extend(self.work_type_bank[matched_work_key])
        else:
            raise ValueError(f"지원하지 않는 공종입니다: {work_type}")

        # 2. Site Conditions Modifiers
        cond_text = site_conditions.strip()
        for cond_key, items in self.site_condition_modifiers.items():
            if cond_key in cond_text:
                checklist.extend(items)

        # 3. Project-Specific Spec Items (from spec_file if provided)
        if spec_file:
            try:
                parsed_spec = self.parser.parse_document(spec_file)
                spec_text = parsed_spec.get("markdown", "")
                spec_items = self._extract_spec_checklist_items(spec_text)
                checklist.extend(spec_items)
            except Exception as e:
                logger.warning(f"Failed to parse spec_file for checklist generation: {e}")

        # Remove duplicate IDs and normalize
        seen_ids = set()
        unique_checklist = []
        for idx, item in enumerate(checklist, 1):
            item_id = item.get("id", f"CHK-{idx:02d}")
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_checklist.append({
                    "no": len(unique_checklist) + 1,
                    "id": item_id,
                    "item": item["item"],
                    "requirement": item.get("req", ""),
                    "keywords": item.get("keywords", []),
                })

        return unique_checklist

    def _extract_spec_checklist_items(self, text: str) -> List[Dict[str, Any]]:
        """Extracts mandatory requirements from owner specification text."""
        spec_items = []
        # Find paragraphs with mandatory keywords ('하여야 한다', '필수', '승인을 득한')
        sentences = re.split(r'[.\n]', text)
        idx = 1
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 20 and any(k in s_clean for k in ["승인을 득하여야", "시험성적서를 제출", "안전율을 확보", "품질검사를 실시"]):
                spec_items.append({
                    "id": f"SPEC-REQ-{idx:02d}",
                    "item": f"[발주처 특기시방] {s_clean[:60]}...",
                    "req": s_clean,
                    "keywords": [w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', s_clean) if len(w) >= 3][:4],
                })
                idx += 1
                if idx > 5:
                    break
        return spec_items

    def evaluate_plan(
        self,
        work_type: str,
        site_conditions: str = "",
        spec_file: Optional[str] = None,
        plan_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates checklist and evaluates a contractor's construction plan against it."""
        checklist = self.generate_checklist(work_type, site_conditions, spec_file)

        plan_text = ""
        plan_meta = {}
        if plan_file:
            try:
                parsed_plan = self.parser.parse_document(plan_file)
                plan_text = parsed_plan.get("markdown", "")
                plan_meta = {"format": parsed_plan.get("format"), "length": len(plan_text)}
            except Exception as e:
                logger.error(f"Failed to read plan_file '{plan_file}': {e}")

        evaluated_items: List[Dict[str, Any]] = []
        pass_count = 0
        modify_count = 0

        for chk in checklist:
            item_text = chk["item"]
            keywords = chk["keywords"]
            req = chk["requirement"]

            if not plan_text:
                # No plan provided, just output empty checklist
                evaluated_items.append({
                    **chk,
                    "status": "UNCHECKED",
                    "evidence": "시공계획서 미제출",
                    "action_required": "검토 대기",
                })
                continue

            # Search plan text for keywords
            matched_keywords = [k for k in keywords if k.lower() in plan_text.lower()]
            match_ratio = len(matched_keywords) / len(keywords) if keywords else 0

            # Find matching sentence / excerpt
            evidence = ""
            for line in plan_text.splitlines():
                if any(k.lower() in line.lower() for k in matched_keywords[:2]):
                    evidence = line.strip()[:100]
                    break

            if match_ratio >= 0.5 or (len(matched_keywords) >= 2):
                status = "EVIDENCE_FOUND (수동판정필요)"
                pass_count += 1
                action = "인용 근거의 수치·도면 일치 여부를 책임기술인이 확인"
            else:
                status = "MODIFY (보완필요)"
                modify_count += 1
                action = f"체크리스트 후보({req[:40]}...)의 적용 여부와 최신 기준을 확인 후 보완"
                if not evidence:
                    evidence = "관련 내용 및 세부 관리계획 미언급"

            evaluated_items.append({
                "no": chk["no"],
                "id": chk["id"],
                "item": item_text,
                "requirement": req,
                "status": status,
                "evidence": evidence,
                "action_required": action,
            })

        total_eval = pass_count + modify_count
        score_pct = round((pass_count / total_eval) * 100, 1) if total_eval > 0 else 0.0

        if not plan_text:
            overall_verdict = "시공계획서 미제출로 판정 불가 (REVIEW_REQUIRED)"
        elif modify_count:
            overall_verdict = "누락 항목 보완 및 근거 수동검토 필요 (REVIEW_REQUIRED)"
        else:
            overall_verdict = "관련 근거 발견, 책임기술인 최종 판정 필요 (REVIEW_REQUIRED)"

        return {
            "status": "SUCCESS",
            "work_type": work_type,
            "site_conditions": site_conditions or "일반 현장 조건",
            "spec_file": spec_file or "-",
            "plan_file": plan_file or "-",
            "overall_verdict": overall_verdict,
            "compliance_score_pct": score_pct,
            "evidence_coverage_pct": score_pct,
            "metric_notice": "compliance_score_pct는 호환용 필드이며 적합률이 아닌 키워드 근거 발견률입니다.",
            "total_items": len(evaluated_items),
            "pass_count": pass_count,
            "evidence_found_count": pass_count,
            "modify_count": modify_count,
            "checklist_results": evaluated_items,
        }


# Singleton instance
_checklist_engine = AdaptiveChecklistEngine()


def generate_and_evaluate_checklist(
    work_type: str,
    site_conditions: str = "",
    spec_file: Optional[str] = None,
    plan_file: Optional[str] = None,
) -> Dict[str, Any]:
    return _checklist_engine.evaluate_plan(
        work_type=work_type,
        site_conditions=site_conditions,
        spec_file=spec_file,
        plan_file=plan_file,
    )
