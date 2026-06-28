from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FilterBankConfig:
    sample_rate: float = 32768.0
    n_bands: int = 32
    n_used_bands: int = 16
    decimation: int = 32
    prototype_taps_per_band: int = 8
    prototype_beta: float = 1.0

    def __post_init__(self) -> None:
        if self.sample_rate <= 0.0:
            raise ValueError("sample_rate must be positive")
        if self.n_bands <= 0:
            raise ValueError("n_bands must be positive")
        if self.decimation <= 0:
            raise ValueError("decimation must be positive")
        if self.decimation != self.n_bands:
            raise ValueError("This implementation assumes critical sampling: decimation == n_bands")
        if self.n_used_bands <= 0 or self.n_used_bands > self.n_bands // 2:
            raise ValueError("n_used_bands must be in the range [1, n_bands // 2]")
        if self.prototype_taps_per_band <= 0:
            raise ValueError("prototype_taps_per_band must be positive")
        if self.prototype_beta <= 0.0:
            raise ValueError("prototype_beta must be positive")

    @property
    def band_width(self) -> float:
        return self.sample_rate / self.n_bands

    @property
    def subband_rate(self) -> float:
        return self.sample_rate / self.decimation

    @property
    def prototype_length(self) -> int:
        return self.decimation * self.prototype_taps_per_band + 1

    @property
    def group_delay_samples(self) -> int:
        return (self.prototype_length - 1) // 2

    @property
    def band_centers_hz(self) -> np.ndarray:
        centers = np.arange(self.n_bands, dtype=float) * self.band_width
        centers[centers >= self.sample_rate / 2.0] -= self.sample_rate
        return centers

    @property
    def positive_band_centers_hz(self) -> np.ndarray:
        return self.band_centers_hz[: self.n_used_bands]


def make_kaiser_prototype(config: FilterBankConfig) -> np.ndarray:
    n = np.arange(config.prototype_length, dtype=float) - config.group_delay_samples
    normalized_cutoff = 0.5 / config.decimation
    prototype = (
        2.0
        * normalized_cutoff
        * np.sinc(2.0 * normalized_cutoff * n)
        * np.kaiser(config.prototype_length, config.prototype_beta)
    )
    return np.asarray(prototype, dtype=float)
