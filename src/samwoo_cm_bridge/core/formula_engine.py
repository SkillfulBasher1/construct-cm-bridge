"""Multi-Disciplinary Engineering Math Verifier (Module 3)

Provides deterministic, Python-evaluated engineering safety verification
across 5 core domains:
- Civil / Structural (토목/구조)
- Mechanical / HVAC (기계/설비)
- Fire Protection (소방)
- Electrical / Telecom (전기/통신)
- Architectural / Building (건축)

Includes an extensible FormulaRegistry and a safe AST-based dynamic formula evaluator.
"""

import ast
import math
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


class SafeEvalVisitor(ast.NodeVisitor):
    """Safely evaluates mathematical expressions using Python AST without eval/exec vulnerabilities."""

    ALLOWED_NODES = {
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name,
        ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Compare,
        ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq, ast.Call
    }

    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "min": min,
        "max": max,
        "round": round,
        "sqrt": math.sqrt,
        "pow": math.pow,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
    }

    def __init__(self, variables: Dict[str, Union[int, float]]):
        self.variables = variables

    def generic_visit(self, node):
        if type(node) not in self.ALLOWED_NODES:
            raise ValueError(f"Disallowed expression node: {type(node).__name__}")
        return super().generic_visit(node)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    def visit_Name(self, node):
        if node.id in self.variables:
            return self.variables[node.id]
        elif node.id in self.ALLOWED_FUNCTIONS:
            return self.ALLOWED_FUNCTIONS[node.id]
        raise ValueError(f"Undefined variable in formula: '{node.id}'")

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
        raise ValueError(f"Unsupported unary operator: {type(node.op)}")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            if right == 0:
                raise ZeroDivisionError("Division by zero in formula calculation.")
            return left / right
        elif isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise ZeroDivisionError("Division by zero in formula calculation.")
            return left // right
        elif isinstance(node.op, ast.Mod):
            return left % right
        elif isinstance(node.op, ast.Pow):
            return left ** right
        raise ValueError(f"Unsupported binary operator: {type(node.op)}")

    def visit_Call(self, node):
        func = self.visit(node.func)
        args = [self.visit(arg) for arg in node.args]
        return func(*args)

    def visit_Compare(self, node):
        left = self.visit(node.left)
        result = True
        for op, comp in zip(node.ops, node.comparators):
            right = self.visit(comp)
            if isinstance(op, ast.Gt):
                result = result and (left > right)
            elif isinstance(op, ast.GtE):
                result = result and (left >= right)
            elif isinstance(op, ast.Lt):
                result = result and (left < right)
            elif isinstance(op, ast.LtE):
                result = result and (left <= right)
            elif isinstance(op, ast.Eq):
                result = result and (left == right)
            elif isinstance(op, ast.NotEq):
                result = result and (left != right)
            else:
                raise ValueError(f"Unsupported comparison operator: {type(op)}")
            left = right
        return result


def safe_eval(expression: str, variables: Dict[str, Union[int, float]]) -> Union[float, bool]:
    """Safely evaluates a mathematical expression string using AST."""
    tree = ast.parse(expression, mode="eval")
    visitor = SafeEvalVisitor(variables)
    return visitor.visit(tree)


