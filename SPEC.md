# 仕様書: DC 親子関係 最適化モデル

---

## 1. 何を解くか（ビジネス説明）

### 背景

仕入れ先への発注は最小ロット（Q ケース）が大きく、全 DC が直接仕入れると
各 DC の平均在庫が Q/2 になり、在庫保管コストが膨らむ。

一方、DC 間で「親子関係」を設定し、子 DC を親 DC 経由で補充する構造にすると、
子 DC は週 1 回・需要量ぶんだけ補充できるため平均在庫が d/2（需要量の半分）まで減る。
ただし親→子の輸送コストが追加で発生する。

**このモデルは「在庫削減メリット」と「輸送コスト増加」を天秤にかけ、
週次コスト合計が最小になる親子関係の組み合わせを求める。**

### DC の役割（最適化で決まる）

```
仕入れ先 ─[タリフA]─> 親 DC ─[タリフB]─> 子 DC
仕入れ先 ─[タリフA]─> 孤立 DC
```

| 役割 | 仕入れ元 | ロット | 子を持つか |
|------|---------|--------|-----------|
| 孤立 DC | 仕入れ先（直接） | Q（大） | なし |
| 親 DC   | 仕入れ先（直接） | Q（大） | あり |
| 子 DC   | 親 DC（経由）   | 週間需要量（小） | なし |

---

## 2. ルールと制約（自然言語）

1. 各 DC は必ずいずれかの役割（孤立・親・子）になる
2. 子 DC の仕入れ元は親 DC のみ（仕入れ先からの直接仕入れ不可）
3. 各 DC が持てる親は 1 つまで
4. 親 DC になった DC は他の DC の子 DC にはなれない（2 層固定）
5. 階層は 親 DC → 子 DC の 1 ホップのみ（3 層以上は不可）
6. 1 つの親 DC が持てる子 DC の数に上限はない
7. 親子関係はすべての DC ペア間で設定可能

---

## 3. 数理モデル

### 3.1 集合

| 記号 | 意味 |
|------|------|
| $J$ | DC の集合 |

### 3.2 パラメータ

| 記号 | 意味 | 単位 |
|------|------|------|
| $d_j$ | DC $j$ の週間需要量 | ケース/週 |
| $h_j$ | DC $j$ の在庫保管単価 | 円/ケース/日 |
| $Q_j$ | DC $j$ の仕入れ先ロットサイズ | ケース |
| $a_j$ | 仕入れ先 → DC $j$ のタリフ（タリフA） | 円/ケース |
| $b_{jk}$ | DC $j$ → DC $k$ のタリフ（タリフB、非対称） | 円/ケース |

### 3.3 決定変数

$$
x_{jk} \in \{0, 1\} \quad (j \in J,\ k \in J,\ j \neq k)
$$

$x_{jk} = 1$：DC $k$ を DC $j$ の子 DC として割り当てる

### 3.4 目的関数（週次コスト最小化）

各 DC $j$ の週次コストを役割別に定義する。

**孤立 DC または 親 DC**（$\sum_l x_{lj} = 0$、仕入れ先から直接受け取る）:

$$
C_j^{\text{direct}} = \underbrace{7 \cdot h_j \cdot \frac{Q_j}{2}}_{\text{在庫コスト}} + \underbrace{a_j \cdot \left(d_j + \sum_{k \in J} x_{jk} \cdot d_k\right)}_{\text{仕入れ先→DC 輸送コスト}}
$$

**子 DC**（$\sum_l x_{lj} = 1$、親 DC から受け取る）:

$$
C_j^{\text{child}} = \underbrace{7 \cdot h_j \cdot \frac{d_j}{2}}_{\text{在庫コスト}} + \underbrace{\sum_{l \in J} x_{lj} \cdot b_{lj} \cdot d_j}_{\text{DC 間輸送コスト（親→子）}}
$$

※DC 間輸送コストは受け取り側（子 DC）に帰属する

**目的関数**:

$$
\min \sum_{j \in J} \left[ \left(1 - \sum_{l \in J} x_{lj}\right) C_j^{\text{direct}} + \left(\sum_{l \in J} x_{lj}\right) C_j^{\text{child}} \right]
$$

