from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FilterBankConfig:
    sample_rate: float = 32768.0
    n_bands: int = 32
    n_used_bands: int = 16
    decimation: int = 32

    def __post_init__(self) -> None:
        if self.n_bands <= 0:
            raise ValueError("n_bands must be positive")
        if self.n_used_bands <= 0 or self.n_used_bands > self.n_bands // 2:
            raise ValueError("n_used_bands must be in the range [1, n_bands // 2]")
        if self.decimation != self.n_bands:
            raise ValueError("This implementation assumes critical sampling: decimation == n_bands")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")

    @property
    def band_width(self) -> float:
        return self.sample_rate / self.n_bands

    @property
    def subband_rate(self) -> float:
        return self.sample_rate / self.decimation


def make_rectangular_prototype(config: FilterBankConfig) -> np.ndarray:
    return np.ones(config.n_bands, dtype=float)
