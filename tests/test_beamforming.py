from __future__ import annotations

from functools import lru_cache

import numpy as np

from scene_adapter import (
    ArrayConfig,
    BeamformerConfig,
    NoiseConfig,
    SignalConfig,
    SimulationConfig,
    add_uncorrelated_white_noise,
    render_scene,
    run_subband_beamforming,
)
from validation import evaluate_beam_response


@lru_cache(maxsize=1)
def _clean_case() -> tuple[SimulationConfig, np.ndarray, np.ndarray]:
    config = SimulationConfig(
        signal=SignalConfig(frequency_hz=1000.0, bearing_deg=60.0, rms_amplitude=1.0),
        beamformer=BeamformerConfig(n_beams=181),
        noise=NoiseConfig(level_db=-30.0),
        array=ArrayConfig(n_ch=32),
    )
    x, positions = render_scene(config)
    y_time, _, beam_angles_deg = run_subband_beamforming(x, positions, config)
    return config, y_time, beam_angles_deg


@lru_cache(maxsize=1)
def _noisy_case() -> tuple[SimulationConfig, np.ndarray, np.ndarray]:
    config = SimulationConfig(
        signal=SignalConfig(frequency_hz=1000.0, bearing_deg=60.0, rms_amplitude=1.0),
        beamformer=BeamformerConfig(n_beams=181),
        noise=NoiseConfig(level_db=-30.0),
        array=ArrayConfig(n_ch=32),
    )
    x, positions = render_scene(config)
    x_noisy = add_uncorrelated_white_noise(x, config.noise.level_db)
    y_time, _, beam_angles_deg = run_subband_beamforming(x_noisy, positions, config)
    return config, y_time, beam_angles_deg


def test_simulation_config_derives_block_and_signal_values() -> None:
    config = SimulationConfig(
        signal=SignalConfig(rms_amplitude=1.0),
        beamformer=BeamformerConfig(n_beams=181),
        noise=NoiseConfig(level_db=-30.0),
        array=ArrayConfig(n_ch=32),
    )

    assert config.block_size == 32768
    assert np.isclose(config.spacing_m, config.c / (config.sample_rate / 2.0) / 2.0)
    assert np.isclose(config.source_amplitude, np.sqrt(2.0))


def test_delay_and_sum_beamforming_peaks_near_60deg() -> None:
    config, y_time, beam_angles_deg = _clean_case()
    metrics = evaluate_beam_response(
        y_time=y_time,
        beam_angles_deg=beam_angles_deg,
        sample_rate=config.sample_rate,
        target_frequency_hz=config.source_frequency_hz,
    )

    assert y_time.shape == (config.n_beams, config.block_size)
    assert abs(metrics["peak_angle_deg"] - config.source_bearing_deg) <= 2.0


def test_beam_response_has_peak_near_source_direction() -> None:
    config, y_time, beam_angles_deg = _clean_case()
    metrics = evaluate_beam_response(
        y_time=y_time,
        beam_angles_deg=beam_angles_deg,
        sample_rate=config.sample_rate,
        target_frequency_hz=config.source_frequency_hz,
    )

    peak_idx = int(np.argmax(metrics["level_db"]))
    source_idx = int(np.argmin(np.abs(metrics["angles_deg"] - config.source_bearing_deg)))
    assert peak_idx == source_idx
    assert abs(metrics["peak_level_db"]) < 0.7


def test_beam_response_remains_visible_with_noise() -> None:
    config, y_time, beam_angles_deg = _noisy_case()
    metrics = evaluate_beam_response(
        y_time=y_time,
        beam_angles_deg=beam_angles_deg,
        sample_rate=config.sample_rate,
        target_frequency_hz=config.source_frequency_hz,
    )

    assert abs(metrics["peak_angle_deg"] - config.source_bearing_deg) <= 4.0
