# SECTION 1: COACHING AGENT METHODOLOGY

## 1.1 Multi-Agent Coaching Architecture

QuantRift implements **9 specialized AI agents**, each focused on a specific coaching aspect:

### Agent Categories

**Performance Analysis (3 agents)**
- **Performance Insights**: Comprehensive analysis combining weakness detection, detailed breakdown, and progress tracking. Identifies low-winrate champions (<45% WR, 5+ games), weak roles, and performance trends over time
- **Champion Mastery**: Analyzes expertise depth and champion-specific mechanics across all game modes
- **Role Specialization**: Identifies role-specific performance gaps and specialization strengths

**Comparison & Benchmarking (1 agent)**
- **Comparison Hub**: Unified comparison tool supporting both friend-to-friend comparisons and peer benchmarking against similar-ranked players

**Temporal Analysis (2 agents)**
- **Annual Summary**: Full-season review (40-50 patches) providing year-in-review performance highlights
- **Version Trends**: Cross-patch trend analysis combining multi-version adaptation assessment and version-to-version comparison

**Tactical Coaching (2 agents)**
- **Build Simulator**: Item build optimization using statistical comparison of historical match data
- **Match Analysis**: Deep dive into recent match timeline, combining frame-by-frame analysis with postgame quantitative diagnosis

**Strategic Recommendations (1 agent)**
- **Champion Recommendation**: Suggests champions matching playstyle with optional Thompson Sampling reinforcement learning

## 1.2 Standardized Player-Pack Data Format

All agents operate on consistent **Player-Pack JSON structure**:

```json
{
    "patch": "15.10",
    "queue_id": 420,  // 420=Solo/Duo, 440=Flex, 400=Normal
    "earliest_match_date": "2024-05-15T10:30:00Z",
    "latest_match_date": "2024-05-20T18:45:00Z",
    "by_cr": [
        {
            "champ_id": 157,
            "role": "MIDDLE",
            "games": 15,
            "wins": 8,
            "kda": 3.2,
            "damage_dealt": 25000,
            "damage_taken": 12000,
            "gold_earned": 12500,
            "cs": 180,
            "vision_score": 45
        }
    ]
}
```

**Metrics per Champion-Role**:
- Combat: KDA, damage, survivability
- Economic: Gold, CS, efficiency
- Objectives: Turret kills, inhibitor kills
- Temporal: Game duration, timing windows

## 1.3 Automated Insight Detection (Zero-LLM Preprocessing)

**Key Innovation**: Pre-process data to identify insights BEFORE LLM processing

```python
# File: backend/src/agents/shared/insight_detector.py
class InsightDetector:
    """Identifies 9 insight categories without LLM"""
    
    CATEGORIES = [
        "performance_decline",      # Losing streaks
        "performance_improvement",  # Upward trends
        "champion_mastery",         # Core champion expertise
        "role_effectiveness",       # Strong/weak roles
        "statistical_anomaly",      # Outliers
        "trend_pattern",            # Linear trends
        "benchmark_comparison",     # vs peers
        "behavioral_pattern",       # Time-of-day effects
        "surprise_insight"          # Unexpected findings
    ]
    
    SEVERITY = ["critical", "high", "medium", "low", "info"]
```

**Benefits**:
- Reduces LLM input tokens by 60-70%
- Provides structured data for both humans and LLMs
- Enables offline analysis
- Improves focus on actionable insights

## 1.4 Weakness Analysis Agent (Detailed Example)

**Implementation** (`backend/src/agents/player_analysis/weakness_analysis/`):

```python
class WeaknessAnalysisAgent:
    def run(self, packs_dir, recent_count=5):
        # Step 1: Load recent N patches
        recent_data = load_recent_data(packs_dir, recent_count)
        
        # Step 2: Identify weaknesses
        weaknesses = identify_weaknesses(recent_data)
        # Returns: {
        #   'low_winrate_champions': [...],  # <45% WR, 5+ games
        #   'weak_roles': [...],              # <48% WR, 10+ games
        #   'overall_stats': {...}
        # }
        
        # Step 3: Automated insight detection (NO LLM NEEDED)
        insights = self.insight_detector.detect_insights(weaknesses)
        # Returns: [Insight(id, category, severity, title, description, ...)]
        
        # Step 4: Format for LLM (use insights as context)
        formatted = format_analysis_for_prompt(weaknesses)
        
        # Step 5: Generate LLM narrative (AWS Bedrock)
        result = self.llm.generate_sync(
            prompt=formatted,
            system="You are a professional League coach..."
        )
        
        return weaknesses, result['text']
```