class FormulaRegistry:
    """Registry of domain-specific engineering calculation formulas."""

    REGISTRY: Dict[str, Dict[str, Any]] = {
        # 1. 토목 / 가설구조 (Civil / Earth Retaining)
        "civil_safety_factor": {
            "domain": "토목/구조",
            "name": "일반 허용응력/안전율 산정",
            "formula_str": "allowable_val / design_val",
            "required_vars": ["design_val", "allowable_val", "req_sf"],
            "unit": "-",
            "eval_func": lambda vars: vars["allowable_val"] / vars["design_val"] if vars["design_val"] != 0 else 0,
            "check_func": lambda calc_val, vars: calc_val >= vars["req_sf"],
        },
        "civil_strut_buckling": {
            "domain": "토목/구조",
            "name": "가설 흙막이 버팀보(Strut) 좌굴 안전율",
            "formula_str": "allowable_axial_stress / design_axial_stress",
            "required_vars": ["design_axial_stress", "allowable_axial_stress", "req_sf"],
            "unit": "-",
            "eval_func": lambda vars: vars["allowable_axial_stress"] / vars["design_axial_stress"] if vars["design_axial_stress"] != 0 else 0,
            "check_func": lambda calc_val, vars: calc_val >= vars["req_sf"],
        },
        "civil_ground_anchor": {
            "domain": "토목/구조",
            "name": "가설 그라운드 앵커 인장 안전율",
            "formula_str": "ultimate_anchor_force / design_anchor_force",
            "required_vars": ["design_anchor_force", "ultimate_anchor_force", "req_sf"],
            "unit": "-",
            "eval_func": lambda vars: vars["ultimate_anchor_force"] / vars["design_anchor_force"] if vars["design_anchor_force"] != 0 else 0,
            "check_func": lambda calc_val, vars: calc_val >= vars["req_sf"],
        },
        # 2. 기계 / 설비 (Mechanical / HVAC)
        "mep_pump_head_margin": {
            "domain": "기계/설비",
            "name": "급수/순환 펌프 양정 여유율(%)",
            "formula_str": "((actual_head - required_head) / required_head) * 100",
            "required_vars": ["actual_head", "required_head", "min_margin_pct"],
            "unit": "%",
            "eval_func": lambda vars: ((vars["actual_head"] - vars["required_head"]) / vars["required_head"]) * 100 if vars["required_head"] != 0 else 0,
            "check_func": lambda calc_val, vars: calc_val >= vars["min_margin_pct"],
        },
        "mep_ventilation_rate": {
            "domain": "기계/설비",
            "name": "실내 필요 환기량 충족 여부",
            "formula_str": "actual_air_flow - (room_volume * required_ach)",
            "required_vars": ["actual_air_flow", "room_volume", "required_ach"],
            "unit": "CMH",
            "eval_func": lambda vars: vars["actual_air_flow"] - (vars["room_volume"] * vars["required_ach"]),
            "check_func": lambda calc_val, vars: calc_val >= 0,
        },
        # 3. 소방 (Fire Protection)
        "fire_reservoir_hydrant": {
            "domain": "소방",
            "name": "옥내소화전설비 유효저수량 검토",
            "formula_str": "actual_reservoir_vol - (min(hydrant_count, 5) * 2.6)",
            "required_vars": ["actual_reservoir_vol", "hydrant_count"],
            "unit": "m³",
            "eval_func": lambda vars: vars["actual_reservoir_vol"] - (min(vars["hydrant_count"], 5) * 2.6),
            "check_func": lambda calc_val, vars: calc_val >= 0,
        },
        "fire_sprinkler_flow": {
            "domain": "소방",
            "name": "스프링클러 헤드 토출량 (K*sqrt(10*P))",
            "formula_str": "k_factor * sqrt(10 * pressure_mpa)",
            "required_vars": ["k_factor", "pressure_mpa", "req_min_flow"],
            "unit": "L/min",
            "eval_func": lambda vars: vars["k_factor"] * math.sqrt(10 * vars["pressure_mpa"]),
            "check_func": lambda calc_val, vars: calc_val >= vars["req_min_flow"],
        },
        # 4. 전기 / 통신 (Electrical / Telecom)
        "elec_voltage_drop_pct": {
            "domain": "전기/통신",
            "name": "3상 4선식 선로 전압강하율(%) 검토",
            "formula_str": "((17.8 * length_m * current_a) / (1000 * wire_area_sqmm * nominal_voltage)) * 100",
            "required_vars": ["length_m", "current_a", "wire_area_sqmm", "nominal_voltage", "max_drop_pct"],
            "unit": "%",
            "eval_func": lambda vars: ((17.8 * vars["length_m"] * vars["current_a"]) / (1000 * vars["wire_area_sqmm"] * vars["nominal_voltage"])) * 100,
            "check_func": lambda calc_val, vars: calc_val <= vars["max_drop_pct"],
        },
        "elec_transformer_load": {
            "domain": "전기/통신",
            "name": "변압기 부하율 및 여유 용량 검토",
            "formula_str": "(connected_load_kva * demand_factor) / transformer_capacity_kva * 100",
            "required_vars": ["connected_load_kva", "demand_factor", "transformer_capacity_kva", "max_load_pct"],
            "unit": "%",
            "eval_func": lambda vars: (vars["connected_load_kva"] * vars["demand_factor"]) / vars["transformer_capacity_kva"] * 100,
            "check_func": lambda calc_val, vars: calc_val <= vars["max_load_pct"],
        },
        # 5. 건축 (Architectural)
        "arch_u_value": {
            "domain": "건축",
            "name": "외벽 열관류율(U-value) 검토",
            "formula_str": "1.0 / (0.13 + (insulation_thick_m / lambda_val) + 0.15 + 0.043)",
            "required_vars": ["insulation_thick_m", "lambda_val", "max_u_value"],
            "unit": "W/m²·K",
            "eval_func": lambda vars: 1.0 / (0.13 + (vars["insulation_thick_m"] / vars["lambda_val"]) + 0.15 + 0.043),
            "check_func": lambda calc_val, vars: calc_val <= vars["max_u_value"],
        },
    }


