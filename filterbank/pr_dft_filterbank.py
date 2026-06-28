from __future__ import annotations

import numpy as np

from .analysis import AnalysisDFTFilterBank
from .prototype import FilterBankConfig
from .synthesis import SynthesisDFTFilterBank


class PRDFTFilterBank:
    def __init__(self, config: FilterBankConfig | None = None) -> None:
        self.config = config or FilterBankConfig()
        self.analysis_bank = AnalysisDFTFilterBank(self.config)
        self.synthesis_bank = SynthesisDFTFilterBank(self.config)

    def analysis(self, x: np.ndarray) -> np.ndarray:
        return self.analysis_bank.process(x)

    def synthesis(self, spectrum: np.ndarray) -> np.ndarray:
        return self.synthesis_bank.process(spectrum)

    def positive_bands(self, spectrum: np.ndarray) -> np.ndarray:
        return np.asarray(spectrum)[:, : self.config.n_used_bands, :]

    def restore_full_band_spectrum(self, positive_spectrum: np.ndarray) -> np.ndarray:
        positive_spectrum = np.asarray(positive_spectrum)
        if positive_spectrum.ndim != 3:
            raise ValueError("positive_spectrum must have shape (n_signal, n_used_bands, n_frame)")
        n_signal, n_used_bands, n_frame = positive_spectrum.shape
        if n_used_bands != self.config.n_used_bands:
            raise ValueError("unexpected number of used bands")

        out = np.zeros((n_signal, self.config.n_bands, n_frame), dtype=np.complex128)
        out[:, :n_used_bands, :] = positive_spectrum

        if self.config.n_bands % 2 == 0:
            nyquist = self.config.n_bands // 2
            out[:, nyquist, :] = 0.0

        for band in range(1, n_used_bands):
            out[:, -band, :] = np.conj(positive_spectrum[:, band, :])
        return out
