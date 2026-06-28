from __future__ import annotations

import numpy as np

from .prototype import FilterBankConfig, make_kaiser_prototype


class AnalysisDFTFilterBank:
    def __init__(
        self,
        config: FilterBankConfig | None = None,
        prototype: np.ndarray | None = None,
    ) -> None:
        self.config = config or FilterBankConfig()
        self.prototype = (
            np.asarray(prototype, dtype=float)
            if prototype is not None
            else make_kaiser_prototype(self.config)
        )
        if self.prototype.shape != (self.config.prototype_length,):
            raise ValueError("prototype must have shape (prototype_length,)")
        self._group_delay = self.config.group_delay_samples
        self._band_centers_hz = self.config.band_centers_hz

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.complex128)
        if x.ndim != 2:
            raise ValueError("x must have shape (n_signal, n_sample)")
        n_signal, n_sample = x.shape
        if n_sample % self.config.decimation != 0:
            raise ValueError("n_sample must be divisible by decimation")

        n_frame = n_sample // self.config.decimation
        time_index = np.arange(n_sample, dtype=float)
        out = np.zeros((n_signal, self.config.n_bands, n_frame), dtype=np.complex128)

        for band, center_hz in enumerate(self._band_centers_hz):
            modulator = np.exp(-1j * 2.0 * np.pi * center_hz * time_index / self.config.sample_rate)
            mixed = x * modulator[np.newaxis, :]
            filtered = np.asarray(
                [np.convolve(row, self.prototype, mode="full") for row in mixed],
                dtype=np.complex128,
            )
            out[:, band, :] = filtered[
                :,
                self._group_delay : self._group_delay + n_frame * self.config.decimation : self.config.decimation,
            ]
        return out
