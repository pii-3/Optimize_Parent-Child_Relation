# CLAUDE.md

## プロジェクト概要

DC（親倉庫）と小倉庫（子倉庫）の親子関係を最適化し、輸送コストを最小化する数理最適化モデル。
Python + PuLP で実装する。

## ファイル構成

| ファイル | 役割 |
|----------|------|
| `SPEC.md` | 仕様書。ビジネス説明・制約・数理モデル・シナリオ例を記載 |
| `src/optimizer.py` | PuLP を使った最適化モデルの実装 |
| `tests/test_scenarios.py` | SPEC.md のシナリオ例に対応するテスト |
| `requirements.txt` | 依存パッケージ |

## 開発フロー

1. **仕様を書く** — `SPEC.md` に変更・追加内容を記載する
2. **テストを書く** — `SPEC.md` のシナリオ例を `test_scenarios.py` に落とし込む
3. **実装する** — テストが通るように `optimizer.py` を実装する

実装の前に `SPEC.md` を確認し、仕様に沿った実装をすること。

## コマンド

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# テスト実行
pytest tests/
```
