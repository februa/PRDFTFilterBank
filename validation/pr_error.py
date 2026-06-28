from __future__ import annotations

import numpy as np

from filterbank import FilterBankConfig, PRDFTFilterBank


def evaluate_pr_error(
    x: np.ndarray,
    config: FilterBankConfig | None = None,
) -> dict[str, float]:
    filterbank = PRDFTFilterBank(config or FilterBankConfig())
    reconstructed = np.real(filterbank.synthesis(filterbank.analysis(x)))
    x = np.asarray(x, dtype=float)
    error = reconstructed - x
    x_rms = float(np.sqrt(np.mean(x ** 2)))
    err_rms = float(np.sqrt(np.mean(error ** 2)))
    snr_db = float(20.0 * np.log10(max(x_rms, 1e-12) / max(err_rms, 1e-12)))
    gain_ratio = float(np.sqrt(np.mean(reconstructed ** 2)) / max(x_rms, 1e-12))

    spectrum_in = np.fft.rfft(x, axis=-1)
    spectrum_out = np.fft.rfft(reconstructed, axis=-1)
    ref = np.abs(spectrum_in)
    significant = ref > (1e-3 * np.max(ref))
    amp_error_db = 20.0 * np.log10(
        np.maximum(np.abs(spectrum_out[significant]), 1e-9)
        / np.maximum(ref[significant], 1e-9)
    )
    abs_amp_error_db = np.abs(amp_error_db[np.isfinite(amp_error_db)])

    return {
        "max_abs_error": float(np.max(np.abs(error))),
        "rms_error": err_rms,
        "snr_db": snr_db,
        "gain_ratio": gain_ratio,
        "max_amp_error_db": float(np.max(abs_amp_error_db)),
        "p95_amp_error_db": float(np.percentile(abs_amp_error_db, 95.0)),
    }
