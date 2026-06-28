# PRDFTFilterBank MATLAB実装設計書

Version: 0.2

---

# 1. 目的

本書は、MATLAB 上で

- 解析から合成まで完全に decimated subband 処理で閉じる
- PR 指向の DFT 変調フィルタバンクを使う
- 各サブ帯域で delay-and-sum beamforming を行う

ための実装設計を整理したものである。

ここでいう「decimated subband 処理で閉じる」とは、解析フィルタバンクで低レートのサブ帯域時系列へ落とした後、

- サブ帯域内 FFT
- サブ帯域ビームフォーミング
- サブ帯域内 IFFT
- 合成フィルタバンク

まで、フルレートの `32768` 点 FFT / IFFT に戻らずに処理することを意味する。

---

# 2. 今回やりたい方式と現在の Python 実装の違い

## 2.1 やりたい方式

実装したい本来の処理は以下である。

```text
x_m[n]
  -> analysis polyphase / DFT FB
x_sb(m, k, r)
  -> 帯域ごとの時間方向 FFT
X_sb(m, k, q)
  -> 帯域ごとの beamforming
Y_sb(b, k, q)
  -> 帯域ごとの時間方向 IFFT
y_sb(b, k, r)
  -> synthesis polyphase / IDFT FB
y_b[n]
```

ここで

- `m`: channel index
- `b`: beam index
- `k`: subband index
- `n`: 元のフルレート時間 index
- `r`: decimation 後の低レート時間 index
- `q`: サブ帯域内 FFT bin index

である。

## 2.2 現在の Python 実装

現在の Python 実装は、理論確認を優先して、実質的に

```text
x[n]
  -> 32768点 rFFT
  -> 16帯域へ切り分け
  -> 帯域ごとに重み付け
  -> 32768点 irFFT
  -> y[n]
```

に近い。

つまり現在の Python 実装は

- ビーム応答の成立確認には有効
- 低レート subband 実装の計算量削減をそのまま実現しているわけではない

という位置付けである。

## 2.3 MATLAB で目指す実装

MATLAB では、上記 Python の簡易化は捨てて、

```text
analysis FB -> decimated subband -> subband processing -> synthesis FB
```

をそのまま実装する。

---

# 3. 処理全体フロー

```text
入力時間信号
x(m, n)                          size = (Mch, N)

解析フィルタバンク
x_sb(m, k, r)                    size = (Mch, K, Nr)

各サブ帯域の時間方向 FFT
X_sb(m, k, q)                    size = (Mch, Kuse, Nr)

各サブ帯域・各周波数 bin で beamforming
Y_sb(b, k, q)                    size = (Nbeam, Kuse, Nr)

各サブ帯域の時間方向 IFFT
y_sb(b, k, r)                    size = (Nbeam, Kuse, Nr)

未使用帯域を 0 として全帯域へ戻す
y_sb_full(b, k, r)               size = (Nbeam, K, Nr)

合成フィルタバンク
y(b, n)                          size = (Nbeam, N)

評価 FFT
Y_eval(b, f)
```

---

# 4. システムパラメータ

## 4.1 基本条件

```matlab
fs = 32768;
block_rate = 1;
N = fs / block_rate;      % 32768
c = 1500;
```

## 4.2 フィルタバンク条件

```matlab
K = 32;                   % 総帯域数
Kuse = 16;                % 利用帯域数
D = 32;                   % decimation
Nr = N / D;               % subband time length = 1024
band_width = fs / K;      % 1024 Hz
fs_sb = fs / D;           % 1024 Hz
```

## 4.3 アレイ条件

```matlab
Mch = 32;
spacing = c / (fs / 2) / 2;
idx = 0:Mch-1;
xpos = (idx - mean(idx)) * spacing;
```

## 4.4 信号条件

```matlab
f0 = 1000;
theta0_deg = 60;
a_rms = 1.0;
a_peak = sqrt(2) * a_rms;
```

## 4.5 ビーム条件

```matlab
Nbeam = 181;
beam_angle_deg = acosd(linspace(1, -1, Nbeam));
```

## 4.6 prototype filter 条件

完全 PR を厳密にやるなら prototype filter 設計が本体になる。まずは MATLAB 実装初版として、

- DFT 変調フィルタバンク
- `K = D = 32`
- prototype 長 `Lp = P * K`
- `P = 2, 4, 8` のいずれか

を明示的に決める。

推奨初期値:

```matlab
P = 4;
Lp = P * K;               % 128
```