### 3.5 制約条件

**C1 — 各 DC の親は 1 つまで**:

$$
\sum_{j \in J} x_{jk} \leq 1 \quad \forall k \in J
$$

**C2 — 2 層固定（親 DC は子 DC になれない）**:

$$
x_{lj} + x_{jk} \leq 1 \quad \forall\ \text{distinct}\ l, j, k \in J
$$

**C3 — 自己割り当て禁止**:

$$
x_{jj} = 0 \quad \forall j \in J
$$

**C4 — バイナリ制約**:

$$
x_{jk} \in \{0, 1\} \quad \forall j, k \in J
$$

---

## 4. 入出力仕様

### 4.1 入力

**① DC マスタ**（DC ごとの 1 レコード）

| フィールド | 型 | 説明 | 単位 |
|-----------|---|------|------|
| `dc_id` | str | DC 識別子 | — |
| `demand` | float | 週間需要量 $d_j$ | ケース/週 |
| `holding_cost` | float | 在庫保管単価 $h_j$ | 円/ケース/日 |
| `lot_size` | float | ロットサイズ $Q_j$ | ケース |
| `tariff_from_supplier` | float | タリフ A $a_j$ | 円/ケース |
| `current_parent_dc_id` | str \| None | 現状の親 DC の ID。親を持たない DC は空欄。列自体が省略された場合は `"current"` シナリオを出力しない | — |

**② DC 間タリフ**（DC ペアごとの 1 レコード、非対称）

| フィールド | 型 | 説明 | 単位 |
|-----------|---|------|------|
| `from_dc_id` | str | 送り元 DC | — |
| `to_dc_id` | str | 送り先 DC | — |
| `tariff` | float | タリフ B $b_{jk}$ | 円/ケース |

### 4.2 出力

**① トップレベル**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | str | `"Optimal"` / `"Infeasible"` / `"Unbounded"` |
| `total_weekly_cost` | float | 最適化後の週次コスト合計（円/週） |
| `parent_of` | dict | 各 DC の親 DC（下表参照） |
| `cost_breakdown` | dict | コスト内訳（下表参照） |
| `current_weekly_cost` | float \| None | 現状の親子設定での週次コスト合計。`current_parent_of` を渡した場合のみ設定、それ以外は `None` |

**② `parent_of`**（DC ごとの 1 レコード）

| キー | 値 | 説明 |
|------|---|------|
| `<dc_id>` | `None` | 孤立 DC または 親 DC（親を持たない） |
| `<dc_id>` | `"<parent_dc_id>"` | 子 DC（値が親 DC の ID） |

**③ `cost_breakdown`**（行のリスト）

`cost_breakdown` は表の各行に対応するレコードのリスト。
`"baseline"`（全倉庫孤立）の倉庫別行＋合計行、`"current_parent_of"` を渡した場合は続いて `"current"`（現状設定）の倉庫別行＋合計行、最後に `"optimized"`（最適化後）の倉庫別行＋合計行の順に並ぶ。

| フィールド | 型 | 説明 | 単位 |
|-----------|---|------|------|
| `scenario` | str | `"baseline"` = 全倉庫孤立 / `"current"` = 現状設定 / `"optimized"` = 最適化後 | — |
| `dc_id` | str \| None | 倉庫 ID。合計行は `None` | — |
| `holding_cost` | float | 在庫コスト | 円/週 |
| `supplier_transport_cost` | float | 仕入れ先→DC 輸送コスト（孤立・親 DC のみ） | 円/週 |
| `dc_transport_cost` | float | DC 間輸送コスト（子 DC のみ） | 円/週 |
| `total` | float | 上記 3 項目の合計 | 円/週 |

*表示形式*（縦: 倉庫、横: コスト区分）

`cost_breakdown` は縦に倉庫・横にコスト区分の表として出力される。
`baseline`（全孤立）、`current`（現状設定、省略可）、`optimized`（最適化後）を上から順に並べて比較できる。

