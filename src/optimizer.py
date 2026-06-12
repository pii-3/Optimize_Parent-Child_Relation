"""
DC 親子関係 最適化モデル (SPEC.md 準拠)

目的: 週次コスト（在庫コスト + 輸送コスト）の最小化
決定変数: x[j,k] = 1 ならば DC k を DC j の子として割り当てる
"""

from __future__ import annotations
import pulp


def solve(dcs: list[dict], dc_tariffs: list[dict]) -> dict:
    """
    Parameters
    ----------
    dcs : DC マスタ
        [{"dc_id": str, "demand": float, "holding_cost": float,
          "lot_size": float, "tariff_from_supplier": float}, ...]
    dc_tariffs : DC 間タリフ（非対称・全ペア必須）
        [{"from_dc_id": str, "to_dc_id": str, "tariff": float}, ...]

    Returns
    -------
    {
        "status": "Optimal" | "Infeasible" | str,
        "total_weekly_cost": float | None,
        "parent_of": {dc_id: parent_dc_id | None}
            None = 孤立 DC または 親 DC（親を持たない）
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
    # delta が負 = 親子化するとコストが下がる

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
        return {"status": status, "total_weekly_cost": None, "parent_of": {}}

    parent_of = {
        k: next(
            (j for j in dc_ids if j != k and pulp.value(x[(j, k)]) > 0.5),
            None,
        )
        for k in dc_ids
    }

    return {
        "status": "Optimal",
        "total_weekly_cost": pulp.value(prob.objective),
        "parent_of": parent_of,
    }
