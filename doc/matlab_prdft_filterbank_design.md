# PRDFTFilterBank MATLAB実装設計書

Version: 0.3

---

# 1. 目的

本書は、MATLAB 上で

- 解析から合成まで完全に decimated subband 処理で閉じる
- 複素変調 + 低域 FIR + decimation/interpolation を使う
- 各サブ帯域で delay-and-sum beamforming を行う

ための実装設計を整理したものである。

本書は、現在の Python 実装の構造に合わせて更新した版である。

---

# 2. 実装方式

## 2.1 現在の Python 実装と合わせる前提

現在の Python 実装は、各帯域について

1. 複素変調で帯域中心を 0 Hz へ落とす
2. 低域 FIR をかける
3. decimation する
4. サブ帯域内 FFT / beamforming / IFFT を行う
5. interpolation する
6. 同じ低域 FIR をかける
7. 複素逆変調で元帯域へ戻す
8. 全帯域を加算する

という構成である。

MATLAB 実装もまずこの構成に合わせる。

## 2.2 処理フロー

```text
x(m, n)
  -> analysis modulation
  -> lowpass FIR
  -> decimation
x_sb(m, k, r)
  -> subband FFT
X_sb(m, k, q)
  -> beamforming
Y_sb(b, k, q)
  -> subband IFFT
y_sb(b, k, r)
  -> interpolation
  -> lowpass FIR
  -> synthesis modulation
y(b, n)
```

ここで

- `m`: channel index
- `b`: beam index
- `k`: subband index
- `n`: フルレート時間 index
- `r`: decimation 後の subband 時間 index
- `q`: subband FFT bin index

である。

---

# 3. システムパラメータ

## 3.1 基本条件

```matlab
fs = 32768;
block_rate = 1;
N = fs / block_rate;          % 32768
c = 1500;
```

## 3.2 フィルタバンク条件

```matlab
K = 32;
Kuse = 16;
D = 32;
Nr = N / D;                   % 1024
band_width = fs / K;          % 1024 Hz
fs_sb = fs / D;               % 1024 Hz
```

## 3.3 アレイ条件

```matlab
Mch = 32;
spacing = c / (fs / 2) / 2;
idx = 0:Mch-1;
xpos = (idx - mean(idx)) * spacing;
```

## 3.4 信号条件

```matlab
f0 = 1000;
theta0_deg = 60;
a_rms = 1.0;
a_peak = sqrt(2) * a_rms;
```

## 3.5 ビーム条件

```matlab
Nbeam = 181;
beam_angle_deg = acosd(linspace(1, -1, Nbeam));
```

## 3.6 prototype 条件

現在の Python 既定値に合わせるなら

```matlab
taps_per_band = 8;
beta = 1.0;
Lp = D * taps_per_band + 1;   % 257
```

品質寄りで始めたいなら

```matlab
taps_per_band = 16;
beta = 1.0;
Lp = 513;
```

も候補になる。

---

# 4. prototype filter 設計

## 4.1 現在の Python 実装と同じ式

prototype `h[p]` は Kaiser 窓付き sinc で以下のように作る。

```matlab
n = (0:Lp-1) - (Lp-1)/2;
fc_norm = 0.5 / D;
h = 2 * fc_norm * sinc(2 * fc_norm * n) .* kaiser(Lp, beta).';
```

ここで `sinc(x)` は MATLAB の正規化 sinc を使うか、自前定義をそろえる。

## 4.2 意味

- cutoff は `fs / (2D)` 相当
- 複素変調後の低域成分だけを通す
- その後 decimation する

## 4.3 設計パラメータ

prototype の主要パラメータは

- `taps_per_band`
- `beta`

の 2 つである。

処理量と関係は [prototype_taps_vs_cost.md](C:/Users/febru/Documents/workspace/projects/github/PRDFTFilterBank/doc/prototype_taps_vs_cost.md) を参照。

---

# 5. 帯域中心周波数

現在の Python 実装では帯域中心は以下で定義している。

```matlab
band_centers = (0:K-1) * band_width;
band_centers(band_centers >= fs/2) = band_centers(band_centers >= fs/2) - fs;
```

したがって `K=32` では

```text
0, 1024, 2048, ..., 15360, -16384, -15360, ..., -1024
```

