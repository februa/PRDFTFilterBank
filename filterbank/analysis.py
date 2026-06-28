from __future__ import annotations

import numpy as np

from .prototype import FilterBankConfig, make_rectangular_prototype


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
            else make_rectangular_prototype(self.config)
        )
        if self.prototype.shape != (self.config.n_bands,):
            raise ValueError("prototype must have shape (n_bands,)")
        n = np.arange(self.config.n_bands, dtype=float)
        self._analysis_twiddle = np.exp(1j * np.pi * n / self.config.n_bands)

    def process(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x)
        if x.ndim != 2:
            raise ValueError("x must have shape (n_ch, n_sample)")
        n_ch, n_sample = x.shape
        if n_sample % self.config.decimation != 0:
            raise ValueError("n_sample must be divisible by decimation")

        n_frame = n_sample // self.config.decimation
        frames = x.reshape(n_ch, n_frame, self.config.n_bands)
        windowed = (
            frames
            * self.prototype[np.newaxis, np.newaxis, :]
            * self._analysis_twiddle[np.newaxis, np.newaxis, :]
        )
        spectrum = np.fft.fft(windowed, axis=-1)
        return np.transpose(spectrum, (0, 2, 1))
