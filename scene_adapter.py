from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from beamforming import beam_angles_cosspace, steering_vector
from filterbank import FilterBankConfig, PRDFTFilterBank


@dataclass(frozen=True)
class ArrayConfig:
    n_ch: int = 32
    sound_speed_mps: float = 1500.0
    sample_rate_hz: float = 32768.0
    aperture_axis: int = 0
    centered: bool = True

    @property
    def spacing_m(self) -> float:
        return self.sound_speed_mps / self.nyquist_hz / 2.0

    @property
    def nyquist_hz(self) -> float:
        return self.sample_rate_hz / 2.0


@dataclass(frozen=True)
class SignalConfig:
    frequency_hz: float = 1000.0
    bearing_deg: float = 60.0
    distance_m: float = 1000.0
    rms_amplitude: float = 1.0

    @property
    def peak_amplitude(self) -> float:
        return float(self.rms_amplitude * np.sqrt(2.0))


@dataclass(frozen=True)
class NoiseConfig:
    level_db: float = -30.0
    seed: int = 0


@dataclass(frozen=True)
class BeamformerConfig:
    n_beams: int = 181
    min_angle_deg: float = 0.0
    max_angle_deg: float = 180.0
    use_cosspace: bool = True

    def beam_angles_deg(self) -> np.ndarray:
        if self.use_cosspace:
            return beam_angles_cosspace(self.n_beams)
        return np.linspace(self.min_angle_deg, self.max_angle_deg, self.n_beams)


@dataclass(frozen=True)
class SimulationConfig:
    sample_rate_hz: float = 32768.0
    processing_rate_hz: float = 1.0
    sound_speed_mps: float = 1500.0
    n_bands: int = 32
    n_used_bands: int = 16
    decimation: int = 32
    prototype_taps_per_band: int = 8
    prototype_beta: float = 1.0
    array: ArrayConfig = field(default_factory=ArrayConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    beamformer: BeamformerConfig = field(default_factory=BeamformerConfig)

    def __post_init__(self) -> None:
        if self.sample_rate_hz <= 0.0:
            raise ValueError("sample_rate_hz must be positive")
        if self.processing_rate_hz <= 0.0:
            raise ValueError("processing_rate_hz must be positive")
        if self.decimation != self.n_bands:
            raise ValueError("This implementation assumes decimation == n_bands")
        if self.n_used_bands > self.n_bands // 2:
            raise ValueError("n_used_bands must not exceed n_bands // 2")
        if self.array.sample_rate_hz != self.sample_rate_hz or self.array.sound_speed_mps != self.sound_speed_mps:
            object.__setattr__(
                self,
                "array",
                ArrayConfig(
                    n_ch=self.array.n_ch,
                    sound_speed_mps=self.sound_speed_mps,
                    sample_rate_hz=self.sample_rate_hz,
                    aperture_axis=self.array.aperture_axis,
                    centered=self.array.centered,
                ),
            )

    @property
    def block_size(self) -> int:
        return int(round(self.sample_rate_hz / self.processing_rate_hz))

    @property
    def block_duration_s(self) -> float:
        return self.block_size / self.sample_rate_hz

    @property
    def sample_rate(self) -> float:
        return self.sample_rate_hz

    @property
    def c(self) -> float:
        return self.sound_speed_mps

    @property
    def n_ch(self) -> int:
        return self.array.n_ch

    @property
    def n_beams(self) -> int:
        return self.beamformer.n_beams

    @property
    def source_frequency_hz(self) -> float:
        return self.signal.frequency_hz

    @property
    def source_bearing_deg(self) -> float:
        return self.signal.bearing_deg

    @property
    def source_amplitude(self) -> float:
        return self.signal.peak_amplitude

    @property
    def noise_level_db(self) -> float:
        return self.noise.level_db

    @property
    def spacing_m(self) -> float:
        return self.array.spacing_m

    @property
    def axis_t(self) -> np.ndarray:
        return np.arange(self.block_size, dtype=float) / self.sample_rate_hz

    @property
    def filterbank(self) -> FilterBankConfig:
        return FilterBankConfig(
            sample_rate=self.sample_rate_hz,
            n_bands=self.n_bands,
            n_used_bands=self.n_used_bands,
            decimation=self.decimation,
            prototype_taps_per_band=self.prototype_taps_per_band,
            prototype_beta=self.prototype_beta,
        )

    @property
    def summary(self) -> dict[str, float | int]:
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "processing_rate_hz": self.processing_rate_hz,
            "block_size": self.block_size,
            "sound_speed_mps": self.sound_speed_mps,
            "n_channels": self.array.n_ch,
            "spacing_m": self.array.spacing_m,
            "n_bands": self.n_bands,
            "n_used_bands": self.n_used_bands,
            "band_width_hz": self.filterbank.band_width,
            "subband_rate_hz": self.filterbank.subband_rate,
            "prototype_length": self.filterbank.prototype_length,
            "source_frequency_hz": self.signal.frequency_hz,
            "source_bearing_deg": self.signal.bearing_deg,
            "source_rms_amplitude": self.signal.rms_amplitude,
            "source_peak_amplitude": self.signal.peak_amplitude,
            "noise_level_db": self.noise.level_db,
            "n_beams": self.beamformer.n_beams,
        }