class FormulaEngine:
    """Verification Engine for Engineering Safety & Calculations."""

    def __init__(self):
        self.registry = FormulaRegistry.REGISTRY

    def verify(
        self,
        item_name: str,
        domain: Optional[str] = None,
        design_val: Optional[float] = None,
        allowable_val: Optional[float] = None,
        req_sf: Optional[float] = None,
        formula_type: Optional[str] = None,
        custom_formula: Optional[str] = None,
        variables: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Verifies calculation safety deterministically using Python.

        Args:
            item_name: Description of member/equipment (e.g. '1단 버팀보(H-300x300)', '소화펌프 주펌프')
            domain: Engineering discipline ('토목/구조', '기계/설비', '소방', '전기/통신', '건축')
            design_val: Design/Applied load value
            allowable_val: Allowable capacity/stress value
            req_sf: Required safety factor or threshold
            formula_type: Key in FormulaRegistry (e.g. 'civil_safety_factor', 'elec_voltage_drop_pct')
            custom_formula: User-defined formula string (e.g. 'allowable_val / design_val')
            variables: Variable dict for formula evaluation
        """
        vars_dict = variables.copy() if variables else {}

        # Fill standard vars if provided directly
        if design_val is not None:
            vars_dict["design_val"] = float(design_val)
        if allowable_val is not None:
            vars_dict["allowable_val"] = float(allowable_val)
        if req_sf is not None:
            vars_dict["req_sf"] = float(req_sf)

        # 1. Custom Formula Evaluation via Safe AST
        if custom_formula:
            try:
                calc_val = float(safe_eval(custom_formula, vars_dict))
                threshold = req_sf if req_sf is not None else vars_dict.get("req_sf", 1.0)
                is_pass = calc_val >= threshold
                margin_pct = ((calc_val - threshold) / threshold) * 100 if threshold != 0 else 0

                return {
                    "status": "SUCCESS",
                    "item_name": item_name,
                    "domain": domain or "사용자 정의",
                    "formula_name": "커스텀 수식 검증",
                    "formula": custom_formula,
                    "variables": vars_dict,
                    "calculated_value": round(calc_val, 4),
                    "threshold_value": threshold,
                    "margin_pct": round(margin_pct, 2),
                    "judgement": "PASS (적합)" if is_pass else "FAIL (부적합/보완필요)",
                    "action_required": "승인 가능" if is_pass else f"기준치({threshold}) 미달 (계산값 {round(calc_val, 3)}), 규격 증대 및 재계산 요구",
                }
            except Exception as e:
                logger.error(f"Custom formula evaluation error: {e}")
                return {
                    "status": "ERROR",
                    "item_name": item_name,
                    "error": f"수식 연산 오류: {str(e)}",
                    "judgement": "ERROR",
                }

        # 2. Registry Formula Type Evaluation
        target_formula_key = formula_type or "civil_safety_factor"

        if target_formula_key in self.registry:
            spec = self.registry[target_formula_key]
            try:
                calc_val = float(spec["eval_func"](vars_dict))
                is_pass = bool(spec["check_func"](calc_val, vars_dict))
                unit = spec.get("unit", "")

                threshold = req_sf if req_sf is not None else vars_dict.get("req_sf", vars_dict.get("max_drop_pct", vars_dict.get("max_u_value", 0)))
                margin_pct = ((calc_val - threshold) / threshold) * 100 if threshold != 0 else 0

                return {
                    "status": "SUCCESS",
                    "item_name": item_name,
                    "domain": spec.get("domain", domain or "공학"),
                    "formula_name": spec.get("name", target_formula_key),
                    "formula": spec.get("formula_str", ""),
                    "variables": vars_dict,
                    "calculated_value": round(calc_val, 4),
                    "unit": unit,
                    "threshold_value": threshold,
                    "margin_pct": round(margin_pct, 2),
                    "judgement": "PASS (적합)" if is_pass else "FAIL (부적합/보완필요)",
                    "action_required": "승인 적정" if is_pass else f"설계 기준 불만족 (계산값: {round(calc_val, 3)}{unit}, 요구치: {threshold}{unit}), 부재/용량 재검토 지시 필요",
                }
            except Exception as e:
                logger.error(f"Registry formula evaluation error: {e}")
                return {
                    "status": "ERROR",
                    "item_name": item_name,
                    "error": f"공식 연산 실패: {str(e)}",
                    "judgement": "ERROR",
                }

        # 3. Default Standard Safety Factor fallback: Fs = allowable / design
        if "allowable_val" in vars_dict and "design_val" in vars_dict:
            d_val = vars_dict["design_val"]
            a_val = vars_dict["allowable_val"]
            target_sf = req_sf if req_sf is not None else vars_dict.get("req_sf", 1.25)

            if d_val == 0:
                calc_sf = 999.0
            else:
                calc_sf = a_val / d_val

            is_pass = calc_sf >= target_sf
            margin_pct = ((calc_sf - target_sf) / target_sf) * 100 if target_sf != 0 else 0

            return {
                "status": "SUCCESS",
                "item_name": item_name,
                "domain": domain or "토목/구조",
                "formula_name": "기본 안전율 (Fs = 허용치 / 설계작용치)",
                "formula": "allowable_val / design_val",
                "variables": {"design_val": d_val, "allowable_val": a_val, "req_sf": target_sf},
                "calculated_value": round(calc_sf, 3),
                "threshold_value": target_sf,
                "margin_pct": round(margin_pct, 2),
                "judgement": "PASS (적합)" if is_pass else "FAIL (부적합/단면증대필요)",
                "action_required": "승인 가능" if is_pass else f"요구 안전율({target_sf}) 미달 (계산 안전율: {round(calc_sf, 2)}), 보강 방안 제출 지시",
            }

        return {
            "status": "ERROR",
            "item_name": item_name,
            "error": "연산에 필요한 변수(design_val, allowable_val 등)가 부족합니다.",
            "judgement": "ERROR",
        }


# Singleton instance
_engine = FormulaEngine()


def verify_calculation_safety(
    item_name: str,
    domain: Optional[str] = None,
    design_val: Optional[float] = None,
    allowable_val: Optional[float] = None,
    req_sf: Optional[float] = None,
    formula_type: Optional[str] = None,
    custom_formula: Optional[str] = None,
    variables: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    return _engine.verify(
        item_name=item_name,
        domain=domain,
        design_val=design_val,
        allowable_val=allowable_val,
        req_sf=req_sf,
        formula_type=formula_type,
        custom_formula=custom_formula,
        variables=variables,
    )
