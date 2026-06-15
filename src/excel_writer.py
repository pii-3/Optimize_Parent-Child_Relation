"""
最適化結果を Excel ファイルに保存する。

出力シート構成:
  - "コスト内訳"           : cost_breakdown（baseline / current / optimized 比較）
  - "DC別サマリー_baseline" : DC 別サマリー（全孤立）
  - "DC別サマリー_current"  : DC 別サマリー（現状設定）  ← current_parent_of を渡した場合のみ
  - "DC別サマリー_optimized": DC 別サマリー（最適化後）
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd

_SCENARIO_LABELS = {
    "baseline":  "ベースライン（全孤立）",
    "current":   "現状設定",
    "optimized": "最適化後",
}

_COST_BREAKDOWN_COLUMNS = {
    "scenario":                 "シナリオ",
    "dc_id":                    "倉庫",
    "holding_cost":             "在庫コスト",
    "supplier_transport_cost":  "仕入れ先→DC輸送",
    "dc_transport_cost":        "DC間輸送",
    "total":                    "合計",
}

_SUMMARY_COLUMNS = {
    "dc_id":                    "DC",
    "demand":                   "週間需要量",
    "holding_cost_unit":        "保管単価",
    "lot_size":                 "ロットサイズ",
    "tariff_supplier":          "タリフA",
    "role":                     "役割",
    "parent_dc":                "親DC",
    "holding_cost":             "在庫コスト",
    "supplier_transport_cost":  "仕入れ先→DC輸送",
    "dc_transport_cost":        "DC間輸送",
    "total_cost":               "合計",
}


def save_result(result: dict, path: str | Path) -> None:
    """
    最適化結果を Excel ファイルに保存する。

    Parameters
    ----------
    result : optimizer.solve() の戻り値
    path   : 出力先ファイルパス（親ディレクトリが存在しない場合は自動作成）
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # cost_breakdown → DataFrame
    breakdown_rows = []
    for r in result["cost_breakdown"]:
        breakdown_rows.append({
            "シナリオ":         _SCENARIO_LABELS.get(r["scenario"], r["scenario"]),
            "倉庫":             r["dc_id"] if r["dc_id"] is not None else "【合計】",
            "在庫コスト":       r["holding_cost"],
            "仕入れ先→DC輸送": r["supplier_transport_cost"],
            "DC間輸送":         r["dc_transport_cost"],
            "合計":             r["total"],
        })
    df_breakdown = pd.DataFrame(breakdown_rows)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_breakdown.to_excel(writer, sheet_name="コスト内訳", index=False)

        summary_order = [k for k in ["baseline", "current", "optimized"] if k in result.get("summary", {})]
        for key in summary_order:
            df = result["summary"][key].copy()
            df["parent_dc"] = df["parent_dc"].fillna("—")
            df = df.rename(columns=_SUMMARY_COLUMNS)
            df.to_excel(writer, sheet_name=f"DC別サマリー_{key}", index=False)
