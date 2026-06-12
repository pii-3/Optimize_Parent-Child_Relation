"""
DC 親子関係 最適化 — CLI エントリポイント

使い方:
  python main.py <Excelファイルパス>
"""

import argparse
import json
import sys
from src.excel_loader import load_excel
from src.optimizer import solve


def main() -> None:
    parser = argparse.ArgumentParser(description="DC 親子関係 最適化")
    parser.add_argument("excel_path", help="入力 Excel ファイルパス")
    args = parser.parse_args()

    try:
        dcs, dc_tariffs = load_excel(args.excel_path)
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません — {args.excel_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: Excel 読み込み失敗 — {e}", file=sys.stderr)
        sys.exit(1)

    result = solve(dcs, dc_tariffs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