| シナリオ | 倉庫 | 在庫コスト | 仕入れ先→DC 輸送 | DC 間輸送 | 合計 |
|---------|------|----------:|----------------:|----------:|-----:|
| ベースライン（全孤立） | DC-A | x,xxx | x,xxx | 0 | x,xxx |
| | DC-B | x,xxx | x,xxx | 0 | x,xxx |
| | 【合計】 | **x,xxx** | **x,xxx** | **0** | **x,xxx** |
| 現状設定 | DC-A | x,xxx | x,xxx | 0 | x,xxx |
| | DC-B | x,xxx | 0 | x,xxx | x,xxx |
| | 【合計】 | **x,xxx** | **x,xxx** | **x,xxx** | **x,xxx** |
| 最適化後 | DC-A | x,xxx | x,xxx | 0 | x,xxx |
| | DC-B | x,xxx | 0 | x,xxx | x,xxx |
| | 【合計】 | **x,xxx** | **x,xxx** | **x,xxx** | **x,xxx** |

**④ コスト帰属ルール**（`optimized` の場合）

| 役割 | 在庫コスト | 仕入れ先→DC 輸送コスト | DC 間輸送コスト |
|------|-----------|----------------------|----------------|
| 孤立 DC | $7 h_j Q_j / 2$ | $a_j d_j$ | 0 |
| 親 DC | $7 h_j Q_j / 2$ | $a_j (d_j + \sum_k x_{jk} d_k)$ | 0 |
| 子 DC | $7 h_j d_j / 2$ | 0 | $b_{\text{parent},j} \cdot d_j$ |

**⑤ DC 別サマリー DataFrame**

各 DC を 1 行とし、マスタ情報・役割・週次コストを横に並べた DataFrame。
`baseline`（親子設定なし・全倉庫孤立）と `optimized`（最適化後）の 2 つを返す。

*列定義*

| 列名 | 型 | 説明 | 単位 |
|------|----|------|------|
| `dc_id` | str | DC 識別子 | — |
| `demand` | float | 週間需要量 $d_j$ | ケース/週 |
| `holding_cost_unit` | float | 在庫保管単価 $h_j$ | 円/ケース/日 |
| `lot_size` | float | ロットサイズ $Q_j$ | ケース |
| `tariff_supplier` | float | タリフ A $a_j$ | 円/ケース |
| `role` | str | `"孤立"` / `"親"` / `"子"` | — |
| `parent_dc` | str \| None | 親 DC の ID。孤立・親 DC は `None` | — |
| `holding_cost` | float | 在庫コスト（週次） | 円/週 |
| `supplier_transport_cost` | float | 仕入れ先→DC 輸送コスト（週次） | 円/週 |
| `dc_transport_cost` | float | DC 間輸送コスト（週次） | 円/週 |
| `total_cost` | float | 週次コスト合計 | 円/週 |

`baseline` では全 DC の `role = "孤立"`、`parent_dc = None` となる。
`current_parent_of` を渡した場合は `"current"` キーにも同形式の DataFrame を格納する。

*表示形式*（シナリオ 1 の例）

**baseline（親子設定なし）**

| dc_id | demand | holding_cost_unit | lot_size | tariff_supplier | role | parent_dc | holding_cost | supplier_transport_cost | dc_transport_cost | total_cost |
|-------|-------:|------------------:|---------:|----------------:|------|-----------|-------------:|------------------------:|------------------:|-----------:|
| DC-A  | 50 | 10 | 500 | 5  | 孤立 | None | 17,500 | 250 | 0 | 17,750 |
| DC-B  | 50 | 10 | 500 | 15 | 孤立 | None | 17,500 | 750 | 0 | 18,250 |

**optimized（最適化後）**

| dc_id | demand | holding_cost_unit | lot_size | tariff_supplier | role | parent_dc | holding_cost | supplier_transport_cost | dc_transport_cost | total_cost |
|-------|-------:|------------------:|---------:|----------------:|------|-----------|-------------:|------------------------:|------------------:|-----------:|
| DC-A  | 50 | 10 | 500 | 5  | 親   | None   | 17,500 | 500 | 0   | 18,000 |
| DC-B  | 50 | 10 | 500 | 15 | 子   | DC-A   |  1,750 |   0 | 150 |  1,900 |

---