この prototype は後で置き換えられるよう、独立パラメータとして持つこと。

---

# 5. 配列形状

## 5.1 入力信号

```text
x(m, n)                   size = (Mch, N)
```

## 5.2 解析後 subband 時系列

```text
x_sb(m, k, r)             size = (Mch, K, Nr)
```

## 5.3 利用帯域のみ抜き出し

```text
x_use(m, k, r)            size = (Mch, Kuse, Nr)
```

## 5.4 サブ帯域内 FFT 後

```text
X_use(m, k, q)            size = (Mch, Kuse, Nr)
```

## 5.5 ビーム形成後スペクトル

```text
Y_use(b, k, q)            size = (Nbeam, Kuse, Nr)
```

## 5.6 サブ帯域内 IFFT 後

```text
y_use(b, k, r)            size = (Nbeam, Kuse, Nr)
```

## 5.7 合成用の全帯域 subband 信号

```text
y_sb_full(b, k, r)        size = (Nbeam, K, Nr)
```

## 5.8 合成後時間信号

```text
y(b, n)                   size = (Nbeam, N)
```

---

# 6. 解析フィルタバンク設計

# 6.1 役割

解析部は、フルレート時間信号 `x(m, n)` から、decimation 後の複素サブ帯域時系列 `x_sb(m, k, r)` を生成する。

## 6.2 基本式

解析フィルタバンクは prototype `h[p]` を DFT 変調して構成する。

解析フィルタ:

```text
h_k[p] = h[p] * exp(-j 2π k p / K)
```

解析出力:

```text
x_sb(m, k, r)
= Σ_p h[p] * x(m, rD - p) * exp(-j 2π k p / K)
```

これは直接計算してもよいが、MATLAB 実装では polyphase 化した方がよい。

## 6.3 polyphase 形

prototype `h[p]` を `K` 相に分ける。

```text
h[p] -> e_l[u]
where p = uK + l,  l = 0,...,K-1
```

すなわち

```matlab
E = reshape(h, K, P);     % 実際の並びは要確認
```

とし、各 decimation 時刻 `r` で必要な過去サンプル列を `K` 相に並べ、最後に `K` 点 DFT する。

概念的には

```text
v_l(m, r) = Σ_u e_l[u] * x(m, rD - (uK + l))
x_sb(m, k, r) = Σ_l v_l(m, r) * exp(-j 2π k l / K)
```

である。

## 6.4 MATLAB 実装イメージ

1. 入力を `D` サンプルごとに進める
2. 各時刻で長さ `Lp` のバッファを取る
3. polyphase 成分ごとに内積する
4. 最後に `K` 点 FFT する

擬似コード:

```matlab
for r = 1:Nr
    n0 = (r-1) * D + 1;
    seg = x(:, n0:n0+Lp-1);              % 実装ではゼロ詰めや遅延方向を要整理

    for l = 1:K
        for u = 1:P
            v(:, l) = v(:, l) + E(l, u) * seg(:, ...);
        end
    end

    x_sb(:, :, r) = fft(v, [], 2);
end
```

実装では時間反転を含む畳み込み方向を厳密にそろえること。ここは MATLAB 実装時の最重要確認点の一つである。

## 6.5 解析部の出力確認

1000 Hz の単一トーンを入れたとき:

- 主成分は第1帯域付近に出る
- 隣接帯域漏れは prototype の性能に依存する
- 出力時系列長は `Nr = 1024` になる

---

# 7. サブ帯域内ビームフォーミング設計

## 7.1 基本方針

解析出力 `x_sb(m, k, r)` は、すでに decimation 後の低レート信号である。

この時点で 32768 点 FFT に戻ってはいけない。

各帯域について、長さ `Nr = 1024` の時系列に対して時間方向 FFT を取る。

```matlab
X_use = fft(x_use, [], 3);
```

## 7.2 サブ帯域内周波数軸

サブ帯域サンプリング周波数は

```text
fs_sb = fs / D = 1024 Hz
```

ゆえに、ローカル周波数軸は

```text
f_local[q] = q * fs_sb / Nr
```

ではなく、負周波数側を含む signed frequency に直す。

```matlab
q = 0:Nr-1;
f_local = q;
f_local(q >= Nr/2) = f_local(q >= Nr/2) - Nr;
f_local = f_local * fs_sb / Nr;
```

この条件では `fs_sb / Nr = 1 Hz` なので

```text
f_local = 0,1,...,511,-512,...,-1 [Hz]
```

