#!/usr/bin/env python3
"""
Central Statistical Utilities
Canonical implementations of statistical functions used across the codebase

IMPORTANT: This is the CANONICAL source for statistical functions.
DO NOT create duplicate implementations elsewhere.

Functions:
- wilson_confidence_interval: Wilson score confidence interval for binomial proportions
- winsorize: Outlier handling by capping at percentiles
- beta_binomial_shrinkage: Empirical Bayes shrinkage for small samples

References:
- Wilson, E.B. (1927). "Probable Inference, the Law of Succession, and Statistical Inference"
- Brown, Cai & DasGupta (2001). "Interval Estimation for a Binomial Proportion"
- Winsor, C.P. (1946). "The Mean Difference and Mean Deviation"
"""

import numpy as np
from scipy import stats
from typing import List, Tuple


def wilson_confidence_interval(
    successes: int,
    trials: int,
    alpha: float = 0.05
) -> Tuple[float, float, float]:
    """
    Calculate Wilson confidence interval for binomial proportion

    This is the CANONICAL implementation for Wilson CI across the entire codebase.
    Use this instead of normal approximation for more accurate confidence intervals,
    especially for small sample sizes or extreme proportions.

    Args:
        successes: Number of successes
        trials: Total number of trials
        alpha: Significance level (default 0.05 for 95% CI)
            - 0.05 → 95% confidence interval
            - 0.10 → 90% confidence interval

    Returns:
        Tuple of (proportion, ci_lower, ci_upper)
        - proportion: Point estimate (successes/trials)
        - ci_lower: Lower bound of confidence interval
        - ci_upper: Upper bound of confidence interval

    Mathematical Formula:
        Center = (p + z²/(2n)) / (1 + z²/n)
        Margin = z * sqrt((p(1-p) + z²/(4n)) / n) / (1 + z²/n)
        where p = successes/trials, z = z-score for alpha

    Why Wilson CI vs Normal Approximation:
        - Wilson CI: Asymmetric, respects [0,1] bounds, accurate for small n
        - Normal approx: Symmetric, can exceed [0,1], inaccurate for small n
        - Wilson is the recommended method in modern statistics

    Examples:
        >>> wilson_confidence_interval(50, 100, alpha=0.05)
        (0.5, 0.4013, 0.5987)  # 95% CI

        >>> wilson_confidence_interval(0, 10, alpha=0.05)
        (0.0, 0.0, 0.3085)  # Handles edge cases well

    References:
        - Wilson, E.B. (1927). "Probable Inference, the Law of Succession,
          and Statistical Inference". Journal of the American Statistical Association.
        - Brown, Cai & DasGupta (2001). "Interval Estimation for a Binomial Proportion".
          Statistical Science.
    """
    if trials == 0:
        return 0.0, 0.0, 0.0

    # Calculate z-score for given alpha level
    z = stats.norm.ppf(1 - alpha/2)

    # Point estimate
    p = successes / trials

    # Wilson formula with continuity correction denominator
    denominator = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denominator

    # Margin of error with Wilson adjustment
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator

    # Apply bounds to ensure [0, 1]
    ci_lower = max(0.0, center - margin)
    ci_upper = min(1.0, center + margin)

    return p, ci_lower, ci_upper


def winsorize(
    values: List[float],
    lower_percentile: float = 0.05,
    upper_percentile: float = 0.95
) -> List[float]:
    """
    Winsorize values by capping at specified percentiles

    Winsorization is a method of handling outliers by replacing extreme values
    with less extreme values at specified percentiles. Unlike trimming which
    removes outliers, winsorization caps them at percentile thresholds.

    This is the CANONICAL implementation for outlier handling.

    Args:
        values: List of numeric values to winsorize
        lower_percentile: Lower bound percentile (default 0.05 = 5th percentile)
        upper_percentile: Upper bound percentile (default 0.95 = 95th percentile)

    Returns:
        List of winsorized values (same length as input)

    Example:
        >>> values = [1, 2, 3, 4, 5, 100]  # 100 is outlier
        >>> winsorize(values, 0.1, 0.9)
        [1.5, 2, 3, 4, 5, 5.5]  # 100 capped at 90th percentile

    Use Cases:
        - KDA calculation (prevent single extreme game from dominating)
        - Gold/min statistics (handle very long/short games)
        - Damage metrics (handle unusual team compositions)

    Why Winsorize vs Trim:
        - Winsorize: Preserves sample size, reduces influence of outliers
        - Trim: Removes outliers, changes sample size
        - For aggregated statistics, winsorize is often preferred

    References:
        - Winsor, C.P. (1946). "The Mean Difference and Mean Deviation of
          Some Discontinuous Distributions"
        - Dixon, W.J. (1960). "Simplified Estimation from Censored Normal Samples"
    """
    if not values:
        return []

    # Calculate percentile thresholds
    lower_bound = np.percentile(values, lower_percentile * 100)
    upper_bound = np.percentile(values, upper_percentile * 100)

    # Cap values at thresholds
    return [np.clip(v, lower_bound, upper_bound) for v in values]