## 5. シナリオ例

### シナリオ 1: 親子関係を作る方が最適（2 DC）

**設定**

| DC | 需要 d | 保管単価 h | ロット Q | タリフA a |
|----|--------|-----------|---------|----------|
| DC-A | 50 | 10 | 500 | 5 |
| DC-B | 50 | 10 | 500 | 15 |

DC 間タリフ B：DC-A → DC-B = 3、DC-B → DC-A = 3

**コスト比較**（週次、円）

| パターン | DC-A コスト | DC-B コスト | 合計 |
|---------|-----------|-----------|------|
| 両方孤立 | 17,500 + 250 = 17,750 | 17,500 + 750 = 18,250 | **36,000** |
| DC-B が DC-A の子 | 17,500 + 500 = 18,000 | 1,750 + 150 = 1,900 | **19,900** ← 最適 |
| DC-A が DC-B の子 | 1,750 + 150 = 1,900 | 17,500 + 1,500 = 19,000 | **20,900** |

> 在庫削減効果（31,500→3,500）が輸送コスト増（250+150=400）を大きく上回るため、
> DC-B を DC-A の子にする構成が最適。

**期待する出力**:
```python
{
  "status": "Optimal",
  "total_weekly_cost": 19900.0,
  "parent_of": {"DC-A": None, "DC-B": "DC-A"},
  "cost_breakdown": [
    {"scenario": "baseline",  "dc_id": "DC-A", "holding_cost": 17500, "supplier_transport_cost": 250,  "dc_transport_cost": 0,   "total": 17750},
    {"scenario": "baseline",  "dc_id": "DC-B", "holding_cost": 17500, "supplier_transport_cost": 750,  "dc_transport_cost": 0,   "total": 18250},
    {"scenario": "baseline",  "dc_id": None,   "holding_cost": 35000, "supplier_transport_cost": 1000, "dc_transport_cost": 0,   "total": 36000},
    {"scenario": "optimized", "dc_id": "DC-A", "holding_cost": 17500, "supplier_transport_cost": 500,  "dc_transport_cost": 0,   "total": 18000},
    {"scenario": "optimized", "dc_id": "DC-B", "holding_cost": 1750,  "supplier_transport_cost": 0,    "dc_transport_cost": 150, "total": 1900},
    {"scenario": "optimized", "dc_id": None,   "holding_cost": 19250, "supplier_transport_cost": 500,  "dc_transport_cost": 150, "total": 19900},
  ]
}
```

---

### シナリオ 2: 全 DC 孤立が最適（2 DC）

**設定**

| DC | 需要 d | 保管単価 h | ロット Q | タリフA a |
|----|--------|-----------|---------|----------|
| DC-A | 50 | 2 | 500 | 5 |
| DC-B | 50 | 2 | 500 | 5 |

DC 間タリフ B：DC-A → DC-B = 70、DC-B → DC-A = 70

**コスト比較**（週次、円）

| パターン | DC-A コスト | DC-B コスト | 合計 |
|---------|-----------|-----------|------|
| 両方孤立 | 3,500 + 250 = 3,750 | 3,500 + 250 = 3,750 | **7,500** ← 最適 |
| DC-B が DC-A の子 | 3,500 + 500 = 4,000 | 350 + 3,500 = 3,850 | **7,850** |
| DC-A が DC-B の子 | 350 + 3,500 = 3,850 | 3,500 + 500 = 4,000 | **7,850** |

> DC 間輸送コストが高いため、在庫削減効果（3,150）を輸送コスト増（3,250）が上回り、
> 全 DC 孤立が最適。

