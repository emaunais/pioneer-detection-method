"""
Pioneer Detection Method (PDM)
==============================

A minimal Python implementation of the Pioneer Detection Method (PDM)—
a convergence-based expert-aggregation algorithm designed for environments
with structural change and heterogeneous learning speeds. The method
identifies “pioneers”: experts whose predictions or opinions deviate early
but toward whom others subsequently converge.

This simplified version is intentionally lightweight and pedagogical:

- no input validation
- no missing-value handling
- fixed cross-sectional benchmark: mean of all other experts
- orientation measured through single-period slopes (first differences)
- weights rescaled to sum to 1 whenever any pioneer is detected

The algorithm follows the three canonical PDM steps:

Step 1 — Distance condition
    An expert moves closer to the group:
    |x_i^t − m_-i^t| < |x_i^{t−1} − m_-i^{t−1}|

Step 2 — Orientation condition
    The group moves more toward the expert than the expert moves toward the group:
    |Δm_-i^t| > |Δx_i^t|

Step 3 — Proportion condition
    Relative contribution of the group’s movement:
    |Δm_-i^t| / (|Δm_-i^t| + |Δx_i^t|)

Weights are computed from Step 3 and normalized across experts at each t.
If no pioneer exists at time t, the pooled estimate defaults to the simple
cross-sectional mean.

This code corresponds to the approach introduced in:
    Vansteenberghe, Eric (2025),
    "Insurance Supervision under Climate Change: A Pioneer Detection Method,"
    The Geneva Papers on Risk and Insurance – Issues and Practice,
    https://doi.org/10.1057/s41288-025-00367-y

The PDM is applicable beyond insurance supervision—including adaptive
forecasting under non-stationarity and multi-agent systems where early
detectors of a regime shift must guide collective behavior
(e.g., drone swarms, robotic fleets, autonomous-vehicle coordination).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO


def compute_pioneer_weights_simple(forecasts: pd.DataFrame) -> pd.DataFrame:
    """
    Compute pioneer weights from a (T x N) DataFrame of forecasts.

    Parameters
    ----------
    forecasts : pandas.DataFrame
        Rows are time periods, columns are experts. Values are numeric.

    Returns
    -------
    weights : pandas.DataFrame
        Same shape as `forecasts`, containing pioneer weights in [0, 1].
    """
    # Work on a float copy
    X = forecasts.astype(float)

    # Step 0: aggregate "other experts" for each expert (mean of others)
    m_minus = pd.DataFrame(index=X.index, columns=X.columns, dtype=float)
    for col in X.columns:
        others = X.drop(columns=col)
        m_minus[col] = others.mean(axis=1)

    # One-period slopes (differences) for each expert and for others
    delta_X = X.diff()
    delta_m = m_minus.diff()

    # Step 1: distance reduction condition
    distance = (X - m_minus).abs()
    distance_prev = distance.shift(1)
    cond_distance = distance < distance_prev

    # Step 2: orientation / convergence condition
    cond_orientation = delta_m.abs() > delta_X.abs()

    # Step 3: proportion of convergence attributed to expert i
    denom = delta_m.abs() + delta_X.abs()
    proportion = delta_m.abs() / denom

    # Conditions must both hold and denominator must be > 0
    mask = cond_distance & cond_orientation & (denom > 0)
    raw = proportion.where(mask, 0.0)

    # Normalise across experts so that weights sum to 1 at each t
    row_sums = raw.sum(axis=1)
    weights = raw.div(row_sums.replace(0.0, np.nan), axis=0)

    return weights


def pooled_forecast_simple(
    forecasts: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.Series:
    """
    Pooled forecast: S_t = sum_i w_i^t * x_i^t.

    If at time t all weights are NaN or sum to zero (no pioneer detected),
    the pooled forecast falls back to the simple mean of forecasts at t.
    """
    forecasts = forecasts.astype(float)
    weights = weights.astype(float)

    weighted_sum = (forecasts * weights).sum(axis=1, min_count=1)

    # Rows where weights are "inactive": all NaN or sum == 0
    weight_sums = weights.sum(axis=1, min_count=1)
    no_pioneer = weight_sums.isna() | (weight_sums == 0)

    # Fallback: simple cross-sectional mean when no pioneer exists
    fallback_mean = forecasts.mean(axis=1)

    pooled = weighted_sum.copy()
    pooled[no_pioneer] = fallback_mean[no_pioneer]

    return pooled

# (You can keep the synthetic examples and plotting here, or move them to examples/)
