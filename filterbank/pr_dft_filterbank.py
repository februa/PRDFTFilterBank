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

    @property
    def band_centers_hz(self) -> np.ndarray:
        return self.config.band_centers_hz

    @property
    def positive_band_centers_hz(self) -> np.ndarray:
        return self.config.positive_band_centers_hz

    def analysis(self, x: np.ndarray) -> np.ndarray:
        return self.analysis_bank.process(x)

    def synthesis(self, subbands: np.ndarray) -> np.ndarray:
        return self.synthesis_bank.process(subbands)

    def positive_bands(self, subbands: np.ndarray) -> np.ndarray:
        return np.asarray(subbands)[:, : self.config.n_used_bands, :]

    def local_frequency_axis(self, n_frame: int) -> np.ndarray:
        return np.fft.fftfreq(n_frame, d=1.0 / self.config.subband_rate)

    def restore_full_band_spectra(self, positive_spectra: np.ndarray) -> np.ndarray:
        positive_spectra = np.asarray(positive_spectra, dtype=np.complex128)
        if positive_spectra.ndim != 3:
            raise ValueError("positive_spectra must have shape (n_signal, n_used_bands, n_frame)")
        n_signal, n_used_bands, n_frame = positive_spectra.shape
        if n_used_bands != self.config.n_used_bands:
            raise ValueError("unexpected number of used bands")

        full_spectra = np.zeros((n_signal, self.config.n_bands, n_frame), dtype=np.complex128)
        full_spectra[:, :n_used_bands, :] = positive_spectra
        full_spectra[:, self.config.n_used_bands, :] = 0.0

        for band in range(1, n_used_bands):
            mirrored = np.conj(np.roll(positive_spectra[:, band, ::-1], 1, axis=-1))
            full_spectra[:, -band, :] = mirrored
        return full_spectra
