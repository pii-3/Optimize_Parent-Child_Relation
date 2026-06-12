"""
SPEC.md セクション 5「シナリオ例」に対応するテスト。
各テスト関数の名前はシナリオ番号と対応している。
"""

import pytest
from src.optimizer import solve


# ---------------------------------------------------------------------------
# シナリオ 1: 親子関係を作る方が最適（2 DC）
#
# 在庫削減効果が輸送コスト増を大きく上回るため、
# DC-B を DC-A の子にする構成が最適になることを検証する。
# ---------------------------------------------------------------------------
def test_scenario1_parent_child_is_optimal():
    dcs = [
        {"dc_id": "DC-A", "demand": 50, "holding_cost": 10, "lot_size": 500, "tariff_from_supplier": 5},
        {"dc_id": "DC-B", "demand": 50, "holding_cost": 10, "lot_size": 500, "tariff_from_supplier": 15},
    ]
    dc_tariffs = [
        {"from_dc_id": "DC-A", "to_dc_id": "DC-B", "tariff": 3},
        {"from_dc_id": "DC-B", "to_dc_id": "DC-A", "tariff": 3},
    ]

    result = solve(dcs, dc_tariffs)

    assert result["status"] == "Optimal"
    assert result["total_weekly_cost"] == pytest.approx(19_900.0)
    assert result["parent_of"]["DC-A"] is None   # DC-A は親（親を持たない）
    assert result["parent_of"]["DC-B"] == "DC-A" # DC-B は DC-A の子


# ---------------------------------------------------------------------------
# シナリオ 2: 全 DC 孤立が最適（2 DC）
#
# DC 間輸送コストが高く、在庫削減メリットを上回るため、
# 親子関係を作らず全 DC 孤立が最適になることを検証する。
# ---------------------------------------------------------------------------
def test_scenario2_all_standalone_is_optimal():
    dcs = [
        {"dc_id": "DC-A", "demand": 50, "holding_cost": 2, "lot_size": 500, "tariff_from_supplier": 5},
        {"dc_id": "DC-B", "demand": 50, "holding_cost": 2, "lot_size": 500, "tariff_from_supplier": 5},
    ]
    dc_tariffs = [
        {"from_dc_id": "DC-A", "to_dc_id": "DC-B", "tariff": 70},
        {"from_dc_id": "DC-B", "to_dc_id": "DC-A", "tariff": 70},
    ]

    result = solve(dcs, dc_tariffs)

    assert result["status"] == "Optimal"
    assert result["total_weekly_cost"] == pytest.approx(7_500.0)
    assert result["parent_of"]["DC-A"] is None  # 孤立
    assert result["parent_of"]["DC-B"] is None  # 孤立


# ---------------------------------------------------------------------------
# シナリオ 3: DC-C を親にした集約が最適（3 DC）
#
# DC-C は保管単価 h=2 が低く大ロットを抱えてもコストが小さいため、
# DC-A・DC-B を束ねる親 DC として機能するのが最適。
# ---------------------------------------------------------------------------
def test_scenario3_dc_c_as_hub_is_optimal():
    dcs = [
        {"dc_id": "DC-A", "demand": 100, "holding_cost": 10, "lot_size": 500, "tariff_from_supplier": 5},
        {"dc_id": "DC-B", "demand": 100, "holding_cost": 10, "lot_size": 500, "tariff_from_supplier": 15},
        {"dc_id": "DC-C", "demand": 100, "holding_cost": 2,  "lot_size": 500, "tariff_from_supplier": 5},
    ]
    dc_tariffs = [
        {"from_dc_id": "DC-A", "to_dc_id": "DC-B", "tariff": 3},
        {"from_dc_id": "DC-B", "to_dc_id": "DC-A", "tariff": 3},
        {"from_dc_id": "DC-A", "to_dc_id": "DC-C", "tariff": 70},
        {"from_dc_id": "DC-C", "to_dc_id": "DC-A", "tariff": 70},
        {"from_dc_id": "DC-B", "to_dc_id": "DC-C", "tariff": 70},
        {"from_dc_id": "DC-C", "to_dc_id": "DC-B", "tariff": 70},
    ]

    result = solve(dcs, dc_tariffs)

    assert result["status"] == "Optimal"
    assert result["total_weekly_cost"] == pytest.approx(26_000.0)
    assert result["parent_of"]["DC-A"] == "DC-C"  # DC-A は DC-C の子
    assert result["parent_of"]["DC-B"] == "DC-C"  # DC-B は DC-C の子
    assert result["parent_of"]["DC-C"] is None     # DC-C は親（親を持たない）
