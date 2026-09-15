"""Tests for Legal Risk Defense Tools (Modules 23-25)

1. Fire Hazard Concurrent Work Conflict Detector (fire_hazard_conflict_detector.py)
2. Structural Member Video Recording Register Manager (video_record_manager.py)
3. Weather Condition Stop-Work Order Trigger (weather_stop_work_trigger.py)
"""

import os
import pytest
from construct_cm_bridge.core.fire_hazard_conflict_detector import (
    FireHazardConflictDetector,
    check_concurrent_work_fire_hazard,
)
from construct_cm_bridge.core.video_record_manager import (
    VideoRecordManager,
    generate_video_recording_log,
)
from construct_cm_bridge.core.weather_stop_work_trigger import (
    WeatherStopWorkTrigger,
    issue_weather_stop_work_order,
)


def test_fire_hazard_conflict_detection_critical():
    tasks = [
        "지하 1층 기계실 소방배관 아크 용접 작업",
        "지하 1층 외벽 우레탄폼 단열재 뿜칠 시공",
        "101동 구간 타워크레인 갱폼 양중 및 비계 해체",
    ]
    res = check_concurrent_work_fire_hazard(tasks)
    assert res["status"] == "CRITICAL_ALERT"
    assert res["conflicts_count"] >= 1
    assert "즉시 작업중지" in res["overall_verdict"] or "경보" in res["overall_verdict"]
    assert any("우레탄" in c["combustible_work"] for c in res["conflicts"])
    assert any("용접" in c["hot_work"] for c in res["conflicts"])
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])


def test_fire_hazard_no_conflict():
    tasks = [
        "지하 1층 기계실 소방배관 아크 용접 작업",
        "지상 10층 세대 내부 타일 시공",
        "옥상 파라펫 철근 배근 및 거푸집 조립",
    ]
    res = check_concurrent_work_fire_hazard(tasks)
    assert res["status"] == "NORMAL"
    assert res["conflicts_count"] == 0
    assert "미검출" in res["overall_verdict"]


def test_video_record_manager():
    records = [
        {
            "video_file": "VID_20260829_B2F_SLAB_REBAR.mp4",
            "work_type": "지하 2층 바닥 슬래브 철근배근 검측",
            "record_date": "2026.08.29",
            "grid_location": "지하 2층 1구역 (X1~X5 / Y2~Y4)",
            "key_items": "상·하부근 피복두께 50mm 확보, 이음길이 40d 확인",
            "inspector": "김수석 책임건설사업관리기술인",
            "result": "적합 (PASS)",
        },
        {
            "video_file": "VID_20260829_B2F_CONC_POUR.mp4",
            "work_type": "지하 2층 바닥 슬래브 콘크리트 타설",
            "record_date": "2026.08.29",
            "grid_location": "지하 2층 1구역 (타설량 320m3)",
            "key_items": "레미콘 시험 입회, 바이브레이터 다짐 확인",
            "inspector": "김수석 책임건설사업관리기술인",
            "result": "적합 (PASS)",
        }
    ]
    res = generate_video_recording_log(records)
    assert res["status"] == "SUCCESS"
    assert res["total_video_records"] == 2
    assert "SWCM-VID-" in res["doc_no"]
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])


def test_weather_stop_work_trigger_rain_and_wind():
    res = issue_weather_stop_work_order(
        rain_mm=8.5,
        wind_speed_ms=13.0,
        planned_work="지하 2층 바닥 매트 콘크리트 타설 및 타워크레인 갱폼 양중",
        temp_c=21.0,
    )
    assert res["status"] == "STOP_REVIEW_REQUIRED"
    assert res["stop_items_count"] >= 2
    assert "작업중지" in res["overall_verdict"]
    assert any("우천" in item["category"] or "타설" in item["category"] for item in res["stop_items"])
    assert any("강풍" in item["category"] or "양중" in item["category"] for item in res["stop_items"])
    assert os.path.exists(res["docx_path"])
    assert os.path.exists(res["md_path"])


def test_weather_normal_pass():
    res = issue_weather_stop_work_order(
        rain_mm=0.0,
        wind_speed_ms=3.5,
        planned_work="실내 미장 및 조적 공사",
        temp_c=23.0,
    )
    assert res["status"] == "NORMAL"
    assert res["stop_items_count"] == 0
    assert "미검출" in res["overall_verdict"]
