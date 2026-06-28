# PRDFTFilterBank

PR 指向の DFT フィルタバンクとサブ帯域 Delay-and-Sum ビームフォーマの最小実装です。

- `filterbank/`
  - 32 分割 DFT 解析/合成フィルタバンク
- `beamforming/`
  - steering vector / delay-and-sum
- `validation/`
  - PR 誤差評価 / ビーム応答評価 / プロット
- `examples/`
  - SceneRenderer, SPFlow 連携例

## Configuration

設定は [scene_adapter.py](C:/Users/febru/Documents/workspace/projects/github/PRDFTFilterBank/scene_adapter.py) の `SimulationConfig` に集約しています。

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

導出される値:

- `block_size = sample_rate_hz / processing_rate_hz`
- `array.spacing_m = c / (fs/2) / 2`
- `signal.peak_amplitude = signal.rms_amplitude * sqrt(2)`
- `filterbank.band_width = sample_rate_hz / n_bands`

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
)
```