である。

## 7.3 絶対周波数軸

各帯域 `k` の中心周波数オフセットは

```text
f_offset[k] = k * band_width
```

とし、絶対周波数は

```text
f_abs(k, q) = f_offset[k] + f_local[q]
```

で与える。

ここで `k = 0,1,...,Kuse-1` として扱う。

## 7.4 steering vector

チャネル位置 `xpos[m]`、ビーム角 `theta_b` に対し、遅延は

```text
tau(m, b) = xpos[m] * cos(theta_b) / c
```

steering vector は

```text
a(m, b, k, q) = exp(-j 2π f_abs(k, q) tau(m, b))
```

である。

## 7.5 Delay-and-Sum

重みは

```text
w(m, b, k, q) = conj(a(m, b, k, q)) / Mch
```

出力は

```text
Y_use(b, k, q) = Σ_m w(m, b, k, q) X_use(m, k, q)
```

である。

MATLAB 擬似コード:

```matlab
for k = 1:Kuse
    for b = 1:Nbeam
        tau = xpos * cosd(beam_angle_deg(b)) / c;
        for q = 1:Nr
            f = f_abs(k, q);
            a = exp(-1j * 2*pi * f * tau);
            w = conj(a) / Mch;
            Y_use(b, k, q) = sum(w .* squeeze(X_use(:, k, q)).');
        end
    end
end
```

## 7.6 サブ帯域時系列へ戻す

```matlab
y_use = ifft(Y_use, [], 3);
```

ここでも処理長は `Nr = 1024` のままである。

---

# 8. 合成フィルタバンク設計

## 8.1 基本方針

使用しない帯域はゼロにして、全帯域の subband 時系列 `y_sb_full(b, k, r)` を作る。

```matlab
y_sb_full = zeros(Nbeam, K, Nr);
y_sb_full(:, 1:Kuse, :) = y_use;
```

必要なら負周波数側帯域を共役対称で埋める。実信号復元を狙うなら、この帯域配置は解析側の定義と必ず整合させる。

## 8.2 合成基本式

合成フィルタ `g_k[p]` を用いて

```text
y_b[n] = Σ_k Σ_r y_sb_full(b, k, r) g_k[n - rD]
```

で復元する。

DFT 変調表現では

```text
g_k[p] = g[p] * exp(+j 2π k p / K)
```

である。

## 8.3 polyphase 合成形

合成では、まず各 decimated 時刻 `r` で `K` 点 IFFT を行い、polyphase 成分へ戻し、その後 overlap-add する。

概念式:

```text
u_l(b, r) = (1/K) Σ_k y_sb_full(b, k, r) exp(+j 2π k l / K)
```

その後

```text
y_b[n] = Σ_r Σ_l Σ_u u_l(b, r) s_l[u] δ[n - (rD + uK + l)]
```

ここで `s_l[u]` は synthesis prototype の polyphase 成分である。

## 8.4 MATLAB 実装イメージ

1. `ifft(..., [], 2)` で帯域方向 IFFT を行う
2. 各相成分を synthesis polyphase filter で重み付けする
3. `D` サンプル間隔で overlap-add する

擬似コード:

```matlab
for r = 1:Nr
    u = ifft(y_sb_full(:, :, r), [], 2);

    for l = 1:K
        for p = 1:P
            n0 = (r-1)*D + (p-1)*K + l;
            y(:, n0) = y(:, n0) + S(l, p) * u(:, l);
        end
    end
end
```

ここでも配列の並び、遅延方向、境界ゼロ詰めは必ず解析側と対で確認すること。

---

# 9. 完全に decimated subband で閉じることの意味

## 9.1 数式上の意味

フル長処理では、主な FFT サイズは `N = 32768` である。

一方、完全 decimated subband 処理では、解析後の主な処理サイズは

```text
Nr = N / D = 1024
```

へ落ち、その後の FFT / IFFT / beamforming は `Nr` ベースで進む。

つまり主処理サイズが

```text
N -> N / D
```

へ圧縮されたまま最後まで維持される。

## 9.2 Python 簡易実装との違い

現在の Python 簡易版は

```text
x -> 32768点 rFFT -> 帯域分割 -> 重み付け -> 32768点 irFFT
```

であるため、入口と出口にまだ `O(N log N)` のフル長処理が残っている。

MATLAB で目指す方式は

```text
x -> analysis FB -> low-rate subbands -> subband FFT/BF/IFFT -> synthesis FB -> y
```

