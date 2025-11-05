# QuantRift Quantitative Analysis System

## Table of Contents
1. [Data Pipeline Architecture](#data-pipeline-architecture)
2. [20 Quantitative Metrics](#20-quantitative-metrics)
3. [Combat Power System](#combat-power-system)
4. [Statistical Framework](#statistical-framework)
5. [Data Governance](#data-governance)
6. [Player-Pack Format](#player-pack-format)

---

## Data Pipeline Architecture

### Medallion Architecture: Bronze → Silver → Gold

QuantRift processes **107,570+ match records** through a three-layer data pipeline designed for scalability and data quality.

```
Raw Riot API Data
       ↓
┌──────────────┐
│ Bronze Layer │  Raw JSON storage by rank tier
│  (6.7 GB)    │  • Immutable source of truth
└──────┬───────┘  • Quality validation
       ↓
┌──────────────┐
│ Silver Layer │  SCD2 dimension tables
│  (362 MB)    │  • Version control by patch
└──────┬───────┘  • Player statistics normalization
       ↓
┌──────────────┐
│  Gold Layer  │  Aggregated metrics
│  (354 MB)    │  • 20 quantitative metrics
└──────┬───────┘  • Wilson CI + governance
       ↓
Player-Pack Format
       ↓
18 AI Agents
```

---

### Bronze Layer: Raw Data

**Location**: `data/bronze/matches/`

**Structure**:
```
bronze/
├── diamond/
│   ├── {match_id}.json          # Raw Riot API match data
│   ├── {match_id}_timeline.json # Frame-by-frame timeline
│   └── ...
├── platinum/
├── gold/
├── silver/
└── bronze/
```

**Data Format**:
```json
{
  "bronze_metadata": {
    "tier": "DIAMOND",
    "quality_flag": "PASS",      // Quality validation result
    "governance_tag": "CONFIDENT"
  },
  "raw_data": {
    "metadata": {
      "matchId": "NA1_5391486684",
      "participants": ["...", "..."]
    },
    "info": {
      "gameCreation": 1703001000000,
      "gameDuration": 1842,
      "gameVersion": "13.24.1.4723",
      "participants": [
        {
          "puuid": "...",
          "championId": 103,
          "kills": 8,
          "deaths": 3,
          "assists": 12,
          "goldEarned": 15420,
          "totalDamageDealt": 185000,
          "item0": 3157,
          "item1": 3020,
          ...
        }
      ]
    }
  }
}
```

**Key Fields**:
- `gameCreation`: Millisecond timestamp → Patch version mapping
- `participants[]`: 10 players with full stats (KDA, items, runes)
- `frames[]`: Timeline data (1 frame/second) for combat power analysis

---

### Silver Layer: SCD2 Dimensions

**Location**: `data/silver/dimensions/`

**Transformation** (`bronze_to_silver_scd2.py`):

1. **Extract** → Pull Bronze data + anonymize PUUIDs
2. **Aggregate** → Accumulate stats by player + patch
3. **SCD2 Apply** → Version control with effective dates
4. **Partition** → Save by patch (14.1, 14.2, etc.)

**SCD2 Dimension Table Schema**:
```python
DimVersionedPlayerStats:
  # SCD2 Fields
  - player_key: str           # Business key (anonymized PUUID)
  - stats_sk: str             # Surrogate key (MD5 hash)
  - patch_version: str        # "14.1", "14.2"
  - effective_date: str       # Version start date
  - expiry_date: str | None   # Version end date (NULL if current)
  - is_current: bool          # Is this the latest version?
  - version_number: int       # Sequential version (1, 2, 3...)

  # Cumulative Statistics
  - total_kills: int
  - total_deaths: int
  - total_assists: int
  - total_gold_earned: int
  - total_damage_dealt: int
  - total_damage_taken: int
  - total_healing_done: int
  - total_vision_score: int
  - total_cs: int

  # Normalized Averages
  - avg_kda_ratio: float
  - avg_damage_per_minute: float
  - avg_gold_per_minute: float
  - avg_cs_per_minute: float

  # Position Distribution
  - top_games: int
  - jungle_games: int
  - mid_games: int
  - adc_games: int
  - support_games: int
  - most_played_position: str

  # Champion Pool
  - unique_champions_played: int
  - most_played_champion: str
  - most_played_champion_games: int

  # Governance
  - data_quality_score: float [0-1]
  - governance_tags: JSON array
```

**SCD2 Version Control**:
```python
# Patches sorted chronologically
sorted_patches = ["14.1", "14.2", "14.3"]

for i, patch in enumerate(sorted_patches):
    record.version_number = i + 1
    record.is_current = (i == len(sorted_patches) - 1)
    record.effective_date = get_patch_release_date(patch)

    if i < len(sorted_patches) - 1:
        # Set expiry date to next patch release
        next_patch_date = get_patch_release_date(sorted_patches[i+1])
        record.expiry_date = next_patch_date
    else:
        # Current version never expires
        record.expiry_date = None
```

---

### Gold Layer: Quantitative Metrics

**Location**: `data/gold/production/`

**Transformation** (`silver_to_gold_metrics.py` → `data_aggregator.py`):

1. **Aggregation Strategy** → 4-tier progressive aggregation ensuring n≥100
2. **Wilson CI** → 95% confidence intervals for win rates
3. **Beta-Binomial Prior** → Bayesian shrinkage using historical data
4. **Governance Tagging** → CONFIDENT/CAUTION/CONTEXT based on sample size

**4-Tier Aggregation Strategy**:

```python
def aggregate_with_fallback(
    champion_id: int,
    role: str,
    rank_tier: str,
    patch: str
) -> dict:
    """
    Progressive aggregation to ensure n≥100 for statistical validity
    """

    # Tier 1: Exact match (champion + role + tier + patch)
    stats = query(champion_id, role, rank_tier, patch)
    if stats.n >= 100:
        return add_governance_tag(stats, "CONFIDENT")

    # Tier 2: Widen to all ranks (champion + role + patch)
    stats = query(champion_id, role, ALL_TIERS, patch)
    if stats.n >= 100:
        return add_governance_tag(stats, "CONFIDENT")

    # Tier 3: Include recent patches (champion + role + last_3_patches)
    stats = query(champion_id, role, ALL_TIERS, last_3_patches)
    if stats.n >= 100:
        return add_governance_tag(stats, "CAUTION")

    # Tier 4: Global baseline (champion + role + all_data)
    stats = query(champion_id, role, ALL_TIERS, ALL_PATCHES)
    return add_governance_tag(stats, "CONTEXT")
```

**Benefit**: Guarantees statistically significant samples while preserving specificity when possible.

---

## 20 Quantitative Metrics

### 1-5: Behavioral Metrics

**1. Pick Rate**
- **Definition**: Frequency a champion is selected
- **Formula**: `pick_rate = champion_games / total_games`
- **Use Case**: Meta popularity indicator

**2. Attach Rate**
- **Definition**: Frequency of teammate pairings
- **Formula**: `attach_rate = duo_games / total_games`
- **Use Case**: Synergy detection, premade identification

**3. Rune Diversity**
- **Definition**: Variety in rune selections
- **Formula**: `rune_diversity = unique_rune_pages / total_games`
- **Use Case**: Adaptability vs one-trick assessment

**4. Synergy Score**
- **Definition**: Team composition effectiveness
- **Formula**: `synergy = Σ(champion_pair_winrate - expected_winrate)`
- **Use Case**: Draft optimization

**5. Counter Matchup Matrix**
- **Definition**: Head-to-head win rates
- **Formula**: `counter_score = (your_wr_vs_opponent) - 0.5`
- **Use Case**: Champion pool expansion guidance

---

### 6-10: Win Rate Metrics (Wilson CI)

**6. Baseline Win Rate**
- **Formula**: Wilson score confidence interval (Brown, Cai & DasGupta 2001)
  ```python
  def wilson_ci(wins: int, games: int, confidence=0.95) -> tuple:
      """
      Calculate Wilson confidence interval for win rate

      Superior to normal approximation for small samples:
      - Asymptotically symmetric
      - Automatic boundary constraints [0, 1]
      - Accurate for n<30
      """
      z = 1.96  # 95% confidence
      p_hat = wins / games

      denominator = 1 + z**2 / games
      center = (p_hat + z**2 / (2*games)) / denominator
      margin = z * sqrt(p_hat*(1-p_hat)/games + z**2/(4*games**2)) / denominator

      return (
          max(0, center - margin),  # ci_lo
          center,                    # winrate
          min(1, center + margin)    # ci_hi
      )
  ```

**7. CI_lo (Lower Bound)**
- 95% confidence interval lower bound
- Conservative win rate estimate

**8. CI_hi (Upper Bound)**
- 95% confidence interval upper bound
- Optimistic win rate estimate

**9. Effective_n (Beta-Binomial Prior)**
- **Purpose**: Combat small sample bias
- **Method**: Add prior "pseudo-games" based on global win rate
  ```python
  def effective_sample_size(
      wins: int,
      games: int,
      prior_alpha: float = 50,  # Prior wins
      prior_beta: float = 50    # Prior losses
  ) -> tuple:
      """
      Beta-Binomial conjugate prior for Bayesian shrinkage
      """
      effective_n = games + prior_alpha + prior_beta
      adjusted_wr = (wins + prior_alpha) / effective_n
      return effective_n, adjusted_wr
  ```

**10. Governance Tag**
- **CONFIDENT**: n≥100, patch-specific, rank-specific
- **CAUTION**: n≥100, cross-rank or multi-patch
- **CONTEXT**: n<100, global fallback data

---

### 11-13: Objective Metrics

**11. Objective Rate (obj_rate)**
- **Definition**: Objective damage per unit time
- **Formula**:
  ```python
  obj_rate = (
      baron_damage +
      dragon_damage +
      tower_damage +
      inhibitor_damage
  ) / (game_duration_seconds / 60)
  ```
- **Units**: Damage per minute
- **Benchmark**: >2000 for carries, >1500 for supports

**12. Baron Control Rate**
- **Definition**: Baron participation percentage
- **Formula**: `baron_rate = (baron_kills + baron_assists) / team_baron_kills`
- **Threshold**: >0.6 for jungle, >0.4 for carries

**13. Dragon Control Rate**
- **Definition**: Dragon participation percentage
- **Formula**: `dragon_rate = (dragon_kills + dragon_assists) / team_dragon_kills`
- **Threshold**: >0.5 for jungle, >0.3 for carries

---

### 14-16: Gold Efficiency Metrics

**14. Item Gold Efficiency**
- **Definition**: Gold value of item stats / item cost
- **Calculation**:
  ```python
  def calculate_item_efficiency(item_id: int) -> float:
      """
      Uses Data Dragon to map item stats to gold values

      Base gold values (from long sword, ruby crystal, etc.):
      - 1 AD = 35 gold
      - 1 AP = 21.75 gold
      - 1 HP = 2.67 gold
      - 1 Armor = 20 gold
      - 1 MR = 18 gold
      """
      item_stats = ddragon.get_item(item_id).stats
      stat_gold_value = sum([
          item_stats.ad * 35,
          item_stats.ap * 21.75,
          item_stats.hp * 2.67,
          item_stats.armor * 20,
          item_stats.mr * 18,
          # ... other stats
      ])

      item_cost = ddragon.get_item(item_id).gold.total
      return stat_gold_value / item_cost
  ```
- **Typical Range**: 0.9-1.3 (>1.0 means cost-efficient)

**15. Gold Per Minute (GPM)**
- **Formula**: `gpm = total_gold_earned / (game_duration_seconds / 60)`
- **Benchmarks**:
  - ADC/Mid: 350-450
  - Top/Jungle: 300-400
  - Support: 200-300

**16. CS Efficiency**
- **Definition**: Gold from CS / Total gold
- **Formula**: `cs_efficiency = (cs * 20) / total_gold_earned`
- **Typical**: 0.4-0.6 for laners, 0.2-0.3 for supports

---

### 17-20: Combat Metrics

**17. Combat Power (cp_t)**

**Core Formula**:
```python
CP = (
    1.0 * damage_component +
    0.6 * survivability_component +
    0.4 * crowd_control_component +
    0.2 * mobility_component
)
```

**Component Breakdown**:

1. **Damage Component**:
   ```python
   damage = (
       total_ad * (1 + armor_pen/100) +
       total_ap * (1 + magic_pen/100) +
       attack_speed * 100 +
       crit_chance * 50
   )
   ```

2. **Survivability Component**:
   ```python
   survivability = (
       total_hp +
       armor * 10 +
       mr * 10 +
       omnivamp * 500 +
       shield_power * 200
   )
   ```

3. **Crowd Control Component**:
   ```python
   cc = (
       ability_haste * 20 +
       total_mana +
       mana_regen * 100
   )
   ```

4. **Mobility Component**:
   ```python
   mobility = movement_speed * 5
   ```

**Analysis Levels**:
- **Level 15 (Early)**: ~8000-10000 CP
- **Level 25 (Mid)**: ~12000-16000 CP
- **Level 35 (Late)**: ~18000-25000 CP

**Governance**:
- **CONFIDENT**: Item coverage ≥80%, level ≥15
- **CAUTION**: Item coverage ≥50%, level ≥10
- **CONTEXT**: Below thresholds

**18. Delta Combat Power**
- **Definition**: Power differential between builds
- **Formula**: `delta_cp = cp_actual - cp_baseline`
- **Use**: Build optimization, item order analysis

**19. Damage Efficiency**
- **Definition**: Damage output relative to gold spent
- **Formula**: `damage_efficiency = total_damage_dealt / total_gold_earned`
- **Benchmark**: >10 for carries, >7 for supports

**20. Time to Core Items**
- **Definition**: Game time when core build completes
- **Measurement**: Timestamp of 2-3 item completion
- **Benchmarks**:
  - ADC 2-item: 18-22 minutes
  - Mid 2-item: 16-20 minutes
  - Support 2-item: 22-28 minutes

---

## Combat Power System

### Architecture

**Service**: `/backend/src/combatpower/` (Flask, port 5000)

**Core Functions**:
1. Build power calculation
2. Item stat aggregation
3. Champion base stat lookup
4. DPS/survivability modeling

### Implementation

**File**: `backend/src/combatpower/champion_power.py`

```python
class CombatPowerCalculator:
    def __init__(self):
        self.ddragon = DataDragonLoader()
        self.item_stats = self._load_item_stats()
        self.champion_stats = self._load_champion_stats()

    def calculate_power(
        self,
        champion_id: int,
        items: List[int],
        level: int,
        runes: dict
    ) -> dict:
        """
        Calculate comprehensive combat power

        Returns:
        {
            "total_cp": 15420.5,
            "damage": 8200.0,
            "survivability": 4800.0,
            "cc": 1800.0,
            "mobility": 620.5,
            "governance": "CONFIDENT",
            "breakdown": {...}
        }
        """
        # 1. Get champion base stats at level
        base = self.champion_stats.get_stats_at_level(champion_id, level)

        # 2. Aggregate item stats
        item_stats = self._sum_item_stats(items)

        # 3. Apply rune bonuses
        rune_stats = self._calculate_rune_stats(runes)

        # 4. Total stats
        total_stats = base + item_stats + rune_stats

        # 5. Calculate components
        damage = self._calc_damage_component(total_stats)
        survivability = self._calc_survivability_component(total_stats)
        cc = self._calc_cc_component(total_stats)
        mobility = self._calc_mobility_component(total_stats)

        # 6. Weighted sum
        cp = (
            1.0 * damage +
            0.6 * survivability +
            0.4 * cc +
            0.2 * mobility
        )

        # 7. Governance
        governance = self._assign_governance(
            item_coverage=len(items)/6,
            level=level
        )

        return {
            "total_cp": cp,
            "damage": damage,
            "survivability": survivability,
            "cc": cc,
            "mobility": mobility,
            "governance": governance,
            "breakdown": total_stats
        }
```

### Data Dragon Integration

**Champion Data**:
```python
champion_stats = ddragon.get_champion(103)  # Ahri
# Returns:
{
    "stats": {
        "hp": 526,
        "hp_per_level": 92,
        "mp": 418,
        "mp_per_level": 25,
        "movespeed": 330,
        "armor": 21,
        "attackdamage": 53,
        "attackrange": 550,
        ...
    }
}

# Level scaling:
hp_at_level_15 = base_hp + (hp_per_level * (level - 1))
```

**Item Data**:
```python
item = ddragon.get_item(3157)  # Zhonya's Hourglass
# Returns:
{
    "gold": {"total": 3000},
    "stats": {
        "ability_power": 120,
        "armor": 45,
        "ability_haste": 15
    },
    "passive": "Stasis: Become invulnerable for 2.5s"
}
```

---

## Statistical Framework

### Wilson Confidence Intervals

**Why Wilson > Normal Approximation?**

| Method | Small Sample (n<30) | Boundary Handling | Asymptotic Properties |
|--------|---------------------|-------------------|----------------------|
| Normal | ❌ Inaccurate | ❌ Can exceed [0,1] | ✅ Good |
| Wilson | ✅ Accurate | ✅ Constrained [0,1] | ✅ Excellent |

**Reference**: Brown, Cai & DasGupta (2001) - "Interval Estimation for a Binomial Proportion"

**Implementation**:
```python
def wilson_score_interval(
    successes: int,
    trials: int,
    confidence: float = 0.95
) -> tuple[float, float, float]:
    """
    Calculate Wilson score confidence interval

    Args:
        successes: Number of wins
        trials: Total games
        confidence: Confidence level (default 95%)

    Returns:
        (lower_bound, point_estimate, upper_bound)
    """
    if trials == 0:
        return (0.0, 0.0, 0.0)

    z = stats.norm.ppf((1 + confidence) / 2)
    p_hat = successes / trials

    denominator = 1 + z**2 / trials

    center = (p_hat + z**2 / (2 * trials)) / denominator

    margin = z * sqrt(
        p_hat * (1 - p_hat) / trials + z**2 / (4 * trials**2)
    ) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return (lower, center, upper)
```

**Example**:
```python
# 15 wins in 25 games
ci_lo, wr, ci_hi = wilson_score_interval(15, 25)
# Returns: (0.416, 0.600, 0.756)
# Interpretation: "True win rate is 60%, likely between 42-76%"
```

### Beta-Binomial Shrinkage

**Problem**: Small samples have high variance
**Solution**: Bayesian shrinkage using historical prior

**Method**:
```python
def bayesian_winrate(
    wins: int,
    games: int,
    prior_alpha: float = 50.0,  # Historical wins
    prior_beta: float = 50.0    # Historical losses
) -> tuple[float, float]:
    """
    Apply Beta-Binomial conjugate prior

    Effect: Shrinks extreme win rates toward 50% for small samples
    """
    posterior_alpha = wins + prior_alpha
    posterior_beta = (games - wins) + prior_beta

    shrunk_wr = posterior_alpha / (posterior_alpha + posterior_beta)
    effective_n = games + prior_alpha + prior_beta

    return shrunk_wr, effective_n
```

**Example**:
```python
# 8 wins in 10 games (80% raw win rate)
shrunk_wr, eff_n = bayesian_winrate(8, 10)
# Returns: (0.580, 110)
# Interpretation: "Adjusted to 58% after accounting for prior knowledge"
```

---

## Data Governance

### Three-Tier System

**CONFIDENT** (Green):
- Sample size n≥100
- Patch-specific data
- Rank-tier specific
- **Statistical Power**: >90%
- **Use**: Primary analysis, confident recommendations

**CAUTION** (Yellow):
- Sample size n≥100
- Cross-rank or multi-patch aggregation
- **Statistical Power**: 70-90%
- **Use**: Secondary analysis, with caveats

**CONTEXT** (Orange):
- Sample size n<100
- Global fallback data
- **Statistical Power**: <70%
- **Use**: Reference only, not for recommendations

### Quality Validation

**File**: `backend/src/core/data_aggregator.py`

```python
def assign_governance_tag(
    sample_size: int,
    is_patch_specific: bool,
    is_rank_specific: bool,
    aggregation_tier: int
) -> str:
    """
    Assign data governance tag based on quality criteria
    """
    if sample_size >= 100:
        if aggregation_tier == 1:  # Exact match
            return "CONFIDENT"
        elif aggregation_tier <= 2:  # Minor generalization
            return "CONFIDENT"
        else:  # Broader aggregation
            return "CAUTION"
    else:
        return "CONTEXT"
```

---

## Player-Pack Format

### Structure

Player-Pack is the unified data format consumed by all 18 AI agents.

**Location**: `data/player_packs/{puuid}/`

**Files**:
```
{puuid}/
├── summary.json          # Cross-patch aggregate
├── pack_15.17.json       # Patch-specific pack
├── pack_15.18.json
├── pack_15.19.json
└── timelines/
    ├── NA1_5391486684_timeline.json
    └── ...
```

### Pack Schema

```json
{
  "metadata": {
    "puuid": "OkHv4J5JcbqQSx9I5Fda7L9rpz4wQcaDVpgDyjtlhEcpdZIM9ExEyrfTpjS6EdsYcZjKX9i5ctKC9A",
    "patch": "15.19",
    "generated_at": "2025-01-15T10:30:00Z",
    "match_count": 20,
    "rank": {"tier": "DIAMOND", "division": "II", "lp": 87}
  },

  "by_champion_role": {
    "Ahri_MID": {
      "games": 15,
      "wins": 9,
      "winrate": 0.60,
      "ci_lo": 0.38,
      "ci_hi": 0.78,

      "kda": 2.8,
      "kda_adj": 3.1,
      "avg_kills": 7.2,
      "avg_deaths": 3.5,
      "avg_assists": 10.1,

      "combat_power": 13200,
      "damage_taken": 18500,
      "obj_rate": 0.45,

      "cs_per_min": 7.2,
      "gold_per_min": 385,
      "vision_score_per_min": 1.3,

      "governance": "CONFIDENT"
    },

    "Syndra_MID": {
      "games": 5,
      "wins": 3,
      "winrate": 0.60,
      "ci_lo": 0.23,
      "ci_hi": 0.88,

      "kda": 3.5,
      "kda_adj": 3.2,

      "combat_power": 14100,
      "damage_taken": 16200,
      "obj_rate": 0.52,

      "governance": "CONTEXT"  // n<10
    }
  },

  "overall_stats": {
    "total_games": 20,
    "total_wins": 12,
    "overall_winrate": 0.60,
    "main_champion": "Ahri",
    "main_role": "MID",
    "avg_combat_power_per_game": 13500,
    "avg_kda": 2.9
  },

  "progression": {
    "early_season": {
      "games": 8,
      "winrate": 0.50,
      "avg_cp": 12800
    },
    "mid_season": {
      "games": 7,
      "winrate": 0.57,
      "avg_cp": 13500
    },
    "late_season": {
      "games": 5,
      "winrate": 0.80,
      "avg_cp": 14200
    }
  },

  "insights": [
    {
      "type": "strength",
      "category": "combat",
      "message": "Combat power consistently above diamond average (+8%)",
      "severity": "high"
    },
    {
      "type": "weakness",
      "category": "vision",
      "message": "Vision score below expected for rank (-15%)",
      "severity": "medium"
    }
  ]
}
```

### Generation Process

**File**: `backend/services/player_data_manager.py`

```python
async def generate_player_pack(
    puuid: str,
    matches: List[dict],
    timelines: List[dict]
) -> dict:
    """
    Generate Player-Pack from raw match data

    Steps:
    1. Group matches by champion + role
    2. Calculate 20 metrics for each group
    3. Apply Wilson CI + governance
    4. Detect insights (zero-LLM)
    5. Structure into pack format
    """

    pack = {
        "metadata": {...},
        "by_champion_role": {},
        "overall_stats": {},
        "progression": {},
        "insights": []
    }

    # Group by champion_role
    grouped = group_matches_by_champion_role(matches, puuid)

    for key, group_matches in grouped.items():
        champion, role = key.split("_")

        # Calculate metrics
        metrics = calculate_all_metrics(group_matches, timelines, puuid)

        # Apply Wilson CI
        ci_lo, wr, ci_hi = wilson_score_interval(
            metrics["wins"],
            metrics["games"]
        )

        # Governance
        governance = assign_governance_tag(
            metrics["games"],
            is_patch_specific=True,
            is_rank_specific=True,
            aggregation_tier=1
        )

        pack["by_champion_role"][key] = {
            **metrics,
            "winrate": wr,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "governance": governance
        }

    # Overall stats
    pack["overall_stats"] = aggregate_overall(pack["by_champion_role"])

    # Progression analysis
    pack["progression"] = analyze_progression(matches)

    # Zero-LLM insights
    pack["insights"] = detect_insights(pack)

    return pack
```

---

## Summary

QuantRift's quantitative analysis system delivers:

✅ **Scalable Data Pipeline**: Bronze → Silver → Gold medallion architecture processing 107K+ matches
✅ **20 Rigorous Metrics**: Behavioral, win rate, objective, gold, and combat metrics
✅ **Statistical Rigor**: Wilson CI for win rates, Beta-Binomial shrinkage, 3-tier governance
✅ **Combat Power System**: Multi-component power index with item/champion/level integration
✅ **Production-Ready**: Player-Pack format optimized for AI agent consumption
✅ **Data Quality**: Governance tags ensure appropriate use of statistical inferences

**Key Innovations**:
- **4-tier aggregation** ensures n≥100 while preserving specificity
- **Wilson CI** provides accurate confidence intervals for all sample sizes
- **Combat Power** unifies champion strength into single interpretable metric
- **Zero-LLM insights** reduce AI costs via pattern-based detection

**Statistical Foundation**: All metrics grounded in peer-reviewed statistical methods, ensuring production-grade data quality for AI-powered analysis.
