"""
DC 親子関係 最適化モデル (SPEC.md 準拠)

目的: 週次コスト（在庫コスト + 輸送コスト）の最小化
決定変数: x[j,k] = 1 ならば DC k を DC j の子として割り当てる
コスト帰属: DC 間輸送コストは受け取り側（子 DC）に計上する
"""

from __future__ import annotations
import pandas as pd
import pulp


def _build_cost_rows(
    dc_ids: list[str],
    demand: dict,
    holding: dict,
    lot: dict,
    tariff_a: dict,
    tariff_b: dict,
    parent_of: dict,
    scenario: str,
) -> list[dict]:
    """SPEC 4.2「表示形式」の各行に対応するレコードを生成する。
    倉庫別行の後に合計行（dc_id=None）を追加して返す。
    """
    rows: list[dict] = []
    h_sum = st_sum = dt_sum = 0.0

    for k in dc_ids:
        parent = parent_of[k]
        children = [c for c in dc_ids if parent_of.get(c) == k]

        if parent is None:
            h  = 7 * holding[k] * lot[k] / 2
            st = tariff_a[k] * (demand[k] + sum(demand[c] for c in children))
            dt = 0.0
        else:
            h  = 7 * holding[k] * demand[k] / 2
            st = 0.0
            dt = tariff_b[(parent, k)] * demand[k]

        rows.append({
            "scenario": scenario,
            "dc_id": k,
            "holding_cost": h,
            "supplier_transport_cost": st,
            "dc_transport_cost": dt,
            "total": h + st + dt,
        })
        h_sum += h
        st_sum += st
        dt_sum += dt

    rows.append({
        "scenario": scenario,
        "dc_id": None,
        "holding_cost": h_sum,
        "supplier_transport_cost": st_sum,
        "dc_transport_cost": dt_sum,
        "total": h_sum + st_sum + dt_sum,
    })
    return rows


def _build_summary_df(
    dc_ids: list[str],
    demand: dict,
    holding: dict,
    lot: dict,
    tariff_a: dict,
    tariff_b: dict,
    parent_of: dict,
) -> pd.DataFrame:
    """SPEC 4.2⑤ DC 別サマリー DataFrame を生成する。"""
    rows = []
    for k in dc_ids:
        parent = parent_of[k]
        children = [c for c in dc_ids if parent_of.get(c) == k]

        if parent is not None:
            role = "子"
            h  = 7 * holding[k] * demand[k] / 2
            st = 0.0
            dt = tariff_b[(parent, k)] * demand[k]
        elif children:
            role = "親"
            h  = 7 * holding[k] * lot[k] / 2
            st = tariff_a[k] * (demand[k] + sum(demand[c] for c in children))
            dt = 0.0
        else:
            role = "孤立"
            h  = 7 * holding[k] * lot[k] / 2
            st = tariff_a[k] * demand[k]
            dt = 0.0

        rows.append({
            "dc_id": k,
            "demand": demand[k],
            "holding_cost_unit": holding[k],
            "lot_size": lot[k],
            "tariff_supplier": tariff_a[k],
            "role": role,
            "parent_dc": parent,
            "holding_cost": h,
            "supplier_transport_cost": st,
            "dc_transport_cost": dt,
            "total_cost": h + st + dt,
        })
    return pd.DataFrame(rows)