**Algorithm Logic**:
```python
def identify_weaknesses(recent_data):
    for patch, pack in recent_data.items():
        for champion_role in pack['by_cr']:
            champ_id = champion_role['champ_id']
            role = champion_role['role']
            games = champion_role['games']
            wins = champion_role['wins']
            
            winrate = wins / games if games > 0 else 0
            
            # Identify low-winrate champions (5+ games, <45% WR)
            if games >= 5 and winrate < 0.45:
                low_winrate_champions.append({
                    'champ_id': champ_id,
                    'role': role,
                    'winrate': winrate,
                    'games': games
                })
    
    return {
        'low_winrate_champions': sorted_by_winrate,
        'overall_stats': {...}
    }
```

## 1.5 Drafting Coach: Counter-Based Recommendations

**Data Sources**:
- Counter matrix: Champion vs Champion matchup win rates
- Power curves: Damage scaling timeline by patch + role
- Composition analyzer: Team balance, role coverage

**Pick Recommendation Logic**:
```python
def generate_pick_recommendations(bp_state, missing_roles, top_n=5):
    """Recommend champions for unfilled roles"""
    
    counter_matrix = bp_state['counter_matrix']['champions']
    power_curves = bp_state['power_curves']['champions']
    
    for role in missing_roles:
        for champ_id, champ_data in counter_matrix.items():
            if role not in champ_data['roles']:
                continue
            
            # Score based on matchups vs enemy team
            score = 0.5  # Base score
            
            # Check matchups against enemy team
            for enemy in bp_state['enemy_composition']:
                if enemy['role'] == role and str(enemy['champion_id']) in matchup_stats:
                    winrate = matchup_stats[str(enemy['champion_id'])]['winrate']
                    score = winrate  # Use actual winrate
            
            # Scaling bonus (prefer mid-game champions 15-25min peak)
            if champ_id in power_curves:
                peak_time = power_curves[champ_id]['roles'][role]['peak_time']
                if 15 <= peak_time <= 25:
                    score += 0.05
            
            recommendations.append({
                'champion_id': champ_id,
                'role': role,
                'score': score
            })
    
    return sorted(recommendations, key=lambda x: x['score'], reverse=True)[:top_n]
```

**Ban Recommendation Logic**:
```python
def generate_ban_recommendations(bp_state, top_n=5):
    """Identify champions that counter our composition"""
    
    bans = []
    for our_member in bp_state['our_composition']:
        our_champ_id = str(our_member['champion_id'])
        our_role = our_member['role']
        
        # Get counters (champions we struggle against)
        counters = counter_matrix[our_champ_id]['roles'][our_role].get('counters', {})
        
        for counter_champ_id, winrate in counters.items():
            threat_score = 0.5 - winrate  # Lower winrate = higher threat
            bans.append({
                'champion_id': counter_champ_id,
                'threat_score': threat_score
            })
    
    return sorted(bans, key=lambda x: x['threat_score'], reverse=True)[:top_n]
```

## 1.6 Build Simulator: Data-Driven Item Optimization

**Methodology**:
```python
def compare_build_options(champion_id, role, build_a, build_b, parquet_path):
    """Compare two builds using historical match data"""
    
    # Load Gold-layer parquet data
    df = pd.read_parquet(parquet_path)
    
    # Filter for this champion + role
    matches = df[
        (df['champion_id'] == champion_id) & 
        (df['role'] == role)
    ]
    
    # For each build, find matches containing those items
    build_a_matches = matches[matches['items'].apply(contains_items(build_a))]
    build_b_matches = matches[matches['items'].apply(contains_items(build_b))]
    
    # Calculate statistics with confidence intervals
    build_a_stats = {
        'sample_size': len(build_a_matches),
        'winrate': build_a_matches['win'].mean(),
        'ci_lo': wilson_ci_lower(wins, n),
        'ci_hi': wilson_ci_upper(wins, n),
        'avg_kda': build_a_matches['kda'].mean(),
        'avg_damage': build_a_matches['damage'].mean()
    }
    
    # Repeat for build_b
    # Compare: which has higher win rate and CI?
    return {
        'build_a_stats': build_a_stats,
        'build_b_stats': build_b_stats,
        'winner': 'build_a' if a_wr > b_wr else 'build_b',
        'statistically_significant': ci_ranges_dont_overlap(a_ci, b_ci)
    }
```

## 1.7 Postgame Review: Rule-Engine Diagnosis

**Architecture**: Pure rule-based quantitative diagnosis (no LLM required for core analysis)

