from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from filterbank import FilterBankConfig

from .steering import beam_angles_cosspace, steering_vector


@dataclass
class DelayAndSumSubbandBeamformer:
    positions: np.ndarray
    c: float = 1500.0
    config: FilterBankConfig = FilterBankConfig()
    beam_angles_deg: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.positions = np.asarray(self.positions, dtype=float)
        if self.positions.ndim != 2 or self.positions.shape[1] != 3:
            raise ValueError("positions must have shape (n_ch, 3)")
        if self.beam_angles_deg is None:
            self.beam_angles_deg = beam_angles_cosspace()
        else:
            self.beam_angles_deg = np.asarray(self.beam_angles_deg, dtype=float)

    def process(self, positive_subbands: np.ndarray) -> np.ndarray:
        positive_subbands = np.asarray(positive_subbands)
        if positive_subbands.ndim != 3:
            raise ValueError("positive_subbands must have shape (n_ch, n_used_bands, n_frame)")

        n_ch, n_bands, n_frame = positive_subbands.shape
        if n_ch != self.positions.shape[0]:
            raise ValueError("channel count and position count must match")
        if n_bands != self.config.n_used_bands:
            raise ValueError("unexpected number of used bands")

        local_freq_hz = np.fft.fftfreq(n_frame, d=1.0 / self.config.subband_rate)
        beam_count = self.beam_angles_deg.size
        out = np.zeros((beam_count, n_bands, n_frame), dtype=np.complex128)

        for band in range(n_bands):
            absolute_freq_hz = (band + 0.5) * self.config.band_width + local_freq_hz
            valid = (absolute_freq_hz >= 0.0) & (absolute_freq_hz <= self.config.sample_rate / 2.0)
            band_spectrum = np.fft.fft(positive_subbands[:, band, :], axis=-1)
            steering = steering_vector(
                positions=self.positions,
                angles_deg=self.beam_angles_deg,
                frequency_hz=absolute_freq_hz,
                c=self.c,
            )
            weights = np.conj(np.transpose(steering, (1, 0, 2))) / n_ch
            steered = np.einsum("bcf,cf->bf", weights, band_spectrum, optimize=True)
            steered[:, ~valid] = 0.0
            out[:, band, :] = np.fft.ifft(steered, axis=-1)
        return out