であり、途中でフル長 FFT へ戻らない。

---

# 10. 演算量の見方

## 10.1 フルバンド方式

FFT 項だけ見ると

```text
C_full ≈ (Mch + Nbeam) N log2 N
```

## 10.2 decimated subband 方式

利用帯域 `Kuse` 本、各帯域長 `Nr = N/D` とすると

```text
C_sub ≈ Kuse (Mch + Nbeam) Nr log2 Nr
```

今回の条件では

```text
N = 32768
Nr = 1024
Kuse = 16
```

なので

```text
C_sub / C_full
= Kuse * (Nr log2 Nr) / (N log2 N)
= 16 * (1024 * 10) / (32768 * 15)
= 1/3
```

となる。

したがって FFT 項ベースでは

```text
約 66.7 % 軽減
```

である。

---

# 11. 設計上の注意点

## 11.1 prototype filter を独立設計にする

本質は prototype である。解析/合成の整合が取れていないと、後段 beamforming が正しくても再構成で崩れる。

## 11.2 解析と合成の polyphase 並び順を必ず固定する

`reshape` だけで済ませると MATLAB の列優先並びで破綻しやすい。`l` 相、`u` tap、時間反転の定義を紙に書いて固定すること。

## 11.3 帯域 index と絶対周波数の対応を固定する

`k = 0` が `0-1024 Hz` の帯域を表すのか、中心周波数 `512 Hz` を表すのかを実装前に決めること。

## 11.4 サブ帯域内 FFT の周波数軸は signed frequency にする

後半ビンを負周波数として扱わないと steering vector が崩れる。

## 11.5 使用しない帯域の扱いを明示する

`Kuse = 16` だけ処理するなら、残り帯域は 0 にするのか、共役対称で埋めるのかを解析/合成定義と合わせること。

## 11.6 RMS と peak を混同しない

評価を RMS 基準で行うなら

```matlab
a_peak = sqrt(2) * a_rms
```

を明示する。

## 11.7 FFT 正規化は元のブロック長で行う

最終 `Angle vs Level` 評価では

```matlab
A_peak = 2 * abs(Y(k0)) / N
A_rms = A_peak / sqrt(2)
```

を使う。

---

# 12. 推奨関数分割

```text
main_prdft_beamforming.m
make_parameters.m
design_prototype_filter.m
analyze_pr_dft_fb.m
beamform_decimated_subbands.m
synthesize_pr_dft_fb.m
evaluate_beam_response.m
plot_beam_response.m
```

役割:

- `design_prototype_filter.m`
  - prototype filter 生成
- `analyze_pr_dft_fb.m`
  - `x(m,n) -> x_sb(m,k,r)`
- `beamform_decimated_subbands.m`
  - `x_sb -> X_use -> Y_use -> y_use`
- `synthesize_pr_dft_fb.m`
  - `y_sb_full -> y(b,n)`

---

# 13. 実装順序

## Step1

パラメータ固定

- `fs, N, K, D, Kuse, Nr, c`
- `xpos`
- `beam_angle_deg`
- `P, Lp`

## Step2

prototype filter 設計

- まずは1種類に固定
- 単独で解析/合成の PR 性能を確認

## Step3

解析フィルタバンク実装

- `x -> x_sb`
- サブ帯域長が `1024` になることを確認

## Step4

サブ帯域内 beamforming 実装

- `x_sb -> X_use`
- 絶対周波数軸生成
- steering / weights / sum
- `Y_use -> y_use`

## Step5

合成フィルタバンク実装

- `y_sb_full -> y`

## Step6

評価部実装

- `y -> FFT`
- `1000 Hz` 抽出
- `Angle vs Level` 作図

## Step7

雑音付き確認

---

# 14. 最低限の確認項目

1. 解析->合成のみで入力波形がほぼ再現されること
2. 1000 Hz, 60 deg 入力で 60 deg 付近にビームピークが出ること
3. RMS=1 入力でピーク方位がほぼ 0 dB になること
4. 雑音付きでもピークが大きく崩れないこと
5. フル長 FFT を途中で使わずに処理が閉じていること

---

# 15. まとめ

MATLAB で今から作るべきものは、現在の Python 簡易版の焼き直しではなく、

- analysis polyphase DFT FB
- decimated subband 時系列
- subband 内 FFT/BF/IFFT
- synthesis polyphase DFT FB

で最後まで閉じる実装である。

この方式なら、理論確認だけでなく、本来狙っている計算量削減と構造上の一貫性を両立できる。