となる。

正帯域として利用するのは前半 `Kuse=16` 帯域である。

---

# 6. 配列形状

## 6.1 入力信号

```text
x(m, n)                   size = (Mch, N)
```

## 6.2 解析後 subband 時系列

```text
x_sb(m, k, r)             size = (Mch, K, Nr)
```

## 6.3 利用帯域

```text
x_use(m, k, r)            size = (Mch, Kuse, Nr)
```

## 6.4 サブ帯域内 FFT 後

```text
X_use(m, k, q)            size = (Mch, Kuse, Nr)
```

## 6.5 ビーム形成後スペクトル

```text
Y_use(b, k, q)            size = (Nbeam, Kuse, Nr)
```

## 6.6 サブ帯域内 IFFT 後

```text
y_use(b, k, r)            size = (Nbeam, Kuse, Nr)
```

## 6.7 全帯域 subband 時系列

```text
y_sb_full(b, k, r)        size = (Nbeam, K, Nr)
```

## 6.8 合成後時間信号

```text
y(b, n)                   size = (Nbeam, N)
```

---

# 7. 解析フィルタバンク設計

## 7.1 基本式

各帯域 `k` の中心周波数を `f_k` とする。

入力 `x(m,n)` に対して

```text
x_mix(m, k, n) = x(m, n) exp(-j 2π f_k n / fs)
```

と複素変調する。

その後、低域 FIR `h[p]` を通して

```text
x_lp(m, k, n) = Σ_p h[p] x_mix(m, k, n-p)
```

を得る。

最後に `D` 点ごとに間引いて

```text
x_sb(m, k, r) = x_lp(m, k, rD)
```

を得る。

## 7.2 MATLAB 擬似コード

```matlab
for k = 1:K
    fk = band_centers(k);
    mod = exp(-1j * 2*pi * fk * (0:N-1) / fs);

    for m = 1:Mch
        x_mix = x(m, :) .* mod;
        x_lp = conv(x_mix, h, 'full');
        x_sb(m, k, :) = x_lp(gd+1 : D : gd + Nr*D);
    end
end
```

ここで

```matlab
gd = (Lp - 1) / 2;
```

である。

## 7.3 注意点

- `conv(..., 'full')` の切り出し位置を固定すること
- group delay を必ず吸収すること
- `Nr = N/D` 個のサンプルを切り出すこと

---

# 8. サブ帯域内ビームフォーミング

## 8.1 サブ帯域内 FFT

利用帯域だけ抜き出して

```matlab
X_use = fft(x_use, [], 3);
```

とする。

## 8.2 ローカル周波数軸

```matlab
q = 0:Nr-1;
f_local = q;
f_local(q >= Nr/2) = f_local(q >= Nr/2) - Nr;
f_local = f_local * fs_sb / Nr;
```

今回の条件では

```text
0,1,...,511,-512,...,-1 [Hz]
```

となる。

## 8.3 絶対周波数軸

帯域 `k` の絶対周波数は

```text
f_abs(k, q) = f_center(k) + f_local(q)
```

で与える。

## 8.4 steering vector

```text
tau(m, b) = xpos(m) cos(theta_b) / c
a(m, b, k, q) = exp(-j 2π f_abs(k, q) tau(m, b))
```

## 8.5 Delay-and-Sum

```text
w(m, b, k, q) = conj(a(m, b, k, q)) / Mch
Y_use(b, k, q) = Σ_m w(m, b, k, q) X_use(m, k, q)
```

## 8.6 サブ帯域時系列へ戻す

```matlab
y_use = ifft(Y_use, [], 3);
```

---

# 9. 正帯域から全帯域への復元

現在の Python 実装では、利用した正帯域スペクトル `Y_use` から、負帯域側を FFT 領域で共役鏡像復元している。

概念的には

```matlab
Y_full = zeros(Nbeam, K, Nr);
Y_full(:, 1:Kuse, :) = Y_use;
Y_full(:, Kuse+1, :) = 0;

for k = 2:Kuse
    Y_full(:, K-k+2, :) = conj(circshift(flip(Y_use(:, k, :), 3), 1, 3));
end
```

のような扱いになる。

その後

```matlab
y_sb_full = ifft(Y_full, [], 3);
```

