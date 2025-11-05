# Agent Tools Deduplication Analysis

## 🔍 Analysis Summary

**Analysis Date**: 2025-10-10
**Scope**: All agent tools and statistical utilities
**Goal**: Identify duplicate functionality and design consolidation plan

---

## 📊 Duplicate Functions Found

### 1. wilson_confidence_interval - **4 Implementations** ❌

#### Implementation A - **CANONICAL** ✅
**File**: `src/metrics/utils/evidence_metadata.py:66-84`
**Type**: Class method inside `EvidenceStandardizer`
**Signature**: `wilson_confidence_interval(self, successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float, float]`
**Returns**: `(proportion, ci_lower, ci_upper)` - 3 values
**Features**:
- Uses scipy.stats.norm.ppf for z-score calculation
- Full Wilson formula: `center = (p + z²/(2n)) / (1 + z²/n)`
- Proper margin calculation with Wilson adjustment
- **Most accurate implementation**

**Usage**:
```python
from src.metrics.utils.evidence_metadata import EvidenceStandardizer
standardizer = EvidenceStandardizer()
p, ci_lo, ci_hi = standardizer.wilson_confidence_interval(wins, games)
```

---

#### Implementation B - SIMPLIFIED (Normal Approximation) ⚠️
**File**: `src/metrics/quantitative/rune_value.py:23-36`
**Type**: Standalone function
**Signature**: `wilson_confidence_interval(successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float]`
**Returns**: `(lower, upper)` - 2 values
**Features**:
- Hardcoded z=1.96 (ignores alpha parameter)
- **Uses normal approximation**: `margin = z * sqrt(p*(1-p)/n)`
- **This is NOT true Wilson CI** - missing Wilson adjustment denominator
- Less accurate for small samples

**Problem**: Misleading name - should be called `normal_approximation_ci`

---

#### Implementation C - **EXACT DUPLICATE** of B ❌
**File**: `src/metrics/quantitative/damage_efficiency.py:23-36`
**Type**: Standalone function
**Identical to**: `rune_value.py` implementation
**Status**: **MUST BE REMOVED**

---

#### Implementation D - Proper Wilson (test_agents)
**File**: `test_agents/player_coach/player_pack_generator.py:22-50`
**Type**: Standalone function
**Signature**: `wilson_confidence_interval(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]`
**Returns**: `(lower, upper)` - 2 values
**Features**:
- Conditional z-score: 1.96 (95%) or 1.645 (90%)
- Full Wilson formula matching Implementation A
- Proper center and margin calculation
- **Accurate implementation, but duplicates Implementation A**

---

### 2. winsorize - **1 Implementation Found** ⚠️

