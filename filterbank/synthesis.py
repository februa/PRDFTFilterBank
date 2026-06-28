from __future__ import annotations

import numpy as np

from .prototype import FilterBankConfig, make_kaiser_prototype


class SynthesisDFTFilterBank:
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

    def process(self, subbands: np.ndarray) -> np.ndarray:
        subbands = np.asarray(subbands, dtype=np.complex128)
        if subbands.ndim != 3:
            raise ValueError("subbands must have shape (n_signal, n_bands, n_frame)")
        n_signal, n_bands, n_frame = subbands.shape
        if n_bands != self.config.n_bands:
            raise ValueError("unexpected number of bands")

        n_sample = n_frame * self.config.decimation
        time_index = np.arange(n_sample, dtype=float)
        out = np.zeros((n_signal, n_sample), dtype=np.complex128)

        for band, center_hz in enumerate(self._band_centers_hz):
            upsampled = np.zeros((n_signal, n_sample), dtype=np.complex128)
            upsampled[:, :: self.config.decimation] = subbands[:, band, :]
            filtered = np.asarray(
                [np.convolve(row, self.prototype, mode="full") for row in upsampled],
                dtype=np.complex128,
            )
            modulator = np.exp(1j * 2.0 * np.pi * center_hz * time_index / self.config.sample_rate)
            out += (
                self.config.decimation
                * filtered[:, self._group_delay : self._group_delay + n_sample]
                * modulator[np.newaxis, :]
            )
        return out
