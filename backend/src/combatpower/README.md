# Riot Rift Rewind Backend

**Comprehensive League of Legends player performance analysis system with multi-patch combat power calculations**

Built for the [Riot Games Rift Rewind Hackathon](https://riftrewind.devpost.com)

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Core Features](#core-features)
- [API Endpoints](#api-endpoints)
- [Combat Power System](#combat-power-system)
- [Testing & Examples](#testing--examples)
- [Project Structure](#project-structure)
- [Data Sources](#data-sources)
- [Configuration](#configuration)
- [License](#license)

---

## Overview

This backend system provides:
- **Player Analysis**: Insights into strengths, weaknesses, and progress
- **Multi-Patch Support**: Track champion power across 26 patches (14.19 - 25.20)
- **Combat Power Calculations**: Unified metric for champion strength
- **Custom Build Analyzer**: Test item combinations across all patches
- **Intelligent Build System**: Automatic build assignment for ALL 171 champions
- **Shareable Summaries**: Fun, social year-end reports

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
```bash
cp .env.example .env
# Edit .env and add your RIOT_API_KEY from https://developer.riotgames.com/
```

### 3. Cache Static Data (IMPORTANT!)
```bash
python fetch_and_cache_data.py
# Type "yes" when prompted
# Downloads 26 patches from Data Dragon (5-10 minutes)
# Only needs to be done once
```

**What gets cached:**
- 168-171 champions per patch × 26 patches
- All abilities, stats, scaling data
- 575+ items per patch
- All rune trees and bonuses

**Why cache?**
- 100x faster than fetching online
- Ensures data accuracy and consistency
- Works offline after caching
- Prevents API rate limiting

### 4. Run Server
```bash
python app.py
# Server starts at http://localhost:5000
# Automatically uses cached data when available
```

### 5. Test It
```bash
# Test all champions across patches
python tests/compare_all_champions.py

# Interactive custom build analyzer
python tests/test_custom_build.py interactive
```

---

## Core Features

### 🎯 Combat Power System

**Unified metric combining all champion attributes:**

```
Total Power = Base Stats + Skills + Items + Runes
```

**Components:**
- **Base Stats**: HP, AD, Armor, MR, AS (level-scaled, patch-specific)
- **Skills**: Q/W/E/R/Passive damage + utility values
- **Items**: Stat bonuses + passive effects (patch-specific stats)
- **Runes**: Primary + Secondary tree bonuses (patch-specific effects)

**Example:**
```python
Draven Level 18 in Patch 14.19:
- Base Stats: 2,145 power (from champion stats)
- Skills: 1,523 power (Q/W/E/R values)
- Items: 2,860 power (IE, BT, PD stats in 14.19)
- Runes: 200 power (Conqueror + secondary)
= Total: 6,728 combat power
```

### 📊 Multi-Patch System

Track changes across **26 patches** from Sept 2024 to Oct 2025:

```
14.19, 14.20, 14.21, 14.22, 14.23, 14.24
25.S1.1, 25.S1.2, 2025.S1.3
25.04, 25.05, 25.06, 25.07, 25.08, 25.09
25.10, 25.11, 25.12, 25.13, 25.14, 25.15
25.16, 25.17, 25.18, 25.19, 25.20
```

**Features:**
- ✅ Automatic patch-specific champion stats
- ✅ Automatic patch-specific item stats  
- ✅ Automatic patch-specific rune effects
- ✅ Automatic match-to-patch mapping
- ✅ Historical power tracking

### 🧪 Custom Build Analyzer

**User picks champion + items, see performance across ALL patches!**

```python
User Flow:
1. Pick Champion → "Draven"
2. Pick Item 1 → Infinity Edge (3031)
3. Pick Item 2 → Bloodthirster (3072)
4. Pick Item 3 → Phantom Dancer (3046)
5. Get Results → Combat power for all 26 patches!

Statistics:
- Average Power: 6,728
- Min Power: 6,728 (Patch 14.19)
- Max Power: 6,728 (Patch 14.24)
- Power Change: +0.0%
```

**Use Cases:**
- Theory craft new builds
- Compare Crit vs Lethality
- Find when a build got nerfed
- Test 3-item core synergies

### 🤖 Intelligent Build System

**Automatic build assignment for ANY champion!**

**3-Tier System:**
```
Tier 1: Manual Builds (Highest Priority)
  ├─ 140+ champions with hand-crafted builds
  └─ Example: Draven, Jinx, Ahri, etc.

Tier 2: Intelligent Auto-Detection (Automatic)
  ├─ Analyzes champion stats (HP, AD, range, etc.)
  ├─ Analyzes champion tags (Mage, Fighter, Tank, etc.)
  ├─ Classifies into 12 build categories
  └─ Assigns appropriate items and runes

Tier 3: Patch-Specific Overrides (Optional)
  ├─ Track when builds change across patches
  └─ Example: Draven switched to Lethality in 14.24
```

**12 Build Categories:**
- ADC_CRIT, ADC_ONHIT
- ASSASSIN_AD, ASSASSIN_AP
- MAGE_BURST, MAGE_BATTLEMAGE
- TANK, TANK_SUPPORT
- FIGHTER_AD, FIGHTER_ONHIT
- SUPPORT_ENCHANTER, SKIRMISHER

**Example:**
```python
# Heimerdinger (not in manual database)
Tags: ['Mage', 'Support']
Range: 550 (ranged)
→ Classified as: MAGE_BURST
→ Build: Liandry's, Shadowflame, Void, Rabadon's, Zhonya's, Sorc Shoes
→ Runes: Arcane Comet (Sorcery + Inspiration)
```

**Result:** ALL 171 champions work automatically! No warnings, no errors.

### 🔍 Intelligent Item Search

**Users never need to memorize item IDs!**

Search items by:
- **Full names**: "Infinity Edge", "Bloodthirster"
- **Abbreviations**: "IE", "BT", "PD", "RFC" (70+ supported)
- **Partial names**: "blood" → Bloodthirster
- **With typos**: "infinty edge" → Infinity Edge
- **Short forms**: "rapid" → Rapid Firecannon

**Examples:**
```python
# All of these work!
"IE" → Infinity Edge
"bloodthirster" → Bloodthirster (typo handled)
"phantom" → Phantom Dancer (partial match)
"bork" → Blade of the Ruined King (abbreviation)
```

**70+ Common Abbreviations:**
```
ADC:     IE, BT, PD, RFC, ER, BORK
Mage:    LIANDRY, DCAP, RABADON, ZHONYA, VOID
Tank:    SUNFIRE, THORNMAIL, VISAGE, RANDUIN
Fighter: GORE, SUNDERER, BC, TRINITY, GA
Boots:   ZERKERS, MERCS, TABIS, SORCS
```

### 📈 Player Analysis

Classify players based on performance:

- **Skill Player**: Low combat power, high win rate (pure mechanics)
- **Meta Player**: High combat power, high win rate (plays strong champions)
- **Meta Follower**: High combat power, low win rate (follows meta but loses)
- **Off-Meta Player**: Low combat power, low win rate

**Flexible Time Ranges:**
- Last N games (10 to 100)
- Last N days (30 to 365)
- Custom date ranges

---

## API Endpoints

### Player Analysis

```python
# Get player summary (flexible range)
GET /api/player/{gameName}/{tagLine}/summary?days=365
GET /api/player/{gameName}/{tagLine}/summary?count=10

# Combat power analysis
GET /api/player/{gameName}/{tagLine}/combat-power

# Player insights
GET /api/player/{gameName}/{tagLine}/insights
```

### Patch-Specific

```python
# List all patches with dates
GET /api/patch/patches

# Champion by patch (with popular build)
GET /api/patch/champion/{name}/patch/{version}

# Player analysis by patch
GET /api/patch/player/{name}/{tag}/analysis?days=90
```

### Custom Build Analyzer

```python
# Analyze custom build across all patches (USES ITEM NAMES!)
POST /api/custom-build/analyze
{
  "champion": "Draven",
  "items": ["IE", "Bloodthirster", "phantom dancer"],  # Names, not IDs!
  "level": 18
}
# Returns: Combat power for each of 26 patches + statistics

# Compare multiple builds
POST /api/custom-build/compare
{
  "champion": "Draven",
  "builds": [
    {"name": "Crit", "items": ["IE", "BT", "PD"]},
    {"name": "Lethality", "items": ["youmuus", "collector", "edge"]}
  ]
}

# Get all items for UI selection
GET /api/custom-build/items/{patch}

# Get specific item details
GET /api/custom-build/item/{item_id}/{patch}
```

### Item Search

```python
# Search for items by name/abbreviation
GET /api/items/search?q=blood&patch=14.19

# Autocomplete suggestions
GET /api/items/suggest?q=blo

# Convert item names to IDs
POST /api/items/convert
{
  "items": ["IE", "Bloodthirster", "phantom dancer"],
  "patch": "14.19"
}
# Returns: {"item_ids": [3031, 3072, 3046], "failed_matches": []}

# List all abbreviations
GET /api/items/abbreviations
```

### Champions

```python
# All champions (baseline patch 14.19)
GET /api/champions

# Champion detail
GET /api/champions/{championName}

# Champion combat power with items
GET /api/champion/{championName}/power?level=18&items=3031,3072,3046
```

### Comparison

```python
# Compare multiple players
POST /api/compare
{
  "players": [
    {"gameName": "Player1", "tagLine": "NA1"},
    {"gameName": "Player2", "tagLine": "NA1"}
  ]
}
```

---

## Testing & Examples

### Run Tests

```bash
# Test all champions across patches
python tests/compare_all_champions.py

# Item search system
python tests/test_item_search.py
python tests/test_item_search.py interactive  # Interactive item search

# Custom build analyzer (with item names!)
python tests/test_custom_build.py
python tests/test_custom_build.py interactive  # Pick items by name
python tests/test_item_name_build.py  # Test with names
python tests/test_item_name_build.py interactive  # Interactive picker

# Patch system tests
python tests/test_patch_system.py

# Specific champion test
python tests/test_draven.py

# Champion across patches
python tests/test_champion_by_patch.py

# Test with meta builds
python tests/test_champion_with_builds.py

# Generate power plots
python tests/plot_champion_power.py Draven
```

### Build Tracking Tools

```bash
# View champion build history
python tools/build_tracker_helper.py view Draven

# Add patch-specific build
python tools/build_tracker_helper.py add Draven 14.24 --items=3142,6676,3814,6691,3036,3111

# Interactive mode
python tools/build_tracker_helper.py interactive

# Generate reports
python tools/build_tracker_helper.py report
```

### API Usage Examples

**Get Last 10 Games:**
```python
import requests

response = requests.get(
    'http://localhost:5000/api/player/S1NE/NA1/summary?count=10'
)
data = response.json()
print(f"Win Rate: {data['analysis']['win_rate']}%")
```

**Compare Champions Across Patches:**
```python
# Draven in 14.19
r1 = requests.get('http://localhost:5000/api/patch/champion/Draven/patch/14.19')
power_14_19 = r1.json()['champion']['total_combat_power']

# Draven in 25.S1.1
r2 = requests.get('http://localhost:5000/api/patch/champion/Draven/patch/25.S1.1')
power_25_S1_1 = r2.json()['champion']['total_combat_power']

print(f"Power change: {power_25_S1_1 - power_14_19}")
```

**Analyze Custom Build (with Item Names):**
```javascript
// Frontend example - uses item NAMES, not IDs!
fetch('http://localhost:5000/api/custom-build/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    champion: 'Draven',
    items: ['IE', 'Bloodthirster', 'phantom dancer'],  // Names!
    level: 18
  })
})
.then(res => res.json())
.then(data => {
  console.log('Item Names:', data.item_names);  // ["Infinity Edge", ...]
  console.log('Average Power:', data.statistics.avg_power);
  console.log('Strongest Patch:', data.statistics.strongest_patch);
  
  // Display patch-by-patch results
  Object.entries(data.patches).forEach(([patch, info]) => {
    console.log(`${patch}: ${info.total_power}`);
  });
});
```

**Search Items (Autocomplete):**
```javascript
// Search as user types
const searchInput = document.getElementById('itemSearch');
searchInput.addEventListener('input', async (e) => {
  const query = e.target.value;
  if (query.length < 2) return;
  
  const response = await fetch(`/api/items/suggest?q=${query}`);
  const data = await response.json();
  
  // Show suggestions dropdown
  showSuggestions(data.suggestions);
});

// Example: User types "blo"
// Returns: [
//   {id: 3072, name: "Bloodthirster", score: 0.8},
//   {id: 3801, name: "Crystalline Bracer", score: 0.3},
//   ...
// ]
```

### Item Abbreviations (Use These Instead of IDs!)

**You don't need to memorize item IDs!** Just use names or abbreviations:

```python
# ADC Items - Use abbreviations or names
"IE" or "infinity edge"      → Infinity Edge (3031)
"BT" or "bloodthirster"      → Bloodthirster (3072)
"PD" or "phantom"            → Phantom Dancer (3046)
"RFC" or "rapid"             → Rapid Firecannon (3094)
"ER" or "essence"            → Essence Reaver (3508)
"BORK" or "blade"            → Blade of the Ruined King (3153)

# Lethality Items
"youmuus" or "ghostblade"    → Youmuu's Ghostblade (3142)
"duskblade"                  → Duskblade of Draktharr (6691)
"collector"                  → The Collector (6676)
"eon" or "edge"              → Edge of Night (3814)

# Mage Items
"liandry" or "liandrys"      → Liandry's Anguish (6653)
"dcap" or "rabadon"          → Rabadon's Deathcap (3089)
"zhonya" or "zhonyas"        → Zhonya's Hourglass (3157)
"shadowflame"                → Shadowflame (4645)
"void" or "voidstaff"        → Void Staff (3135)

# Tank Items
"sunfire"                    → Sunfire Aegis (3068)
"thornmail"                  → Thornmail (3075)
"visage"                     → Spirit Visage (3065)
"randuin" or "randuins"      → Randuin's Omen (3143)

# Fighter Items
"gore" or "goredrinker"      → Goredrinker (6630)
"sunderer" or "divine"       → Divine Sunderer (6632)
"bc" or "cleaver"            → Black Cleaver (3071)
"trinity" or "tf"            → Trinity Force (3078)

# Boots
"zerkers" or "berserkers"    → Berserker's Greaves (3006)
"mercs" or "mercury"         → Mercury's Treads (3111)
"tabis" or "steelcaps"       → Plated Steelcaps (3047)
"sorcs" or "sorcerer"        → Sorcerer's Shoes (3020)
```

**Even typos work!** "infinty edge" → Infinity Edge ✓

---

## Project Structure

```
riot/
├── app.py                          # Main Flask application
├── config.py                       # Configuration
├── requirements.txt                # Python dependencies
│
├── services/                       # Core backend services
│   ├── riot_api.py                # Riot API integration
│   ├── data_dragon.py             # Static game data (online)
│   ├── data_provider.py           # Smart data layer (cache/online)
│   ├── local_data_loader.py       # Load from cached files
│   ├── patch_manager.py           # Patch version management
│   ├── combat_power.py            # Combat power calculator
│   ├── analytics.py               # Player analytics
│   ├── meta_builds.py             # 140+ hand-crafted builds
│   ├── intelligent_build_provider.py  # Auto-detect builds
│   ├── patch_specific_builds.py   # Track build changes
│   ├── custom_build_analyzer.py   # Custom build analysis
│   ├── item_search.py             # Intelligent item search (70+ abbrevs)
│   └── build_tracker.py           # Build tracking utilities
│
├── routes/                         # API routes
│   ├── patch_routes.py            # Patch-specific endpoints
│   ├── custom_build_routes.py     # Custom build endpoints
│   └── item_search_routes.py      # Item search endpoints
│
├── tools/                          # Helper tools
│   └── build_tracker_helper.py    # CLI for managing builds
│
├── data/                           # Local cache (gitignored)
│   └── patches/                    # Cached patch data
│       ├── 14.19/
│       │   ├── champions.json
│       │   ├── items.json
│       │   └── runes.json
│       ├── 14.20/
│       └── ... (26 patches total)
│
└── tests/                          # Test suite
    ├── test_api.py                # API connectivity tests
    ├── test_patch_system.py       # Patch system tests
    ├── test_item_search.py        # Item search tests
    ├── test_custom_build.py       # Custom build tests
    ├── test_item_name_build.py    # Build with item names
    ├── compare_all_champions.py   # Compare all champs
    ├── test_draven.py             # Champion-specific tests
    ├── test_champion_by_patch.py  # Cross-patch comparison
    ├── test_champion_with_builds.py  # Test with builds
    └── plot_champion_power.py     # Visualization
```

---

## Data Sources

### All Data is Official from Riot Games

**Static Game Data (Data Dragon CDN):**
- **Champions**: Stats, abilities, scaling
  - https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json
- **Items**: Stats, effects
  - https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/item.json
- **Runes**: Bonuses, effects
  - https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/runesReforged.json
- **Documentation**: https://developer.riotgames.com/docs/lol#data-dragon

**Player Data (Riot API):**
- **Match History**: Real-time player matches
- **Player Stats**: Summoner info, rankings
- **Requires API Key**: https://developer.riotgames.com/

**Data Accuracy:**
- ✅ 100% official from Riot Games
- ✅ Validated on download (champion count, item count, JSON integrity)
- ✅ Version-specific (each patch has its own data)
- ✅ No third-party aggregation

**Verify Yourself:**
```bash
# Test a URL
curl "https://ddragon.leagueoflegends.com/cdn/14.19.1/data/en_US/champion.json" | python -m json.tool | head -20
```

---

## Configuration

### Environment Variables

Create `.env`:
```env
RIOT_API_KEY=your_key_here
FLASK_ENV=development
FLASK_PORT=5000
REDIS_URL=redis://localhost:6379/0  # Optional
```

### API Rate Limits

- 20 requests per second
- 100 requests per 2 minutes
- Per-region routing limits

### Adding New Patches

When a new patch releases:
```bash
python add_new_patch.py
# Interactive script - enter patch info
# Example: Patch 25.21, date 2025-10-21, Data Dragon 15.21.1
```

The script will:
1. Download data for the new patch only
2. Update `patch_manager.py` automatically
3. Validate all data
4. Make the patch immediately available

---

## Advanced Topics

### What's Automatic vs Manual

**✅ Fully Automatic (No Configuration Needed):**
- Champion stats per patch (HP, AD, Armor, etc.)
- Skill stats per patch (Q/W/E/R damage, cooldowns)
- Item stats per patch (IE damage, BT lifesteal, etc.)
- Rune effects per patch (Conqueror stacks, PTA damage)
- Intelligent build assignment for ANY champion
- Match-to-patch mapping

**⚠️ Optional (For Enhanced Accuracy):**
- Manual builds for specific champions (140+ already included)
- Patch-specific build overrides (track build meta shifts)
- Use `tools/build_tracker_helper.py` to manage

### Build Tracking

**When to track build changes:**
- Item reworks (e.g., tank item update in 14.20)
- Item stat changes > 10%
- New items become meta
- Champion role shifts

**How to track:**
```bash
# Option 1: Interactive
python tools/build_tracker_helper.py interactive

# Option 2: Direct command
python tools/build_tracker_helper.py add Draven 14.24 --items=3142,6676,3814,6691,3036,3111

# Option 3: Edit services/patch_specific_builds.py
```

### For Your Hackathon

**✅ Recommended Approach:**
- Use the system as-is
- All 171 champions work automatically
- Patch-specific data handled automatically
- Optional: Add build tracking for popular champions

**No configuration needed!** The intelligent build system handles everything.

---

## Hackathon Features Checklist

- ✅ Insights into persistent strengths and weaknesses
- ✅ Visualizations of player progress over time
- ✅ Fun, shareable year-end summaries
- ✅ Social comparisons (against friends)
- ✅ Patch-based meta analysis
- ✅ Custom build theory crafting
- ✅ Intelligent champion analysis
- ✅ Multi-patch combat power tracking

---

## License

MIT License

## Credits

Built for the [Riot Games Rift Rewind Hackathon](https://riftrewind.devpost.com)

**All game data sourced from official Riot Games APIs**
