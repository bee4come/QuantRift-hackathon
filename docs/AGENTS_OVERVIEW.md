# QuantRift AI Agent System Overview

## Introduction

QuantRift features **18 specialized AI agents** powered by AWS Bedrock (Claude 3.5 Haiku and Claude 4.5 Sonnet). Each agent analyzes different aspects of player performance using quantitative metrics and LLM-powered insights.

## Agent Categories

### Player Analysis Agents (11)
Focus on individual player performance, improvement tracking, and skill assessment.

### Meta Analysis Agents (3)
Analyze game meta, champion recommendations, and cross-patch performance.

### Coach Tools (4)
Provide tactical guidance for drafting, item builds, and post-game review.

---

## Player Analysis Agents

### 1. Weakness Analysis

**Endpoint**: `POST /v1/agents/weakness-analysis`

**Purpose**: Diagnose performance weaknesses across four dimensions: Laning, Teamfighting, Vision, and Macro play.

**Input Data**:
- Recent 5-20 matches
- Player-Pack metrics (KDA, CS, vision, objectives)
- Combat power trends
- Role-specific benchmarks

**Analysis Methodology**:
1. **Laning Phase Analysis**:
   - CS efficiency (target: >6.0 CS/min)
   - Gold differential at 10/15 minutes
   - Early game deaths (target: <1.5)
   - Trading effectiveness

2. **Teamfighting Analysis**:
   - Team damage participation (target: >25%)
   - Positioning (damage taken vs dealt ratio)
   - Ultimate usage timing
   - Objective fight participation

3. **Vision Analysis**:
   - Vision score per minute (target: >1.0)
   - Ward placement timing
   - Vision denial (control wards)

4. **Macro Play Analysis**:
   - Objective participation rate
   - Rotation timing
   - Map pressure indicators

**Output**:
```json
{
  "one_liner": "Early-game CSing is your primary weakness, losing 15 CS avg by 10min",
  "detailed": "...",
  "weaknesses": [
    {
      "category": "laning",
      "severity": "high",
      "metric": "cs_per_min",
      "your_value": 5.2,
      "benchmark": 6.5,
      "deficit_pct": -20.0
    }
  ],
  "recommendations": [...]
}
```

---

### 2. Champion Mastery

**Endpoint**: `POST /v1/agents/champion-mastery`

**Purpose**: Deep analysis of champion expertise, mechanics rating, and mastery progression.

**Input Data**:
- Champion-specific games (minimum 5)
- Combat power progression
- Build diversity
- Matchup performance

**Analysis Methodology**:
1. **Mechanics Rating** (0-100):
   - Combo execution (damage efficiency)
   - Skill shot accuracy (estimated from damage/kill efficiency)
   - Power spike utilization (CP growth curves)

2. **Matchup Knowledge**:
   - Win rate vs counters
   - Ban rate analysis
   - Opponent champion frequency

3. **Build Optimization**:
   - Item efficiency scores
   - Build path consistency
   - Adaptation to game state

**Output**:
```json
{
  "mastery_score": 72,
  "mechanics_rating": 68,
  "matchup_knowledge": 75,
  "build_optimization": 73,
  "progression": {
    "games_played": 45,
    "winrate_trend": "+12% over last 20 games",
    "skill_curve": "improving"
  }
}
```

---

### 3. Progress Tracker

**Endpoint**: `POST /v1/agents/progress-tracker`

**Purpose**: Long-term improvement tracking with statistical validation of skill growth.

**Input Data**:
- Historical match data (30+ games recommended)
- Tri-period segmentation (early/mid/late season)
- Metric deltas over time

**Analysis Methodology**:
1. **Trend Detection**:
   - Linear regression on key metrics
   - Statistical significance testing (p < 0.05)
   - Slope interpretation (positive/negative/flat)

2. **Milestone Identification**:
   - Rank promotions
   - Win rate inflection points
   - Metric breakout moments

