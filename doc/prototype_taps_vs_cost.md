# prototype_taps_per_band と処理量の関係

Version: 0.1

---

# 1. 目的

本書は、`prototype_taps_per_band` を変更したときに

- prototype filter 長
- 理論計算量
- 実装上の重さ
- PR / ビーム応答への影響

がどう変わるかを整理したものである。

対象実装は、現在の Python 実装で採用している

- 複素変調
- 低域 FIR
- decimation / interpolation
- subband 内 FFT / beamforming / IFFT

の構成である。

---

# 2. 定義

現在の実装では、prototype 長 `L` は以下で定義している。

```text
L = D * taps_per_band + 1
```

ここで

- `D`: decimation
- `taps_per_band`: `prototype_taps_per_band`

である。

今回の条件は

```text
D = 32
```

なので

```text
L = 32 * taps_per_band + 1
```

となる。

---

# 3. 代表値

| `prototype_taps_per_band` | prototype 長 `L` |
|---|---:|
| 4 | 129 |
| 8 | 257 |
| 12 | 385 |
| 16 | 513 |
| 24 | 769 |
| 32 | 1025 |
| 64 | 2049 |

---

# 4. 処理量との関係

## 4.1 基本関係

現在の解析部は、各帯域ごとに

- 入力を複素変調
- 長さ `L` の FIR
- `D` 点ごとに decimate

を行っている。

合成部は、各帯域ごとに

- upsample
- 長さ `L` の FIR
- 複素逆変調

を行っている。

したがって、FIR 部分の処理量は概ね

```text
処理量 ∝ L
```

すなわち

```text
処理量 ∝ prototype_taps_per_band
```

である。

`D` は固定なので、`prototype_taps_per_band` を 2 倍にすると、FIR 部分の計算量はほぼ 2 倍になる。

## 4.2 解析側の概算

解析側の代表計算量は

```text
C_analysis ∝ Mch * K * N * L
```

で見られる。

## 4.3 合成側の概算

合成側の代表計算量は

```text
C_synthesis ∝ Nbeam * K * N * L
```

で見られる。

今回の条件では

- `Mch = 32`
- `Nbeam = 181`
- `K = 32`
- `N = 32768`

なので、支配的なのは合成側である。

比で見ると

```text
C_synthesis / C_analysis ≈ Nbeam / Mch = 181 / 32 ≈ 5.66
```

となる。

つまり `prototype_taps_per_band` を増やしたとき、特に重くなるのはビーム出力側の合成 FIR である。

---

# 5. taps_per_band の比と処理量比

`prototype_taps_per_band` を変えたときの FIR 処理量比は、おおむねそのまま比で見てよい。

| 変更 | 処理量比 |
|---|---:|
| `8 -> 16` | 約 `2.0` 倍 |
| `8 -> 24` | 約 `3.0` 倍 |
| `8 -> 32` | 約 `4.0` 倍 |
| `16 -> 24` | 約 `1.5` 倍 |
| `16 -> 32` | 約 `2.0` 倍 |

---

# 6. 品質とのトレードオフ

現在の実装では、`prototype_taps_per_band` を増やすと概ね以下の傾向になる。

- 帯域分離が良くなる
- leakage が減る
- 解析->合成の近似再構成誤差が改善しやすい
- ビームピークレベルの落ち込みが小さくなりやすい
- その代わり FIR 部分が比例で重くなる

逆に `prototype_taps_per_band` を小さくすると

- 処理は軽い
- ただし再構成誤差は増えやすい
- 振幅利得が少し落ちやすい
- ピークレベルが 0 dB から少し下がりやすい

---

# 7. 現時点の実用上の目安

今回確認した範囲では、実装上の感触は次の通りである。

| `prototype_taps_per_band` | 傾向 |
|---|---|
| 8 | 軽い。ピーク方位は出るが、PR はやや悪い |
| 16 | バランスが良い |
| 24 | PR は改善しやすいが、かなり重くなる |

したがって、設計の初期検討では

- 軽さ優先: `8`
- バランス優先: `16`
- 品質優先: `24`

の 3 点を比較軸にするとよい。

---

# 8. MATLAB 設計時の使い方

MATLAB 実装では、まず `prototype_taps_per_band = 8` で通し、

1. 解析->合成が動くか
2. 60 deg にピークが立つか
3. RMS レベルがどれだけ落ちるか

を確認する。

その後、品質不足なら

```text
8 -> 16 -> 24
```

の順で上げるのが安全である。

---

# 9. まとめ

現在の構成では

```text
prototype_taps_per_band を増やす
=> prototype 長が線形に増える
=> 解析/合成 FIR の処理量がほぼ線形に増える
=> 特に合成側コストが効く
```

である。

よって、`prototype_taps_per_band` は

- 品質
- 実行時間

の最も分かりやすいトレードオフパラメータとして扱える。