```python
# File: backend/src/agents/player_analysis/postgame_review/engine.py
class PostgameReviewEngine:
    """Diagnoses single match across 4 game phases"""
    
    def generate_postgame_review(self, match_features, timeline_features):
        
        # Phase 1: Laning (0-14 min)
        lane_issues = self._diagnose_lane_phase(match, timeline)
        # Rules:
        #   - CS@10 < percentile_30 → lane pressure issue
        #   - Gold@10 < threshold → gold deficit
        #   - First back > 6:30 → rotation timing issue
        
        # Phase 2: Objectives (14-25 min)
        objective_issues = self._diagnose_objective_phase(match, timeline)
        # Rules:
        #   - Ward <60s before objective → poor setup
        #   - Miss objective window → map awareness
        
        # Phase 3: Items
        build_issues = self._diagnose_build_timing(match, timeline)
        # Rules:
        #   - Core 2 items > 20min (+2:10 delay) → build slow
        
        # Phase 4: Teamfights
        teamfight_issues = self._diagnose_teamfight(match, timeline)
        # Rules:
        #   - Join fight in bottom 30% → detection failure
        #   - Assist share < 20% → impact low
        
        return {
            'match_id': match_id,
            'champion': champion_name,
            'role': role,
            'result': 'WIN' if match['win'] else 'LOSS',
            'lane_phase': lane_issues,
            'objective_phase': objective_issues,
            'build_timing': build_issues,
            'teamfight': teamfight_issues,
            'overall_score': self._calculate_overall_score(...)
        }
```

---

# SECTION 2: AWS AI SERVICES INTEGRATION

## 2.1 AWS Bedrock: Core LLM Service

**Service**: AWS Bedrock Runtime (bedrock-runtime API)

**Models**:
- **Claude 4.5 Sonnet**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
  - High quality, better reasoning, slower (5-15s)
  - ~10x cost vs Haiku
  - Used for: Annual summary, deep strategic analysis

- **Claude 3.5 Haiku**: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
  - Fast (2-5s), cost-effective
  - Sufficient for straightforward analysis
  - Used for: Weakness analysis, postgame review, single matches

**Region**: us-west-2 (most stable)

## 2.2 BedrockLLM Adapter Implementation

```python
# File: backend/src/agents/shared/bedrock_adapter.py
class BedrockLLM:
    """Adapts boto3 Bedrock to unified agent interface"""
    
    def __init__(self, model="haiku", region="us-west-2"):
        config = Config(
            read_timeout=600,        # 10 minute timeout for long generations
            connect_timeout=60,
            retries={'max_attempts': 3}
        )
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=region,
            config=config
        )
        self.model_id = BedrockModel.resolve_model_id(model)
        self.default_max_tokens = 16000 if "sonnet" in model else 8000
        self.default_temperature = 0.7
    
    def generate_sync(self, prompt, system=None, max_tokens=None, **kwargs):
        """Synchronous generation (blocking)"""
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.default_max_tokens,
            "temperature": self.default_temperature,
            "messages": [{"role": "user", "content": prompt}],
            "system": system  # Optional system prompt
        }
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return {
            "text": response_body['content'][0]['text'],
            "usage": response_body.get('usage', {}),
            "model": self.model_id
        }
    
    async def generate(self, prompt, system=None, **kwargs):
        """Asynchronous generation (non-blocking)"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.generate_sync(prompt, system, **kwargs)
        )
        return result
```

## 2.3 Data Flow: Agent → Bedrock → Response

**Complete Flow Example (Weakness Analysis)**:

```
User Request (FastAPI endpoint)
    ↓
WeaknessAnalysisAgent.run(packs_dir, recent_count=5)
    ├─ load_recent_data(packs_dir, 5)
    │   └─ Load 5 most recent patch pack_*.json files
    │
    ├─ identify_weaknesses(recent_data)
    │   └─ Find <45% WR champions, <48% WR roles
    │
    ├─ InsightDetector.detect_insights(weaknesses)
    │   └─ Pre-process to identify key patterns (ZERO LLM)
    │       Returns: [{id, category, severity, title, evidence, ...}]
    │
    ├─ format_analysis_for_prompt(weaknesses)
    │   └─ Format data + insights as readable text
    │
    ├─ BedrockLLM.generate_sync(formatted_text, system_prompt)
    │   └─ Call AWS Bedrock API with:
    │       - Model: haiku-4-5 (fast)
    │       - Max tokens: 12000
    │       - System: "You are professional League coach..."
    │       - Messages: [{role: "user", content: formatted_data}]
    │
    └─ return (weaknesses_json, report_text)
        └─ Return structured data + LLM narrative to frontend
```

## 2.4 Multi-Agent Synthesis Pattern

**Example: Meta Strategy Agent**