として全帯域 subband 時系列へ戻す。

---

# 10. 合成フィルタバンク設計

## 10.1 基本式

各帯域 `k` の subband 時系列 `y_sb(b, k, r)` を、まず `D` 倍 upsample する。

```text
y_up(b, k, n) = upsample(y_sb(b, k, r), D)
```

その後、同じ低域 FIR `h[p]` を通す。

```text
y_lp(b, k, n) = Σ_p h[p] y_up(b, k, n-p)
```

最後に複素逆変調する。

```text
y_mod(b, k, n) = y_lp(b, k, n) exp(+j 2π f_k n / fs)
```

全帯域を加算して

```text
y(b, n) = D Σ_k y_mod(b, k, n)
```

とする。

## 10.2 MATLAB 擬似コード

```matlab
for k = 1:K
    fk = band_centers(k);
    mod = exp(+1j * 2*pi * fk * (0:N-1) / fs);

    for b = 1:Nbeam
        up = zeros(1, N);
        up(1:D:end) = y_sb_full(b, k, :);
        y_lp = conv(up, h, 'full');
        y(b, :) = y(b, :) + D * y_lp(gd+1 : gd+N) .* mod;
    end
end

y = real(y);
```

---

# 11. 計算量の見方

## 11.1 FIR 部分

現在の構成では、FIR 長 `L = D * taps_per_band + 1` が支配的である。

解析:

```text
C_analysis ∝ Mch * K * N * L
```

合成:

```text
C_synthesis ∝ Nbeam * K * N * L
```

したがって

```text
処理量 ∝ prototype_taps_per_band
```

と見てよい。

詳細は [prototype_taps_vs_cost.md](C:/Users/febru/Documents/workspace/projects/github/PRDFTFilterBank/doc/prototype_taps_vs_cost.md) を参照。

## 11.2 FFT 部分

subband 内 FFT は

```text
Kuse * Nr log2 Nr
```

であり、フル長 `32768` 点 FFT を毎回使うより軽い。

---

# 12. 設計上の注意点

## 12.1 振幅定義を隠さない

```matlab
a_rms = 1.0;
a_peak = sqrt(2) * a_rms;
```

を明示する。

## 12.2 group delay の切り出し位置を固定する

解析と合成で `gd = (Lp-1)/2` を同じ意味で使うこと。

## 12.3 ローカル周波数軸は signed frequency にする

後半ビンを負周波数として扱わないと steering vector が崩れる。

## 12.4 絶対周波数で steering を計算する

```text
f_abs = f_center + f_local
```

を必ず使うこと。

## 12.5 正帯域から負帯域を戻す規則を固定する

共役鏡像の作り方が 1 サンプルずれると、実信号復元が崩れる。

## 12.6 `prototype_taps_per_band` は品質と速度のトレードオフ

- `8`: 軽い
- `16`: バランス
- `24`: 品質寄り

という感触で設計を進める。

---

# 13. 推奨関数分割

```text
main_prdft_beamforming.m
make_parameters.m
design_prototype_filter.m
analyze_modulated_subbands.m
beamform_decimated_subbands.m
restore_full_subband_spectra.m
synthesize_modulated_subbands.m
evaluate_beam_response.m
plot_beam_response.m
```

---

# 14. 実装順序

1. パラメータ生成
2. prototype filter 設計
3. 解析部実装
4. 解析->合成だけで PR 確認
5. subband beamforming 実装
6. 正帯域から全帯域復元
7. 評価部実装
8. 雑音付き確認

---

# 15. 最低限の確認項目

1. `x -> x_sb -> y` で大きく破綻しないこと
2. 1000 Hz, 60 deg 入力で 60 deg にピークが出ること
3. RMS=1 入力でピークレベルが 0 dB 近傍に出ること
4. `prototype_taps_per_band` を変えたときに速度と品質の変化を説明できること
5. 途中でフル長 FFT を使わず処理が閉じていること

---

# 16. まとめ

MATLAB で今から作るべきものは、

- 複素変調
- 低域 FIR
- decimation/interpolation
- subband 内 FFT/BF/IFFT

で最後まで閉じる実装である。

この構成は、現在の Python 実装と一致しており、MATLAB 側でも同じ設計思想で再現できる。
