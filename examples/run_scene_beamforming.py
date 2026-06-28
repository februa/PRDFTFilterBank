from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scene_adapter import SimulationConfig, add_uncorrelated_white_noise, render_scene, run_subband_beamforming
from validation import evaluate_beam_response, evaluate_pr_error, plot_beam_response


def main() -> None:
    config = SimulationConfig()
    x, positions = render_scene(config)
    x_noisy = add_uncorrelated_white_noise(x, config.noise.level_db)
    y_time, _, beam_angles_deg = run_subband_beamforming(x_noisy, positions, config)

    pr_metrics = evaluate_pr_error(np.real(x[:1]), config.filterbank)
    beam_metrics = evaluate_beam_response(
        y_time=y_time,
        beam_angles_deg=beam_angles_deg,
        sample_rate=config.sample_rate_hz,
        target_frequency_hz=config.signal.frequency_hz,
    )
    plot_path = ROOT / "outputs" / "beam_response.png"
    plot_beam_response(
        beam_metrics=beam_metrics,
        output_path=plot_path,
        expected_angle_deg=config.signal.bearing_deg,
        title=f"Beam Response at {config.signal.frequency_hz:.1f} Hz",
    )

    print("config:", config.summary)
    print("input shape:", x.shape)
    print("output shape:", y_time.shape)
    print("PR:", pr_metrics)
    print("Peak angle:", beam_metrics["peak_angle_deg"])
    print("Peak bin Hz:", beam_metrics["frequency_bin_hz"])
    peak_idx = int(np.argmax(beam_metrics["level_db"]))
    print("Peak level dB:", beam_metrics["level_db"][peak_idx])
    print("Beam response plot:", plot_path)


if __name__ == "__main__":
    main()
