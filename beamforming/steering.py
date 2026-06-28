from __future__ import annotations

import numpy as np


def beam_angles_cosspace(n_beams: int = 181) -> np.ndarray:
    if n_beams <= 1:
        raise ValueError("n_beams must be greater than 1")
    return np.rad2deg(np.arccos(np.linspace(1.0, -1.0, n_beams)))


def steering_vector(
    positions: np.ndarray,
    angles_deg: np.ndarray,
    frequency_hz: np.ndarray | float,
    c: float,
) -> np.ndarray:
    positions = np.asarray(positions, dtype=float)
    angles_deg = np.asarray(angles_deg, dtype=float)
    frequency_hz = np.asarray(frequency_hz, dtype=float)

    directions = np.stack(
        [
            np.cos(np.deg2rad(angles_deg)),
            np.sin(np.deg2rad(angles_deg)),
            np.zeros_like(angles_deg),
        ],
        axis=-1,
    )
    tau = positions @ directions.T / float(c)
    phase = -2.0j * np.pi * tau[:, :, np.newaxis] * frequency_hz[np.newaxis, np.newaxis, :]
    return np.exp(phase)