3. **Forecast**:
   - Projected rank by season end
   - Improvement velocity

**Output**:
```json
{
  "trends": {
    "winrate": {"slope": +0.012, "p_value": 0.023, "direction": "improving"},
    "kda": {"slope": +0.08, "p_value": 0.041, "direction": "improving"},
    "cs_per_min": {"slope": -0.02, "p_value": 0.412, "direction": "stable"}
  },
  "forecast": {
    "target_rank": "DIAMOND I",
    "estimated_games_needed": 42,
    "confidence": 0.73
  }
}
```

---

### 4. Detailed Analysis

**Endpoint**: `POST /v1/agents/detailed-analysis`

**Purpose**: Comprehensive multi-dimensional performance review of recent games.

**Input Data**:
- Last 5 matches
- Per-game breakdowns (timeline data)
- Comparative metrics

**Analysis Methodology**:
- Game-by-game narrative analysis
- Pattern recognition across matches
- Highlight plays vs critical mistakes
- Comparative benchmarking vs rank average

**Output**: Detailed narrative report with game-specific insights and actionable feedback.

---

### 5. Peer Comparison

**Endpoint**: `POST /v1/agents/peer-comparison`

**Purpose**: Benchmark player performance against others of similar rank.

**Input Data**:
- Player metrics
- Rank tier (e.g., Diamond II)
- Regional data (NA1)
- OP.GG MCP leaderboard data

**Analysis Methodology**:
1. **Percentile Rankings**:
   - Calculate percentile for each metric vs rank tier
   - Identify strengths (>75th percentile)
   - Identify weaknesses (<25th percentile)

2. **Composite Score**:
   - Weighted average across metrics
   - Rank within tier estimation

**Output**:
```json
{
  "rank_percentile": 62.5,
  "metric_percentiles": {
    "combat_power": 71.2,
    "kda": 58.3,
    "vision_score": 44.1,
    "cs_per_min": 67.8
  },
  "strengths": ["combat_power", "cs_per_min"],
  "weaknesses": ["vision_score"]
}
```

---

### 6. Role Specialization

**Endpoint**: `POST /v1/agents/role-specialization`

**Purpose**: Analyze role-specific strengths, weaknesses, and position mastery.

**Input Data**:
- Games grouped by role (TOP/JG/MID/ADC/SUP)
- Role-specific benchmarks
- Position diversity

**Analysis Methodology**:
1. **Primary Role Analysis**:
   - Win rate by role
   - Games played distribution
   - Metric performance vs role benchmarks

2. **Secondary Role Assessment**:
   - Off-role performance
   - Champion pool overlap
   - Flexibility score

**Output**:
```json
{
  "primary_role": "MID",
  "role_performance": {
    "MID": {"games": 45, "winrate": 0.58, "mastery": "proficient"},
    "TOP": {"games": 8, "winrate": 0.50, "mastery": "competent"},
    "ADC": {"games": 2, "winrate": 0.50, "mastery": "learning"}
  },
  "flexibility_score": 6.2
}
```

---

### 7. Timeline Deep Dive

**Endpoint**: `POST /v1/agents/timeline-deep-dive`

**Purpose**: Minute-by-minute game analysis for pattern detection and power spike identification.

**Input Data**:
- Timeline data (frame-by-frame)
- Combat power progression
- Objective timing
- Gold/XP curves

**Analysis Methodology**:
1. **Power Spike Detection**:
   - Identify CP breakpoints (level 6, 11, 16)
   - Item completion timings
   - Relative power vs opponent

2. **Critical Moments**:
   - First blood timing
   - Death timestamps and context
   - Objective contests

3. **Macro Patterns**:
   - Lane swap timing
   - Recall patterns
   - Jungle proximity

**Output**: Interactive timeline with annotated key events and analysis commentary.

---

### 8. Annual Summary

**Endpoint**: `POST /v1/agents/annual-summary`

**Purpose**: Year-in-review analysis with tri-period progression tracking.