def _add_local_dependency(name: str) -> None:
    repo_path = Path(__file__).resolve().parents[1] / name
    if repo_path.exists():
        sys.path.insert(0, str(repo_path))


def render_scene(config: SimulationConfig) -> tuple[np.ndarray, np.ndarray]:
    _add_local_dependency("scene_renderer")
    from scene_renderer import (  # type: ignore
        AcousticSource,
        ConstantEnvelope,
        FreeField,
        LinearArray,
        Receiver,
        Scene,
        SceneRenderer,
        SourceComponent,
        StaticPose,
        ToneSpectrum,
    )

    receiver = Receiver(
        trajectory=StaticPose(position_world=[0.0, 0.0, 0.0], heading_deg=0.0),
        array=LinearArray(
            n_ch=config.array.n_ch,
            spacing=config.array.spacing_m,
            axis=config.array.aperture_axis,
            centered=config.array.centered,
        ),
    )
    component = SourceComponent.from_amplitude(
        spectrum=ToneSpectrum(config.signal.frequency_hz),
        envelope=ConstantEnvelope(),
        amplitude=config.signal.peak_amplitude,
    )
    scene = Scene(
        sources=[
            AcousticSource.from_relative_bearing(
                bearing_deg=config.signal.bearing_deg,
                distance=config.signal.distance_m,
                receiver_pose=receiver.trajectory.pose(0.0),
                components=[component],
                elevation_deg=0.0,
            )
        ],
        ambient_fields=[],
        environment=FreeField(c=config.sound_speed_mps),
    )
    x = SceneRenderer().render(scene, receiver, config.axis_t)
    return np.asarray(x, dtype=np.complex128), receiver.array.positions()


def add_uncorrelated_white_noise(
    x: np.ndarray,
    noise_level_db: float,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    x = np.asarray(x, dtype=np.complex128)
    rng = rng or np.random.default_rng(0)
    signal_rms = np.sqrt(np.mean(np.abs(x) ** 2))
    noise_rms = signal_rms * (10.0 ** (noise_level_db / 20.0))
    noise = (
        rng.standard_normal(x.shape) + 1j * rng.standard_normal(x.shape)
    ) / np.sqrt(2.0)
    return x + noise_rms * noise


def run_subband_beamforming(
    x: np.ndarray,
    positions: np.ndarray,
    config: SimulationConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(np.real(x), dtype=np.float64)
    positions = np.asarray(positions, dtype=float)
    if x.ndim != 2:
        raise ValueError("x must have shape (n_ch, n_sample)")
    if x.shape[-1] != config.block_size:
        raise ValueError("This implementation expects one block per run")

    filterbank = PRDFTFilterBank(config.filterbank)
    beam_angles_deg = config.beamformer.beam_angles_deg()

    x_subbands = filterbank.analysis(x)
    x_positive = filterbank.positive_bands(x_subbands)
    n_frame = x_positive.shape[-1]
    local_freq_hz = filterbank.local_frequency_axis(n_frame)
    positive_centers_hz = filterbank.positive_band_centers_hz

    y_positive_spectrum = np.zeros(
        (config.n_beams, config.filterbank.n_used_bands, n_frame),
        dtype=np.complex128,
    )
    for band, center_hz in enumerate(positive_centers_hz):
        x_band_spectrum = np.fft.fft(x_positive[:, band, :], axis=-1)
        absolute_freq_hz = center_hz + local_freq_hz
        steering = steering_vector(
            positions=positions,
            angles_deg=beam_angles_deg,
            frequency_hz=absolute_freq_hz,
            c=config.sound_speed_mps,
        )
        weights = np.conj(np.transpose(steering, (1, 0, 2))) / config.n_ch
        y_positive_spectrum[:, band, :] = np.einsum(
            "bcf,cf->bf",
            weights,
            x_band_spectrum,
            optimize=True,
        )

    y_positive_time = np.fft.ifft(y_positive_spectrum, axis=-1)
    y_full_spectrum = filterbank.restore_full_band_spectra(y_positive_spectrum)
    y_full_subbands = np.fft.ifft(y_full_spectrum, axis=-1)
    y_time = np.real(filterbank.synthesis(y_full_subbands))
    return y_time, y_positive_time, beam_angles_deg
