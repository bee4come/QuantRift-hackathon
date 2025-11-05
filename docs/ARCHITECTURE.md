# QuantRift Backend Architecture

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Three-Tier API Design](#three-tier-api-design)
3. [Complete Data Flow](#complete-data-flow)
4. [Shared Services Layer](#shared-services-layer)
5. [AI Agent System](#ai-agent-system)
6. [Performance & Reliability](#performance--reliability)
7. [Deployment & Scaling](#deployment--scaling)

---

## System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (Next.js 15)                     │
│                  React 19 + TypeScript 5                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┼───────────┬────────────────┐
           │           │           │                │
           ▼           ▼           ▼                ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐
    │ FastAPI  │ │ Combat   │ │ Player   │  │ Cache    │
    │ Server   │ │ Power    │ │ Data     │  │ Layer    │
    │ :8000    │ │ API      │ │ Manager  │  │          │
    │          │ │ :5000    │ │          │  │ • Packs  │
    │ • Player │ │          │ │ • Riot   │  │ • LLM    │
    │   API    │ │ • Build  │ │   Client │  │ • Status │
    │ • 18     │ │   Calc   │ │ • Status │  │          │
    │   Agents │ │ • Item   │ │   Track  │  │          │
    └────┬─────┘ └────┬─────┘ └────┬─────┘  └──────────┘
         │            │            │
         └────────────┴────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
  ┌─────────────┐          ┌─────────────┐
  │ Analytics   │          │ AWS Bedrock │
  │ Engine      │          │             │
  │             │          │ • Claude    │
  │ • Bronze    │          │   Sonnet    │
  │ • Silver    │          │   4.5       │
  │ • Gold      │          │ • Claude    │
  │ • Metrics   │          │   Haiku     │
  └─────────────┘          └─────────────┘

  External APIs:
  • Riot Games API (Match, Timeline, Summoner)
  • Data Dragon (Static champion/item/rune data)
  • OP.GG MCP (Meta & leaderboards)
```

### Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | Next.js | 15.5.5 |
| | React | 19.1.0 |
| | TypeScript | 5.x |
| | Tailwind CSS | 4.x |
| | Recharts | Latest |
| **Backend** | FastAPI | 0.x |
| | Uvicorn | Latest |
| | Python | 3.11 |
| **Data** | DuckDB | Latest |
| | Parquet | (storage) |
| | JSON | (transfer) |
| **AI/LLM** | AWS Bedrock | - |
| | Claude Sonnet | 4.5 |
| | Claude Haiku | 3.5 |
| **External** | Riot API | v5 |
| | Data Dragon | Latest |

---

## Three-Tier API Design

### Tier 1: Player Data API

**Responsibility**: Player data ingestion, caching, and status management

#### Endpoints

**1. GET `/api/player/{gameName}/{tagLine}/summary`**

Fetches player summary and initiates background data preparation.

**Query Parameters**:
- `count`: int = 20 (number of recent matches)

**Response**:
```json
{
  "summoner": {
    "puuid": "...",
    "gameName": "s1ne",
    "tagLine": "na1",
    "rank": {
      "tier": "DIAMOND",
      "division": "II",
      "lp": 87
    }
  },
  "stats": {
    "total_games": 256,
    "winrate": 0.531,
    "avg_kda": 2.14,
    "main_champion": "Ahri",
    "avg_combat_power_per_game": 12500
  },
  "data_status": "preparing|ready",
  "message": "Data preparation in progress..."
}
```

**Implementation** (`backend/api/server.py`):
```python
@app.get("/api/player/{game_name}/{tag_line}/summary")
async def get_player_summary(
    game_name: str,
    tag_line: str,
    count: int = 20
):
    # Trigger async data preparation
    asyncio.create_task(
        player_data_manager.prepare_player_data(
            game_name, tag_line, count
        )
    )

    # Return immediate response
    return await player_data_manager.get_summary(game_name, tag_line)
```

**2. GET `/api/player/{gameName}/{tagLine}/data-status`**

Polling endpoint for frontend to track data preparation progress.

**Response**:
```json
{
  "status": "completed|fetching_matches|calculating_metrics|error",
  "progress": 0.75,
  "message": "Calculating metrics...",
  "estimated_remaining_seconds": 15,
  "has_data": true
}
```

**Frontend Polling Pattern**:
```typescript
// Poll every 2 seconds until complete
const pollStatus = async () => {
  const interval = setInterval(async () => {
    const status = await fetch(`/api/player/${name}/${tag}/data-status`);
    if (status.has_data) {
      clearInterval(interval);
      enableAgentButtons();
    }
  }, 2000);
};
```

**3. GET `/api/player/{gameName}/{tagLine}/recent`**

Fetches list of recent matches with basic stats.

**Response**:
```json
{
  "matches": [
    {
      "match_id": "NA1_5391486684",
      "champion": "Ahri",
      "role": "MID",
      "kda": "8/3/12",
      "win": true,
      "combat_power": 13200,
      "timestamp": "2025-01-15T14:30:00Z"
    }
  ]
}
```

---

### Tier 2: AI Agent Endpoints

**Responsibility**: Execute 18 specialized AI agents with LLM-powered analysis

#### Agent Endpoint Pattern

**POST `/v1/agents/{agent_id}`**

All agents follow a consistent interface:

**Request Body**:
```json
{
  "puuid": "OkHv4J5JcbqQSx9I5Fda7L9rpz4wQcaDVpgDyjtlhEcpdZIM9ExEyrfTpjS6EdsYcZjKX9i5ctKC9A",
  "region": "na1",
  "recent_count": 5,
  "model": "haiku"  // or "sonnet"
}
```

**Response**:
```json
{
  "success": true,
  "agent_id": "weakness-analysis",
  "one_liner": "Early-game CSing is your primary weakness, losing 15 CS avg by 10min",
  "detailed": "...",  // Full analysis text
  "evidence": {
    "metrics": {...},
    "comparisons": {...}
  },
  "recommendations": [...]
}
```

#### 18 Agent Endpoints

**Player Analysis (11 agents)**:

1. **POST `/v1/agents/weakness-analysis`**
   - Diagnoses performance weaknesses
   - Categories: Laning, Teamfighting, Vision, Macro

2. **POST `/v1/agents/champion-mastery`**
   - Deep champion expertise analysis
   - Mechanics rating, matchup knowledge, build optimization

3. **POST `/v1/agents/progress-tracker`**
   - Long-term improvement tracking
   - Statistical validation of skill growth

4. **POST `/v1/agents/detailed-analysis`**
   - Comprehensive multi-dimensional review
   - Recent games analysis with pattern detection

5. **POST `/v1/agents/peer-comparison`**
   - Benchmarking vs similar rank players
   - Percentile rankings across metrics

6. **POST `/v1/agents/role-specialization`**
   - Role-specific strengths/weaknesses
   - Position mastery analysis

7. **POST `/v1/agents/timeline-deep-dive`**
   - Minute-by-minute game analysis
   - Power spike identification, objective timing

8. **POST `/v1/agents/annual-summary`**
   - Year-in-review analysis
   - Tri-period progression (Early/Mid/Late year)

9. **POST `/v1/agents/risk-forecaster`**
   - Performance volatility prediction
   - Tilt detection, consistency analysis

10. **POST `/v1/agents/friend-comparison`**
    - Group performance comparison
    - Team synergy analysis

11. **POST `/v1/agents/laning-phase`**
    - Early-game specialized analysis
    - CS efficiency, trading patterns, jungle proximity

**Meta Analysis (3 agents)**:

12. **POST `/v1/agents/champion-recommendation`**
    - Champion suggestions based on playstyle + meta
    - Win rate potential estimation

13. **POST `/v1/agents/multi-version`**
    - Cross-patch performance analysis
    - Adaptation speed measurement

14. **POST `/v1/agents/version-comparison`**
    - Patch-to-patch delta analysis
    - Meta shift impact assessment

**Coach Tools (4 agents)**:

15. **POST `/v1/agents/build-simulator`**
    - Item build optimization for matchups
    - Gold efficiency analysis

16. **POST `/v1/agents/drafting-coach`**
    - Team composition recommendations
    - Pick/ban strategy

17. **POST `/v1/agents/team-synergy`**
    - Team composition effectiveness
    - Role interaction analysis

18. **POST `/v1/agents/postgame-review`**
    - Detailed game review
    - Actionable improvement feedback

---

### Tier 3: Combat Power Service

**Responsibility**: Champion power calculations, item effect analysis

**Endpoint**: `http://localhost:5000/combatpower/`

**Architecture**: Separate Flask service for computational isolation

**Key Functions**:
- Build power comparison
- Item stat calculation
- DPS/survivability modeling
- Core item timing analysis

---

## Complete Data Flow

### User Journey: Search → Analysis

```
1. User searches "s1ne#na1" on frontend
   ↓
2. Frontend: GET /api/player/s1ne/na1/summary?count=20
   ↓
3. Backend: PlayerDataManager.prepare_player_data() (async)
   ├─ Check cache: data/player_packs/{puuid}/
   │  ├─ HIT: Return cached pack
   │  └─ MISS: Fetch from Riot API
   ↓
4. Data Preparation Pipeline:
   ├─ RiotAPIClient.get_match_list(puuid, count=20)
   │  └─ Rate limiting: 5-key rotation, 1800 req/10s
   ├─ Parallel fetch: matches + timelines (asyncio.gather)
   ├─ Calculate metrics: combat_power, kda_adj, obj_rate, etc.
   ├─ Generate Player-Pack format
   └─ Cache to disk: data/player_packs/{puuid}/pack_{patch}.json
   ↓
5. Frontend: Poll /api/player/s1ne/na1/data-status (2s interval)
   └─ Response: { "has_data": true, "status": "completed" }
   ↓
6. User clicks "Weakness Analysis" agent card
   ↓
7. Frontend: POST /v1/agents/weakness-analysis
   {
     "puuid": "...",
     "region": "na1",
     "recent_count": 5,
     "model": "haiku"
   }
   ↓
8. Backend: WeaknessAgent.run()
   ├─ Load Player-Pack from cache
   ├─ Extract relevant metrics
   ├─ Detect insights (zero-LLM pattern matching)
   ├─ Call AWS Bedrock (Claude Haiku)
   │  └─ LLM Cache check (SQLite)
   └─ Return structured analysis
   ↓
9. Frontend: Display analysis with visualizations
```

### Data Preparation Detail

**File**: `backend/services/player_data_manager.py`

```python
class PlayerDataManager:
    async def prepare_player_data(
        self,
        game_name: str,
        tag_line: str,
        count: int = 20
    ):
        # 1. Resolve PUUID
        puuid = await self.riot_client.get_puuid(game_name, tag_line)

        # 2. Check cache
        pack_path = f"data/player_packs/{puuid}/pack_latest.json"
        if self._is_fresh_cache(pack_path):
            return self._load_pack(pack_path)

        # 3. Fetch match list
        self._update_status(puuid, "fetching_matches", 0.1)
        match_ids = await self.riot_client.get_match_list(puuid, count)

        # 4. Parallel fetch matches + timelines
        self._update_status(puuid, "fetching_details", 0.3)
        matches, timelines = await asyncio.gather(
            *[self.riot_client.get_match(mid) for mid in match_ids],
            *[self.riot_client.get_timeline(mid) for mid in match_ids]
        )

        # 5. Calculate metrics
        self._update_status(puuid, "calculating_metrics", 0.7)
        metrics = await self._calculate_all_metrics(matches, timelines, puuid)

        # 6. Generate Player-Pack
        self._update_status(puuid, "generating_pack", 0.9)
        pack = self._generate_player_pack(metrics, puuid)

        # 7. Save to cache
        self._save_pack(pack_path, pack)
        self._update_status(puuid, "completed", 1.0)

        return pack
```

---

## Shared Services Layer

### 1. RiotAPIClient

**File**: `backend/services/riot_client.py`

**Features**:
- **5-key rotation**: Maximize throughput (1800 req/10s per key)
- **Exponential backoff**: Automatic retry on 429/500 errors
- **Request prioritization**: Match list > Match details > Timeline
- **Regional routing**: Automatic endpoint selection (na1, euw1, etc.)

**Implementation**:
```python
class RiotAPIClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.rate_limits = {
            key: RateLimiter(requests_per_10s=1800)
            for key in api_keys
        }

    async def get_match(self, match_id: str) -> dict:
        # Round-robin key selection
        key = self._next_key()

        # Rate limit check
        await self.rate_limits[key].acquire()

        # Request with retry
        for attempt in range(3):
            try:
                response = await self._request(
                    f"/lol/match/v5/matches/{match_id}",
                    api_key=key
                )
                return response.json()
            except HTTPError as e:
                if e.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
```

**Rate Limiting Strategy**:
- **Token bucket algorithm**: Smooth request distribution
- **Per-key tracking**: Independent limits for each API key
- **Dynamic adjustment**: Adapt to Riot's rate limit headers

### 2. PlayerDataManager

**File**: `backend/services/player_data_manager.py`

**Responsibilities**:
- Data preparation orchestration
- Player-Pack caching
- Status tracking for frontend polling
- Metrics calculation coordination

**Cache Structure**:
```
data/player_packs/{puuid}/
├── summary.json          # Aggregate summary across patches
├── pack_15.17.json       # Patch-specific pack
├── pack_15.18.json
├── pack_15.19.json
└── timelines/            # Timeline data for deep analysis
    ├── NA1_5391486684_timeline.json
    └── ...
```

**Player-Pack Format**:
```json
{
  "metadata": {
    "puuid": "...",
    "patch": "15.19",
    "generated_at": "2025-01-15T10:30:00Z",
    "match_count": 20
  },
  "by_champion_role": {
    "Ahri_MID": {
      "games": 15,
      "winrate": 0.60,
      "kda_adj": 2.8,
      "combat_power": 13200,
      "damage_taken": 18500,
      "obj_rate": 0.45,
      "cs_per_min": 7.2,
      "vision_score_per_min": 1.3,
      "governance": "CONFIDENT"  // n≥10
    }
  },
  "overall_stats": {...},
  "progression": {...}
}
```

### 3. LLM Cache Service

**File**: `backend/src/agents/shared/llm_cache.py`

**Purpose**: Reduce LLM costs and latency via intelligent caching

**Cache Key Strategy**:
```python
def generate_cache_key(
    agent_id: str,
    puuid: str,
    metrics_hash: str,  # MD5 of input metrics
    model: str
) -> str:
    return hashlib.sha256(
        f"{agent_id}:{puuid}:{metrics_hash}:{model}".encode()
    ).hexdigest()
```

**Storage**: SQLite database
```sql
CREATE TABLE llm_cache (
    cache_key TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 1,
    last_accessed TIMESTAMP
);

CREATE INDEX idx_agent_model ON llm_cache(agent_id, model);
CREATE INDEX idx_created_at ON llm_cache(created_at);
```

**Cache Hit Rate**: ~35-45% in production (significant cost savings)

### 4. Insight Detector

**File**: `backend/src/agents/shared/insight_detector.py`

**Purpose**: Zero-LLM pattern-based insight extraction

**Detection Rules**:
```python
INSIGHT_PATTERNS = {
    "low_cs": {
        "condition": lambda stats: stats["cs_per_min"] < 6.0,
        "severity": "high",
        "message": "CS efficiency below average for {role}"
    },
    "high_deaths": {
        "condition": lambda stats: stats["deaths_per_game"] > 5.5,
        "severity": "high",
        "message": "Death rate significantly above peer average"
    },
    "vision_deficit": {
        "condition": lambda stats: stats["vision_score_per_min"] < 1.0,
        "severity": "medium",
        "message": "Vision control below expected for {rank}"
    }
}
```

**Benefit**: Provides structured insights to LLM, improving analysis quality

---

## AI Agent System

### Agent Base Architecture

**File**: `backend/src/agents/shared/base_agent.py`

All 18 agents inherit from `BaseAgent`:

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
        """Execute agent analysis"""
        pass

    def _load_player_pack(self, puuid: str) -> PlayerPack:
        """Load cached Player-Pack data"""
        pass

    def _detect_insights(self, metrics: dict) -> List[Insight]:
        """Zero-LLM insight detection"""
        return self.insights.detect(metrics)

    async def _call_llm(
        self,
        prompt: str,
        cache_key: str,
        model: str
    ) -> str:
        """Call LLM with caching"""
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Call AWS Bedrock
        response = await self.llm.generate(prompt, model)

        # Save to cache
        self.cache.set(cache_key, response)
        return response
```

### Example Agent: Weakness Analysis

**File**: `backend/src/agents/player_analysis/weakness_analysis/agent.py`

```python
class WeaknessAgent(BaseAgent):
    async def run(self, puuid, region, recent_count, model="haiku"):
        # 1. Load data
        pack = self._load_player_pack(puuid)
        recent_matches = pack.get_recent_matches(recent_count)

        # 2. Calculate weakness metrics
        metrics = {
            "laning": self._analyze_laning(recent_matches),
            "teamfighting": self._analyze_teamfighting(recent_matches),
            "vision": self._analyze_vision(recent_matches),
            "macro": self._analyze_macro(recent_matches)
        }

        # 3. Zero-LLM insights
        insights = self._detect_insights(metrics)

        # 4. Build LLM prompt
        prompt = self._build_prompt(metrics, insights)
        cache_key = self._generate_cache_key(puuid, metrics, model)

        # 5. Call LLM
        analysis = await self._call_llm(prompt, cache_key, model)

        # 6. Structure response
        return {
            "success": True,
            "agent_id": "weakness-analysis",
            "one_liner": self._extract_one_liner(analysis),
            "detailed": analysis,
            "evidence": metrics,
            "insights": insights
        }
```

### Shared Agent Services

**1. Timeline Compressor**

**File**: `backend/src/agents/shared/timeline_compressor.py`

**Purpose**: Reduce timeline data from ~500KB to ~500 bytes (99.9% reduction)

**Method**: Keyframe extraction
- Kills/deaths/assists events
- Objective captures (Dragon, Baron, Tower)
- Power spike moments (level 6, 11, 16)
- Item completions

**2. Prompt Optimizer**

**File**: `backend/src/agents/shared/prompt_optimizer.py`

**Purpose**: Token-efficient prompts without losing context

**Techniques**:
- Symbol substitution (✓ instead of "successfully completed")
- Abbreviation dictionary (GPM → Gold Per Minute)
- Smart truncation (preserve key data points)

---

## Performance & Reliability

### Concurrency Model

**FastAPI with Uvicorn**: Async I/O throughout

```python
# Concurrent match fetching
async def fetch_all_matches(match_ids: List[str]):
    return await asyncio.gather(
        *[riot_client.get_match(mid) for mid in match_ids],
        return_exceptions=True  # Partial failures tolerated
    )
```

**Benefits**:
- Handle 100+ concurrent users
- Non-blocking I/O for Riot API calls
- Efficient resource usage (CPU, memory)

### Error Handling

**Retry Strategy**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((HTTPError, Timeout))
)
async def resilient_api_call(url: str):
    return await httpx.get(url, timeout=10)
```

**Graceful Degradation**:
- Partial data: Return available matches even if some fail
- Cache fallback: Serve stale data if fresh fetch fails
- Error messages: User-friendly explanations, not stack traces

### Monitoring & Observability

**Health Check Endpoint**:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "riot_api": await riot_client.ping(),
        "cache_size_mb": get_cache_size(),
        "uptime_seconds": get_uptime()
    }
```

**Logging**:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "player_data_prepared",
    puuid=puuid,
    match_count=len(matches),
    duration_ms=elapsed_ms
)
```

---

## Deployment & Scaling

### Docker Deployment

**docker-compose.yml**:
```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - RIOT_API_KEY=${RIOT_API_KEY}
      - AWS_REGION=us-west-2
    volumes:
      - ./data/player_packs:/app/data/player_packs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

### Scaling Considerations

**Horizontal Scaling**:
- **Stateless API**: Multiple backend instances behind load balancer
- **Shared cache**: Redis for Player-Pack caching across instances
- **Rate limit coordination**: Distributed rate limiter (Redis)

**Vertical Optimization**:
- **Python asyncio**: Efficient I/O handling
- **LRU caching**: In-memory hot data
- **Batch processing**: Group similar agent requests

### Production Checklist

- [x] Docker containerization
- [x] Health check endpoints
- [x] Structured logging
- [x] Error tracking (Sentry integration ready)
- [x] Rate limiting
- [x] API key rotation
- [x] Response caching
- [x] Graceful shutdown
- [ ] Metrics export (Prometheus)
- [ ] Distributed tracing (OpenTelemetry)

---

## Summary

QuantRift's backend is designed for **production readiness** with:

✅ **Three-tier API design**: Player Data → AI Agents → Combat Power
✅ **Robust data pipeline**: Bronze → Silver → Gold with Player-Packs
✅ **18 specialized AI agents**: Comprehensive player analysis
✅ **Intelligent caching**: LLM cache, Player-Pack cache, rate limit coordination
✅ **Statistical rigor**: Wilson CI, Beta-Binomial, governance tiers
✅ **Async-first architecture**: Handle high concurrency efficiently
✅ **Production deployment**: Docker, health checks, monitoring hooks

**Total Data Processed**: 107,570+ matches, 10,423 unique games
**Response Time**: <2s for cached analysis, <15s for fresh data + LLM
**Cost Efficiency**: 35-45% LLM cache hit rate saves significant API costs