**Input Data**:
- Full season match history
- Segmented into Early/Mid/Late periods
- Aggregate statistics

**Analysis Methodology**:
1. **Tri-Period Analysis**:
   - Early season performance
   - Mid-season adjustments
   - Late-season trends

2. **Milestone Highlights**:
   - Peak rank achieved
   - Best win streak
   - Most improved metric

3. **Champion Highlights**:
   - Most played champion
   - Highest win rate champion (min 10 games)
   - Signature picks

**Output**:
```json
{
  "season_summary": {
    "total_games": 256,
    "winrate": 0.531,
    "peak_rank": "DIAMOND I",
    "most_played": "Ahri",
    "best_champion": "Syndra (65% WR, 20 games)"
  },
  "tri_period": {
    "early": {"games": 102, "winrate": 0.49},
    "mid": {"games": 89, "winrate": 0.54},
    "late": {"games": 65, "winrate": 0.58}
  },
  "narrative": "..."
}
```

---

### 9. Risk Forecaster

**Endpoint**: `POST /v1/agents/risk-forecaster`

**Purpose**: Predict performance volatility, tilt detection, and consistency analysis.

**Input Data**:
- Recent 20+ games
- Win/loss streaks
- Performance variance metrics

**Analysis Methodology**:
1. **Volatility Measurement**:
   - Standard deviation of KDA
   - Win rate variance
   - Hot/cold streak detection

2. **Tilt Indicators**:
   - Performance drop after losses
   - Death rate spike patterns
   - CS efficiency degradation

3. **Consistency Score**:
   - Game-to-game performance stability
   - Baseline vs peak performance gap

**Output**:
```json
{
  "risk_level": "moderate",
  "volatility_score": 0.42,
  "tilt_probability": 0.28,
  "consistency_rating": 6.8,
  "recommendations": [
    "Take breaks after 2 consecutive losses",
    "Focus on stabilizing CS efficiency (high variance detected)"
  ]
}
```

---

### 10. Friend Comparison

**Endpoint**: `POST /v1/agents/friend-comparison`

**Purpose**: Group performance comparison and team synergy analysis.

**Input Data**:
- Multiple player PUUIDs
- Shared games detection
- Individual metrics for each player

**Analysis Methodology**:
1. **Individual Rankings**:
   - Rank each player by key metrics
   - Identify group leader in each category

2. **Synergy Analysis**:
   - Win rate when playing together
   - Role compatibility
   - Complementary strengths

**Output**: Comparative dashboard with rankings and team synergy score.

---

### 11. Laning Phase Analyzer

**Endpoint**: `POST /v1/agents/laning-phase`

**Purpose**: Specialized early-game analysis (0-15 minutes).

**Input Data**:
- Early game CS (10min, 15min marks)
- Gold differential
- Jungle proximity events
- First blood participation

**Analysis Methodology**:
1. **CS Efficiency**:
   - CS @ 10min target: 80-90
   - CS differential vs opponent

2. **Trading Patterns**:
   - Damage dealt vs taken ratio
   - Health advantage maintenance

3. **Wave Management**:
   - Freeze/push timing (inferred from CS patterns)
   - Back timing optimization

**Output**: Early-game specific report with laning mechanics breakdown.

---

## Meta Analysis Agents

### 12. Champion Recommendation

**Endpoint**: `POST /v1/agents/champion-recommendation`

**Purpose**: Suggest champions based on player style, current meta, and win rate potential.

**Input Data**:
- Player champion pool history
- Current patch meta (OP.GG MCP)
- Role preference
- Rank tier

**Analysis Methodology**:
1. **Playstyle Matching**:
   - Aggressive vs passive style detection
   - Preferred champion archetypes
   - Mechanical complexity preference

2. **Meta Alignment**:
   - Current S/A tier champions
   - Synergy with player's mechanics
   - Ban rate considerations

3. **Win Rate Potential**:
   - Expected win rate based on similar players
   - Learning curve estimation

