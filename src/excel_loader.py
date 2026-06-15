"""
Excel ファイルから最適化モデルの入力データを読み込む。

シート構成:
  - "DCマスタ"   : dc_id, demand, holding_cost, lot_size, tariff_from_supplier
                   [, current_parent_dc_id]  ← 省略可
  - "DC間タリフ" : from_dc_id, to_dc_id, tariff
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd


def load_excel(path: str | Path) -> tuple[list[dict], list[dict], dict | None]:
    """
    Parameters
    ----------
    path : Excel ファイルパス

    Returns
    -------
    (dcs, dc_tariffs, current_parent_of)
      - dcs          : optimizer.solve() の dcs 引数に渡せる形式
      - dc_tariffs   : optimizer.solve() の dc_tariffs 引数に渡せる形式
      - current_parent_of : DCマスタに current_parent_dc_id 列がある場合のみ設定、それ以外は None
          {dc_id: parent_dc_id | None}
    """
    df_master = pd.read_excel(path, sheet_name="DCマスタ")
    dc_tariffs = pd.read_excel(path, sheet_name="DC間タリフ").to_dict(orient="records")

    current_parent_of = None
    if "current_parent_dc_id" in df_master.columns:
        current_parent_of = {
            row["dc_id"]: None if pd.isna(row["current_parent_dc_id"]) else row["current_parent_dc_id"]
            for _, row in df_master.iterrows()
        }

    dcs = df_master.drop(columns=["current_parent_dc_id"], errors="ignore").to_dict(orient="records")
    return dcs, dc_tariffs, current_parent_of
