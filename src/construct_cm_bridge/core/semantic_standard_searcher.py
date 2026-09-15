"""Semantic Standard & Legal Searcher with Backtracking (Module 3)

Analyzes natural language engineering queries (e.g., '버팀보 허용응력', '피난계단 보행거리',
'소화수조 유효수량', '간선 전압강하율') and backtracks them to relevant:
- KDS (설계기준) / KCS (표준시방서) codes
- National statutory articles (건축법, 주택법, 건진법, 소방시설법, 전기사업법 등)
- Core numeric thresholds and suggested Python verification formula hints.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .openapi_client import OpenApiClient

logger = logging.getLogger(__name__)


class SemanticStandardSearcher:
    """Natural Language Semantic Searcher for Construction Standards and Laws."""

    def __init__(self, api_client: Optional[OpenApiClient] = None):
        self.client = api_client or OpenApiClient()
        self._build_search_index()

    def _build_search_index(self):
        """Builds an inverted keyword & synonym index across all standards and laws."""
        self.corpus: List[Dict[str, Any]] = []

        # 1. Index KCSC standards from mock/cached DB
        for code, data in self.client.kcsc_mock.items():
            sections = data.get("sections", {})
            full_text = f"{data.get('standard_name', '')} {data.get('discipline', '')} "
            thresholds = []

            for s_key, s_val in sections.items():
                s_title = s_val.get("title", "")
                s_content = s_val.get("content", "")
                full_text += f"{s_title} {s_content} "

            # Determine pre-configured formula hints
            formula_hint = None
            if "21 30 00" in code:
                formula_hint = {"formula_type": "civil_strut_buckling", "req_sf": 1.25, "domain": "토목/구조"}
            elif "31 10 00" in code:
                formula_hint = {"formula_type": "fire_reservoir_hydrant", "domain": "소방"}
            elif "232" in code:
                formula_hint = {"formula_type": "elec_voltage_drop_pct", "domain": "전기/통신"}
            elif "41 10 00" in code:
                formula_hint = {"formula_type": "arch_u_value", "domain": "건축"}

            self.corpus.append({
                "type": "KCSC_STANDARD",
                "code": code,
                "title": data.get("standard_name", ""),
                "category": data.get("category", "건설기준"),
                "discipline": data.get("discipline", "공학"),
                "body": full_text,
                "formula_hint": formula_hint,
            })

        # 2. Index National Laws
        for law_name, law_data in self.client.laws_mock.items():
            articles = law_data.get("articles", {})
            for art_no, art in articles.items():
                art_title = art.get("title", "")
                art_content = art.get("content", "")
                full_text = f"{law_name} 제{art_no}조 {art_title} {art_content}"

                self.corpus.append({
                    "type": "NATIONAL_LAW",
                    "code": f"{law_name} 제{art_no}조",
                    "title": art_title,
                    "category": "국가법령",
                    "discipline": law_name,
                    "body": full_text,
                    "formula_hint": None,
                })

        # Synonyms dictionary for query expansion
        self.synonyms = {
            "버팀보": ["버팀보", "스트러트", "strut", "h-pile", "엄지말뚝", "흙막이", "좌굴", "지보공", "kds 21 30 00"],
            "흙막이": ["흙막이", "버팀보", "지보공", "지반앵커", "히빙", "보일링", "kds 21 30 00"],
            "안전율": ["안전율", "fs", "safety factor", "허용응력", "1.25", "1.5"],
            "피난계단": ["피난계단", "직통계단", "보행거리", "피난시설", "50미터", "30미터", "건축법 49조"],
            "소화수조": ["소화수조", "옥내소화전", "유효수량", "저수량", "가압송수장치", "kcs 31 10 00", "소방시설법"],
            "소화펌프": ["소화펌프", "가압송수펌프", "방수압력", "토출량", "양정", "kcs 31 10 00"],
            "전압강하": ["전압강하", "전압강하율", "간선", "배선", "kec 232", "전기사업법"],
            "변압기": ["변압기", "수용률", "부하율", "용량", "kec"],
            "열관류율": ["열관류율", "u-value", "단열재", "외벽", "에너지절약", "kds 41 10 00"],
            "안전관리계획": ["안전관리계획", "건진법", "62조", "10미터", "착공전"],
        }

    def search_standards(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """Searches standards and laws by natural language query with synonym expansion."""
        if not isinstance(query, str) or not query.strip():
            return {
                "status": "ERROR",
                "query": query,
                "domain_filter": domain or "전체",
                "total_matches": 0,
                "top_results": [],
                "pipeline_hint": None,
                "error": "검색어는 비어 있을 수 없습니다.",
            }
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            return {
                "status": "ERROR",
                "query": query,
                "domain_filter": domain or "전체",
                "total_matches": 0,
                "top_results": [],
                "pipeline_hint": None,
                "error": "top_k는 1 이상의 정수여야 합니다.",
            }
        clean_q = query.strip().lower()
        q_tokens = clean_q.split()

        # Expand query tokens using synonym dictionary
        expanded_terms = set(q_tokens)
        for word in q_tokens:
            for syn_key, syn_list in self.synonyms.items():
                if word in syn_key or syn_key in word:
                    expanded_terms.update(syn_list)

        results: List[Dict[str, Any]] = []

        for doc in self.corpus:
            doc_body = doc["body"].lower()
            doc_code = doc["code"].lower()
            doc_title = doc["title"].lower()

            score = 0.0
            matched_terms = []

            # 1. Exact query match boost
            if clean_q in doc_body or clean_q in doc_title:
                score += 40.0

            # 2. Token overlap score
            for term in expanded_terms:
                term_lower = term.lower()
                if term_lower in doc_code:
                    score += 30.0
                    matched_terms.append(term)
                elif term_lower in doc_title:
                    score += 20.0
                    matched_terms.append(term)
                elif term_lower in doc_body:
                    score += 10.0
                    matched_terms.append(term)

            # Domain filter if provided
            if domain and domain in doc["discipline"]:
                score += 15.0

            if score > 0:
                # Extract excerpt
                excerpt = ""
                for line in doc["body"].split("\n"):
                    if any(t in line.lower() for t in matched_terms[:2]):
                        excerpt = line.strip()[:140]
                        break
                if not excerpt:
                    excerpt = doc["body"][:140]

                results.append({
                    "score": round(score, 1),
                    "code": doc["code"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "discipline": doc["discipline"],
                    "excerpt": excerpt,
                    "matched_keywords": list(set(matched_terms)),
                    "formula_hint": doc.get("formula_hint"),
                })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        top_results = results[:top_k]

        return {
            "status": "SUCCESS",
            "query": query,
            "domain_filter": domain or "전체",
            "total_matches": len(results),
            "top_results": top_results,
            "pipeline_hint": top_results[0].get("formula_hint") if top_results else None,
        }


# Singleton instance
_searcher = SemanticStandardSearcher()


def search_standards_by_keyword(query: str, domain: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
    return _searcher.search_standards(query=query, domain=domain, top_k=top_k)