**File**: `test_agents/player_coach/player_pack_generator.py:53-71`
**Type**: Standalone function
**Status**: **No equivalent in src/**
**Signature**: `winsorize(values: List[float], lower_percentile: float = 0.05, upper_percentile: float = 0.95) -> List[float]`
**Functionality**:
- Caps values at specified percentiles
- Uses numpy.percentile and numpy.clip
- Essential for outlier handling in statistical analysis

**Recommendation**: Move to `src/core/statistical_utils.py` or `src/metrics/utils/outlier_handling.py`

---

### 3. analyze_trends - **2 Implementations** (Expected)

#### Implementation A - Agent Tool
**File**: `src/agents/player_analysis/multi_version/tools.py:33`
**Purpose**: MultiVersionAgent tool function
**Status**: Extracted from original implementation (expected, not a duplicate)

#### Implementation B - Original
**File**: `test_agents/player_coach/multi_version_analyzer.py:53`
**Purpose**: Original analyzer class method
**Status**: Original implementation, wrapped by agent

**Relationship**: Implementation A was extracted from B for agent integration. This is expected architectural pattern.

---

### 4. identify_key_transitions - **2 Implementations** (Expected)

#### Implementation A - Agent Tool
**File**: `src/agents/player_analysis/multi_version/tools.py:117`
**Purpose**: MultiVersionAgent tool function
**Status**: Extracted from original implementation (expected, not a duplicate)

#### Implementation B - Original
**File**: `test_agents/player_coach/multi_version_analyzer.py:131`
**Purpose**: Original analyzer class method
**Status**: Original implementation, wrapped by agent

**Relationship**: Same as analyze_trends - expected pattern.

---

### 5. load_all_packs - **Multiple Implementations** (Expected)

**Files**:
- `src/agents/player_analysis/multi_version/tools.py:11` (agent tool)
- `test_agents/player_coach/multi_version_analyzer.py:40` (original class method)
- `test_agents/player_coach/coach_card_generator.py:62` (variant: load_all_data)

**Status**: Expected pattern - agent tools extracted from originals

---

## 🎯 Consolidation Plan

### Phase 1: Create Central Statistical Utilities Module

**Create**: `src/core/statistical_utils.py`

```python
#!/usr/bin/env python3
"""
Central Statistical Utilities
Canonical implementations of statistical functions used across the codebase
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

    This is the CANONICAL implementation used across the codebase.
    DO NOT create duplicate implementations.

    Args:
        successes: Number of successes
        trials: Total trials
        alpha: Significance level (default 0.05 for 95% CI)

    Returns:
        (proportion, ci_lower, ci_upper)

    References:
        - Wilson, E.B. (1927). "Probable Inference, the Law of Succession,
          and Statistical Inference". Journal of the American Statistical Association.
        - Brown, Cai & DasGupta (2001). "Interval Estimation for a Binomial Proportion"
    """
    if trials == 0:
        return 0.0, 0.0, 0.0

    z = stats.norm.ppf(1 - alpha/2)
    p = successes / trials

    center = (p + z**2 / (2 * trials)) / (1 + z**2 / trials)
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / (1 + z**2 / trials)

    ci_lower = max(0, center - margin)
    ci_upper = min(1, center + margin)

    return p, ci_lower, ci_upper


def winsorize(
    values: List[float],
    lower_percentile: float = 0.05,
    upper_percentile: float = 0.95
) -> List[float]:
    """
    Winsorize values by capping at percentiles

    This is the CANONICAL implementation for outlier handling.

    Args:
        values: List of values to winsorize
        lower_percentile: Lower bound percentile (default 5%)
        upper_percentile: Upper bound percentile (default 95%)

    Returns:
        Winsorized values (capped at percentiles)

    References:
        - Winsor, C.P. (1946). "The Mean Difference and Mean Deviation
          of Some Discontinuous Distributions"
    """
    if not values:
        return []

    lower_bound = np.percentile(values, lower_percentile * 100)
    upper_bound = np.percentile(values, upper_percentile * 100)

    return [np.clip(v, lower_bound, upper_bound) for v in values]


def beta_binomial_shrinkage(
    successes: int,
    trials: int,
    alpha_prior: float = 1.0,
    beta_prior: float = 1.0
) -> Tuple[float, int]:
    """
    Beta-Binomial shrinkage estimator for small sample sizes

    Args:
        successes: Number of successes
        trials: Total trials
        alpha_prior: Beta distribution alpha parameter (default 1.0 = uniform prior)
        beta_prior: Beta distribution beta parameter (default 1.0 = uniform prior)

    Returns:
        (shrunk_proportion, effective_sample_size)

    References:
        - Empirical Bayes methods
        - Stein's paradox
    """
    effective_successes = successes + alpha_prior
    effective_trials = trials + alpha_prior + beta_prior

    shrunk_proportion = effective_successes / effective_trials
    effective_n = effective_trials

    return shrunk_proportion, int(effective_n)
```

---

### Phase 2: Remove Duplicates and Update Imports

#### Step 2.1: Update `rune_value.py`

**File**: `src/metrics/quantitative/rune_value.py`

**Remove**: Lines 23-36 (duplicate wilson_confidence_interval)

**Add**:
```python
from src.core.statistical_utils import wilson_confidence_interval
```

**Update usage**: Line 96 and 134
```python
# Before:
confidence = wilson_confidence_interval(80, 100)

# After (adjust to handle 3-value return):
p, ci_lower, ci_upper = wilson_confidence_interval(80, 100)
confidence = (ci_lower, ci_upper)
```

---

#### Step 2.2: Update `damage_efficiency.py`

**File**: `src/metrics/quantitative/damage_efficiency.py`

**Remove**: Lines 23-36 (exact duplicate of rune_value.py)

**Add**:
```python
from src.core.statistical_utils import wilson_confidence_interval
```

**Update usage**: Lines 133 and 135
```python
# Before:
confidence = wilson_confidence_interval(85, 100)

# After:
p, ci_lower, ci_upper = wilson_confidence_interval(85, 100)
confidence = (ci_lower, ci_upper)
```

---

#### Step 2.3: Update `evidence_metadata.py`

**File**: `src/metrics/utils/evidence_metadata.py`

**Option A - Recommended**: Keep as-is, but add deprecation note to use `statistical_utils.py` for new code

**Option B**: Refactor to use central implementation
```python
from src.core.statistical_utils import wilson_confidence_interval as _wilson_ci

class EvidenceStandardizer:
    def wilson_confidence_interval(self, successes: int, trials: int, alpha: float = 0.05):
        """Wrapper for backward compatibility"""
        return _wilson_ci(successes, trials, alpha)
```

---

#### Step 2.4: Update `player_pack_generator.py`

**File**: `test_agents/player_coach/player_pack_generator.py`

**Remove**: Lines 22-50 (wilson_confidence_interval) and Lines 53-71 (winsorize)

**Add**:
```python
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.statistical_utils import wilson_confidence_interval, winsorize
```

**Update usage**: Line 236
```python
# Before:
ci_lower, ci_upper = wilson_confidence_interval(wins, games)

# After:
p, ci_lower, ci_upper = wilson_confidence_interval(wins, games)
# (p is already calculated, can ignore)
```

---

### Phase 3: Agent Tools Organization

**Current Status**: Agent tools are already properly organized

**Structure**:
```
src/agents/player_analysis/
├── multi_version/tools.py       # ✅ Properly located
├── detailed_analysis/agent.py   # ✅ Wraps original analyzer
├── version_comparison/agent.py  # ✅ Wraps original generator
└── postgame_review/
    ├── agent.py                 # ✅ Wrapper with LLM enhancement
    └── engine.py                # ✅ Rule-based logic
```

**Recommendation**: No changes needed - these are properly organized

---

## 📋 Implementation Checklist

### Critical (Must Do)

- [ ] **Create** `src/core/statistical_utils.py` with canonical implementations
- [ ] **Update** `src/metrics/quantitative/rune_value.py` to import wilson_ci
- [ ] **Update** `src/metrics/quantitative/damage_efficiency.py` to import wilson_ci
- [ ] **Update** `test_agents/player_coach/player_pack_generator.py` to import both functions
- [ ] **Test** all affected metrics to ensure no regressions
- [ ] **Verify** Wilson CI calculations produce identical results

### Recommended (Should Do)

- [ ] **Add** unit tests for `statistical_utils.py`
- [ ] **Document** canonical implementations with references
- [ ] **Add** deprecation warnings to duplicate implementations
- [ ] **Create** migration guide for developers

### Optional (Nice to Have)

- [ ] **Refactor** evidence_metadata.py to use central implementation
- [ ] **Add** performance benchmarks for statistical functions
- [ ] **Create** statistical utilities documentation page

---

## 🔬 Testing Strategy

### 1. Unit Tests for statistical_utils.py

```python
def test_wilson_ci_zero_trials():
    p, ci_lo, ci_hi = wilson_confidence_interval(0, 0)
    assert (p, ci_lo, ci_hi) == (0.0, 0.0, 0.0)

def test_wilson_ci_perfect_score():
    p, ci_lo, ci_hi = wilson_confidence_interval(100, 100)
    assert 0.9 < ci_lo < 1.0  # CI should not be [1.0, 1.0]

def test_wilson_ci_vs_old_implementation():
    # Verify new implementation matches evidence_metadata.py
    from src.metrics.utils.evidence_metadata import EvidenceStandardizer
    std = EvidenceStandardizer()

    p_new, ci_lo_new, ci_hi_new = wilson_confidence_interval(50, 100)
    p_old, ci_lo_old, ci_hi_old = std.wilson_confidence_interval(50, 100)

    assert abs(ci_lo_new - ci_lo_old) < 1e-10
    assert abs(ci_hi_new - ci_hi_old) < 1e-10

def test_winsorize_basic():
    values = [1, 2, 3, 4, 5, 100]  # 100 is outlier
    result = winsorize(values, 0.1, 0.9)
    assert max(result) < 100  # Outlier should be capped
```

### 2. Integration Tests

- Run full Gold layer metrics generation with new imports
- Compare outputs with baseline (should be identical)
- Check all agents still function correctly

### 3. Regression Prevention

- Add CI check to prevent new duplicate implementations
- Lint rule: "wilson_confidence_interval must be imported from statistical_utils"

---

## 📊 Impact Analysis

### Files Affected: 5

1. `src/core/statistical_utils.py` - **NEW**
2. `src/metrics/quantitative/rune_value.py` - **MODIFIED**
3. `src/metrics/quantitative/damage_efficiency.py` - **MODIFIED**
4. `test_agents/player_coach/player_pack_generator.py` - **MODIFIED**
5. `src/metrics/utils/evidence_metadata.py` - **OPTIONAL REFACTOR**

### Risk Level: LOW

- Changes are primarily import path updates
- Statistical calculations remain identical
- No API surface changes (internal refactoring only)
- Backward compatibility maintained

### Effort Estimate: 2-3 hours

- 1 hour: Create statistical_utils.py and tests
- 1 hour: Update imports and verify outputs
- 0.5 hour: Documentation and final validation

---

## 🎓 Developer Guidelines

### For New Statistical Functions

**DO**:
- Add to `src/core/statistical_utils.py`
- Include docstring with mathematical references
- Add unit tests with edge cases
- Document in this analysis file

**DON'T**:
- Create standalone statistical functions in individual metrics
- Duplicate implementations "because it's easier"
- Use normal approximation and call it "Wilson CI"

### For Agent Tools

**DO**:
- Keep tools in `src/agents/{suite}/{agent}/tools.py`
- Extract common utilities to `src/core/` or `src/metrics/utils/`
- Document tool dependencies and usage

**DON'T**:
- Duplicate statistical functions in agent tools
- Create agent-specific versions of core utilities

---

## 📚 References

- **Wilson CI**: Wilson, E.B. (1927). "Probable Inference, the Law of Succession, and Statistical Inference"
- **Wilson CI Modern**: Brown, Cai & DasGupta (2001). "Interval Estimation for a Binomial Proportion"
- **Winsorization**: Winsor, C.P. (1946). "The Mean Difference and Mean Deviation"
- **Beta-Binomial**: Empirical Bayes methods, Stein's paradox

---

**Analysis Complete**
**Next Step**: Review with user → Create `statistical_utils.py` → Update imports → Test
