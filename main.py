"""
DC 親子関係 最適化 — CLI エントリポイント

使い方:
  python main.py <Excelファイルパス>
  python main.py data/sample2.xlsx
"""

import argparse
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
from src.excel_loader import load_excel
from src.excel_writer import save_result
from src.optimizer import solve


def main() -> None:
    parser = argparse.ArgumentParser(description="DC 親子関係 最適化")
    parser.add_argument("excel_path", help="入力 Excel ファイルパス")
    args = parser.parse_args()

    try:
        dcs, dc_tariffs, current_parent_of = load_excel(args.excel_path)
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません — {args.excel_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: Excel 読み込み失敗 — {e}", file=sys.stderr)
        sys.exit(1)

    result = solve(dcs, dc_tariffs, current_parent_of=current_parent_of)

    status = result["status"]
    print(f"ステータス: {status}")
    if status != "Optimal":
        sys.exit(1)

    print(f"最適週次コスト: {result['total_weekly_cost']:,.1f} 円/週")
    if result.get("current_weekly_cost") is not None:
        diff = result["current_weekly_cost"] - result["total_weekly_cost"]
        print(f"現状週次コスト: {result['current_weekly_cost']:,.1f} 円/週")
        print(f"削減効果      : {diff:,.1f} 円/週")
    print()

    # 親子関係
    print("【最適化後の親子関係】")
    for dc_id, parent in result["parent_of"].items():
        role = "子" if parent else "孤立/親"
        parent_str = f"→ 親: {parent}" if parent else ""
        print(f"  {dc_id}: {role}  {parent_str}")
    print()

    # DC 別サマリー DataFrame
    summary = result["summary"]
    cost_cols = ["holding_cost", "supplier_transport_cost", "dc_transport_cost", "total_cost"]
    scenario_labels = {
        "baseline":  "baseline（親子設定なし）",
        "current":   "current（現状設定）",
        "optimized": "optimized（最適化後）",
    }
    for key in [k for k in ["baseline", "current", "optimized"] if k in summary]:
        df = summary[key]
        print(f"【{scenario_labels[key]}】")
        disp = df.copy()
        disp["parent_dc"] = disp["parent_dc"].fillna("—")
        for col in cost_cols:
            disp[col] = disp[col].map(lambda v: f"{v:,.0f}")
        print(disp.to_string(index=False))
        total = df[cost_cols].sum()
        print(
            f"  合計  holding={total['holding_cost']:>10,.0f}"
            f"  supplier={total['supplier_transport_cost']:>10,.0f}"
            f"  dc_transport={total['dc_transport_cost']:>10,.0f}"
            f"  total={total['total_cost']:>10,.0f}"
        )
        print()

    # Excel 出力
    output_path = Path("output") / f"{Path(args.excel_path).stem}_result.xlsx"
    save_result(result, output_path)
    print(f"結果を保存しました: {output_path}")


if __name__ == "__main__":
    main()
