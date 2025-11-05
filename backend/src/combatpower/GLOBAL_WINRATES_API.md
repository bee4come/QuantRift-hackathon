# Global Win Rates API Documentation

## Overview

The Global Win Rates API provides champion position statistics including win rates, pick rates, and ban rates for all champions across different roles. Data is sourced from OP.GG's global statistics API.

### Which Endpoint Should I Use?

- **`/api/champions/leaderboard`** - Use this for the **Live Meta Tier list**
  - Provides official OP.GG tier rankings (S, A, B, C, D)
  - Returns champions sorted by rank
  - Supports position filtering (TOP, JUNGLE, MID, ADC, SUPPORT)
  - Best for displaying tier lists like OP.GG

- **`/api/champions/global-winrates`** - Use this for comprehensive champion data
  - Returns all champions with their statistics across all positions
  - Includes primary lane calculation
  - Best for champion lookup, comparisons, and analytics

- **`/api/champions/<champion>/positions`** - Use this for individual champion details
  - Returns position statistics for a specific champion
  - Best for champion detail pages

## API Endpoints

### 1. Get All Champion Win Rates

**Endpoint:** `GET /api/champions/global-winrates`

Retrieves win rate data for all champions across all positions.

**Query Parameters:**
- `refresh` (optional): Force refresh from OP.GG API instead of using cache
  - Values: `true` or `false` (default: `false`)

**Example Request:**
```bash
# Get cached data
curl http://localhost:5000/api/champions/global-winrates

# Force refresh from OP.GG
curl http://localhost:5000/api/champions/global-winrates?refresh=true
```

**Example Response:**
```json
{
  "success": true,
  "patch": "15.20",
  "region": "global",
  "tier": "all",
  "total_champions": 55,
  "champions": {
    "Yasuo": {
      "MID": {
        "win_rate": 50.04,
        "pick_rate": 10.2,
        "ban_rate": 21.24,
        "tier": "S",
        "rank": 23
      }
    },
    "Morgana": {
      "MID": {
        "win_rate": 52.9,
        "pick_rate": 5.05,
        "ban_rate": 31.84,
        "tier": "S",
        "rank": 1
      },
      "SUPPORT": {
        "win_rate": 51.73,
        "pick_rate": 9.1,
        "ban_rate": 31.85,
        "tier": "S",
        "rank": 11
      }
    }
  },
  "primary_lanes": {
    "Yasuo": "MID",
    "Morgana": "MID"
  }
}
```

### 2. Get Champion Leaderboard (Official Tier List)

**Endpoint:** `GET /api/champions/leaderboard`

Retrieves the official OP.GG champion leaderboard with tier rankings. This is the primary endpoint for the Live Meta Tier list.

**Query Parameters:**
- `position` (optional): Filter by position - `top`, `jungle`, `mid`, `adc`, `support`, or `all` (default: `all`)
- `refresh` (optional): Force refresh from OP.GG API instead of using cache
  - Values: `true` or `false` (default: `false`)

**Example Request:**
```bash
# Get all champions leaderboard
curl http://localhost:5000/api/champions/leaderboard

# Get Mid lane leaderboard
curl http://localhost:5000/api/champions/leaderboard?position=mid

# Force refresh jungle leaderboard
curl http://localhost:5000/api/champions/leaderboard?position=jungle&refresh=true
```

**Example Response:**
```json
{
  "success": true,
  "position": "MID",
  "total_entries": 20,
  "leaderboard": {
    "data": [
      {
        "champion_name": "Morgana",
        "position": "MID",
        "win_rate": 52.9,
        "pick_rate": 5.05,
        "ban_rate": 31.84,
        "tier": "S",
        "rank": 1
      },
      {
        "champion_name": "Veigar",
        "position": "MID",
        "win_rate": 51.88,
        "pick_rate": 6.0,
        "ban_rate": 2.72,
        "tier": "S",
        "rank": 9
      }
    ],
    "patch": "15.20",
    "region": "global",
    "tier": "all",
    "position": "MID"
  }
}
```

### 3. Get Champion Position Statistics

**Endpoint:** `GET /api/champions/<champion_name>/positions`

Retrieves position statistics for a specific champion.

**Path Parameters:**
- `champion_name`: Name of the champion (case-sensitive)

**Example Request:**
```bash
curl http://localhost:5000/api/champions/Yasuo/positions
```

**Example Response:**
```json
{
  "success": true,
  "champion": "Yasuo",
  "primary_lane": "MID",
  "positions": {
    "MID": {
      "win_rate": 50.04,
      "pick_rate": 10.2,
      "ban_rate": 21.24,
      "tier": "S",
      "rank": 23
    }
  }
}
```