```python
class MetaStrategyAgent:
    """Synthesizes multiple agents into unified strategic overview"""
    
    def run(self, packs_dir):
        # Run 3 independent agents
        weakness_analysis = WeaknessAnalysisAgent().run(packs_dir)
        champion_recommendations = ChampionRecommendationAgent().run(packs_dir)
        role_analysis = RoleSpecializationAgent().run(packs_dir)
        
        # Synthesis using high-capacity model (Sonnet)
        synthesis_llm = BedrockLLM(model="sonnet")
        
        synthesis_prompt = f"""
        Based on three player analysis reports, synthesize strategic roadmap:
        
        1. WEAKNESSES:
        {weakness_analysis['report']}
        
        2. CHAMPION RECOMMENDATIONS:
        {champion_recommendations['report']}
        
        3. ROLE ANALYSIS:
        {role_analysis['report']}
        
        Generate unified improvement roadmap addressing:
        - Priority fixes for current weaknesses
        - Recommended champion picks
        - Role focus areas
        - 90-day improvement plan
        """
        
        result = synthesis_llm.generate_sync(
            prompt=synthesis_prompt,
            system="Synthesize these reports into strategic coaching narrative",
            max_tokens=16000
        )
        
        return result['text']
```

## 2.5 Streaming with AWS Bedrock

**Real-Time Token Streaming**:

```python
# File: backend/src/agents/shared/stream_helper.py
def stream_agent_with_thinking(prompt, system_prompt, model, max_tokens=8000):
    """Stream LLM response token-by-token via SSE"""
    
    client = boto3.client('bedrock-runtime')
    
    # Use streaming invoke_model_with_response_stream
    with client.invoke_model_with_response_stream(
        modelId=model,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        })
    ) as response:
        
        for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            
            if chunk['type'] == 'content_block_delta':
                text = chunk['delta'].get('text', '')
                # Emit as SSE message
                yield f"data: {json.dumps({'text': text})}\n\n"
            
            elif chunk['type'] == 'message_stop':
                yield f"data: {json.dumps({'done': True})}\n\n"
```

**Endpoint**:
```python
@app.post("/v1/agents/weakness-analysis/stream")
async def weakness_analysis_stream(request: WeaknessAnalysisRequest):
    async def event_generator():
        agent = WeaknessAnalysisAgent(model=request.model)
        for sse_message in agent.run_stream(
            packs_dir=f"data/player_packs/{request.puuid}",
            recent_count=request.recent_count
        ):
            yield sse_message
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## 2.6 Performance & Cost Metrics

**Monitoring** (via structured logging):

```python
# Metrics tracked for every LLM call:
metrics = {
    "llm_calls_total": {"model": "haiku", "status": "success"},
    "llm_call_duration_seconds": 3.2,  # Haiku average
    "llm_input_tokens": 2500,
    "llm_output_tokens": 1200,
    "llm_cache_hits": True,  # If cached
    "llm_cache_duration_ms": 45
}
```

**Cost Examples** (as of Nov 2024):
- Haiku: $0.80/1M input tokens, $4.00/1M output tokens
- Sonnet: $3/1M input, $15/1M output
- Average call: Haiku (2000→1200 tokens) = $2.64; Sonnet = $12.60

**Optimization Strategies**:
1. **Token reduction**: 60-75% via insight detector
2. **Model selection**: Use Haiku for 80% of requests
3. **Caching**: Skip identical requests (SQLite cache, TTL 24h)
4. **Streaming**: Real-time UI updates with fewer re-generations

---

# SECTION 3: QUANTITATIVE ANALYSIS ENGINE

## 3.1 Combat Power Index

**Purpose**: Single metric combining offensive, defensive, and efficiency factors

**Calculation**:

```python
# File: backend/src/combatpower/services/combat_power.py
class CombatPowerCalculator:
    # Conversion rates for combat power
    ATTACK_DAMAGE_RATE = 2.0
    ABILITY_POWER_RATE = 1.5
    ARMOR_RATE = 1.5
    MAGIC_RESIST_RATE = 1.5
    HEALTH_RATE = 0.5
    ATTACK_SPEED_RATE = 25.0
    CRIT_CHANCE_RATE = 30.0
    LIFESTEAL_RATE = 20.0
    
    def calculate_total_power(self, champion_id, build_items, level=18):
        # Power = Base Stats + Items + Runes + Skills
        base_power = self.calculate_base_stats_power(stats, level)
        item_power = self.calculate_item_power(build_items)
        rune_power = self.calculate_rune_power(rune_ids)
        skill_power = self.calculate_skill_power(abilities)
        
        return base_power + item_power + rune_power + skill_power
    
    def calculate_base_stats_power(self, stats, level=18):
        # Level-scale champion stats
        hp = base_hp + (hp_per_level * (level - 1))
        ad = base_ad + (ad_per_level * (level - 1))
        
        # Convert to combat power
        power = 0
        power += hp * self.HEALTH_RATE
        power += ad * self.ATTACK_DAMAGE_RATE
        power += armor * self.ARMOR_RATE
        
        return power
    
    def calculate_item_power(self, item_ids):
        # Sum power from all equipped items
        power = 0
        for item_id in item_ids:
            item = self.items_db[item_id]
            power += item['stats']['FlatAD'] * self.ATTACK_DAMAGE_RATE
            power += item['stats']['FlatAP'] * self.ABILITY_POWER_RATE
            power += item['stats']['FlatHP'] * self.HEALTH_RATE
        return power