**Output**:
```json
{
  "recommendations": [
    {
      "champion": "Syndra",
      "match_score": 0.87,
      "reasoning": "Matches your aggressive playstyle, S-tier in current meta",
      "expected_winrate": 0.56,
      "learning_curve": "moderate"
    }
  ]
}
```

---

### 13. Multi-Version Analysis

**Endpoint**: `POST /v1/agents/multi-version`

**Purpose**: Cross-patch performance analysis and adaptation speed measurement.

**Input Data**:
- Match history across 3+ patches
- Patch-specific metrics
- Champion/item changes per patch

**Analysis Methodology**:
1. **Adaptation Speed**:
   - Win rate change velocity after patch
   - Time to return to baseline performance

2. **Patch Impact**:
   - Identify patches with significant performance shifts
   - Correlate with champion/item nerfs/buffs

**Output**: Multi-patch performance dashboard with adaptation insights.

---

### 14. Version Comparison

**Endpoint**: `POST /v1/agents/version-comparison`

**Purpose**: Detailed patch-to-patch delta analysis and meta shift impact.

**Input Data**:
- Performance in Patch A vs Patch B
- Champion win rate changes
- Item build adjustments

**Analysis Methodology**:
- Direct statistical comparison (two-sample t-test)
- Metric-by-metric delta calculation
- Meta shift correlation

**Output**: Side-by-side patch comparison report.

---

## Coach Tools

### 15. Build Simulator

**Endpoint**: `POST /v1/agents/build-simulator`

**Purpose**: Optimize item builds for specific matchups and game states.

**Input Data**:
- Champion selection
- Opponent champion
- Game state (ahead/behind/even)
- Current items

**Analysis Methodology**:
1. **Combat Power Simulation**:
   - Calculate CP for different build paths
   - Compare damage output vs survivability trade-offs

2. **Gold Efficiency**:
   - Identify cost-effective items for current state
   - Power spike timing optimization

3. **Matchup-Specific**:
   - Armor vs MR priority
   - Penetration vs raw damage

**Output**:
```json
{
  "recommended_build": ["Luden's", "Sorcs", "Shadowflame", "Rabadon's"],
  "power_curve": [...],
  "alternative_builds": {
    "defensive": ["Luden's", "Zhonya's", "Banshee's"],
    "scaling": ["Luden's", "Rabadon's", "Void Staff"]
  }
}
```

---

### 16. Drafting Coach

**Endpoint**: `POST /v1/agents/drafting-coach`

**Purpose**: Team composition recommendations and pick/ban strategy.

**Input Data**:
- Current draft state (picked/banned champions)
- Player champion pool
- Role to fill
- OP.GG meta tier list

**Analysis Methodology**:
1. **Synergy Calculation**:
   - Team composition score (engage, poke, split-push)
   - Role balance check

2. **Counter Pick Analysis**:
   - Identify opponent vulnerabilities
   - Avoid counter matchups

3. **Ban Priority**:
   - High ban rate champions
   - Personal counters
   - OP meta picks

**Output**: Prioritized champion suggestions with synergy scores.

---

### 17. Team Synergy

**Endpoint**: `POST /v1/agents/team-synergy`

**Purpose**: Analyze team composition effectiveness and role interactions.

**Input Data**:
- 5 champion team composition
- Role assignments
- OP.GG synergy matrix

**Analysis Methodology**:
1. **Composition Type**:
   - Poke, Engage, Protect-the-Carry, Split-push
   - Damage distribution (AP/AD ratio)

2. **Win Condition Clarity**:
   - Early/mid/late game strength
   - Primary win path identification

3. **Weaknesses**:
   - Lack of engage
   - No crowd control
   - All AD/AP vulnerable to armor/MR stacking

**Output**:
```json
{
  "synergy_score": 7.8,
  "composition_type": "Engage",
  "power_spike": "mid-game",
  "strengths": ["Strong teamfight", "Good engage"],
  "weaknesses": ["Weak late-game scaling"],
  "win_condition": "Force teamfights at objectives 15-25 min"
}
```

