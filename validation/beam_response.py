from __future__ import annotations

from pathlib import Path

import numpy as np


def evaluate_beam_response(
    y_time: np.ndarray,
    beam_angles_deg: np.ndarray,
    sample_rate: float,
    target_frequency_hz: float,
) -> dict[str, np.ndarray | float]:
    y_time = np.asarray(y_time)
    beam_angles_deg = np.asarray(beam_angles_deg, dtype=float)
    spectrum = np.fft.rfft(np.real(y_time), axis=-1)
    freq_hz = np.fft.rfftfreq(y_time.shape[-1], d=1.0 / sample_rate)
    idx = int(np.argmin(np.abs(freq_hz - target_frequency_hz)))
    N = y_time.shape[-1]
    level = np.maximum(10.0 * np.log10(2 * ((np.abs(spectrum[:, idx] / N)) ** 2)), -300.0)
    peak_idx = int(np.argmax(level))
    return {
        "angles_deg": beam_angles_deg,
        "level_db": level,
        "peak_angle_deg": float(beam_angles_deg[peak_idx]),
        "peak_level_db": float(level[peak_idx]),
        "frequency_bin_hz": float(freq_hz[idx]),
    }


def plot_beam_response(
    beam_metrics: dict[str, np.ndarray | float],
    output_path: str | Path,
    expected_angle_deg: float | None = None,
    title: str | None = None,
) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    angles_deg = np.asarray(beam_metrics["angles_deg"], dtype=float)
    level_db = np.asarray(beam_metrics["level_db"], dtype=float)
    peak_angle_deg = float(beam_metrics["peak_angle_deg"])
    peak_level_db = float(beam_metrics["peak_level_db"])
    frequency_bin_hz = float(beam_metrics["frequency_bin_hz"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    ax.plot(angles_deg, level_db, color="tab:blue", linewidth=2.0, label="Beam response")
    ax.scatter([peak_angle_deg], [peak_level_db], color="tab:red", zorder=3, label="Peak")
    ax.axvline(peak_angle_deg, color="tab:red", linestyle="--", linewidth=1.2)

    if expected_angle_deg is not None:
        ax.axvline(expected_angle_deg, color="tab:green", linestyle=":", linewidth=1.5, label="Expected DOA")

    ax.set_xlabel("Angle [deg]")
    ax.set_ylabel("Level [dB]")
    ax.set_title(title or f"Beam Response at {frequency_bin_hz:.1f} Hz")
    ax.set_xlim(float(np.min(angles_deg)), float(np.max(angles_deg)))
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
