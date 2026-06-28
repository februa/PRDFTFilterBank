from __future__ import annotations

import numpy as np

from filterbank import FilterBankConfig, PRDFTFilterBank
from validation import evaluate_pr_error


def test_analysis_filterbank_concentrates_1000hz_in_low_positive_bands() -> None:
    config = FilterBankConfig()
    axis_t = np.arange(32768, dtype=float) / config.sample_rate
    x = np.sin(2.0 * np.pi * 1000.0 * axis_t)[np.newaxis, :]

    filterbank = PRDFTFilterBank(config)
    analyzed = filterbank.analysis(x)
    energy = np.sum(np.abs(analyzed[0]) ** 2, axis=-1)

    peak_band = int(np.argmax(energy[: config.n_used_bands]))
    low_band_energy = float(np.sum(energy[:2]))
    remaining_energy = float(np.sum(energy[2: config.n_used_bands]))

    assert peak_band in (0, 1)
    assert low_band_energy > 10.0 * remaining_energy


def test_analysis_synthesis_has_reasonable_pr_quality_for_random_input() -> None:
    config = FilterBankConfig()
    rng = np.random.default_rng(0)
    x = rng.standard_normal((2, 32768))

    metrics = evaluate_pr_error(x, config)

    assert metrics["snr_db"] > 10.0
    assert abs(metrics["gain_ratio"] - 1.0) < 0.12
    assert metrics["p95_amp_error_db"] < 7.5