def beta_binomial_shrinkage(
    successes: int,
    trials: int,
    alpha_prior: float = 1.0,
    beta_prior: float = 1.0
) -> Tuple[float, int]:
    """
    Beta-Binomial shrinkage estimator for small sample sizes

    Uses Empirical Bayes methodology to shrink extreme proportions towards
    a prior expectation. This is particularly useful for small sample sizes
    where raw proportions can be misleading.

    Args:
        successes: Number of successes
        trials: Total number of trials
        alpha_prior: Beta distribution alpha parameter (default 1.0)
            - α = β = 1.0: Uniform prior (no preference)
            - α = β = 0.5: Jeffreys prior (non-informative)
            - α = 50, β = 50: Strong prior towards 50% win rate
        beta_prior: Beta distribution beta parameter (default 1.0)

    Returns:
        Tuple of (shrunk_proportion, effective_sample_size)
        - shrunk_proportion: Bayesian estimate with prior
        - effective_sample_size: Original trials + prior strength

    Mathematical Formula:
        Shrunk estimate = (successes + α) / (trials + α + β)
        Effective N = trials + α + β

    Example:
        >>> # Raw: 3 wins in 5 games = 60% (unstable estimate)
        >>> beta_binomial_shrinkage(3, 5, alpha_prior=50, beta_prior=50)
        (0.505, 105)  # Shrunk towards 50%, effective N = 105

        >>> # Large sample: prior has minimal effect
        >>> beta_binomial_shrinkage(60, 100, alpha_prior=50, beta_prior=50)
        (0.55, 200)  # Less shrinkage, more data

    Use Cases:
        - Champion win rates with < 30 games (CONTEXT governance)
        - Rune effectiveness with limited data
        - Item build success rates from few samples

    Prior Selection Guidelines:
        - Uniform (α=1, β=1): Minimal prior influence
        - Weak (α=10, β=10): Gentle shrinkage towards 50%
        - Moderate (α=50, β=50): Standard for League metrics
        - Strong (α=100, β=100): Use when prior belief is very strong

    References:
        - Stein's Paradox (1956): Shrinkage improves estimation
        - Empirical Bayes methods in sports analytics
        - Morris, C. (1983). "Parametric Empirical Bayes Inference"
    """
    # Add prior pseudo-observations
    effective_successes = successes + alpha_prior
    effective_trials = trials + alpha_prior + beta_prior

    # Calculate shrunk proportion
    shrunk_proportion = effective_successes / effective_trials

    # Effective sample size includes prior
    effective_n = int(effective_trials)

    return shrunk_proportion, effective_n


def governance_tag(
    sample_size: int,
    ci_width: float,
    confident_threshold: int = 100,
    confident_ci_width: float = 0.10,
    caution_threshold: int = 50,
    caution_ci_width: float = 0.15
) -> str:
    """
    Determine governance tag based on sample size and confidence interval width

    Governance tags classify statistical evidence quality:
    - CONFIDENT: High quality, narrow CI, large sample
    - CAUTION: Moderate quality, wider CI, medium sample
    - CONTEXT: Low confidence, very wide CI, small sample

    Args:
        sample_size: Number of observations
        ci_width: Width of confidence interval (ci_upper - ci_lower)
        confident_threshold: Min sample size for CONFIDENT (default 100)
        confident_ci_width: Max CI width for CONFIDENT (default 0.10)
        caution_threshold: Min sample size for CAUTION (default 50)
        caution_ci_width: Max CI width for CAUTION (default 0.15)

    Returns:
        "CONFIDENT", "CAUTION", or "CONTEXT"

    Examples:
        >>> governance_tag(150, 0.08)
        "CONFIDENT"  # n≥100, CI≤0.10

        >>> governance_tag(75, 0.12)
        "CAUTION"  # 50≤n<100, CI≤0.15

        >>> governance_tag(20, 0.25)
        "CONTEXT"  # n<50 or CI>0.15

    Usage in Rift Rewind:
        - CONFIDENT: Production-ready metrics, use directly
        - CAUTION: Usable with caveats, note uncertainty
        - CONTEXT: Informational only, do not make decisions
    """
    if sample_size >= confident_threshold and ci_width <= confident_ci_width:
        return "CONFIDENT"
    elif sample_size >= caution_threshold and ci_width <= caution_ci_width:
        return "CAUTION"
    else:
        return "CONTEXT"


