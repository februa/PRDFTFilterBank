from __future__ import annotations

import numpy as np

from filterbank import FilterBankConfig, PRDFTFilterBank
from validation import evaluate_pr_error


def test_analysis_filterbank_concentrates_1000hz_near_the_first_subband() -> None:
    config = FilterBankConfig()
    axis_t = np.arange(32768, dtype=float) / config.sample_rate
    x = np.sin(2.0 * np.pi * 1000.0 * axis_t)[np.newaxis, :]

    filterbank = PRDFTFilterBank(config)
    analyzed = filterbank.analysis(x)
    energy = np.sum(np.abs(analyzed[0]) ** 2, axis=-1)

    dominant_pair = np.argsort(energy)[-2:]
    remaining_peak = np.max(energy[2:])

    assert set(dominant_pair.tolist()) == {0, 1}
    assert min(energy[0], energy[1]) > remaining_peak


def test_analysis_synthesis_is_perfect_for_block_input() -> None:
    config = FilterBankConfig()
    rng = np.random.default_rng(0)
    x = rng.standard_normal((2, 32768))

    metrics = evaluate_pr_error(x, config)

    assert metrics["max_abs_error"] < 1e-12
    assert metrics["rms_error"] < 1e-13
    assert metrics["max_amp_error_db"] < 1e-9
