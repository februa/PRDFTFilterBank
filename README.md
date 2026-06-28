# PRDFTFilterBank

PR 指向の DFT フィルタバンクとサブ帯域 Delay-and-Sum ビームフォーマの最小実装です。

- `filterbank/`
  - decimated subband 解析/合成フィルタバンク
- `beamforming/`
  - steering vector / delay-and-sum
- `validation/`
  - PR 誤差評価 / ビーム応答評価 / プロット
- `examples/`
  - SceneRenderer, SPFlow 連携例
- `doc/`
  - MATLAB 実装設計書 / prototype と処理量の整理

## Local Setup

このリポジトリは `scene_renderer` と `spflow` を sibling directory として見つける前提でも動きます。
最も簡単な配置は以下です。

```text
github/
├─ PRDFTFilterBank/
├─ scene_renderer/
└─ spflow/
```

### 1. Clone

```bash
git clone https://github.com/februa/PRDFTFilterBank.git
cd PRDFTFilterBank
```

`examples/run_scene_beamforming.py` と `examples/spflow_pipeline.py` をそのまま使う場合は、同じ親ディレクトリへ依存リポジトリも clone します。

```bash
cd ..
git clone https://github.com/februa/scene_renderer.git
git clone https://github.com/februa/spflow.git
cd PRDFTFilterBank
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 3. Install

```bash
pip install -e .
pip install pytest
```

依存リポジトリを editable install したい場合は以下でもよいです。

```bash
pip install -e ../scene_renderer
pip install -e ../spflow
```

## Run

ビーム応答の確認:

```bash
python examples/run_scene_beamforming.py
```

実行後、以下が出力されます。

- 181 本のビーム出力
- `1000 Hz` / `60 deg` に対するピーク確認
- `outputs/beam_response.png`

SPFlow 連携例:

```bash
python examples/spflow_pipeline.py
```

## Test

```bash
python -m pytest -q -p no:cacheprovider
```

## Configuration

設定は `scene_adapter.py` の `SimulationConfig` に集約しています。

ユーザが主に直接指定する値:

- `sample_rate_hz`
- `processing_rate_hz`
- `sound_speed_mps`
- `signal.frequency_hz`
- `signal.bearing_deg`
- `signal.distance_m`
- `signal.rms_amplitude`
- `noise.level_db`
- `beamformer.n_beams`
- `array.n_ch`
- `prototype_taps_per_band`
- `prototype_beta`

導出される値:

- `block_size = sample_rate_hz / processing_rate_hz`
- `array.spacing_m = c / (fs/2) / 2`
- `signal.peak_amplitude = signal.rms_amplitude * sqrt(2)`
- `filterbank.band_width = sample_rate_hz / n_bands`
- `filterbank.prototype_length = decimation * prototype_taps_per_band + 1`

例:

```python
from scene_adapter import ArrayConfig, BeamformerConfig, NoiseConfig, SignalConfig, SimulationConfig

config = SimulationConfig(
    signal=SignalConfig(
        frequency_hz=1000.0,
        bearing_deg=60.0,
        rms_amplitude=1.0,
    ),
    noise=NoiseConfig(level_db=-30.0),
    beamformer=BeamformerConfig(n_beams=181),
    array=ArrayConfig(n_ch=32),
    prototype_taps_per_band=8,
    prototype_beta=1.0,
)
```