```

**Applications**:
- Build comparison (CP per gold spent)
- Champion power curves (CP at 5, 10, 15, 20 min)
- Team fight risk assessment (our_team_CP vs enemy_team_CP)

## 3.2 Wilson Confidence Intervals

**Problem**: Small sample sizes (5-20 games) need robust statistical estimation

```python
# File: backend/src/core/statistical_utils.py
def wilson_confidence_interval(successes, trials, alpha=0.05):
    """
    Calculate Wilson Score Confidence Interval for binomial proportion
    
    Why Wilson CI?
    - Asymmetric (respects [0,1] bounds)
    - Accurate for small n (n < 30)
    - Respects boundary conditions
    - Recommended by modern statistics
    
    Example:
    >>> wilson_confidence_interval(wins=8, trials=15, alpha=0.05)
    (0.533, 0.445, 0.620)  # (point_estimate, ci_lower, ci_upper)
    
    vs Normal Approximation CI: (0.533, 0.369, 0.697)  # Too wide
    """
    
    if trials == 0:
        return 0.0, 0.0, 0.0
    
    # Z-score for 95% confidence (alpha=0.05)
    z = stats.norm.ppf(1 - alpha/2)  # ~1.96
    
    # Point estimate
    p = successes / trials
    
    # Wilson CI formula
    center = (p + z*z/(2*trials)) / (1 + z*z/trials)
    margin = z * math.sqrt(
        (p*(1-p) + z*z/(4*trials))/trials
    ) / (1 + z*z/trials)
    
    ci_lower = max(0, center - margin)
    ci_upper = min(1, center + margin)
    
    return (p, ci_lower, ci_upper)
```

**Usage in Agents**:

```python
# Weakness analysis - identify truly weak champions
for champ_role in recent_data:
    wins = champ_role['wins']
    games = champ_role['games']
    
    point_est, ci_lo, ci_hi = wilson_confidence_interval(wins, games, alpha=0.05)
    
    # Only flag as weak if lower bound < 0.45
    if ci_lo < 0.45 and games >= 5:
        weak_champions.append({
            'winrate': point_est,
            'ci_lower': ci_lo,
            'ci_upper': ci_hi,
            'confidence': 'CONFIDENT' if games >= 100 else 'CAUTION'
        })
```

## 3.3 20 Quantitative Metrics System

| Category | Metric | Calculation | Use Case |
|----------|--------|-----------|----------|
| **Behavioral** | Pick rate | Champ picks / Total games | Meta popularity |
| | Attach rate | Co-picks with other champs | Synergy |
| | Rune diversity | Unique rune builds | Flexibility |
| | Synergy score | Team comp match rating | Drafting |
| | Counter effectiveness | Vs enemy champs win rate | Matchup analysis |
| **Win Rate** | Baseline WR | Wins / Games | Performance |
| | CI Lower | Wilson CI lower bound | Confidence min |
| | CI Upper | Wilson CI upper bound | Confidence max |
| | Effective N | Adjusted sample size | Statistical weight |
| | Governance | CONFIDENT/CAUTION/CONTEXT | Data quality |
| **Objectives** | Objective rate | (Baron+Dragon) / Games | Map control |
| | Baron rate | Baron kills / Games | Late-game control |
| | Dragon rate | Dragon kills / Games | Early-mid control |
| **Economic** | Item efficiency | Avg damage / Gold spent | Build value |
| | Gold per min | Total gold / Duration | Economy |
| | CS efficiency | Gold / CS | Farming |
| **Combat** | Combat power | Calculated from stats+items+runes | Overall strength |
| | Damage efficiency | Damage / Gold | DPS value |
| | Time to core | Minutes to 2 core items | Tempo |
| | Shock impact | Unexpected perf changes | Variance |

## 3.4 Data Governance Framework

```python
# Confidence tiers based on sample size + CI width
class GovernanceFramework:
    CONFIDENT = "confident"      # n ≥ 100, very reliable
    CAUTION = "caution"          # 20 ≤ n < 100, use carefully
    CONTEXT = "context"          # n < 20, informational only

    @staticmethod
    def assign_tier(sample_size, ci_width, point_estimate):
        if sample_size >= 100 and ci_width < 0.15:
            return "CONFIDENT"
        elif sample_size >= 20 and ci_width < 0.30:
            return "CAUTION"
        else:
            return "CONTEXT"  # Use as context, not primary recommendation
