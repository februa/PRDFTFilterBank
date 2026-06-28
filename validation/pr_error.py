from __future__ import annotations

import numpy as np

from filterbank import FilterBankConfig, PRDFTFilterBank


def evaluate_pr_error(
    x: np.ndarray,
    config: FilterBankConfig | None = None,
) -> dict[str, float]:
    filterbank = PRDFTFilterBank(config or FilterBankConfig())
    reconstructed = filterbank.synthesis(filterbank.analysis(x))
    error = np.asarray(reconstructed) - np.asarray(x)
    ref = np.maximum(np.abs(np.asarray(x)), 1e-12)
    amp_error_db = 20.0 * np.log10(np.maximum(np.abs(reconstructed), 1e-12) / ref)
    return {
        "max_abs_error": float(np.max(np.abs(error))),
        "rms_error": float(np.sqrt(np.mean(np.abs(error) ** 2))),
        "max_amp_error_db": float(np.max(np.abs(amp_error_db))),
    }