## Data Structure

### Champion Position Data

Each champion position entry contains:

- `win_rate` (float): Win rate percentage (0-100)
- `pick_rate` (float): Pick rate percentage (0-100)
- `ban_rate` (float): Ban rate percentage (0-100)
- `tier` (string): Tier ranking (S, A, B, C, D)
- `rank` (integer): Overall rank among all champions in that position

### Primary Lanes

The `primary_lanes` object maps each champion to their most popular/successful lane, determined by:
- Win rate × Pick rate score
- Used when displaying champions in "ALL" lane filter

## Position Names

The API uses standardized position names:
- `TOP`: Top lane
- `JUNGLE`: Jungle
- `MID`: Mid lane
- `ADC`: Bot lane (AD Carry)
- `SUPPORT`: Support

## Tier System

The leaderboard endpoint provides official OP.GG tier rankings:

- **S Tier**: Top performers with excellent win rates and strong pick rates
- **A Tier**: Strong champions with good win rates
- **B Tier**: Balanced champions with average performance
- **C Tier**: Below-average performers
- **D Tier**: Weak champions requiring buffs

Tier assignments are based on a combination of:
- Win rate percentage
- Pick rate (popularity)
- Ban rate (threat level)
- Overall performance in ranked games

The `rank` field indicates the champion's overall ranking within their position (lower is better).

## Caching

Win rate data is cached locally to reduce API calls and improve performance:

- **Cache File:** `combatpower/data/opgg_winrates.json`
- **Auto-refresh:** Cache is used by default unless `refresh=true` is specified
- **Manual Refresh:** Use the `refresh=true` parameter to force update from OP.GG

## Data Source

Win rate data is fetched from OP.GG's internal statistics API:
- **API:** `https://op.gg/api/v1.0/internal/bypass/statistics/global/champions/15.20/ranked`
- **Region:** Global
- **Tier:** All ranks
- **Patch:** 15.20 (automatically updated)

## Usage Example in Frontend

```typescript
// Fetch champion leaderboard for Live Meta Tier (recommended)
const leaderboardResponse = await fetch('/api/combatpower/champions/leaderboard?position=mid');
const leaderboardData = await leaderboardResponse.json();

if (leaderboardData.success) {
  const champions = leaderboardData.leaderboard.data;
  
  // Display tier list
  champions.forEach((champ, index) => {
    console.log(`#${index + 1}: ${champ.champion_name} - ${champ.tier} Tier`);
    console.log(`  WR: ${champ.win_rate}%, PR: ${champ.pick_rate}%, BR: ${champ.ban_rate}%`);
  });
}

// Fetch all positions leaderboard
const allLanesResponse = await fetch('/api/combatpower/champions/leaderboard?position=all');
const allLanesData = await allLanesResponse.json();

// Group by position
const byPosition = {};
allLanesData.leaderboard.data.forEach(entry => {
  if (!byPosition[entry.position]) byPosition[entry.position] = [];
  byPosition[entry.position].push(entry);
});

// Fetch global win rates (alternative approach)
const response = await fetch('/api/combatpower/champions/global-winrates');
const data = await response.json();

if (data.success) {
  const champions = data.champions;
  const primaryLanes = data.primary_lanes;
  
  // Display champion win rates by position
  Object.entries(champions).forEach(([champName, positions]) => {
    console.log(`${champName} (Primary: ${primaryLanes[champName]})`);
    Object.entries(positions).forEach(([lane, stats]) => {
      console.log(`  ${lane}: ${stats.win_rate}% WR, ${stats.pick_rate}% PR, Tier: ${stats.tier}`);
    });
  });
}

// Fetch specific champion
const yasuo = await fetch('/api/combatpower/champions/Yasuo/positions');
const yasuoData = await yasuo.json();
console.log(yasuoData.primary_lane); // "MID"
console.log(yasuoData.positions.MID.win_rate); // 50.04
console.log(yasuoData.positions.MID.tier); // "S"
```

## Error Handling

### 404 Not Found
```json
{
  "success": false,
  "error": "Champion Yasuo not found"
}
```

### 500 Server Error
```json
{
  "success": false,
  "error": "Error message details"
}
```

## Notes

- Win rates are updated periodically from OP.GG
- Data represents global statistics across all tiers
- Primary lane is calculated based on win rate × pick rate
- Champions may appear in multiple positions
- Cache should be refreshed after new patches

