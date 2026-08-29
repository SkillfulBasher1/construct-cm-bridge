"""Adaptive CM Checklist Generator and Automatic Plan Evaluator (Module 2)

Dynamically generates tailored 15~20 inspection checklist items based on:
1. Work Discipline (토공/가설, 골조/철근콘크리트, 철골, 기계/소방, 전기, 마감/방수 등)
2. Site Conditions (도심지 인접, 고지하수위/연약지반, 암반파쇄, 동절기/서중 등)
3. Owner Specifications (특기시방서 HWPX/DOCX)

Automatically inspects contractor's construction plan (시공계획서) and assigns:
- Status: [PASS (적합) / MODIFY (보완필요) / NA (해당없음)]
- Compliance Score (%)
- Matched Evidence Excerpts
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
                {"id": "TC-01", "item": "지하 10m 이상 굴착 시 건진법 안전관리계획 수립 및 승인 여부", "req": "건진법 제62조 안전관리계획서 제출 및 인허가청 승인", "keywords": ["안전관리계획", "건진법", "굴착", "승인"]},
                {"id": "TC-02", "item": "가설 흙막이 버팀보(Strut) 좌굴 및 축력 안전율(Fs >= 1.25) 확보", "req": "KDS 21 30 00 기준 Fs 1.25 이상 구조계산 반영", "keywords": ["버팀보", "Strut", "1.25", "안전율", "좌굴"]},
                {"id": "TC-03", "item": "엄지말뚝(H-Pile) 근입깊이 및 천공홀 그라우팅 충진성", "req": "설계 근입깊이 확보 및 토사 유실 방지 그라우팅", "keywords": ["엄지말뚝", "H-Pile", "근입", "천공", "그라우팅"]},
                {"id": "TC-04", "item": "지반 앵커(Ground Anchor) 인장시험 및 인장력 안전율(Fs >= 1.5)", "req": "인장력 확인시험(전체 공수의 5% 이상) 및 긴장력 관리", "keywords": ["앵커", "인장시험", "긴장", "안전율", "1.5"]},
                {"id": "TC-05", "item": "토사 굴착 단계별 사면 구배 및 버팀보 선행 설치 절차", "req": "과굴착 금지 및 1단 굴착 후 즉시 지보공 설치", "keywords": ["굴착", "과굴착", "단계별", "사면", "선행"]},
                {"id": "TC-06", "item": "가설 강재 품질 규격 및 KS 정품 밀시트(Mill Sheet) 제출", "req": "KS D 3503(SS275) / KS D 3515(SM355) 자재검수", "keywords": ["강재", "KS", "SS275", "SM355", "밀시트", "성적서"]},
            ],
            "골조/콘크리트": [
                {"id": "RC-01", "item": "거푸집 및 동바리 구조안전성 계산서 및 조립도 검토", "req": "KDS 21 50 00 기준 동바리 허용응력 및 안전율 확보", "keywords": ["동바리", "거푸집", "구조계산", "조립도", "안전율"]},
                {"id": "RC-02", "item": "철근 배근 간격, 이음길이 및 피복두께 유지 계획", "req": "KDS 14 20 50 기준 이음/정착길이 및 스페이서 배치", "keywords": ["철근", "배근", "피복두께", "이음길이", "스페이서"]},
                {"id": "RC-03", "item": "레미콘 공장 배합설계 승인 및 슬럼프/공기량/염화물 검사", "req": "공장 배합표 승인 및 반입 차량별 품질검사(슬럼프, 염화물)", "keywords": ["배합설계", "슬럼프", "공기량", "염화물", "품질검사"]},
                {"id": "RC-04", "item": "콘크리트 타설 구획 및 이어치기(콜드조인트 방지) 계획", "req": "타설 속도 및 이어치기 시간 한도(외기 25℃ 이상 2.0시간 이내)", "keywords": ["이어치기", "콜드조인트", "타설구획", "타설속도"]},
                {"id": "RC-05", "item": "타설 후 수밀/습윤 보온 양생 및 거푸집 탈형 압축강도 관리", "req": "탈형 기준 압축강도(5MPa / 14MPa) 확보 시까지 양생", "keywords": ["양생", "습윤", "탈형", "압축강도", "강도확인"]},
            ],
            "기계/소방": [
                {"id": "MEP-01", "item": "옥내소화전설비 소화수조 법적/특기시방 유효수량 확보", "req": "소방시설법 및 KCS 31 10 00 기준 V >= N x 2.6 m³ 확보", "keywords": ["소화수조", "유효수량", "저수량", "2.6", "수원"]},
                {"id": "MEP-02", "item": "가압송수펌프 정격토출압력 및 토출량 선정 적정성", "req": "최상층 방수압력 0.17~0.70 MPa 및 정격 토출량 확보", "keywords": ["가압송수장치", "소화펌프", "방수압력", "토출량", "양정"]},
                {"id": "MEP-03", "item": "배관 수압시험(1.5배 이상 가압 2시간 유지) 및 누수 방지 계획", "req": "최고사용압력의 1.5배 이상 수압시험 및 감리 입회", "keywords": ["수압시험", "내압시험", "누수", "가압", "기밀"]},
                {"id": "MEP-04", "item": "방화구획 관통부 내화채움구조 시공 및 성적서 검토", "req": "건축법 제49조 및 내화채움 인증 자재 적용", "keywords": ["방화구획", "내화채움", "관통부", "시험성적서"]},
            ],
            "전기/통신": [
                {"id": "EL-01", "item": "수전설비 인입구로부터 최종 부하 간 전압강하율(<= 3.0%) 만족", "req": "KEC 232 규격 조명/동력 간선 전압강하 기준 준수", "keywords": ["전압강하", "KEC", "3.0%", "간선", "케이블"]},
                {"id": "EL-02", "item": "변압기 용량 산정 시 수용률, 부하율 및 여유율(15% 이상) 검토", "req": "수용 부하 집계 및 피크 부하 대비 적정 여유율 확보", "keywords": ["변압기", "수용률", "부하율", "용량", "여유율"]},
                {"id": "EL-03", "item": "통합 접지공사 및 접지저항값 기준 만족 여부", "req": "KEC 규정 기준 공통/통합접지 전위간섭 방지 및 등전위본딩", "keywords": ["접지", "접지저항", "등전위본딩", "접지극"]},
            ],
        }

        self.site_condition_modifiers = {
            "도심지": [
                {"id": "SITE-URB-01", "item": "[도심지 특화] 인접 건물 경사계(Tilt) 및 지표 침하계 계측(주 2회 이상)", "req": "인접 구조물 변위 허용기준(1/500) 이내 관리 및 일일 보고", "keywords": ["인접건물", "경사계", "침하계", "계측", "주2회", "변위"]},
                {"id": "SITE-URB-02", "item": "[도심지 특화] 굴착/항타 공사 소음(65dB 이하) 및 진동(0.2cm/s 이하) 방지 대책", "req": "방음벽 설치, 저소음 장비 적용 및 특정공사 사전신고", "keywords": ["소음", "진동", "방음벽", "저소음", "소음진동"]},
                {"id": "SITE-URB-03", "item": "[도심지 특화] 보행자 안전통로, 낙하물 방지망 및 교통정리원 배치 계획", "req": "현장 진출입로 신호수 2인 이상 상시 배치 및 보행로 분리", "keywords": ["보행자", "안전통로", "신호수", "낙하물", "교통정리"]},
            ],
            "지하수위": [
                {"id": "SITE-GW-01", "item": "[지하수 특화] 흙막이 배면 차수 그라우팅(JSP/SGR) 연속성 및 차수성 검증", "req": "투수계수 k <= 1.0x10^-5 cm/s 확보 및 확인시추", "keywords": ["차수", "그라우팅", "JSP", "SGR", "투수계수", "지하수"]},
                {"id": "SITE-GW-02", "item": "[지하수 특화] 굴착 저면 히빙(Heaving) 및 보일링(Boiling Fs >= 1.5) 검토", "req": "수두차에 의한 분사현상 방지 및 웰포인트/디프웰 양수 계획", "keywords": ["히빙", "보일링", "안전율", "디프웰", "웰포인트", "양수"]},
                {"id": "SITE-GW-03", "item": "[지하수 특화] 지하수위계(Water Level Meter) 매일 자동계측 및 일일 수위 보고", "req": "수위 급변 시 즉시 공사 중단 및 비상 차수대책 가동", "keywords": ["수위계", "지하수위", "일일계측", "수위변화"]},
            ],
            "암반": [
                {"id": "SITE-RK-01", "item": "[암반 특화] 무진동/미진동 암파쇄 공법 적용 및 발파진동 제어 계획", "req": "보안물건 이격거리별 발파진동 규제기준(0.3 kine 이하) 준수", "keywords": ["암반", "암파쇄", "무진동", "발파", "진동제어"]},
            ],
            "동절기": [
                {"id": "SITE-COLD-01", "item": "[동절기 특화] 한중 콘크리트 보온양생(방풍막, 열풍기) 및 초기동해 방지 계획", "req": "타설 후 압축강도 5MPa 발현 시까지 5℃ 이상 보온 유지", "keywords": ["한중", "동절기", "보온", "열풍기", "초기동해", "온도기록"]},
            ],
            "서중": [
                {"id": "SITE-HOT-01", "item": "[서중 특화] 서중 콘크리트 타설 온도(35℃ 이하) 제어 및 급결 방지제 적용", "req": "직사광선 차단, 골재 살수 및 수화열 제어 계획", "keywords": ["서중", "타설온도", "수화열", "급결방지", "양생"]},
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
            # Add general construction items from civil/concrete
            checklist.extend(self.work_type_bank["토공/가설"][:3])
            checklist.extend(self.work_type_bank["골조/콘크리트"][:3])

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
                status = "PASS (적합)"
                pass_count += 1
                action = "승인 적정"
            else:
                status = "MODIFY (보완필요)"
                modify_count += 1
                action = f"시공계획서 내 누락된 관리기준({req[:40]}...) 보완 작성 지시"
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

        overall_verdict = "시공계획서 원안 승인 (PASS)" if score_pct >= 85.0 and modify_count == 0 else (
            "조건부 승인 및 보완 지시 (CONDITIONAL_PASS)" if score_pct >= 70.0 else "시공계획서 반려 및 전면 재작성 (REJECT)"
        )

        return {
            "status": "SUCCESS",
            "work_type": work_type,
            "site_conditions": site_conditions or "일반 현장 조건",
            "spec_file": spec_file or "-",
            "plan_file": plan_file or "-",
            "overall_verdict": overall_verdict,
            "compliance_score_pct": score_pct,
            "total_items": len(evaluated_items),
            "pass_count": pass_count,
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