---

### 18. Post-game Review

**Endpoint**: `POST /v1/agents/postgame-review`

**Purpose**: Detailed game review with actionable improvement feedback.

**Input Data**:
- Single match data (full details + timeline)
- Combat power progression
- Objective control events
- Death analysis

**Analysis Methodology**:
1. **Critical Mistakes**:
   - Deaths with high impact (shutdown gold, Baron control loss)
   - Missed objective opportunities

2. **Highlight Plays**:
   - Multi-kills
   - Game-winning teamfights
   - Clutch Baron steals

3. **Macro Decisions**:
   - Baron vs pushing lanes
   - Teamfight positioning
   - Recall timing

**Output**: Narrative review with timestamped events and improvement suggestions.

---

## Shared Agent Infrastructure

### Base Agent Architecture

All agents inherit from `BaseAgent` class:

```python
class BaseAgent(ABC):
    def __init__(self, llm_client, cache, insight_detector):
        self.llm = llm_client
        self.cache = cache
        self.insights = insight_detector

    @abstractmethod
    async def run(
        self,
        puuid: str,
        region: str,
        recent_count: int,
        model: str = "haiku"
    ) -> AgentResponse:
        pass
```

### Shared Services

1. **LLM Cache** (`llm_cache.py`):
   - SQLite-based response caching
   - 35-45% cache hit rate
   - Significant cost savings

2. **Insight Detector** (`insight_detector.py`):
   - Zero-LLM pattern-based detection
   - Structured insights fed to LLM
   - Improves analysis quality

3. **Timeline Compressor** (`timeline_compressor.py`):
   - 99.9% data reduction (500KB → 500B)
   - Keyframe extraction (kills, objectives, power spikes)

4. **Prompt Optimizer** (`prompt_optimizer.py`):
   - Token-efficient prompts
   - Symbol substitution
   - Smart abbreviations

### Agent Response Format

All agents return consistent JSON:

```json
{
  "success": true,
  "agent_id": "weakness-analysis",
  "one_liner": "Concise summary insight",
  "detailed": "Full analysis text",
  "evidence": {
    "metrics": {...},
    "comparisons": {...}
  },
  "recommendations": [...],
  "governance": "CONFIDENT|CAUTION|CONTEXT"
}
```

---

## Model Selection

### Claude 3.5 Haiku (Default)
- **Speed**: <3s response time
- **Cost**: $0.25 per 1M input tokens
- **Use Case**: Most agents, quick analysis

### Claude 4.5 Sonnet (Premium)
- **Speed**: ~5-8s response time
- **Cost**: $3.00 per 1M input tokens
- **Use Case**: Complex analysis (Annual Summary, Post-game Review)
- **Quality**: Higher reasoning depth

**Selection Strategy**: Default to Haiku, upgrade to Sonnet for agents requiring deep reasoning or creative narrative generation.

---

## Performance Metrics

- **Average Response Time**: 2-6 seconds (cached data)
- **Cache Hit Rate**: 35-45%
- **Cost per Analysis**: $0.001-$0.01 depending on model
- **Concurrency**: 10+ simultaneous agent requests supported

---

## Summary

QuantRift's 18-agent system provides comprehensive player analysis through:

✅ **Specialized Expertise**: Each agent focuses on specific aspect of gameplay
✅ **Quantitative Foundation**: All insights backed by Player-Pack metrics
✅ **Statistical Rigor**: Wilson CI, governance tags ensure data quality
✅ **Production Infrastructure**: Shared services (caching, optimization, compression)
✅ **Flexible Models**: Haiku for speed, Sonnet for depth
✅ **Actionable Insights**: Every analysis includes concrete recommendations

**Innovation**: Zero-LLM insight detection reduces costs while improving analysis quality by providing structured context to LLM.