```

## 3.5 Player-Pack Data Compression & Aggregation

**Challenge**: Full-year analysis requires processing 300-500 matches × 40KB raw data = ~20MB per player

**Solution - Multi-Level Data Compression**:

### Level 1: Match-to-Metrics Compression (100:1 ratio)
```python
# Raw match data (40KB JSON) → Aggregated metrics (400 bytes)
def compress_match_to_metrics(match_json):
    """Extract only quantitative metrics from raw match"""
    return {
        'match_id': match_json['metadata']['matchId'],
        'champion_id': participant['championId'],
        'role': participant['teamPosition'],
        'win': participant['win'],

        # 15 core metrics (60 bytes)
        'kda': (kills + assists) / max(deaths, 1),
        'damage_dealt': participant['totalDamageDealtToChampions'],
        'damage_taken': participant['totalDamageTaken'],
        'gold_earned': participant['goldEarned'],
        'cs': participant['totalMinionsKilled'],
        'vision_score': participant['visionScore'],
        'turret_kills': participant['turretKills'],
        'baron_kills': participant['baronKills'],
        'dragon_kills': participant['dragonKills'],

        # Temporal data (12 bytes)
        'game_duration': match_json['info']['gameDuration'],
        'patch': match_json['info']['gameVersion'].split('.')[0:2]
    }
# Result: 40KB → 400 bytes = 100x compression
```

### Level 2: Metrics-to-Pack Aggregation (10:1 ratio)
```python
# 20 matches × 400 bytes = 8KB → Patch Pack 800 bytes
def aggregate_to_patch_pack(matches_for_patch):
    """Group by champion-role, calculate aggregates"""
    pack = {'patch': '15.10', 'by_cr': []}

    for (champ_id, role), games in group_by_cr(matches_for_patch).items():
        pack['by_cr'].append({
            'champ_id': champ_id,
            'role': role,
            'games': len(games),
            'wins': sum(g['win'] for g in games),

            # Aggregated metrics (mean values)
            'kda': mean([g['kda'] for g in games]),
            'damage_dealt': mean([g['damage_dealt'] for g in games]),
            'cs': mean([g['cs'] for g in games]),

            # Statistical bounds
            'winrate_ci_lo': wilson_ci_lower(wins, games),
            'winrate_ci_hi': wilson_ci_upper(wins, games),
            'governance': assign_tier(games, ci_width)
        })

    return pack
# Result: 8KB → 800 bytes = 10x compression
```

### Level 3: Timeline Event Filtering (950:1 ratio)
```python
# Timeline data: 2400 frames × 8KB = 19MB → 20KB significant events
def compress_timeline(timeline_json, target_events=50):
    """Keep only critical game events"""

    significant_events = []

    for frame in timeline_json['info']['frames']:
        timestamp = frame['timestamp']

        # Keep only high-impact events
        for event in frame.get('events', []):
            if event['type'] in [
                'CHAMPION_KILL',      # Kills (KDA)
                'BUILDING_KILL',      # Turrets/Inhibitors
                'ELITE_MONSTER_KILL', # Baron/Dragon
                'ITEM_PURCHASED'      # Build timing
            ]:
                significant_events.append({
                    'timestamp': timestamp,
                    'type': event['type'],
                    'details': extract_minimal_details(event)
                })

    # Keep only top N most impactful events
    return sorted(significant_events, key=impact_score, reverse=True)[:target_events]