**期待する出力**:
```python
{
  "status": "Optimal",
  "total_weekly_cost": 7500.0,
  "parent_of": {"DC-A": None, "DC-B": None},
  "cost_breakdown": [  # 全孤立が最適なので baseline と optimized は同一
    {"scenario": "baseline",  "dc_id": "DC-A", "holding_cost": 3500, "supplier_transport_cost": 250, "dc_transport_cost": 0, "total": 3750},
    {"scenario": "baseline",  "dc_id": "DC-B", "holding_cost": 3500, "supplier_transport_cost": 250, "dc_transport_cost": 0, "total": 3750},
    {"scenario": "baseline",  "dc_id": None,   "holding_cost": 7000, "supplier_transport_cost": 500, "dc_transport_cost": 0, "total": 7500},
    {"scenario": "optimized", "dc_id": "DC-A", "holding_cost": 3500, "supplier_transport_cost": 250, "dc_transport_cost": 0, "total": 3750},
    {"scenario": "optimized", "dc_id": "DC-B", "holding_cost": 3500, "supplier_transport_cost": 250, "dc_transport_cost": 0, "total": 3750},
    {"scenario": "optimized", "dc_id": None,   "holding_cost": 7000, "supplier_transport_cost": 500, "dc_transport_cost": 0, "total": 7500},
  ]
}
```

---

### シナリオ 3: DC-C を親にした集約が最適（3 DC）

**設定**

| DC | 需要 d | 保管単価 h | ロット Q | タリフA a |
|----|--------|-----------|---------|----------|
| DC-A | 100 | 10 | 500 | 5 |
| DC-B | 100 | 10 | 500 | 15 |
| DC-C | 100 | 2  | 500 | 5 |

DC 間タリフ B：DC-A ↔ DC-B = 3（双方向）、DC-C ↔ 他 = 70（双方向）

**コスト比較**（週次、円）

| パターン | 合計 |
|---------|------|
| 全孤立 | 18,000 + 19,000 + 4,000 = **41,000** |
| DC-B が DC-A の子・DC-C 孤立 | 18,500 + 3,800 + 4,000 = **26,300** |
| DC-B が DC-A の子・DC-C が DC-A の子 | 19,000 + 3,800 + 7,700 = **30,500** |
| DC-A・DC-B が DC-C の子 | 10,500 + 10,500 + 5,000 = **26,000** ← 最適 |

※ DC-A・DC-B（子）の内訳: それぞれ 在庫 3,500 + DC-C→X 輸送 7,000 = 10,500。DC-C（親）の内訳: 在庫 3,500 + 仕入れ先輸送 1,500 = 5,000

> DC-C は保管単価 h=2 が低いため、大ロット Q を抱えても在庫コストが小さく、
> 親 DC として DC-A・DC-B を束ねる役割に適している。
> DC-C ↔ 他の輸送コスト（70/ケース）は高いが、
> DC-A・DC-B の在庫削減効果（各 14,000/週）がそれを上回る。

**期待する出力**:
```python
{
  "status": "Optimal",
  "total_weekly_cost": 26000.0,
  "parent_of": {"DC-A": "DC-C", "DC-B": "DC-C", "DC-C": None},
  "cost_breakdown": [
    {"scenario": "baseline",  "dc_id": "DC-A", "holding_cost": 17500, "supplier_transport_cost": 500,  "dc_transport_cost": 0,     "total": 18000},
    {"scenario": "baseline",  "dc_id": "DC-B", "holding_cost": 17500, "supplier_transport_cost": 1500, "dc_transport_cost": 0,     "total": 19000},
    {"scenario": "baseline",  "dc_id": "DC-C", "holding_cost": 3500,  "supplier_transport_cost": 500,  "dc_transport_cost": 0,     "total": 4000},
    {"scenario": "baseline",  "dc_id": None,   "holding_cost": 38500, "supplier_transport_cost": 2500, "dc_transport_cost": 0,     "total": 41000},
    {"scenario": "optimized", "dc_id": "DC-A", "holding_cost": 3500,  "supplier_transport_cost": 0,    "dc_transport_cost": 7000,  "total": 10500},
    {"scenario": "optimized", "dc_id": "DC-B", "holding_cost": 3500,  "supplier_transport_cost": 0,    "dc_transport_cost": 7000,  "total": 10500},
    {"scenario": "optimized", "dc_id": "DC-C", "holding_cost": 3500,  "supplier_transport_cost": 1500, "dc_transport_cost": 0,     "total": 5000},
    {"scenario": "optimized", "dc_id": None,   "holding_cost": 10500, "supplier_transport_cost": 1500, "dc_transport_cost": 14000, "total": 26000},
  ]
}
```
