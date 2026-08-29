"""Tests for Multi-Disciplinary Formula Engine (Module 3)"""

import pytest
from samwoo_cm_bridge.core.formula_engine import (
    FormulaEngine,
    verify_calculation_safety,
    safe_eval,
)


def test_safe_eval_math_expressions():
    vars_dict = {"a": 10, "b": 2.5, "c": 4}
    res = safe_eval("a / b + sqrt(c)", vars_dict)
    assert res == 6.0


def test_safe_eval_disallowed_syntax():
    with pytest.raises(Exception):
        safe_eval("__import__('os').system('dir')", {})


def test_civil_safety_factor_fail():
    res = verify_calculation_safety(
        item_name="1단 버팀보",
        domain="토목/구조",
        design_val=205.4,
        allowable_val=220.0,
        req_sf=1.25,
    )
    assert res["status"] == "SUCCESS"
    assert res["calculated_value"] == pytest.approx(1.071, 0.01)
    assert "FAIL" in res["judgement"]


def test_civil_safety_factor_pass():
    res = verify_calculation_safety(
        item_name="2단 버팀보",
        domain="토목/구조",
        design_val=163.8,
        allowable_val=220.0,
        req_sf=1.25,
    )
    assert res["status"] == "SUCCESS"
    assert res["calculated_value"] == pytest.approx(1.343, 0.01)
    assert "PASS" in res["judgement"]


def test_fire_reservoir_hydrant():
    res = verify_calculation_safety(
        item_name="옥내소화전 저수조",
        domain="소방",
        formula_type="fire_reservoir_hydrant",
        variables={"actual_reservoir_vol": 15.0, "hydrant_count": 5},
    )
    assert res["status"] == "SUCCESS"
    assert "PASS" in res["judgement"]


def test_elec_voltage_drop():
    res = verify_calculation_safety(
        item_name="동력간선",
        domain="전기/통신",
        formula_type="elec_voltage_drop_pct",
        variables={
            "length_m": 85,
            "current_a": 150,
            "wire_area_sqmm": 50,
            "nominal_voltage": 380,
            "max_drop_pct": 3.0,
        },
    )
    assert res["status"] == "SUCCESS"
    assert res["calculated_value"] == pytest.approx(1.194, 0.01)
    assert "PASS" in res["judgement"]


def test_custom_formula_evaluation():
    res = verify_calculation_safety(
        item_name="특수장비 하중비",
        custom_formula="(capacity_ton - load_ton) / capacity_ton * 100",
        variables={"capacity_ton": 50, "load_ton": 35, "req_sf": 20.0},
    )
    assert res["status"] == "SUCCESS"
    assert res["calculated_value"] == 30.0
    assert "PASS" in res["judgement"]