# Result: 19MB → 20KB = 950x compression
```

**Overall Compression Summary**:
- **Input**: 500 matches × 40KB raw + 500 timelines × 19MB = 9.5GB
- **Output**: 50 patch packs × 800 bytes + 50 compressed timelines × 20KB = 1.04MB
- **Compression ratio**: 9,100:1
- **Agent processing time**: 9.5GB (5min) → 1MB (0.3s) = 1000x faster

## 3.6 Annual Summary Agent - Technical Highlights

**What Makes It Special**:

1. **Full-Year Data Coverage** (40-50 patches)
   - Analyzes entire competitive season (Jan-Dec)
   - Processes 300-500 matches across version changes
   - Identifies long-term trends vs short-term variance

2. **Three-Tier Narrative Generation**
   ```python
   class AnnualSummaryAgent:
       def run_stream(self, packs_dir, start_date, end_date):
           # Load all patches in date range
           all_packs = load_packs_in_range(packs_dir, start_date, end_date)

           # Tier 1: Executive Summary (200-300 words)
           exec_summary = self._generate_exec_summary(all_packs)
           # - Total games, overall WR, rank progression
           # - Top 3 achievements, top 3 weaknesses
           # - Season trajectory (improving/declining/stable)

           # Tier 2: Detailed Analysis (1000-1500 words)
           detailed = self._generate_detailed_analysis(all_packs)
           # - Champion pool evolution (meta adaptation)
           # - Role performance across patches
           # - Quarterly performance breakdown
           # - Statistical trends (KDA, damage, gold efficiency)

           # Tier 3: Forward-Looking Recommendations (500-800 words)
           recommendations = self._generate_recommendations(all_packs)
           # - Champions to master
           # - Roles to focus
           # - Skill priorities
           # - 90-day improvement roadmap
   ```

3. **Cross-Patch Trend Analysis**
   ```python
   def analyze_cross_patch_trends(all_packs):
       """Identify performance patterns across version changes"""

       trends = {
           'champion_winrate_trends': {},  # Did Yasuo WR improve after patch 15.10?
           'role_shift_trends': {},        # Switched from Top→Mid in Q2?
           'meta_adaptation': {},          # Picked S-tier champs? Or off-meta?
           'learning_curves': {}           # How fast did they improve on new champs?
       }

       # Example: Champion learning curve
       for champ_id in get_all_champions(all_packs):
           games_over_time = []
           for patch in sorted(all_packs.keys()):
               champ_data = find_champion(all_packs[patch], champ_id)
               if champ_data:
                   games_over_time.append({
                       'patch': patch,
                       'winrate': champ_data['wins'] / champ_data['games'],
                       'games': champ_data['games']
                   })

           # Fit linear regression: is winrate improving over time?
           slope, r_squared = fit_trend(games_over_time)

           if slope > 0.05 and r_squared > 0.7:
               trends['learning_curves'][champ_id] = {
                   'improvement': 'STRONG',  # +5% WR per 10 games
                   'consistency': 'HIGH'     # R²=0.7
               }

       return trends
   ```

4. **Seasonal Milestone Detection**
   ```python
   def detect_milestones(all_packs):
       """Identify significant achievements"""

       milestones = []

       # Career-high winrate patch
       best_patch = max(all_packs.items(), key=lambda x: x[1]['overall_wr'])
       milestones.append({
           'type': 'PEAK_PERFORMANCE',
           'patch': best_patch[0],
           'winrate': best_patch[1]['overall_wr'],
           'description': f"Career-high {best_patch[1]['overall_wr']:.1%} WR"
       })

       # First pentakill
       for patch, pack in all_packs.items():
           if pack.get('pentakills', 0) > 0:
               milestones.append({
                   'type': 'ACHIEVEMENT',
                   'patch': patch,
                   'description': 'First pentakill!'
               })
               break

       # Rank promotion
       rank_history = [pack.get('rank') for pack in all_packs.values()]
       if 'GOLD' in rank_history and 'PLATINUM' in rank_history:
           promo_patch = find_rank_change(all_packs, 'GOLD', 'PLATINUM')
           milestones.append({
               'type': 'RANK_UP',
               'patch': promo_patch,
               'description': 'Promoted to Platinum!'
           })

       return sorted(milestones, key=lambda x: x['patch'])
   ```

5. **AWS Bedrock Streaming for Long Reports**
   - Uses **Claude 4.5 Sonnet** (high quality for comprehensive analysis)
   - Streams 3000-5000 word reports token-by-token
   - Real-time progress indicators for 30-60s generation time
   - Structured sections with markdown formatting

**Output Example**:
```markdown
# 2024 League of Legends Annual Summary

## Executive Summary
In 2024, you played **487 ranked games** across **48 patches** (15.1 through 15.23),
achieving an overall **53.2% win rate** and climbing from **Gold II to Platinum I**.

Your **top 3 achievements**:
1. 68% win rate on Yasuo (Mid) in Q2 - your signature champion
2. Consistent objective control: 2.1 dragons/game (top 15% of Platinum)
3. Strong meta adaptation: picked S-tier champions in 72% of games

**Areas for improvement**:
1. Support role: 42% WR (15 games) - needs focus
2. Late-game decision making: -8% WR in games >35min
3. Champion pool depth: 80% games on top 5 champions

## Quarterly Breakdown
### Q1 (Patches 15.1-15.12): Foundation Building
- 120 games, 49% WR (climbing from Gold II)
- Learning phase: tried 28 different champions
- Best champion: Ahri (Mid) - 58% WR, 22 games

### Q2 (Patches 15.13-15.18): Performance Peak
- 145 games, **61% WR** - career high
- Mastered Yasuo: 68% WR, 45 games
- Reached Platinum II

### Q3 (Patches 15.19-15.21): Adaptation Struggles
- 110 games, 48% WR
- Meta shift affected champion pool
- Experimented with new roles (Top lane)

### Q4 (Patches 15.22-15.23): Recovery & Growth
- 112 games, 55% WR
- Refined champion pool to core 5
- Promoted to Platinum I