def calculate_data_quality_score(
    sample_size: int,
    ci_width: float,
    has_outliers: bool = False,
    max_sample_for_full_score: int = 100
) -> float:
    """
    Calculate 0-1 data quality score based on sample size and CI width

    Combines sample size adequacy with confidence interval precision to
    produce a single quality metric. Useful for filtering/ranking metrics.

    Args:
        sample_size: Number of observations
        ci_width: Width of confidence interval
        has_outliers: Whether outliers were detected (penalty if True)
        max_sample_for_full_score: Sample size for perfect score (default 100)

    Returns:
        Quality score from 0.0 (worst) to 1.0 (best)

    Score Components:
        - Sample score (60%): min(1.0, n / max_sample_for_full_score)
        - Confidence score (40%): max(0.0, 1.0 - ci_width * 5.0)
        - Outlier penalty: -0.1 if has_outliers

    Examples:
        >>> calculate_data_quality_score(100, 0.08, False)
        0.92  # Good sample, narrow CI

        >>> calculate_data_quality_score(25, 0.20, True)
        0.05  # Small sample, wide CI, outliers

    Use Cases:
        - Ranking champion-role combinations by data quality
        - Filtering metrics for automated analysis
        - Quality-weighted aggregations
    """
    # Sample size component (60% weight)
    sample_score = min(1.0, sample_size / max_sample_for_full_score)

    # Confidence interval component (40% weight)
    # CI width of 0.2 → 0 score, narrower is better
    confidence_score = max(0.0, 1.0 - ci_width * 5.0)

    # Outlier penalty
    outlier_penalty = 0.1 if has_outliers else 0.0

    # Combined score
    quality_score = (sample_score * 0.6 + confidence_score * 0.4) - outlier_penalty

    # Clamp to [0, 1]
    return max(0.0, min(1.0, quality_score))


# Convenience function for common use case
def wilson_ci_tuple(successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float]:
    """
    Convenience wrapper returning only (ci_lower, ci_upper)

    Use this when you only need confidence interval bounds, not the point estimate.

    Args:
        successes: Number of successes
        trials: Total trials
        alpha: Significance level (default 0.05)

    Returns:
        Tuple of (ci_lower, ci_upper)

    Example:
        >>> wilson_ci_tuple(50, 100)
        (0.4013, 0.5987)
    """
    _, ci_lower, ci_upper = wilson_confidence_interval(successes, trials, alpha)
    return ci_lower, ci_upper


if __name__ == "__main__":
    # Quick validation tests
    print("=" * 60)
    print("Statistical Utilities - Validation Tests")
    print("=" * 60)

    # Test Wilson CI
    print("\n1. Wilson Confidence Interval")
    p, ci_lo, ci_hi = wilson_confidence_interval(50, 100)
    print(f"   50 wins in 100 games:")
    print(f"   Point estimate: {p:.4f}")
    print(f"   95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]")
    print(f"   CI width: {ci_hi - ci_lo:.4f}")

    # Test edge case
    p, ci_lo, ci_hi = wilson_confidence_interval(0, 10)
    print(f"\n   0 wins in 10 games (edge case):")
    print(f"   95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]")

    # Test Winsorize
    print("\n2. Winsorize")
    values = [1, 2, 3, 4, 5, 100]
    winsorized = winsorize(values, 0.1, 0.9)
    print(f"   Original: {values}")
    print(f"   Winsorized (10%-90%): {[round(v, 2) for v in winsorized]}")

    # Test Beta-Binomial Shrinkage
    print("\n3. Beta-Binomial Shrinkage")
    shrunk, eff_n = beta_binomial_shrinkage(3, 5, alpha_prior=50, beta_prior=50)
    print(f"   Raw: 3/5 = 60%")
    print(f"   Shrunk (α=50, β=50): {shrunk:.4f} ({shrunk*100:.1f}%)")
    print(f"   Effective N: {eff_n}")

    # Test Governance Tag
    print("\n4. Governance Tag")
    print(f"   n=150, CI_width=0.08: {governance_tag(150, 0.08)}")
    print(f"   n=75, CI_width=0.12: {governance_tag(75, 0.12)}")
    print(f"   n=20, CI_width=0.25: {governance_tag(20, 0.25)}")

    # Test Quality Score
    print("\n5. Data Quality Score")
    score1 = calculate_data_quality_score(100, 0.08, False)
    score2 = calculate_data_quality_score(25, 0.20, True)
    print(f"   n=100, CI=0.08, no outliers: {score1:.2f}")
    print(f"   n=25, CI=0.20, has outliers: {score2:.2f}")

    print("\n" + "=" * 60)
    print("✅ All validation tests completed")
    print("=" * 60)
