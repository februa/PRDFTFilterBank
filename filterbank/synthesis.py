from __future__ import annotations

import numpy as np

from .prototype import FilterBankConfig, make_rectangular_prototype


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
            else make_rectangular_prototype(self.config)
        )
        if self.prototype.shape != (self.config.n_bands,):
            raise ValueError("prototype must have shape (n_bands,)")
        if np.any(self.prototype == 0.0):
            raise ValueError("prototype must be non-zero for synthesis")
        n = np.arange(self.config.n_bands, dtype=float)
        self._synthesis_twiddle = np.exp(-1j * np.pi * n / self.config.n_bands)

    def process(self, spectrum: np.ndarray) -> np.ndarray:
        spectrum = np.asarray(spectrum)
        if spectrum.ndim != 3:
            raise ValueError("spectrum must have shape (n_signal, n_bands, n_frame)")
        n_signal, n_bands, n_frame = spectrum.shape
        if n_bands != self.config.n_bands:
            raise ValueError("unexpected number of bands")

        frames = np.fft.ifft(np.transpose(spectrum, (0, 2, 1)), axis=-1)
        time_frames = np.real_if_close(
            frames
            * self._synthesis_twiddle[np.newaxis, np.newaxis, :]
            / self.prototype[np.newaxis, np.newaxis, :]
        )
        return np.asarray(time_frames).reshape(n_signal, n_frame * self.config.decimation)