## 2025 Improvement Roadmap
...
```

**Why Annual Summary Agent is Unique**:
- Only agent that processes **full year** of data (others focus on recent 5-20 games)
- Combines **quantitative trends** (WR, KDA, CS) with **qualitative milestones** (rank ups, achievements)
- Uses **Sonnet model** for nuanced storytelling (other agents use Haiku for speed)
- Generates **shareable year-in-review** content (like Spotify Wrapped for League)

---

# SECTION 4: DEVELOPMENT CHALLENGES & SOLUTIONS

## 4.1 Token Optimization for LLM Costs

**Challenge**: Large contexts (20+ patches, 100+ metrics) exceed reasonable token budgets

**Solutions Implemented**:

1. **Automated Insight Detector** (Phase 1.5)
   - Pre-process in Python (no LLM cost)
   - Identify 5-10 key insights
   - Pass only insights + highlights to LLM
   - **Result**: 60-70% token reduction

2. **Timeline Compressor** (Phase 3)
   ```python
   def compress_timeline(timeline, target_events=20):
       # Keep only significant events (kills, objectives, items)
       # 2400 frames (40 min) × 8 KB = 19 MB becomes 20 KB
       # Compression: 950x reduction
   ```

3. **Prompt Optimizer** (Phase 4)
   - Use compact JSON instead of verbose prose
   - Focus on exceptions (weaknesses, improvements)
   - Skip summarizing known data

## 4.2 Data Freshness with Rate Limiting

**Challenge**: Riot API = 1800 req/10s per key, need to fetch 500+ matches per player

**Solution - Player Data Manager**:

```python
class PlayerDataManager:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(20)  # Max 20 concurrent
        self.cache_dir = Path("data/player_packs")
    
    async def prepare_player_data(self, puuid, max_matches=500):
        # Step 1: Fetch match IDs
        match_ids = await riot_client.get_match_ids(puuid, limit=max_matches)
        
        # Step 2: Parallel fetch match details (rate-limited via semaphore)
        matches = await asyncio.gather(
            *[self._fetch_match_with_semaphore(m_id) for m_id in match_ids],
            return_exceptions=True
        )
        
        # Step 3: Calculate metrics (CPU-bound, parallelizable)
        metrics = self._calculate_metrics(matches)
        
        # Step 4: Cache for agents
        self._save_player_pack(puuid, metrics)
    
    async def _fetch_match_with_semaphore(self, match_id):
        async with self.semaphore:
            return await riot_client.get_match_details(match_id)
```

## 4.3 Streaming for Real-Time Feedback

**Challenge**: LLM generation takes 5-15 seconds, users stare at blank screen

**Solution - Server-Sent Events (SSE)**:

```python
@app.post("/v1/agents/weakness-analysis/stream")
async def weakness_analysis_stream(request):
    async def event_generator():
        agent = WeaknessAnalysisAgent(model=request.model)
        for sse_message in agent.run_stream(packs_dir):
            yield sse_message  # Token-by-token
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Frontend TypeScript
const response = await fetch('/v1/agents/weakness-analysis/stream', {method: 'POST'})
const reader = response.body.getReader()

while (true) {
    const {done, value} = await reader.read()
    if (done) break
    
    const text = new TextDecoder().decode(value)
    // Parse SSE: "data: {\"text\": \"token\"}\n\n"
    setContent(prev => prev + token)  // Real-time UI update
}
```

## 4.4 Python Module Import Errors

**Problem**: Code looks correct but `IndentationError` or import failure

**Root Cause**: Stale `.pyc` bytecode

**Solution**:
```bash
find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find backend -name "*.pyc" -delete 2>/dev/null
# Then re-run
```

## 4.5 Next.js 15 Dynamic Routes

**Challenge**: Route params must be awaited (breaking change from v13)

**Correct Implementation**:
```typescript
// ✅ CORRECT for Next.js 15
export default async function Page({ 
    params 
}: { 
    params: Promise<{gameName: string, tagLine: string}> 
}) {
    const {gameName, tagLine} = await params
    // ...
}

// ❌ WRONG - Runtime error
export default function Page({ params }: ...) {
    return <div>{params.gameName}</div>
}
```

---

# CONCLUSION

This technical deep dive documents the implementation methodology behind QuantRift's AI-powered coaching platform. For high-level architecture, technology stack, and deployment information, refer to the [README.md](./README.md).

**Key Technical Innovations**:

1. **9 specialized AI agents** with automated insight detection reducing LLM token costs by 60-70%
2. **20 quantitative metrics** using Wilson confidence intervals for robust statistical analysis on small sample sizes
3. **AWS Bedrock integration** with model selection strategy (Haiku for 80% of requests, Sonnet for complex synthesis)
4. **Zero-LLM preprocessing** via InsightDetector identifying 9 insight categories before LLM processing
5. **Real-time streaming** via Server-Sent Events for responsive user experience
6. **Multi-source data integration** with intelligent caching and rate limit management

The platform demonstrates production-grade implementation combining quantitative analysis, AI-powered insights, and scalable architecture to deliver actionable coaching feedback beyond traditional stat dashboards.

The platform goes beyond traditional stat dashboards to provide **actionable, personalized coaching feedback** answering "why are you struggling?" and "what should you do differently?" powered by AI and quantitative analysis.