def solve(
    dcs: list[dict],
    dc_tariffs: list[dict],
    current_parent_of: dict | None = None,
) -> dict:
    """
    Parameters
    ----------
    dcs : DC マスタ
        [{"dc_id": str, "demand": float, "holding_cost": float,
          "lot_size": float, "tariff_from_supplier": float}, ...]
    dc_tariffs : DC 間タリフ（非対称・全ペア必須）
        [{"from_dc_id": str, "to_dc_id": str, "tariff": float}, ...]
    current_parent_of : 現状の親子設定（省略可）
        {dc_id: parent_dc_id | None}
        渡した場合は "current" シナリオを cost_breakdown / summary に追加する。

    Returns
    -------
    {
        "status": "Optimal" | "Infeasible" | str,
        "total_weekly_cost": float | None,
        "current_weekly_cost": float | None,  # current_parent_of を渡した場合のみ
        "parent_of": {dc_id: parent_dc_id | None},
        "cost_breakdown": [
            {"scenario": "baseline"|"current"|"optimized", "dc_id": str|None,
             "holding_cost": float, "supplier_transport_cost": float,
             "dc_transport_cost": float, "total": float},
            ...  # 倉庫別行 + 合計行(dc_id=None) が baseline[/current]/optimized の順に並ぶ
        ],
        "summary": {
            "baseline":  pd.DataFrame,  # 親子設定なし（全倉庫孤立）
            "current":   pd.DataFrame,  # 現状設定（current_parent_of を渡した場合のみ）
            "optimized": pd.DataFrame,  # 最適化後
        }
    }
    """
    dc_ids = [dc["dc_id"] for dc in dcs]
    demand   = {dc["dc_id"]: dc["demand"]               for dc in dcs}
    holding  = {dc["dc_id"]: dc["holding_cost"]          for dc in dcs}
    lot      = {dc["dc_id"]: dc["lot_size"]              for dc in dcs}
    tariff_a = {dc["dc_id"]: dc["tariff_from_supplier"]  for dc in dcs}
    tariff_b = {(t["from_dc_id"], t["to_dc_id"]): t["tariff"] for t in dc_tariffs}

    prob = pulp.LpProblem("dc_parent_child", pulp.LpMinimize)

    # 決定変数: x[j,k] = 1 → DC k を DC j の子にする
    x = {
        (j, k): pulp.LpVariable(f"x_{j}_{k}", cat="Binary")
        for j in dc_ids
        for k in dc_ids
        if j != k
    }

    # 補助変数: y[j] = 1 → DC j は少なくとも 1 つの子を持つ（親 DC）
    y = {j: pulp.LpVariable(f"y_{j}", cat="Binary") for j in dc_ids}

    # ---------- 目的関数 ----------
    # 全 DC スタンドアロン時のベースコストに、
    # 各割り当て x[j,k] によるコスト変化（delta）を加算する。
    #
    # delta[j,k] = (子 DC k の在庫コスト削減) - (輸送コスト増加)
    #            = -7*h_k*(Q_k - d_k)/2  +  d_k*(a_j + b_jk - a_k)
    #
    # コスト帰属（親 vs 子）に関わらず合計は同一なので、
    # 目的関数はどちらの帰属でも変わらない。

    base_cost = sum(
        7 * holding[j] * lot[j] / 2 + tariff_a[j] * demand[j]
        for j in dc_ids
    )

    delta_cost = pulp.lpSum(
        x[(j, k)] * (
            -7 * holding[k] * (lot[k] - demand[k]) / 2
            + demand[k] * (tariff_a[j] + tariff_b[(j, k)] - tariff_a[k])
        )
        for j in dc_ids
        for k in dc_ids
        if j != k
    )

    prob += base_cost + delta_cost

    # ---------- 制約 ----------

    # C1: 各 DC の親は 1 つまで
    for k in dc_ids:
        prob += (
            pulp.lpSum(x[(j, k)] for j in dc_ids if j != k) <= 1,
            f"c1_{k}",
        )

    # C2a: DC j に子が 1 つでもいれば y[j] = 1
    for j in dc_ids:
        for k in dc_ids:
            if j != k:
                prob += x[(j, k)] <= y[j], f"c2a_{j}_{k}"

    # C2b: 親 DC（y[j]=1）は子 DC にはなれない（2 層固定）
    for j in dc_ids:
        prob += (
            pulp.lpSum(x[(l, j)] for l in dc_ids if l != j) + y[j] <= 1,
            f"c2b_{j}",
        )

    # ---------- 求解 ----------
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return {
            "status": status,
            "total_weekly_cost": None,
            "parent_of": {},
            "cost_breakdown": [],
        }

    parent_of = {
        k: next(
            (j for j in dc_ids if j != k and pulp.value(x[(j, k)]) > 0.5),
            None,
        )
        for k in dc_ids
    }

    baseline_parent = {k: None for k in dc_ids}
    cost_breakdown = _build_cost_rows(
        dc_ids, demand, holding, lot, tariff_a, tariff_b, baseline_parent, "baseline"
    )

    current_weekly_cost = None
    if current_parent_of is not None:
        current_rows = _build_cost_rows(
            dc_ids, demand, holding, lot, tariff_a, tariff_b, current_parent_of, "current"
        )
        cost_breakdown += current_rows
        current_weekly_cost = next(r["total"] for r in current_rows if r["dc_id"] is None)

    cost_breakdown += _build_cost_rows(
        dc_ids, demand, holding, lot, tariff_a, tariff_b, parent_of, "optimized"
    )

    summary = {
        "baseline":  _build_summary_df(dc_ids, demand, holding, lot, tariff_a, tariff_b, baseline_parent),
        "optimized": _build_summary_df(dc_ids, demand, holding, lot, tariff_a, tariff_b, parent_of),
    }
    if current_parent_of is not None:
        summary["current"] = _build_summary_df(
            dc_ids, demand, holding, lot, tariff_a, tariff_b, current_parent_of
        )

    return {
        "status": "Optimal",
        "total_weekly_cost": pulp.value(prob.objective),
        "current_weekly_cost": current_weekly_cost,
        "parent_of": parent_of,
        "cost_breakdown": cost_breakdown,
        "summary": summary,
    }
