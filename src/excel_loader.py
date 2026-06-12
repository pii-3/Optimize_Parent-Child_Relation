"""
Excel ファイルから最適化モデルの入力データを読み込む。

シート構成:
  - "DCマスタ"   : dc_id, demand, holding_cost, lot_size, tariff_from_supplier
  - "DC間タリフ" : from_dc_id, to_dc_id, tariff
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd


def load_excel(path: str | Path) -> tuple[list[dict], list[dict]]:
    """
    Parameters
    ----------
    path : Excel ファイルパス

    Returns
    -------
    (dcs, dc_tariffs) — optimizer.solve() に渡せる形式
    """
    dcs = pd.read_excel(path, sheet_name="DCマスタ").to_dict(orient="records")
    dc_tariffs = pd.read_excel(path, sheet_name="DC間タリフ").to_dict(orient="records")
    return dcs, dc_tariffs
