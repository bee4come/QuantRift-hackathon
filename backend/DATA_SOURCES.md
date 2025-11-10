# Available Data Sources for Chat Agent

## 1. Player Pack Data Structure

**Location**: `data/player_packs/{puuid}/`

### Files:
- `pack_{patch}_{queue_id}.json` - Per-patch aggregated statistics
- `matches_data.json` - Raw match details
- `timelines/*.json` - Match timeline data (frame-by-frame)

### Pack File Schema:
```json
{
  "patch": "15.10",
  "queue_id": 420,  // 420=Solo/Duo, 440=Flex, 400=Normal
  "earliest_match_date": "2024-05-15T10:30:00Z",
  "latest_match_date": "2024-05-20T18:45:00Z",
  "by_cr": [  // Aggregated by Champion + Role
    {
      "champ_id": 157,  // Yasuo
      "role": "MIDDLE",
      "games": 15,
      "wins": 8,
      "kda": 3.2,
      "avg_damage": 25000,
      "avg_gold": 12500,
      "avg_cs": 180,
      // ... more metrics
    }
  ]
}
```

### Available Metrics per Champion-Role:
- **Basic**: `games`, `wins`, `losses`, `winrate`
- **Combat**: `kills`, `deaths`, `assists`, `kda`, `damage_dealt`, `damage_taken`
- **Economy**: `gold_earned`, `cs` (creep score), `vision_score`
- **Objectives**: `turret_kills`, `inhibitor_kills`
- **Time**: `avg_game_duration`

### Time Range Filters:
- `"2024-01-01"`: Season 2024 (patches 14.1 - 14.25)
- `"past-365"`: Past 365 days from now
- `None`: All available data

### Queue ID Filters:
- `420`: Ranked Solo/Duo
- `440`: Ranked Flex
- `400`: Normal Games
- `None`: All queue types

## 2. How Existing Agents Use Data

### Example 1: Weakness Analysis
```python
# Load recent 5 patches
packs = load_recent_data(packs_dir, recent_count=5, time_range="past-365", queue_id=420)

# Aggregate by champion
for patch, pack in packs.items():
    for cr in pack.get("by_cr", []):
        champ_id = cr["champ_id"]
        role = cr["role"]
        games = cr["games"]
        winrate = cr["wins"] / cr["games"]

        # Identify low winrate champions (games >= 5 and winrate < 45%)
        if games >= 5 and winrate < 0.45:
            low_winrate_champions.append(...)
```

### Example 2: Annual Summary
```python
# Load all patches for the season
all_packs = load_all_annual_packs(packs_dir, time_range="2024-01-01", queue_id=420)

# Analyze cross-patch trends
for patch in sorted(all_packs.keys()):
    pack = all_packs[patch]
    total_games += sum(cr["games"] for cr in pack["by_cr"])
    # ... trend analysis
```

## 3. Data Access Patterns for Chat Agent

### Pattern 1: Recent Performance
```python
# "How did I perform recently?"
recent_packs = load_recent_data(packs_dir, recent_count=3, time_range="past-365")
# → Analyze last 3 patches (about 1-2 months)
```

### Pattern 2: Season Analysis
```python
# "Analyze my 2024 season"
season_packs = load_all_annual_packs(packs_dir, time_range="2024-01-01")
# → All patches from Season 2024
```

### Pattern 3: Champion-Specific
```python
# "How's my Yasuo?"
all_packs = load_all_annual_packs(packs_dir)
yasuo_stats = []
for patch, pack in all_packs.items():
    for cr in pack["by_cr"]:
        if cr["champ_id"] == 157:  # Yasuo
            yasuo_stats.append(cr)
```

### Pattern 4: Role-Specific
```python
# "How's my jungle performance?"
all_packs = load_all_annual_packs(packs_dir, queue_id=420)
jungle_stats = []
for patch, pack in all_packs.items():
    for cr in pack["by_cr"]:
        if cr["role"] == "JUNGLE":
            jungle_stats.append(cr)
```

### Pattern 5: Time Comparison
```python
# "Compare my first 30 games vs last 30 games"
# Need to load matches_data.json and manually filter by game_creation timestamp
with open(f"{packs_dir}/matches_data.json") as f:
    matches = json.load(f)
    matches.sort(key=lambda x: x["game_creation"])
    first_30 = matches[:30]
    last_30 = matches[-30:]
```

## 4. Raw Match Data (matches_data.json)

**Use Case**: When pack aggregation is insufficient (e.g., time-of-day analysis, specific match queries)

```json
[
  {
    "match_id": "NA1_5123456789",
    "game_creation": 1715800000000,  // Unix timestamp (milliseconds)
    "game_duration": 1800,  // seconds
    "queue_id": 420,
    "game_version": "15.10",
    "champion_id": 157,
    "role": "MIDDLE",
    "win": true,
    "kills": 8,
    "deaths": 3,
    "assists": 12,
    // ... full match details
  }
]
```

## 5. Timeline Data (timelines/)

**Use Case**: Frame-by-frame analysis (gold lead, XP diff, item builds)

**Format**: `{match_id}_timeline.json`

```json
{
  "metadata": {
    "match_id": "NA1_5123456789",
    "participants": ["puuid1", "puuid2", ...]
  },
  "info": {
    "frames": [
      {
        "timestamp": 60000,  // 1 minute
        "participantFrames": {
          "1": {
            "totalGold": 625,
            "level": 2,
            "xp": 420,
            "position": {"x": 1250, "y": 3500}
          }
        },
        "events": [
          {"type": "CHAMPION_KILL", "killerId": 1, "victimId": 6, "timestamp": 65000}
        ]
      }
    ]
  }
}
```

## 6. Champion ID Mappings

**Utility**: `src/utils/id_mappings.py`

```python
from src.utils.id_mappings import get_champion_name

champ_name = get_champion_name(157)  # → "Yasuo"
```

## 7. Statistical Utilities

**Utility**: `src/core/statistical_utils.py`

```python
from src.core.statistical_utils import wilson_confidence_interval

# Calculate confidence interval for winrate
ci_lo, ci_hi = wilson_confidence_interval(wins, total_games, confidence=0.95)
```

## Summary for Chat Agent Development

**Key Takeaways**:
1. **Primary Data Source**: Player Pack files (`pack_*.json`)
2. **Granularity**: Champion + Role + Patch + Queue
3. **Time Filtering**: Use `time_range` parameter
4. **Queue Filtering**: Use `queue_id` parameter
5. **Fallback**: Use `matches_data.json` for custom queries beyond pack aggregation
6. **Deep Analysis**: Use `timelines/` for frame-by-frame insights

**Recommendation**:
- Start with Player Pack data (covers 90% of use cases)
- Fall back to raw matches only when pack aggregation is insufficient
- Use timelines only for deep-dive specific match analysis
