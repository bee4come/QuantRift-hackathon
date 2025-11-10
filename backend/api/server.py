"""
Rift Rewind API Server - FastAPI Implementation
Provides RESTful API endpoints for Risk Forecaster and Annual Summary agents
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import threading
import json
import subprocess
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.player_analysis.risk_forecaster.agent import RiskForecasterAgent
from src.agents.player_analysis.annual_summary.agent import AnnualSummaryAgent

# Import combatpower services
from services.riot_client import riot_client
from src.combatpower.services.analytics import player_analytics
from src.combatpower.services.combat_power import combat_power_calculator
from src.combatpower.services.data_dragon import data_dragon
from src.combatpower.services.item_search import item_search
from src.combatpower.services.patch_manager import patch_manager
from src.combatpower.services.multi_patch_data import multi_patch_data
from src.combatpower.services.build_tracker import build_tracker
from src.combatpower.custom_build_manager import custom_build_manager
from services.player_data_manager import player_data_manager, DataStatus
from services.opgg_mcp_service import opgg_mcp_service
from services.report_cache import report_cache
import requests
import os
import time as time_module
import threading
from collections import defaultdict

# ============================================================================
# Response Cache for API endpoints
# ============================================================================

class ResponseCache:
    """Simple in-memory response cache with TTL"""

    def __init__(self, ttl_seconds: int = 30):
        self.cache = {}
        self.ttl = ttl_seconds
        self.lock = threading.Lock()

    def get(self, key: str):
        """Get cached response if not expired"""
        with self.lock:
            if key in self.cache:
                data, timestamp = self.cache[key]
                if time_module.time() - timestamp < self.ttl:
                    print(f"✅ Cache HIT for {key}")
                    return data
                else:
                    print(f"⏰ Cache EXPIRED for {key}")
                    del self.cache[key]
            return None

    def set(self, key: str, data: Any):
        """Cache response with current timestamp"""
        with self.lock:
            self.cache[key] = (data, time_module.time())
            print(f"💾 Cached response for {key}")

    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()

# Initialize response cache
response_cache = ResponseCache(ttl_seconds=30)

# Initialize FastAPI app
app = FastAPI(
    title="Rift Rewind API",
    description="League of Legends Player Analysis API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request/Response Models
# ============================================================================

class ChampionComposition(BaseModel):
    """Champion composition for a team"""
    champion_id: int = Field(..., description="Champion ID (e.g., 92 for Riven)")
    role: str = Field(..., description="Role: TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY")
    summoner_id: Optional[str] = Field(None, description="Summoner ID (optional)")


class TeamComposition(BaseModel):
    """Team composition"""
    composition: List[ChampionComposition] = Field(..., description="List of 5 champions")


class RiskForecastRequest(BaseModel):
    """Risk Forecaster API Request"""
    match_id: str = Field(..., description="Match ID", example="NA1_1234567890")
    our_team: TeamComposition = Field(..., description="Our team composition")
    enemy_team: TeamComposition = Field(..., description="Enemy team composition")
    include_visualizations: bool = Field(True, description="Include visualization data")
    language: str = Field("en", description="Output language", example="en")

    class Config:
        schema_extra = {
            "example": {
                "match_id": "NA1_1234567890",
                "our_team": {
                    "composition": [
                        {"champion_id": 92, "role": "MIDDLE"},
                        {"champion_id": 67, "role": "TOP"},
                        {"champion_id": 10, "role": "JUNGLE"},
                        {"champion_id": 145, "role": "BOTTOM"},
                        {"champion_id": 236, "role": "UTILITY"}
                    ]
                },
                "enemy_team": {
                    "composition": [
                        {"champion_id": 157, "role": "MIDDLE"},
                        {"champion_id": 122, "role": "TOP"},
                        {"champion_id": 64, "role": "JUNGLE"},
                        {"champion_id": 222, "role": "BOTTOM"},
                        {"champion_id": 412, "role": "UTILITY"}
                    ]
                },
                "include_visualizations": True,
                "language": "en"
            }
        }


class PowerCurvePoint(BaseModel):
    """Single point in power curve"""
    minute: int
    our_power: float
    enemy_power: float
    power_diff: float
    risk_level: str


class RiskForecastResponse(BaseModel):
    """Risk Forecaster API Response"""
    match_id: str
    timestamp: str
    analysis_version: str = "2.1.0"
    overview: Dict[str, Any]
    power_curve: Dict[str, Any]
    key_milestones: List[Dict[str, Any]]
    phase_tactics: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    decision_checklist: Dict[str, Any]
    victory_path: Dict[str, Any]
    final_reminder: Dict[str, str]


class AnnualSummaryRequest(BaseModel):
    """Annual Summary API Request (Query Parameters)"""
    region: str = Field("na1", description="Region code", example="na1")
    start_patch: str = Field(..., description="Start patch version", example="15.12")
    end_patch: str = Field(..., description="End patch version", example="15.20")
    include_visualizations: bool = Field(True, description="Include visualization data")
    language: str = Field("en", description="Output language")
    detail_level: str = Field("comprehensive", description="Detail level: basic, standard, comprehensive")


class AnnualSummaryResponse(BaseModel):
    """Annual Summary API Response"""
    summoner_id: str
    summoner_name: str
    region: str
    season_id: str
    analysis_timestamp: str
    season_overview: Dict[str, Any]
    temporal_evolution: Dict[str, Any]
    version_adaptation: Dict[str, Any]
    champion_pool_evolution: Dict[str, Any]
    annual_highlights: Dict[str, Any]
    future_outlook: Dict[str, Any]
    conclusion: Dict[str, str]


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Rift Rewind API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "risk_forecaster": "/v1/risk-forecaster/analyze",
            "annual_summary": "/v1/annual-summary/{summoner_id}",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "risk_forecaster": "ready",
            "annual_summary": "ready"
        }
    }


@app.post("/v1/risk-forecaster/analyze", response_model=RiskForecastResponse)
async def analyze_match_risk(request: RiskForecastRequest):
    """
    Analyze match risk and generate power curve predictions

    This endpoint analyzes team compositions to predict power curves,
    identify key time windows, and provide tactical recommendations.

    **Processing time**: ~5-10 seconds (includes LLM generation)

    **Returns**:
    - Power curve data (minute-by-minute battle power)
    - Key milestone analysis (critical time windows)
    - Phase-specific tactical recommendations
    - Risk assessment and mitigation strategies
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 Risk Forecast Request: {request.match_id}")
        print(f"{'='*60}")

        # Convert request to agent format
        our_composition = [
            {"champion_id": c.champion_id, "role": c.role}
            for c in request.our_team.composition
        ]
        enemy_composition = [
            {"champion_id": c.champion_id, "role": c.role}
            for c in request.enemy_team.composition
        ]

        # Initialize agent
        agent = RiskForecasterAgent()

        # Run analysis
        result = agent.run(
            our_composition=our_composition,
            enemy_composition=enemy_composition,
            output_dir=None  # Don't save to disk for API calls
        )

        # Transform to API response format
        analysis = result['analysis']

        # Build power curve data
        power_curve_data = {
            "time_series": [],
            "crossover_point": None
        }

        # Generate time series data points
        for minute in range(0, 45, 5):
            our_power = analysis['power_curves']['our_team'].get(minute, 0)
            enemy_power = analysis['power_curves']['enemy_team'].get(minute, 0)
            power_diff = our_power - enemy_power

            # Determine risk level
            if power_diff < -10:
                risk_level = "critical"
            elif power_diff < -5:
                risk_level = "high"
            elif power_diff < -2:
                risk_level = "medium"
            elif power_diff < 2:
                risk_level = "neutral"
            elif power_diff < 5:
                risk_level = "advantage"
            else:
                risk_level = "strong_advantage"

            power_curve_data["time_series"].append({
                "minute": minute,
                "our_power": round(our_power, 1),
                "enemy_power": round(enemy_power, 1),
                "power_diff": round(power_diff, 1),
                "risk_level": risk_level
            })

        # Find crossover point (where power_diff changes from negative to positive)
        for i, point in enumerate(power_curve_data["time_series"]):
            if i > 0 and power_curve_data["time_series"][i-1]["power_diff"] < 0 and point["power_diff"] > 0:
                power_curve_data["crossover_point"] = {
                    "minute": point["minute"],
                    "description": "Power curves intersect - critical turning point"
                }
                break

        # Build key milestones
        key_milestones = []
        for moment in analysis['key_moments'][:4]:  # Top 4 key moments
            key_milestones.append({
                "minute": moment['minute'],
                "type": moment.get('type', 'milestone'),
                "power_diff": round(moment.get('power_diff', 0), 1),
                "risk_level": moment.get('risk_level', 'medium'),
                "title": moment.get('title', f"{moment['minute']} minute mark"),
                "description": moment.get('description', ''),
                "risk_points": moment.get('risk_points', []),
                "tactical_advice": moment.get('tactical_advice', [])
            })

        # Build response
        response = {
            "match_id": request.match_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis_version": "2.1.0",
            "overview": {
                "our_comp_type": analysis.get('our_comp_type', 'balanced'),
                "enemy_comp_type": analysis.get('enemy_comp_type', 'balanced'),
                "predicted_outcome": "comeback_victory" if power_curve_data["crossover_point"] else "maintain_lead",
                "win_probability": {
                    "overall": 0.56,
                    "by_phase": {
                        "early": 0.35,
                        "mid": 0.52,
                        "late": 0.68
                    }
                }
            },
            "power_curve": power_curve_data,
            "key_milestones": key_milestones,
            "phase_tactics": [
                {
                    "phase": "early",
                    "time_range": "0-15min",
                    "objective": "Survival Priority",
                    "goal": "Keep gold deficit under 3000",
                    "strategies": []
                },
                {
                    "phase": "mid",
                    "time_range": "15-25min",
                    "objective": "Operational Control",
                    "goal": "Close gold gap to under 1000",
                    "strategies": []
                },
                {
                    "phase": "late",
                    "time_range": "25min+",
                    "objective": "Proactive Aggression",
                    "goal": "Complete comeback by 30-35min",
                    "strategies": []
                }
            ],
            "risk_assessment": {
                "high_risks": [],
                "medium_risks": []
            },
            "decision_checklist": {
                "every_5min": [
                    "Is current gold diff within expected range?",
                    "Are core items on schedule?",
                    "What's the next milestone tactical objective?",
                    "Is vision control adequate?",
                    "Is team communication smooth?"
                ],
                "before_teamfights": [
                    "Are all our key abilities available?",
                    "Have enemy ultimates been used?",
                    "Does current timing favor us?",
                    "Do we have TP/respawn backup?",
                    "Is fight location advantageous?"
                ]
            },
            "victory_path": {
                "summary": "Early farm safely, late game domination",
                "stages": [
                    {"stage": 1, "time": "0-15min", "goal": "Survive", "metric": "Gold diff ≤2500"},
                    {"stage": 2, "time": "15-25min", "goal": "Close gap", "metric": "Gold even"},
                    {"stage": 3, "time": "25-30min", "goal": "Find opportunities", "metric": "Complete comeback"},
                    {"stage": 4, "time": "30-35min", "goal": "Establish advantage", "metric": "Secure Baron"},
                    {"stage": 5, "time": "35min+", "goal": "Steady execution", "metric": "Victory"}
                ],
                "core_principles": [
                    "Early: Don't die - Every kill = 300g + XP advantage",
                    "Mid: Don't collapse - Defend key towers",
                    "Late: Don't rush - Post-30min is our domain"
                ]
            },
            "final_reminder": {
                "key_message": "The match outcome hinges on the 30-minute mark!",
                "motivation": "No matter how far behind early, don't panic. Our composition is designed for late game.",
                "mantra": "Remember: Patience is the greatest weapon for late-game compositions."
            }
        }

        print(f"✅ Analysis complete")
        print(f"📤 Sending response with {len(power_curve_data['time_series'])} power curve points")

        return response

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/v1/annual-summary/{summoner_id}")
async def get_annual_summary(
    summoner_id: str,
    region: str = "na1",
    start_patch: str = "15.12",
    end_patch: str = "15.20",
    include_visualizations: bool = True,
    language: str = "en",
    detail_level: str = "comprehensive"
):
    """
    Generate comprehensive annual season summary for a player

    This endpoint analyzes a player's performance across an entire season,
    tracking growth, champion pool evolution, and version adaptation.

    **Processing time**: ~30-60 seconds (includes full season data analysis + LLM generation)

    **Parameters**:
    - summoner_id: Player's summoner ID or GameName#TAG
    - region: Region code (na1, euw1, kr, etc.)
    - start_patch: Starting patch version (e.g., "15.12")
    - end_patch: Ending patch version (e.g., "15.20")

    **Returns**:
    - Complete season overview and statistics
    - Three-phase temporal evolution analysis
    - Version adaptation performance
    - Champion pool evolution tracking
    - Annual highlights and achievements
    - Future outlook and recommendations
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 Annual Summary Request: {summoner_id}")
        print(f"   Region: {region}, Season: {start_patch} - {end_patch}")
        print(f"{'='*60}")

        # Parse summoner_id (gameName#tagLine format)
        if '#' not in summoner_id:
            raise HTTPException(
                status_code=400,
                detail="summoner_id must be in gameName#tagLine format (e.g., s1ne#na1)"
            )

        game_name, tag_line = summoner_id.split('#', 1)

        # Get PUUID using riot_client
        from services.riot_client import riot_client
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, region="americas")
        if not account or 'puuid' not in account:
            raise HTTPException(
                status_code=404,
                detail=f"Player {summoner_id} not found in {region}"
            )

        puuid = account['puuid']

        # Get player packs directory
        packs_dir = player_data_manager.get_packs_dir(puuid)

        # Check if player pack exists
        packs_path = Path(packs_dir)
        if not packs_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Player data not found for {summoner_id}. Please ensure data has been collected first."
            )

        print(f"   PUUID: {puuid}")
        print(f"   Packs Dir: {packs_dir}")

        # Initialize agent (use haiku as default model for GET endpoint)
        agent = AnnualSummaryAgent(model="haiku", use_optimized_prompts=True)

        # Run analysis
        analysis, report = agent.run(
            packs_dir=packs_dir,
            output_dir=None  # Don't save to disk for API calls
        )

        # Return simplified response with raw analysis data
        # Let frontend do the transformation
        response = {
            "summoner_id": summoner_id,
            "summoner_name": game_name,
            "region": region,
            "puuid": puuid,
            "analysis": analysis,  # Raw agent analysis data
            "report": report       # Markdown report (optional)
        }

        summary = analysis.get('summary', {})
        print(f"✅ Analysis complete")
        print(f"📤 Sending response: {summary.get('total_games', 0)} games, {summary.get('overall_winrate', 0):.1%} WR")

        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ============================================================================
# Data Collection Endpoints
# ============================================================================

class PlayerDataFetchRequest(BaseModel):
    """Request to fetch player match data"""
    game_name: str = Field(..., description="Player game name", example="S1NE")
    tag_line: str = Field(..., description="Player tag line", example="NA1")
    region: str = Field("na1", description="Region code", example="na1")
    days: int = Field(365, description="Number of days to fetch", example=365)
    include_timeline: bool = Field(True, description="Include timeline data")


class PlayerDataFetchResponse(BaseModel):
    """Response for player data fetch"""
    task_id: str
    status: str
    message: str
    puuid: Optional[str] = None
    estimated_time: Optional[str] = None


class PlayerDataStatusResponse(BaseModel):
    """Status of data fetch task"""
    task_id: str
    status: str  # pending, in_progress, completed, failed
    progress: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# In-memory task storage (in production, use Redis or database)
fetch_tasks = {}
task_lock = threading.Lock()


@app.post("/v1/player/fetch-data", response_model=PlayerDataFetchResponse)
async def fetch_player_data(request: PlayerDataFetchRequest, background_tasks: BackgroundTasks):
    """
    Fetch match data for a player from patch 14.1 (2024-01-09) to today

    This endpoint triggers a background task to fetch all matches and timelines
    for a player from patch 14.1 to today. Use the task_id to check status.

    **Data fetching**: Always starts from patch 14.1 (2024-01-09) to today
    **Time range filtering**: Applied in agents (past-365, Season 2024, etc.)

    **Processing time**: 5-30 minutes depending on match count

    **Parameters**:
    - game_name: Player's game name (e.g., "S1NE")
    - tag_line: Player's tag line (e.g., "NA1")
    - region: Region code (na1, euw1, kr, etc.)
    - days: Kept for compatibility but not used (default: 365)
    - include_timeline: Whether to fetch timeline data (default: true)

    **Returns**:
    - task_id: Use this to check status via /v1/player/fetch-status/{task_id}
    - estimated_time: Approximate time to completion
    """
    try:
        import uuid
        import asyncio

        print(f"\n{'='*60}")
        print(f"📥 Data Fetch Request: {request.game_name}#{request.tag_line}")
        print(f"   Region: {request.region}")
        print(f"   Fetching from: Patch 14.1 (2024-01-09) to today")
        print(f"{'='*60}")

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Step 1: Get PUUID from Riot API
        print(f"📡 Fetching PUUID for {request.game_name}#{request.tag_line}...")

        # Map platform region to routing region
        routing_map = {
            'na1': 'americas', 'br1': 'americas', 'la1': 'americas', 'la2': 'americas',
            'euw1': 'europe', 'eun1': 'europe', 'tr1': 'europe', 'ru': 'europe',
            'kr': 'asia', 'jp1': 'asia'
        }
        routing_region = routing_map.get(request.region, 'americas')

        account_data = await riot_client.get_account_by_riot_id(
            request.game_name,
            request.tag_line,
            routing_region
        )

        if not account_data or 'puuid' not in account_data:
            raise HTTPException(status_code=404, detail=f"Account not found: {request.game_name}#{request.tag_line}")

        puuid = account_data['puuid']
        print(f"✅ Found PUUID: {puuid}")

        # Create task entry
        with task_lock:
            fetch_tasks[task_id] = {
                "status": "pending",
                "game_name": request.game_name,
                "tag_line": request.tag_line,
                "region": request.region,
                "puuid": puuid,
                "days": request.days,
                "include_timeline": request.include_timeline,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "progress": {
                    "total_matches": 0,
                    "fetched_matches": 0,
                    "fetched_timelines": 0
                }
            }

        # Start background task using PlayerDataManager
        async def run_fetch_task_async():
            """Background task to fetch player data using PlayerDataManager"""
            try:
                with task_lock:
                    fetch_tasks[task_id]["status"] = "in_progress"
                    fetch_tasks[task_id]["started_at"] = datetime.now(timezone.utc).isoformat()

                # Step 2: Use PlayerDataManager to prepare data
                print(f"🚀 Starting PlayerDataManager.prepare_player_data()...")
                job = await player_data_manager.prepare_player_data(
                    puuid=puuid,
                    region=request.region,
                    game_name=request.game_name,
                    tag_line=request.tag_line,
                    max_matches=request.days
                )

                # Step 3: Monitor job progress
                while job.status not in [DataStatus.COMPLETED, DataStatus.FAILED]:
                    await asyncio.sleep(2)  # Poll every 2 seconds

                    # Update task progress
                    with task_lock:
                        fetch_tasks[task_id]["progress"] = {
                            "status": job.status.value if job.status else "processing",
                            "progress_percent": int(job.progress * 100),
                            "total_matches": 0,  # PlayerDataManager doesn't expose these
                            "fetched_matches": 0,
                            "fetched_timelines": 0
                        }

                # Step 4: Check final status
                if job.status == DataStatus.FAILED:
                    raise RuntimeError(job.error or "Data fetch failed")

                # Mark as completed
                with task_lock:
                    fetch_tasks[task_id]["status"] = "completed"
                    fetch_tasks[task_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                    fetch_tasks[task_id]["result"] = {
                        "puuid": puuid,
                        "player_pack_path": f"data/player_packs/{puuid}/",
                        "message": "Player data prepared successfully"
                    }

                print(f"✅ Data fetch completed for task {task_id}")

            except Exception as e:
                print(f"❌ Error in fetch task {task_id}: {str(e)}")
                with task_lock:
                    fetch_tasks[task_id]["status"] = "failed"
                    fetch_tasks[task_id]["error"] = str(e)
                    fetch_tasks[task_id]["failed_at"] = datetime.now(timezone.utc).isoformat()

        # Start async background task
        asyncio.create_task(run_fetch_task_async())

        # Estimate time (rough: ~100 matches/minute)
        estimated_matches = request.days * 5  # Rough estimate
        estimated_minutes = estimated_matches / 100

        return {
            "task_id": task_id,
            "status": "pending",
            "message": f"Data fetch task created. Check status at /v1/player/fetch-status/{task_id}",
            "estimated_time": f"~{int(estimated_minutes)} minutes"
        }

    except Exception as e:
        print(f"❌ Error creating fetch task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create fetch task: {str(e)}")


@app.get("/v1/player/fetch-status/{task_id}", response_model=PlayerDataStatusResponse)
async def get_fetch_status(task_id: str):
    """
    Check the status of a data fetch task

    **Returns**:
    - status: pending, in_progress, completed, failed
    - progress: Current progress information
    - result: Final result when completed
    - error: Error message if failed
    """
    with task_lock:
        if task_id not in fetch_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        task = fetch_tasks[task_id]

        return {
            "task_id": task_id,
            "status": task["status"],
            "progress": task.get("progress", {}),
            "result": task.get("result"),
            "error": task.get("error")
        }


# ============================================================================
# Player Analysis Agents - Batch Endpoints
# ============================================================================

class AgentRequest(BaseModel):
    """Generic Agent Request Model"""
    puuid: str = Field(..., description="Player PUUID")
    region: str = Field("na1", description="Region code")
    recent_count: int = Field(5, description="Number of recent patches to analyze")
    model: str = Field("haiku", description="LLM model to use (haiku, sonnet)")
    # Player identification
    game_name: Optional[str] = Field(None, description="Current player's game name")
    tag_line: Optional[str] = Field(None, description="Current player's tag line")
    # Optional parameters for specific agents
    champion_id: Optional[int] = Field(None, description="Champion ID for champion-mastery agent")
    rank: Optional[str] = Field(None, description="Rank tier for peer-comparison agent (IRON/BRONZE/SILVER/GOLD/PLATINUM/EMERALD/DIAMOND/MASTER/GRANDMASTER/CHALLENGER)")
    role: Optional[str] = Field(None, description="Role for role-specialization agent (TOP/JUNGLE/MID/ADC/SUPPORT)")
    match_id: Optional[str] = Field(None, description="Match ID for timeline-deep-dive agent")
    friend_game_name: Optional[str] = Field(None, description="Friend's game name for friend-comparison agent")
    friend_tag_line: Optional[str] = Field(None, description="Friend's tag line for friend-comparison agent")
    time_range: Optional[str] = Field(None, description="Time range filter: 'past-365' for past 365 days")
    queue_id: Optional[int] = Field(None, description="Queue ID filter: 420 for Ranked Solo/Duo, 440 for Ranked Flex, 400 for Normal")

class AgentResponse(BaseModel):
    """Generic Agent Response Model"""
    success: bool
    agent: str
    detailed: Optional[str] = Field(None, description="Complete detailed report")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured data (backward compatibility)")
    error: Optional[str] = None


@app.post("/v1/agents/weakness-analysis")
async def weakness_analysis(request: AgentRequest):
    """Weakness Diagnosis - ADK-compliant agent endpoint with SSE streaming"""
    from fastapi.responses import StreamingResponse
    from src.agents.player_analysis.weakness_analysis.agent import WeaknessAnalysisAgent

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎯 Weakness Analysis (ADK) - Model: {request.model or 'haiku'}\n{'='*60}")

            # Step 1: Wait for data preparation
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Step 2: Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 3: Create ADK agent instance
            agent = WeaknessAnalysisAgent(model=request.model or "haiku")

            # Step 4: Execute agent with streaming
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 Params: time_range={time_range}, queue_id={queue_id}, recent_count={request.recent_count or 5}")

            for message in agent.run_stream(
                packs_dir=packs_dir,
                recent_count=request.recent_count or 5,
                time_range=time_range,
                queue_id=queue_id
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
async def _extract_postgame_features(timeline_data: dict, target_puuid: str, match_id: str, packs_dir: str) -> tuple:
    """Extract match_features and timeline_features from timeline data and match data"""
    import json
    from pathlib import Path

    # Read match data from global matches pool (shared across all players)
    global_matches_dir = Path("data/matches")
    match_file = global_matches_dir / f"{match_id}.json"

    if not match_file.exists():
        raise ValueError(f"Match data file not found in global pool: {match_file}")

    with open(match_file, 'r', encoding='utf-8') as f:
        match_data = json.load(f)

    if not match_data:
        raise ValueError(f"Failed to load match data for {match_id}")

    # Find target player data in match
    target_participant = None
    for p in match_data['info']['participants']:
        if p['puuid'] == target_puuid:
            target_participant = p
            break

    if not target_participant:
        raise ValueError(f"Target player not found in match {match_id}")

    # Extract match_features
    match_features = {
        'match_id': match_id,
        'champion_id': target_participant.get('championId', 0),
        'champion_name': target_participant.get('championName', f"Champion{target_participant.get('championId', 0)}"),
        'role': target_participant.get('teamPosition', 'UNKNOWN'),
        'win': target_participant.get('win', False),
        'game_duration': match_data['info'].get('gameDuration', 0),
        'kills': target_participant.get('kills', 0),
        'deaths': target_participant.get('deaths', 0),
        'assists': target_participant.get('assists', 0),
        'total_damage_dealt': target_participant.get('totalDamageDealtToChampions', 0),
        'gold_earned': target_participant.get('goldEarned', 0)
    }

    # Extract timeline_features
    frames = timeline_data.get('info', {}).get('frames', [])

    # Find participant_id from timeline metadata
    puuid_list = timeline_data.get('metadata', {}).get('participants', [])
    try:
        puuid_index = puuid_list.index(target_puuid)
        participant_id = puuid_index + 1
    except ValueError:
        raise ValueError(f"Target PUUID not found in timeline participants")

    # Extract CS data
    cs_at = {}
    for frame in frames:
        minute = frame.get('timestamp', 0) // 60000
        if minute in [5, 10, 15, 20]:
            pf = frame.get('participantFrames', {}).get(str(participant_id), {})
            cs = pf.get('minionsKilled', 0) + pf.get('jungleMinionsKilled', 0)
            cs_at[f'cs_{minute}'] = cs

    # Extract gold curve
    gold_curve = []
    for frame in frames:
        minute = frame.get('timestamp', 0) // 60000
        pf = frame.get('participantFrames', {}).get(str(participant_id), {})
        gold = pf.get('totalGold', 0)
        gold_curve.append({'min': minute, 'gold': gold})

    # Extract item purchase events
    item_purchases = []
    for frame in frames:
        for event in frame.get('events', []):
            if event.get('type') == 'ITEM_PURCHASED' and event.get('participantId') == participant_id:
                item_purchases.append({
                    'timestamp': event.get('timestamp', 0),
                    'item_id': event.get('itemId', 0)
                })

    timeline_features = {
        'cs_at': cs_at,
        'gold_curve': gold_curve,
        'item_purchases': item_purchases,
        'timeline_data': timeline_data  # Preserve complete timeline for engine use
    }

    return match_features, timeline_features


@app.post("/v1/agents/annual-summary")
async def annual_summary(request: AgentRequest):
    """Annual Summary - ADK-compliant agent endpoint with SSE streaming"""
    from fastapi.responses import StreamingResponse
    from src.agents.player_analysis.annual_summary.agent import AnnualSummaryAgent
    from src.agents.player_analysis.annual_summary.tools import (
        load_all_annual_packs, generate_comprehensive_annual_analysis
    )

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n📅 Annual Summary (ADK) - Model: {request.model or 'haiku'}\n{'='*60}")

            # Step 1: Wait for data preparation
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Step 2: Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 3: Get params
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 Params: time_range={time_range}, queue_id={queue_id}")

            # Step 4: Load data and generate analysis for frontend widgets
            all_packs_dict = load_all_annual_packs(packs_dir, time_range=time_range, queue_id=queue_id)
            if len(all_packs_dict) > 0:
                analysis = generate_comprehensive_annual_analysis(all_packs_dict)
                # Send analysis data for frontend widgets
                yield f"data: {{\"type\": \"analysis\", \"data\": {json.dumps(analysis, ensure_ascii=False)}}}\n\n"
                print(f"✅ Sent analysis data for frontend widgets")

            # Step 5: Create ADK agent and stream report
            agent = AnnualSummaryAgent(model=request.model or "haiku")
            for message in agent.run_stream(packs_dir, time_range, queue_id):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/champion-mastery")
async def champion_mastery(request: AgentRequest):
    """Champion Mastery - Champion mastery analysis (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            # Validate required parameters
            if not request.champion_id:
                yield f"data: {{\"error\": \"Champion Mastery analysis requires a champion_id parameter\"}}\n\n"
                return

            print(f"\n{'='*60}\n🎮 Champion Mastery Stream (Champion ID: {request.champion_id}, Model: {request.model or 'haiku'})\n{'='*60}")

            # Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Load data and build prompt
            from src.agents.player_analysis.champion_mastery.tools import (
                generate_comprehensive_mastery_analysis,
                format_analysis_for_prompt,
                load_champion_data
            )
            from src.agents.player_analysis.champion_mastery.prompts import build_narrative_prompt

            time_range = getattr(request, 'time_range', None)
            
            # Check if data exists for the selected time range before generating analysis
            champion_data = load_champion_data(packs_dir, request.champion_id, time_range=time_range)
            if not champion_data:
                if time_range == "past-365":
                    error_msg = "No data found for Past 365 Days"
                else:
                    error_msg = f"No data found for champion_id {request.champion_id}"
                yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
                return
            
            analysis = generate_comprehensive_mastery_analysis(
                champion_id=request.champion_id,
                packs_dir=packs_dir,
                time_range=time_range
            )
            formatted_data = format_analysis_for_prompt(analysis)
            prompts = build_narrative_prompt(analysis, formatted_data)

            # Stream generation
            model = "haiku"  # Force use of Haiku 4.5
            print(f"🚀 Using model: {model} with extended thinking")

            for message in stream_agent_with_thinking(
                prompt=prompts['user'],
                system_prompt=prompts['system'],
                model=model,
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/progress-tracker")
async def progress_tracker(request: AgentRequest):
    """Progress Tracker - Progress tracking analysis (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n📈 Progress Tracker Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Load player pack data and build prompt
            from src.agents.player_analysis.progress_tracker.tools import (
                load_recent_packs,
                analyze_progress,
                format_analysis_for_prompt
            )
            from src.agents.player_analysis.progress_tracker.prompts import build_narrative_prompt

            window_size = request.recent_count or 10
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 [Progress Tracker] Received time_range: {time_range}, queue_id: {queue_id}")
            recent_packs = load_recent_packs(packs_dir, window_size=window_size, time_range=time_range, queue_id=queue_id)

            queue_name = {420: "Solo/Duo", 440: "Flex", 400: "Normal"}.get(queue_id, "All") if queue_id else "All"
            print(f"📊 Loaded {len(recent_packs)} patches" + (f" (time_range: {time_range}, queue: {queue_name})" if time_range or queue_id else ""))

            analysis = analyze_progress(recent_packs)
            formatted_data = format_analysis_for_prompt(analysis)
            prompts = build_narrative_prompt(analysis, formatted_data)

            # Step 1.5: Send analysis data first (for frontend widgets)
            yield f"data: {{\"type\": \"analysis\", \"data\": {json.dumps(analysis, ensure_ascii=False)}}}\n\n"
            print(f"✅ Sent analysis data for frontend widgets")

            # Step 2: Use generic stream helper (supports model switching)
            model = "haiku"  # Force use of Haiku 4.5 for best speed
            print(f"🚀 Using model: Haiku 4.5")

            for message in stream_agent_with_thinking(
                prompt=prompts['user'],
                system_prompt=prompts['system'],
                model=model,
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/detailed-analysis")
async def detailed_analysis(request: AgentRequest):
    """Detailed Analysis - Deep detailed analysis (SSE Stream output - currently unavailable)"""
    from fastapi.responses import StreamingResponse

    async def generate_stream():
        try:
            # This agent requires meta_dir parameter, currently not supported by frontend
            yield f"data: {{\"error\": \"Detailed Analysis requires a meta_dir parameter for patch meta data. This feature is not currently available through the standard UI.\"}}\n\n"
        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/peer-comparison")
async def peer_comparison(request: AgentRequest):
    """Peer Comparison - Same rank comparison analysis (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            # Validate required parameters
            if not request.rank:
                yield f"data: {{\"error\": \"Peer Comparison requires a rank parameter (IRON/BRONZE/SILVER/GOLD/PLATINUM/EMERALD/DIAMOND/MASTER/GRANDMASTER/CHALLENGER).\"}}\n\n"
                return

            print(f"\n{'='*60}\n🏅 Peer Comparison Stream (Rank: {request.rank.upper()}, Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Load player pack data and build prompt
            from src.agents.player_analysis.peer_comparison.tools import (
                load_player_data,
                load_rank_baseline,
                compare_to_baseline,
                format_analysis_for_prompt
            )
            from src.agents.player_analysis.peer_comparison.prompts import build_narrative_prompt

            rank = request.rank.upper()
            player_data = load_player_data(packs_dir)
            baseline = load_rank_baseline(rank)

            if baseline is None:
                yield f"data: {{\"error\": \"Rank baseline data not available for {rank}\"}}\n\n"
                return

            comparison = compare_to_baseline(player_data, baseline)
            formatted_data = format_analysis_for_prompt(comparison, rank)
            prompts = build_narrative_prompt(comparison, formatted_data, rank)

            # Step 2: Use generic stream helper (supports model switching)
            model = "haiku"  # Force use of Haiku 4.5 for best speed
            print(f"🚀 Using model: Haiku 4.5")

            for message in stream_agent_with_thinking(
                prompt=prompts['user'],
                system_prompt=prompts['system'],
                model=model,
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/friend-comparison")
async def friend_comparison(request: AgentRequest):
    """Friend Comparison - Friend comparison (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            # Validate required parameters
            if not request.friend_game_name or not request.friend_tag_line:
                yield f"data: {{\"error\": \"Friend Comparison requires friend_game_name and friend_tag_line parameters.\"}}\n\n"
                return

            print(f"\n{'='*60}\n👥 Friend Comparison Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for current player data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
            current_player_packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not current_player_packs_dir:
                yield f"data: {{\"error\": \"Current player data not ready\"}}\n\n"
                return

            print(f"✅ Current player data ready: {current_player_packs_dir}")

            # Get friend's PUUID
            from services.riot_client import RiotAPIClient
            riot_client = RiotAPIClient()
            friend_account_info = await riot_client.get_account_by_riot_id(
                game_name=request.friend_game_name,
                tag_line=request.friend_tag_line,
                region="americas"  # NA1 maps to americas
            )

            if not friend_account_info:
                yield f"data: {{\"error\": \"Friend {request.friend_game_name}#{request.friend_tag_line} not found\"}}\n\n"
                return

            friend_puuid = friend_account_info["puuid"]

            # Prepare friend data (fetch last 30 days data)
            print(f"📊 Preparing friend data for {request.friend_game_name}#{request.friend_tag_line}...")
            await player_data_manager.prepare_player_data(
                puuid=friend_puuid,
                region=request.region,
                game_name=request.friend_game_name,
                tag_line=request.friend_tag_line,
                max_matches=30
            )

            # Wait for friend data preparation to complete
            await player_data_manager.wait_for_data(puuid=friend_puuid, timeout=120)
            friend_packs_dir = player_data_manager.get_packs_dir(friend_puuid)
            if not friend_packs_dir:
                yield f"data: {{\"error\": \"Friend data not ready\"}}\n\n"
                return

            print(f"✅ Friend data ready: {friend_packs_dir}")

            # Step 1: Load data and build prompt
            from src.agents.player_analysis.friend_comparison.tools import (
                load_player_data,
                compare_two_players,
                format_comparison_for_prompt
            )
            from src.agents.player_analysis.friend_comparison.prompts import build_narrative_prompt

            player1_name = f"{request.game_name}#{request.tag_line}"
            player2_name = f"{request.friend_game_name}#{request.friend_tag_line}"

            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 [Friend Comparison] Received time_range: {time_range}, queue_id: {queue_id}")
            player1_data = load_player_data(current_player_packs_dir, time_range=time_range, queue_id=queue_id)
            player2_data = load_player_data(friend_packs_dir, time_range=time_range, queue_id=queue_id)
            
            queue_name = {420: "Solo/Duo", 440: "Flex", 400: "Normal"}.get(queue_id, "All") if queue_id else "All"
            print(f"📊 Loaded player data" + (f" (time_range: {time_range}, queue: {queue_name})" if time_range or queue_id else ""))
            
            # Check if no data found
            if player1_data.get("total_games", 0) == 0 or player2_data.get("total_games", 0) == 0:
                if queue_id == 400:
                    error_msg = "No Normal game data found. Please play some Normal games first."
                elif queue_id == 440:
                    error_msg = "No Ranked Flex data found. Please play some Ranked Flex games first."
                elif queue_id == 420:
                    error_msg = "No Ranked Solo/Duo data found. Please play some Ranked Solo/Duo games first."
                elif time_range == "past-365":
                    error_msg = "No data found for Past 365 Days"
                else:
                    error_msg = "No data found"
                yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
                return
            
            comparison = compare_two_players(player1_data, player2_data, player1_name, player2_name)
            formatted_data = format_comparison_for_prompt(comparison, player1_name, player2_name)
            prompts = build_narrative_prompt(comparison, formatted_data, player1_name, player2_name)

            # Step 2: Use generic stream helper (supports model switching)
            model = "haiku"  # Force use of Haiku 4.5 for best speed
            print(f"🚀 Using model: Haiku 4.5")

            for message in stream_agent_with_thinking(
                prompt=prompts['user'],
                system_prompt=prompts['system'],
                model=model,
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/role-specialization")
async def role_specialization(request: AgentRequest):
    """Role Specialization - Role specialization analysis (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            # Validate required parameters
            if not request.role:
                yield f"data: {{\"error\": \"Role Specialization requires a role parameter (TOP/JUNGLE/MID/ADC/SUPPORT).\"}}\n\n"
                return

            print(f"\n{'='*60}\n🎮 Role Specialization Stream (Role: {request.role.upper()}, Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Load player pack data and build prompt
            from src.agents.player_analysis.role_specialization.tools import (
                generate_comprehensive_role_analysis,
                format_analysis_for_prompt,
                load_role_data
            )
            from src.agents.player_analysis.role_specialization.prompts import build_narrative_prompt

            role = request.role.upper()
            # Map ADC → BOTTOM for backend compatibility
            if role == 'ADC':
                role = 'BOTTOM'
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 [Role Specialization] Received time_range: {time_range}, queue_id: {queue_id}")
            
            # Check if data exists for the selected filters before generating analysis
            role_data = load_role_data(packs_dir, role, time_range=time_range, queue_id=queue_id)
            if not role_data:
                if queue_id == 400:
                    error_msg = "No Normal game data found. Please play some Normal games first."
                elif queue_id == 440:
                    error_msg = "No Ranked Flex data found. Please play some Ranked Flex games first."
                elif queue_id == 420:
                    error_msg = "No Ranked Solo/Duo data found. Please play some Ranked Solo/Duo games first."
                elif time_range == "past-365":
                    error_msg = "No data found for Past 365 Days"
                else:
                    error_msg = f"No data found for role {role}"
                yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
                return
            
            analysis = generate_comprehensive_role_analysis(
                role=role,
                packs_dir=packs_dir,
                time_range=time_range,
                queue_id=queue_id
            )
            formatted_data = format_analysis_for_prompt(analysis)
            prompts = build_narrative_prompt(analysis, formatted_data)

            # Step 2: Use generic stream helper (supports model switching)
            model = "haiku"  # Force use of Haiku 4.5 for best speed
            print(f"🚀 Using model: Haiku 4.5")

            for message in stream_agent_with_thinking(
                prompt=prompts['user'],
                system_prompt=prompts['system'],
                model=model,
                max_tokens=12000,  # Role Specialization needs detailed analysis
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/champion-recommendation")
async def champion_recommendation(request: AgentRequest):
    """Champion Recommendation - ADK-compliant agent endpoint with SSE streaming"""
    from fastapi.responses import StreamingResponse
    from src.agents.player_analysis.champion_recommendation.agent import ChampionRecommendationAgent

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎯 Champion Recommendation (ADK) - Model: {request.model or 'haiku'}\n{'='*60}")

            # Step 1: Wait for data preparation
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Step 2: Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 3: Create ADK agent instance
            agent = ChampionRecommendationAgent(model=request.model or "haiku")

            # Step 4: Execute agent with streaming
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)

            for message in agent.run_stream(
                packs_dir=packs_dir,
                time_range=time_range,
                queue_id=queue_id
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/multi-version")
async def multi_version_comparison(request: AgentRequest):
    """Multi-Version Analysis - ADK-compliant agent endpoint with SSE streaming"""
    from fastapi.responses import StreamingResponse
    from src.agents.player_analysis.multi_version.agent import MultiVersionAgent

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎮 Multi-Version Analysis (ADK) - Model: {request.model or 'haiku'}\n{'='*60}")

            # Step 1: Wait for data preparation
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Step 2: Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 3: Create ADK agent instance
            agent = MultiVersionAgent(model=request.model or "haiku")

            # Step 4: Execute agent with streaming
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)

            for message in agent.run_stream(
                packs_dir=packs_dir,
                time_range=time_range,
                queue_id=queue_id
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/build-simulator")
async def build_simulator(request: AgentRequest):
    """Build Simulator - Build optimization analysis (Compare player build vs Meta optimal build) (SSE Stream output)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎮 Build Simulator Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Analyze player build vs Meta optimal build
            from src.agents.player_analysis.build_simulator.player_build_analyzer import (
                generate_player_build_analysis,
                format_player_build_analysis_for_prompt
            )

            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 [Build Simulator] Received time_range: {time_range}, queue_id: {queue_id}")
            
            analysis = generate_player_build_analysis(packs_dir, time_range=time_range, queue_id=queue_id)

            if not analysis.get("analysis_ready"):
                yield f"data: {{\"error\": \"{analysis.get('error', 'Analysis failed')}\"}}\n\n"
                return

            # Format as prompt
            prompt = format_player_build_analysis_for_prompt(analysis)
            print(f"✅ Build analysis ready ({len(prompt)} chars)")

            # Step 2: Stream generate AI analysis
            system_prompt = """You are a professional League of Legends equipment analyst, skilled in build selection based on data analysis.

Your tasks:
1. Compare player build with Meta high win rate builds
2. Analyze the strengths and weaknesses of each build
3. Provide specific build optimization recommendations
4. Suggest build choices for different game situations

Output format: Complete analysis report in Markdown format"""

            for message in stream_agent_with_thinking(
                prompt=prompt,
                system_prompt=system_prompt,
                model="haiku",  # Force use of Haiku 4.5
                enable_thinking=False  # Build Simulator does not show thinking
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/drafting-coach")
async def drafting_coach(request: AgentRequest):
    """Drafting Coach - Champion draft coaching (SSE Stream output - currently unavailable)"""
    from fastapi.responses import StreamingResponse

    async def generate_stream():
        try:
            # This agent requires team compositions parameter, currently not supported by frontend
            yield f"data: {{\"error\": \"Drafting Coach requires team compositions (our_composition and enemy_composition). This feature will be available during champion select.\"}}\n\n"
            return  # ✅ End stream immediately
        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return  # ✅ End stream immediately

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/team-synergy")
async def team_synergy(request: AgentRequest):
    """Team Synergy - Team synergy analysis (SSE Stream output - currently unavailable)"""
    from fastapi.responses import StreamingResponse

    async def generate_stream():
        try:
            # This agent requires player_keys list parameter, currently not supported by frontend
            yield f"data: {{\"error\": \"Team Synergy requires a list of player_keys to analyze. This feature will be available through a specialized UI.\"}}\n\n"
            return  # ✅ End stream immediately
        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return  # ✅ End stream immediately

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/postgame-review")
async def postgame_review(request: AgentRequest):
    """Postgame Review - Post-game review (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking
    import json

    async def generate_stream():
        try:
            # Validate required parameters
            if not request.match_id:
                yield f"data: {{\"error\": \"Postgame Review requires a match_id parameter. Please select a match to review.\"}}\n\n"
                return

            print(f"\n{'='*60}\n🔍 Postgame Review Stream (Match ID: {request.match_id}, Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            # Check timeline data
            timelines_dir = Path(packs_dir) / "timelines"
            timeline_file = timelines_dir / f"{request.match_id}_timeline.json"
            if not timeline_file.exists():
                yield f"data: {{\"error\": \"Timeline data for match {request.match_id} not found.\"}}\n\n"
                return

            print(f"✅ Timeline file found: {timeline_file}")

            # Step 1: Load timeline data
            with open(timeline_file, 'r', encoding='utf-8') as f:
                timeline_data = json.load(f)

            # Step 2: Extract match_features and timeline_features
            print("📊 Extracting features from timeline and match data...")
            match_features, timeline_features = await _extract_postgame_features(
                timeline_data, request.puuid, request.match_id, packs_dir
            )

            # Step 3: Use rule engine to generate quantified diagnosis
            from src.agents.player_analysis.postgame_review.engine import PostgameReviewEngine
            from src.agents.player_analysis.postgame_review.prompts import build_narrative_prompt

            engine = PostgameReviewEngine()
            review = engine.generate_postgame_review(
                match_features=match_features,
                timeline_features=timeline_features
            )

            print(f"✅ Engine analysis complete")

            # Step 4: Build LLM prompt and stream generate
            prompt = build_narrative_prompt(review)
            model = "haiku"  # Force use of Haiku 4.5
            print(f"🚀 Using model: {model} with extended thinking")

            for message in stream_agent_with_thinking(
                prompt=prompt,
                system_prompt="",  # system prompt already included in build_narrative_prompt
                model=model,
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/risk-forecaster")
async def risk_forecaster_agent(request: AgentRequest):
    """Risk Forecaster - Risk prediction (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking
    import json

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🔮 Risk Forecaster Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            # Extract team composition from recent matches
            # First, read player's match ID list
            match_ids_file = Path(packs_dir) / "match_ids.json"
            if not match_ids_file.exists():
                yield f"data: {{\"error\": \"No match IDs found for player\"}}\n\n"
                return

            with open(match_ids_file, 'r', encoding='utf-8') as f:
                match_ids = json.load(f)

            if not match_ids:
                yield f"data: {{\"error\": \"No match data available for analysis\"}}\n\n"
                return

            # Read most recent match from global pool
            global_matches_dir = Path("data/matches")
            most_recent_match_id = match_ids[0]  # match_ids is already sorted by recency
            match_file = global_matches_dir / f"{most_recent_match_id}.json"

            if not match_file.exists():
                yield f"data: {{\"error\": \"Match data not found in global pool\"}}\n\n"
                return

            with open(match_file, 'r', encoding='utf-8') as f:
                match_data = json.load(f)

            # Extract team compositions
            our_team_id = None
            for participant in match_data['info']['participants']:
                if participant['puuid'] == request.puuid:
                    our_team_id = participant['teamId']
                    break

            if our_team_id is None:
                yield f"data: {{\"error\": \"Target player not found in match data\"}}\n\n"
                return

            # Extract team compositions
            our_team = []
            enemy_team = []

            for participant in match_data['info']['participants']:
                comp_item = {
                    "champion_id": participant['championId'],
                    "role": participant.get('teamPosition', 'UNKNOWN')
                }

                if participant['teamId'] == our_team_id:
                    our_team.append(comp_item)
                else:
                    enemy_team.append(comp_item)

            print(f"✅ Team compositions extracted")

            # Step 1: Analyze team composition matchup and build prompt
            from src.agents.player_analysis.risk_forecaster.tools import (
                analyze_composition_matchup,
                format_analysis_for_prompt
            )
            from src.agents.player_analysis.risk_forecaster.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

            analysis = analyze_composition_matchup(
                our_composition=our_team,
                enemy_composition=enemy_team
            )
            formatted_data = format_analysis_for_prompt(analysis)
            user_prompt = USER_PROMPT_TEMPLATE.format(analysis_data=formatted_data)

            # Step 2: Use generic stream helper (supports model switching)
            model = "haiku"  # Force use of Haiku 4.5 for best speed
            print(f"🚀 Using model: Haiku 4.5")

            for message in stream_agent_with_thinking(
                prompt=user_prompt,
                system_prompt=SYSTEM_PROMPT,
                model=model,
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/timeline-deep-dive")
async def timeline_deep_dive(request: AgentRequest):
    """Timeline Deep Dive - Timeline deep analysis (SSE Stream output - currently unavailable)"""
    from fastapi.responses import StreamingResponse

    async def generate_stream():
        try:
            # Timeline Deep Dive has complex custom logic that needs refactoring for stream mode
            yield f"data: {{\"error\": \"Timeline Deep Dive requires custom implementation refactoring for stream mode. This feature will be available in a future update.\"}}\n\n"
        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/version-comparison")
async def version_comparison(request: AgentRequest):
    """Version Comparison - Cross-version performance comparison analysis (SSE Stream output)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎮 Version Comparison Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Reuse multi-version analysis tools
            from src.agents.player_analysis.multi_version.tools import (
                load_all_packs,
                analyze_trends,
                identify_key_transitions,
                generate_comprehensive_analysis
            )
            from src.agents.player_analysis.multi_version.prompts import build_multi_version_prompt

            # Load all patch data with optional time range and queue_id filter
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 [Version Comparison] Received time_range: {time_range}, queue_id: {queue_id}")
            all_packs = load_all_packs(packs_dir, time_range=time_range, queue_id=queue_id)
            
            queue_name = {420: "Solo/Duo", 440: "Flex", 400: "Normal"}.get(queue_id, "All") if queue_id else "All"
            print(f"📊 Loaded {len(all_packs)} patches" + (f" (time_range: {time_range}, queue: {queue_name})" if time_range or queue_id else ""))
            
            # Check if no data found for the selected filters
            if len(all_packs) == 0:
                if queue_id == 400:
                    error_msg = "No Normal game data found. Please play some Normal games first."
                elif queue_id == 440:
                    error_msg = "No Ranked Flex data found. Please play some Ranked Flex games first."
                elif queue_id == 420:
                    error_msg = "No Ranked Solo/Duo data found. Please play some Ranked Solo/Duo games first."
                elif time_range == "past-365":
                    error_msg = "No data found for Past 365 Days"
                else:
                    error_msg = "No data found"
                yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
                return

            # Analyze trends
            trends = analyze_trends(all_packs)

            # Identify key turning points
            transitions = identify_key_transitions(trends)

            # Generate comprehensive analysis
            analysis = generate_comprehensive_analysis(trends, transitions)

            # Build AI prompt (Version Comparison focuses on patch transitions)
            prompt = build_multi_version_prompt(analysis)
            print(f"✅ Prompt constructed ({len(prompt)} chars)")

            # Step 2: Stream generate AI analysis
            for message in stream_agent_with_thinking(
                prompt=prompt,
                model="haiku",  # Force use of Haiku 4.5
                enable_thinking=False
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Merged Agent Endpoints (Optimized 9-Agent System)
# ============================================================================

@app.post("/v1/agents/comparison-hub")
async def comparison_hub(request: AgentRequest):
    """Comparison Hub - Comparison center (Friend comparison + Same rank comparison) (SSE Stream output)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    # Debug: Print request parameters
    print(f"\n🔍 DEBUG Comparison Hub Request:")
    print(f"   rank: {request.rank}")
    print(f"   friend_game_name: {request.friend_game_name}")
    print(f"   friend_tag_line: {request.friend_tag_line}")
    print(f"   puuid: {request.puuid}")
    print(f"   region: {request.region}\n")

    # Validate parameters before starting stream
    if not request.rank and (not request.friend_game_name or not request.friend_tag_line):
        raise HTTPException(
            status_code=400,
            detail="Comparison Hub requires either friend info (friend_game_name + friend_tag_line) or rank parameter"
        )

    async def generate_stream():
        try:
            # Check if friend parameter exists → use friend-comparison
            # Check if rank parameter exists → use peer-comparison
            # Default to friend-comparison

            if request.rank:
                # === Peer Comparison logic ===
                print(f"\n{'='*60}\n🏅 Comparison Hub - Peer Comparison (Rank: {request.rank.upper()})\n{'='*60}")

                await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
                packs_dir = player_data_manager.get_packs_dir(request.puuid)
                if not packs_dir:
                    yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                    return

                from src.agents.player_analysis.peer_comparison.tools import (
                    load_player_data, load_rank_baseline, compare_to_baseline, format_analysis_for_prompt
                )
                from src.agents.player_analysis.peer_comparison.prompts import build_narrative_prompt

                rank = request.rank.upper()
                time_range = getattr(request, 'time_range', None)
                queue_id = getattr(request, 'queue_id', None)
                print(f"🔍 [Comparison Hub - Peer] Received time_range: {time_range}, queue_id: {queue_id}")
                player_data = load_player_data(packs_dir, time_range=time_range, queue_id=queue_id)
                
                queue_name = {420: "Solo/Duo", 440: "Flex", 400: "Normal"}.get(queue_id, "All") if queue_id else "All"
                print(f"📊 Loaded player data" + (f" (time_range: {time_range}, queue: {queue_name})" if time_range or queue_id else ""))
                
                # Check if no data found
                if player_data.get("total_games", 0) == 0:
                    if queue_id == 400:
                        error_msg = "No Normal game data found. Please play some Normal games first."
                    elif queue_id == 440:
                        error_msg = "No Ranked Flex data found. Please play some Ranked Flex games first."
                    elif queue_id == 420:
                        error_msg = "No Ranked Solo/Duo data found. Please play some Ranked Solo/Duo games first."
                    elif time_range == "past-365":
                        error_msg = "No data found for Past 365 Days"
                    else:
                        error_msg = "No data found"
                    yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
                    return
                
                baseline = load_rank_baseline(rank)

                if baseline is None:
                    yield f"data: {{\"error\": \"Rank baseline data not available for {rank}\"}}\n\n"
                    return

                comparison = compare_to_baseline(player_data, baseline)
                formatted_data = format_analysis_for_prompt(comparison, rank)
                prompts = build_narrative_prompt(comparison, formatted_data, rank)

                for message in stream_agent_with_thinking(
                    prompt=prompts['user'],
                    system_prompt=prompts['system'],
                    model="haiku",  # Force use of Haiku 4.5
                    max_tokens=8000,  # Reduced for faster response
                    enable_thinking=False  # Disabled for speed
                ):
                    yield message

            else:
                # === Friend Comparison logic ===
                print(f"\n{'='*60}\n👥 Comparison Hub - Friend Comparison ({request.friend_game_name}#{request.friend_tag_line})\n{'='*60}")

                # Wait for current player data
                await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
                player_packs_dir = player_data_manager.get_packs_dir(request.puuid)
                if not player_packs_dir:
                    yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                    return

                # Get friend PUUID and prepare friend data
                print(f"🔍 Fetching friend PUUID for {request.friend_game_name}#{request.friend_tag_line}...")
                friend_account = await riot_client.get_account_by_riot_id(request.friend_game_name, request.friend_tag_line, "americas")
                if not friend_account or 'puuid' not in friend_account:
                    yield f"data: {{\"error\": \"Could not find friend {request.friend_game_name}#{request.friend_tag_line}\"}}\n\n"
                    return

                friend_puuid = friend_account['puuid']
                print(f"✅ Got friend PUUID: {friend_puuid[:20]}...")

                # Trigger friend data preparation
                print(f"📊 Preparing friend data...")
                friend_job = await player_data_manager.prepare_player_data(
                    puuid=friend_puuid,
                    region=request.region,
                    game_name=request.friend_game_name,
                    tag_line=request.friend_tag_line,
                    max_matches=100  # 100 per queue: Solo/Duo+Flex+Normal, total ~100-300 matches
                )

                # Wait for friend data
                await player_data_manager.wait_for_data(puuid=friend_puuid, timeout=120)
                friend_packs_dir = player_data_manager.get_packs_dir(friend_puuid)
                if not friend_packs_dir:
                    yield f"data: {{\"error\": \"Friend data preparation failed\"}}\n\n"
                    return

                # Load both players' data
                from src.agents.player_analysis.friend_comparison.tools import (
                    load_player_data, compare_two_players, format_comparison_for_prompt
                )
                from src.agents.player_analysis.friend_comparison.prompts import build_narrative_prompt as build_friend_prompt

                time_range = getattr(request, 'time_range', None)
                queue_id = getattr(request, 'queue_id', None)
                print(f"🔍 [Comparison Hub - Friend] Received time_range: {time_range}, queue_id: {queue_id}")
                player_data = load_player_data(player_packs_dir, time_range=time_range, queue_id=queue_id)
                friend_data = load_player_data(friend_packs_dir, time_range=time_range, queue_id=queue_id)
                
                queue_name = {420: "Solo/Duo", 440: "Flex", 400: "Normal"}.get(queue_id, "All") if queue_id else "All"
                print(f"📊 Loaded player data" + (f" (time_range: {time_range}, queue: {queue_name})" if time_range or queue_id else ""))
                
                # Check if no data found
                if player_data.get("total_games", 0) == 0 or friend_data.get("total_games", 0) == 0:
                    if queue_id == 400:
                        error_msg = "No Normal game data found. Please play some Normal games first."
                    elif queue_id == 440:
                        error_msg = "No Ranked Flex data found. Please play some Ranked Flex games first."
                    elif queue_id == 420:
                        error_msg = "No Ranked Solo/Duo data found. Please play some Ranked Solo/Duo games first."
                    elif time_range == "past-365":
                        error_msg = "No data found for Past 365 Days"
                    else:
                        error_msg = "No data found"
                    yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
                    return

                # Compare
                player_name = f"{request.game_name}#{request.tag_line}"
                friend_name = f"{request.friend_game_name}#{request.friend_tag_line}"
                comparison = compare_two_players(player_data, friend_data, player_name, friend_name)
                formatted_data = format_comparison_for_prompt(comparison, player_name, friend_name)
                prompts = build_friend_prompt(comparison, formatted_data, player_name, friend_name)

                for message in stream_agent_with_thinking(
                    prompt=prompts['user'],
                    system_prompt=prompts['system'],
                    model="haiku",  # Force use of Haiku 4.5
                    max_tokens=12000,
                    enable_thinking=False
                ):
                    yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/match-analysis")
async def match_analysis(request: AgentRequest):
    """Match Analysis - Match deep analysis (Timeline Deep Dive + Postgame Review merged) (SSE Stream output)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking
    import json
    from pathlib import Path

    async def generate_stream():
        try:
            if not request.match_id:
                yield f"data: {{\"error\": \"Match Analysis requires a match_id parameter\"}}\n\n"
                return

            print(f"\n{'='*60}\n🎮 Match Analysis Stream (Match ID: {request.match_id})\n{'='*60}")

            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            # Use Timeline Deep Dive logic (already includes postgame functionality)
            timelines_dir = Path(packs_dir) / "timelines"
            timeline_file = timelines_dir / f"{request.match_id}_timeline.json"
            if not timeline_file.exists():
                yield f"data: {{\"error\": \"Timeline data for match {request.match_id} not found\"}}\n\n"
                return

            with open(timeline_file, 'r', encoding='utf-8') as f:
                timeline_data = json.load(f)

            # Extract features (includes match and timeline features)
            match_features, timeline_features = await _extract_postgame_features(
                timeline_data, request.puuid, request.match_id, packs_dir
            )

            # Use Postgame Review Engine to generate diagnosis
            from src.agents.player_analysis.postgame_review.engine import PostgameReviewEngine
            from src.agents.player_analysis.postgame_review.prompts import build_narrative_prompt as build_postgame_prompt

            engine = PostgameReviewEngine()
            review = engine.generate_postgame_review(
                match_features=match_features,
                timeline_features=timeline_features
            )

            # Build comprehensive analysis prompt (combine timeline and postgame)
            prompt = build_postgame_prompt(review)

            for message in stream_agent_with_thinking(
                prompt=prompt,
                model="haiku",  # Force use of Haiku 4.5
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/version-trends")
async def version_trends(request: AgentRequest):
    """Version Trends - ADK-compliant agent endpoint with SSE streaming"""
    from fastapi.responses import StreamingResponse
    from src.agents.player_analysis.multi_version.agent import MultiVersionAgent

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n📊 Version Trends (ADK) - Model: {request.model or 'haiku'}\n{'='*60}")

            # Step 1: Wait for data preparation
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Step 2: Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 3: Create ADK agent instance
            agent = MultiVersionAgent(model=request.model or "haiku")

            # Step 4: Execute agent with streaming
            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)

            for message in agent.run_stream(
                packs_dir=packs_dir,
                time_range=time_range,
                queue_id=queue_id
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/v1/agents/performance-insights")
async def performance_insights(request: AgentRequest):
    """Performance Insights - Comprehensive performance insights (Weakness + Detailed + Progress merged) (SSE Stream output)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n💡 Performance Insights Stream\n{'='*60}")

            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            # Use Weakness Analysis tools (includes most complete analysis)
            from src.agents.player_analysis.weakness_analysis.tools import (
                load_recent_data, identify_weaknesses, format_analysis_for_prompt
            )
            from src.agents.player_analysis.weakness_analysis.prompts import build_narrative_prompt as build_weakness_prompt

            time_range = getattr(request, 'time_range', None)
            queue_id = getattr(request, 'queue_id', None)
            print(f"🔍 [Performance Insights] Received time_range: {time_range}, queue_id: {queue_id}")
            recent_data = load_recent_data(packs_dir, request.recent_count or 20, time_range=time_range, queue_id=queue_id)
            
            queue_name = {420: "Solo/Duo", 440: "Flex", 400: "Normal"}.get(queue_id, "All") if queue_id else "All"
            print(f"📊 Loaded {len(recent_data)} patches" + (f" (time_range: {time_range}, queue: {queue_name})" if time_range or queue_id else ""))
            
            # Check if no data found for the selected filters
            if len(recent_data) == 0:
                if queue_id == 400:
                    error_msg = "No Normal game data found. Please play some Normal games first."
                elif queue_id == 440:
                    error_msg = "No Ranked Flex data found. Please play some Ranked Flex games first."
                elif queue_id == 420:
                    error_msg = "No Ranked Solo/Duo data found. Please play some Ranked Solo/Duo games first."
                elif time_range == "past-365":
                    error_msg = "No data found for Past 365 Days"
                else:
                    error_msg = "No data found"
                yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
                return
            
            weaknesses = identify_weaknesses(recent_data)
            formatted = format_analysis_for_prompt(weaknesses)
            prompts = build_weakness_prompt(weaknesses, formatted)

            # Enhance prompt to include strengths, weaknesses, growth trends
            enhanced_prompt = prompts['user'] + """

Please include the following sections in your analysis:
1. 💪 **Strength Analysis** - Areas where the player performs best
2. ⚠️ **Weakness Identification** - Core issues that need improvement
3. 📈 **Growth Recommendations** - Specific improvement paths and priorities

Ensure the analysis is comprehensive and actionable."""

            for message in stream_agent_with_thinking(
                prompt=enhanced_prompt,
                system_prompt=prompts['system'],
                model="haiku",  # Force use of Haiku 4.5
                max_tokens=8000,  # Reduced for faster response
                enable_thinking=False  # Disabled for speed
            ):
                yield message

        except Exception as e:
            import traceback
            print(f"❌ Error: {traceback.format_exc()}")
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            return

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Utility Endpoints
# ============================================================================

# ============================================================================
# Player Data Endpoints (from combatpower)
# ============================================================================

def infer_platform_and_region(tag_line: str):
    """
    Infer platform and routing region from tag_line
    
    Args:
        tag_line: Tag line (e.g., "KR1", "NA1", "EUW1")
    
    Returns:
        tuple: (platform, routing_region)
    """
    tag_lower = tag_line.upper()
    
    # Platform to region mapping
    platform_to_region = {
        "NA1": ("na1", "americas"),
        "BR1": ("br1", "americas"),
        "LA1": ("la1", "americas"),
        "LA2": ("la2", "americas"),
        "KR": ("kr", "asia"),
        "KR1": ("kr", "asia"),
        "JP1": ("jp1", "asia"),
        "EUW1": ("euw1", "europe"),
        "EUN1": ("eun1", "europe"),
        "TR1": ("tr1", "europe"),
        "RU": ("ru", "europe"),
        "OC1": ("oc1", "sea"),
        "PH2": ("ph2", "sea"),
        "SG2": ("sg2", "sea"),
        "TH2": ("th2", "sea"),
        "TW2": ("tw2", "sea"),
        "VN2": ("vn2", "sea"),
    }
    
    # Try exact match first
    if tag_lower in platform_to_region:
        return platform_to_region[tag_lower]
    
    # Try prefix match (e.g., "KR1" -> "KR")
    for prefix, (platform, region) in platform_to_region.items():
        if tag_lower.startswith(prefix):
            return (platform, region)
    
    # Default to NA/Americas
    return ("na1", "americas")


@app.get("/api/player/{game_name}/{tag_line}/summary")
async def get_player_summary(
    game_name: str,
    tag_line: str,
    days: int = None,
    count: int = None,
    time_range: str = None
):
    """
    Trigger background data preparation and return basic player info

    This endpoint:
    1. Gets basic summoner information from Riot API (fast, <1s)
    2. Starts background data preparation task (match fetching + analysis)
    3. Returns immediately with basic info

    Frontend should then poll /api/player/{game_name}/{tag_line}/data-status
    to check when data preparation is complete.

    Query params:
    - days: Number of days to fetch data from (legacy, optional)
    - count: Number of matches to fetch (optional, takes priority over days/time_range)
    - time_range: Time range preset ("past-365")

    Priority: count > time_range > days (default 365)

    Example: /api/player/s1ne/na1/summary?time_range=past-365
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    import time
    from datetime import datetime, timedelta
    start_time = time.time()

    # Data fetching now always starts from patch 14.1 (2024-01-09) to today
    # time_range parameter is only used for filtering data in agents, not for fetching
    # Keep days parameter for compatibility but it's not used for fetching anymore
    if days is None:
        days = 365  # Default value for compatibility
    print(f"📅 Fetching data from patch 14.1 (2024-01-09) to today")
    if time_range:
        print(f"📅 Time range filter will be applied in agents: {time_range}")

    try:
        print(f"\n{'='*60}")
        if count:
            print(f"🔍 Player Summary Request: {game_name}#{tag_line} (count={count})")
        else:
            print(f"🔍 Player Summary Request: {game_name}#{tag_line} (days={days})")
        print(f"⏱️  Start time: {time.strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")

        # Step 1: Infer platform and region from tag_line
        platform, routing_region = infer_platform_and_region(tag_line)
        print(f"📍 Inferred platform: {platform}, routing region: {routing_region}")

        # Step 2: Get account info - try inferred region first, then try other regions if needed
        step_start = time.time()
        try:
            account = await riot_client.get_account_by_riot_id(game_name=game_name, tag_line=tag_line, region=routing_region)
        except Exception as e:
            # Handle Riot API errors more gracefully
            error_msg = str(e)
            if "decrypting" in error_msg.lower() or "400" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=f"Riot API authentication error. This may indicate an invalid or expired API key. Please check your RIOT_API_KEY_PRIMARY environment variable. Error: {error_msg}"
                )
            # If it's not a decrypt error, continue with fallback regions
            print(f"⚠️  Error fetching account from {routing_region}: {error_msg}, trying fallback regions...")
            account = None
        
        # If not found in inferred region, try other regions
        if not account:
            print(f"⚠️  Account not found in {routing_region}, trying other regions...")
            fallback_regions = ['americas', 'asia', 'europe', 'sea']
            for region in fallback_regions:
                if region != routing_region:
                    print(f"🔍 Trying region: {region}")
                    try:
                        account = await riot_client.get_account_by_riot_id(game_name=game_name, tag_line=tag_line, region=region)
                        if account:
                            print(f"✅ Found account in {region}")
                            break
                    except Exception as e:
                        error_msg = str(e)
                        if "decrypting" in error_msg.lower() or "400" in error_msg:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Riot API authentication error. This may indicate an invalid or expired API key. Please check your RIOT_API_KEY_PRIMARY environment variable. Error: {error_msg}"
                            )
                        print(f"⚠️  Error fetching account from {region}: {error_msg}")
                        continue
        
        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found for {game_name}#{tag_line}")

        puuid = account['puuid']
        print(f"✅ [1/2] Got PUUID ({time.time()-step_start:.2f}s): {puuid[:20]}...")

        # Step 3: Get summoner info
        step_start = time.time()

        try:
            summoner = await riot_client.get_summoner_by_puuid(puuid=puuid, platform=platform)
        except Exception as e:
            error_msg = str(e)
            # Check if it's a decrypt error (API key issue)
            if "decrypting" in error_msg.lower() or "400" in error_msg:
                print(f"❌ PUUID解密失败: {error_msg}")
                print(f"   这通常说明API key在获取Account和Summoner信息时发生了变化")
                print(f"   可能原因：429 rate limit重试时切换了API key")
                raise HTTPException(
                    status_code=400,
                    detail=f"Riot API authentication error: The API key cannot decrypt the PUUID. This indicates the API key changed between Account API and Summoner API calls (likely due to rate limit retry). Error: {error_msg}"
                )
            else:
                # Re-raise other errors
                raise

        if not summoner:
            raise HTTPException(status_code=404, detail=f"Summoner not found for PUUID on platform {platform}")
        print(f"✅ [2/2] Got summoner info ({time.time()-step_start:.2f}s)")

        # Step 4: Start background data preparation (non-blocking)
        print(f"\n🔄 Starting background data preparation from patch 14.1 (2024-01-09) to today...")
        job = await player_data_manager.prepare_player_data(
            puuid=puuid,
            region=platform,
            game_name=game_name,
            tag_line=tag_line,
            max_matches=days  # max_matches per queue (100 by default)
        )

        # Step 4: Try to get role stats and champion stats
        # If count parameter is provided and job has matches_data, calculate stats from current job
        # Otherwise, use existing pack files
        role_stats = []
        best_champions = []
        
        # Wait a bit for matches_data to be populated (if count-based request)
        if count:
            import asyncio
            # Wait up to 5 seconds for matches_data to be populated
            for _ in range(10):
                if job.matches_data and len(job.matches_data) > 0:
                    break
                await asyncio.sleep(0.5)
        
        if count and job.matches_data and len(job.matches_data) > 0:
            # Calculate stats from current job's matches_data (for count-based requests)
            from collections import defaultdict
            role_stats_dict = defaultdict(lambda: {"games": 0, "wins": 0, "total_kda": 0.0})
            champion_stats_dict = defaultdict(lambda: {"games": 0, "wins": 0, "total_kda": 0.0})
            
            for match in job.matches_data:
                player_data = None
                for p in match['info']['participants']:
                    if p.get('puuid') == puuid or (p.get('riotIdGameName', '').lower() == game_name.lower() and
                                                   p.get('riotIdTagline', '').lower() == tag_line.lower()):
                        player_data = p
                        break
                
                if not player_data:
                    continue
                
                role = player_data.get('teamPosition', 'UNKNOWN')
                if role == 'Invalid' or not role:
                    continue
                
                champ_id = player_data.get('championId')
                win = player_data.get('win', False)
                kills = player_data.get('kills', 0)
                deaths = player_data.get('deaths', 0)
                assists = player_data.get('assists', 0)
                kda_adj = (kills + 0.7 * assists) / (deaths + 1) if deaths > 0 else (kills + 0.7 * assists)
                
                role_stats_dict[role]["games"] += 1
                if win:
                    role_stats_dict[role]["wins"] += 1
                role_stats_dict[role]["total_kda"] += kda_adj
                
                if champ_id:
                    champion_stats_dict[champ_id]["games"] += 1
                    if win:
                        champion_stats_dict[champ_id]["wins"] += 1
                    champion_stats_dict[champ_id]["total_kda"] += kda_adj
            
            # Convert role_stats_dict to list format
            for role, stats in role_stats_dict.items():
                games = stats["games"]
                wins = stats["wins"]
                win_rate = (wins / games * 100) if games > 0 else 0
                avg_kda = (stats["total_kda"] / games) if games > 0 else 0
                role_stats.append({
                    "role": role,
                    "games": games,
                    "wins": wins,
                    "win_rate": round(win_rate, 1),
                    "avg_kda": round(avg_kda, 2)
                })
            
            # Convert champion_stats_dict to list format
            from src.utils.id_mappings import get_champion_name
            for champ_id, stats in champion_stats_dict.items():
                games = stats["games"]
                wins = stats["wins"]
                win_rate = (wins / games * 100) if games > 0 else 0
                avg_kda = (stats["total_kda"] / games) if games > 0 else 0
                best_champions.append({
                    "champ_id": champ_id,
                    "name": get_champion_name(champ_id),
                    "games": games,
                    "wins": wins,
                    "win_rate": round(win_rate, 1),
                    "avg_kda": round(avg_kda, 2)
                })
            best_champions.sort(key=lambda x: x["games"], reverse=True)
            best_champions = best_champions[:5]
        else:
            # Use existing pack files (for time_range or days-based requests)
            role_stats = player_data_manager.get_role_stats(puuid)
            best_champions = player_data_manager.get_best_champions(puuid, limit=5)

        # Step 5: Calculate analysis summary from role_stats
        analysis = {
            'total_games': 0,
            'total_wins': 0,
            'total_losses': 0,
            'win_rate': 0.0,
            'avg_kda': 0.0,
            'champion_pool': len(best_champions),  # Champion pool size
            'best_champions': best_champions
        }

        if role_stats:
            total_games = sum(role['games'] for role in role_stats)
            total_wins = sum(role['wins'] for role in role_stats)
            total_losses = total_games - total_wins
            win_rate = (total_wins / total_games * 100) if total_games > 0 else 0

            # Weighted average KDA
            total_kda_weighted = sum(role['avg_kda'] * role['games'] for role in role_stats)
            avg_kda = (total_kda_weighted / total_games) if total_games > 0 else 0

            analysis = {
                'total_games': total_games,
                'total_wins': total_wins,
                'total_losses': total_losses,
                'win_rate': round(win_rate, 1),
                'avg_kda': round(avg_kda, 2),
                'champion_pool': len(best_champions),  # Champion pool size
                'best_champions': best_champions
            }

        # Step 6: Fetch OPGG profile data (tier, division, LP, ladder rank)
        step_start = time.time()
        opgg_profile = None
        try:
            # Map platform to OP.GG region format
            platform_to_opgg_region = {
                'na1': 'na', 'br1': 'br', 'la1': 'lan', 'la2': 'las',
                'kr': 'kr', 'jp1': 'jp',
                'euw1': 'euw', 'eun1': 'eune', 'tr1': 'tr', 'ru': 'ru',
                'oc1': 'oce', 'ph2': 'ph', 'sg2': 'sg', 'th2': 'th', 'tw2': 'tw', 'vn2': 'vn'
            }
            opgg_region = platform_to_opgg_region.get(platform, 'na')
            
            print(f"🔍 Fetching OP.GG profile data (region: {opgg_region})...")
            opgg_profile = opgg_mcp_service.get_summoner_profile(game_name, tag_line, region=opgg_region)
            if opgg_profile:
                print(f"✅ Got OP.GG profile ({time.time()-step_start:.2f}s)")
            else:
                print(f"⚠️  OP.GG profile not available ({time.time()-step_start:.2f}s)")
        except Exception as e:
            print(f"⚠️  Failed to fetch OP.GG profile: {e}")

        response_data = {
            'success': True,
            'player': {
                'game_name': game_name,
                'tag_line': tag_line,
                'puuid': puuid,
                'summonerId': summoner.get('id'),
                'accountId': summoner.get('accountId'),
                'name': summoner.get('name'),
                'profileIconId': summoner.get('profileIconId'),
                'summonerLevel': summoner.get('summonerLevel'),
                'region': platform
            },
            'analysis': analysis,  # Add analysis summary data
            'role_stats': role_stats,  # Add role statistics data
            'opgg': opgg_profile if opgg_profile else None,  # Add OP.GG profile data (tier, ladder rank, etc.)
            'data_preparation': {
                'status': job.status,
                'progress': job.progress,
                'days': days if not count else None,
                'count': count if count else None,
                'time_range': time_range,
                'message': f'Data preparation started in background for {count} matches.' if count else f'Data preparation started in background for past {days} days. Poll /data-status endpoint to check progress.'
            }
        }

        print(f"✅ Response ready in {time.time()-start_time:.2f}s")
        print(f"{'='*60}\n")

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/champions")
async def get_all_champions():
    """Get all champions with their base combat power"""
    try:
        all_champions_power = combat_power_calculator.calculate_all_champions_base_power()

        champions_list = [
            {'name': name, 'combat_power': round(power, 2)}
            for name, power in sorted(all_champions_power.items(), key=lambda x: x[1], reverse=True)
        ]

        avg_power = sum(all_champions_power.values()) / len(all_champions_power) if all_champions_power else 0

        return {
            'success': True,
            'patch': data_dragon.version,
            'total_champions': len(champions_list),
            'avg_combat_power': round(avg_power, 2),
            'champions': champions_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Item Search Routes (from combatpower/routes/item_search_routes.py)
# ============================================================================

@app.get("/api/items/search")
async def search_items(q: str, patch: str = "14.19", limit: int = 5):
    """Search for items by name, abbreviation, or partial match"""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    try:
        results = item_search.search_item(q, patch, max_results=limit)
        return {
            'query': q,
            'patch': patch,
            'results': results,
            'count': len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/items/suggest")
async def suggest_items(q: str = "", patch: str = "14.19", count: int = 10):
    """Autocomplete suggestions for item search"""
    if not q:
        return {'suggestions': []}

    try:
        suggestions = item_search.get_suggestions(q, patch, max_results=count)
        return {'suggestions': suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Patch Routes (from combatpower/routes/patch_routes.py)
# ============================================================================

@app.get("/api/patches")
async def get_all_patches():
    """Get all available patch versions with dates"""
    try:
        patches = []
        for patch in patch_manager.get_all_patches():
            patch_date = patch_manager.get_patch_date(patch)
            patches.append({
                'version': patch,
                'date': patch_date.strftime('%Y-%m-%d') if patch_date else None,
                'ddragon_version': patch_manager.get_ddragon_version(patch)
            })

        return {
            'success': True,
            'patches': patches
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patch/champion/{champion_name}/patch/{patch}")
async def get_champion_by_patch(champion_name: str, patch: str):
    """Get champion combat power for a specific patch with popular build"""
    try:
        # Get popular build (if available from tracked data)
        popular_build = build_tracker.get_popular_build(patch, champion_name, min_games=5)

        # Get champion data for this patch
        champions = multi_patch_data.get_champions_for_patch(patch)

        if champion_name not in champions:
            raise HTTPException(
                status_code=404,
                detail=f'Champion {champion_name} not found in patch {patch}'
            )

        champion_data = champions[champion_name]

        # Calculate combat power with popular build if available
        if popular_build:
            combat_power = combat_power_calculator.calculate_champion_power(
                champion_data,
                popular_build.get('items', []),
                popular_build.get('runes', [])
            )
        else:
            combat_power = combat_power_calculator.calculate_base_power(champion_data)

        return {
            'success': True,
            'champion': champion_name,
            'patch': patch,
            'combat_power': round(combat_power, 2),
            'popular_build': popular_build,
            'has_build_data': popular_build is not None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Custom Build Routes (from combatpower/routes/custom_build_routes.py)
# ============================================================================

@app.get("/api/custom-builds/champions")
async def get_custom_build_champions():
    """Get list of all configured champions"""
    try:
        champions = custom_build_manager.get_all_champions()
        return {
            'success': True,
            'champions': champions,
            'total': len(champions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/custom-builds/champions/{champion_name}")
async def get_champion_custom_build(champion_name: str):
    """Get build configuration for specified champion"""
    try:
        build = custom_build_manager.get_champion_build(champion_name)
        return {
            'success': True,
            'champion': champion_name,
            'build': build
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/custom-builds/champions/{champion_name}")
async def set_champion_custom_build(champion_name: str, build_data: dict):
    """Set build configuration for specified champion"""
    try:
        custom_build_manager.set_champion_build(champion_name, build_data)
        return {
            'success': True,
            'champion': champion_name,
            'message': 'Build configuration updated'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/agents/list")
async def list_agents():
    """List all available Agents"""
    return {
        "agents": [
            {"id": "annual-summary", "name": "Annual Summary", "endpoint": "/v1/annual-summary/{summoner_id}"},
            {"id": "risk-forecaster", "name": "Risk Forecaster", "endpoint": "/v1/risk-forecaster/analyze"},
            {"id": "weakness-analysis", "name": "Weakness Analysis", "endpoint": "/v1/agents/weakness-analysis"},
            {"id": "champion-mastery", "name": "Champion Mastery", "endpoint": "/v1/agents/champion-mastery"},
            {"id": "progress-tracker", "name": "Progress Tracker", "endpoint": "/v1/agents/progress-tracker"},
            {"id": "detailed-analysis", "name": "Detailed Analysis", "endpoint": "/v1/agents/detailed-analysis"},
            {"id": "peer-comparison", "name": "Peer Comparison", "endpoint": "/v1/agents/peer-comparison"},
            {"id": "role-specialization", "name": "Role Specialization", "endpoint": "/v1/agents/role-specialization"},
            {"id": "champion-recommendation", "name": "Champion Recommendation", "endpoint": "/v1/agents/champion-recommendation"},
            {"id": "multi-version", "name": "Multi-Version Comparison", "endpoint": "/v1/agents/multi-version"},
            {"id": "build-simulator", "name": "Build Simulator", "endpoint": "/v1/agents/build-simulator"},
            {"id": "drafting-coach", "name": "Drafting Coach", "endpoint": "/v1/agents/drafting-coach"},
            {"id": "team-synergy", "name": "Team Synergy", "endpoint": "/v1/agents/team-synergy"},
            {"id": "postgame-review", "name": "Postgame Review", "endpoint": "/v1/agents/postgame-review"},
            {"id": "timeline-deep-dive", "name": "Timeline Deep Dive", "endpoint": "/v1/agents/timeline-deep-dive"},
            {"id": "version-comparison", "name": "Version Comparison", "endpoint": "/v1/agents/version-comparison"},
            {"id": "player-summary", "name": "Player Summary", "endpoint": "/api/player/{game_name}/{tag_line}/summary"},
        ]
    }


# ============================================================================
# Player Data Status API
# ============================================================================

@app.get("/api/player/{game_name}/{tag_line}/champions")
async def get_player_champions(
    game_name: str,
    tag_line: str,
    time_range: str = None,
    queue_id: int = None,
    limit: int = 50
):
    """
    Get player's champion statistics filtered by time_range and queue_id
    
    Query params:
    - time_range: Time range filter ("past-365")
    - queue_id: Queue ID filter (420 for Ranked Solo/Duo, 440 for Ranked Flex, 400 for Normal, None for all)
    - limit: Maximum number of champions to return (default: 50)
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()
    
    try:
        # Get PUUID
        platform, _ = infer_platform_and_region(tag_line)
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, "americas")
        if not account or 'puuid' not in account:
            raise HTTPException(status_code=404, detail="Player not found")
        
        puuid = account['puuid']
        
        # Get champion stats with filters
        # Note: Champion Mastery uses all game modes, so queue_id should be None
        champions = player_data_manager.get_best_champions(puuid, limit=limit, time_range=time_range, queue_id=queue_id)
        
        return {
            'success': True,
            'champions': champions
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/player/{game_name}/{tag_line}/role-stats")
async def get_player_role_stats(
    game_name: str,
    tag_line: str,
    time_range: str = None,
    queue_id: int = None
):
    """
    Get player's role statistics filtered by time_range and queue_id
    
    Query params:
    - time_range: Time range filter ("past-365")
    - queue_id: Queue ID filter (420 for Ranked Solo/Duo, 440 for Ranked Flex, 400 for Normal)
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()
    
    try:
        # Get PUUID
        platform, _ = infer_platform_and_region(tag_line)
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, "americas")
        if not account or 'puuid' not in account:
            raise HTTPException(status_code=404, detail="Player not found")
        
        puuid = account['puuid']
        
        # Get role stats with filters
        role_stats = player_data_manager.get_role_stats(puuid, time_range=time_range, queue_id=queue_id)
        
        return {
            'success': True,
            'role_stats': role_stats
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/player/{game_name}/{tag_line}/data-status")
async def get_player_data_status(game_name: str, tag_line: str):
    """
    Get player's data availability status

    Returns information about available player pack data:
    - Total number of patches
    - Total number of games
    - Earliest and latest patch
    - List of all patches
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    try:
        # Get account info (same as summary endpoint)
        try:
            account = await riot_client.get_account_by_riot_id(game_name, tag_line, region='americas')
        except Exception as e:
            # Handle Riot API errors more gracefully
            error_msg = str(e)
            if "decrypting" in error_msg.lower() or "400" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=f"Riot API authentication error. This may indicate an invalid or expired API key. Please check your RIOT_API_KEY_PRIMARY environment variable. Error: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=f"Failed to fetch account info: {error_msg}")
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        puuid = account['puuid']

        # Get player packs directory
        player_dir = Path("data/player_packs") / puuid

        if not player_dir.exists():
            return {
                "success": True,
                "puuid": puuid,
                "game_name": game_name,
                "tag_line": tag_line,
                "has_data": False,
                "total_patches": 0,
                "total_games": 0,
                "patches": [],
                "rank_types": {
                    "solo_duo": {"total_games": 0, "past_season_games": 0, "past_365_days_games": 0},
                    "flex": {"total_games": 0, "past_season_games": 0, "past_365_days_games": 0},
                    "normal": {"total_games": 0, "past_season_games": 0, "past_365_days_games": 0}
                }
            }

        # Read all pack files (including queue_id-specific packs)
        pack_files = sorted(player_dir.glob("pack_*.json"))

        if not pack_files:
            return {
                "success": True,
                "puuid": puuid,
                "game_name": game_name,
                "tag_line": tag_line,
                "has_data": False,
                "total_patches": 0,
                "total_games": 0,
                "patches": [],
                "rank_types": {
                    "solo_duo": {"total_games": 0, "past_season_games": 0, "past_365_days_games": 0},
                    "flex": {"total_games": 0, "past_season_games": 0, "past_365_days_games": 0},
                    "normal": {"total_games": 0, "past_season_games": 0, "past_365_days_games": 0}
                }
            }

        # Collect patch information, grouped by queue_id
        patches = []
        total_games = 0
        earliest_match_date = None
        latest_match_date = None
        
        # Track games by queue_id
        queue_games = {420: 0, 440: 0, 400: 0}  # solo_duo, flex, normal
        queue_past_season_games = {420: 0, 440: 0, 400: 0}
        queue_past_365_days_games = {420: 0, 440: 0, 400: 0}
        
        # Patch release date mapping for Season 2024 (14.1 - 14.24)
        # Also include patch 15.x (2025 season) for fallback date inference
        patch_release_dates = {
            # Season 2024 patches
            '14.1': datetime(2024, 1, 10), '14.2': datetime(2024, 1, 24), '14.3': datetime(2024, 2, 7),
            '14.4': datetime(2024, 2, 21), '14.5': datetime(2024, 3, 6), '14.6': datetime(2024, 3, 20),
            '14.7': datetime(2024, 4, 3), '14.8': datetime(2024, 4, 17), '14.9': datetime(2024, 5, 1),
            '14.10': datetime(2024, 5, 15), '14.11': datetime(2024, 5, 29), '14.12': datetime(2024, 6, 12),
            '14.13': datetime(2024, 6, 26), '14.14': datetime(2024, 7, 17), '14.15': datetime(2024, 7, 31),
            '14.16': datetime(2024, 8, 14), '14.17': datetime(2024, 8, 28), '14.18': datetime(2024, 9, 11),
            '14.19': datetime(2024, 9, 24), '14.20': datetime(2024, 10, 8), '14.21': datetime(2024, 10, 22),
            '14.22': datetime(2024, 11, 5), '14.23': datetime(2024, 11, 19), '14.24': datetime(2024, 12, 10),
            # Season 2025 patches (for date inference)
            '15.17': datetime(2025, 8, 26), '15.18': datetime(2025, 9, 10),
            '15.21': datetime(2025, 10, 28), '15.22': datetime(2025, 11, 5),
        }

        # Past Season date range: patch 14.1 (2024-01-09) to patch 14.25 (2025-01-06)
        past_season_start = datetime(2024, 1, 9)
        past_season_end = datetime(2025, 1, 6, 23, 59, 59, 999000)
        
        # Past 365 Days: from today - 365 days to today (UTC)
        today = datetime.now(timezone.utc)
        past_365_days_start = today - timedelta(days=365)

        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                pack = json.load(f)

            patch = pack.get("patch", "unknown")
            games = pack.get("total_games", 0)
            queue_id = pack.get("queue_id", 420)  # Default to Solo/Duo for legacy packs
            
            # Extract match dates from pack
            pack_earliest = pack.get("earliest_match_date")
            pack_latest = pack.get("latest_match_date")
            
            # If pack doesn't have match dates, try to infer from patch version first
            if not pack_earliest or not pack_latest:
                # Try to get patch release date
                patch_base = '.'.join(patch.split('.')[:2])  # "14.1.1" -> "14.1"
                if patch_base in patch_release_dates:
                    patch_release_date = patch_release_dates[patch_base]
                    # Use patch release date as fallback
                    if not pack_earliest:
                        pack_earliest = patch_release_date.isoformat()
                    if not pack_latest:
                        # Assume matches can be up to 2 weeks after patch release
                        pack_latest = (patch_release_date + timedelta(days=14)).isoformat()
            
            # Calculate past_season_games and past_365_days_games if not present
            past_season_games = pack.get("past_season_games")
            past_365_days_games = pack.get("past_365_days_games")
            
            # If these fields don't exist, calculate them from match dates (or inferred dates)
            if past_season_games is None or past_365_days_games is None:
                # If we have match dates (or inferred dates), estimate based on date range overlap
                if pack_earliest and pack_latest:
                    try:
                        # Parse dates
                        if isinstance(pack_earliest, str):
                            date_str = pack_earliest.replace('Z', '+00:00')
                            if '+' not in date_str and 'T' in date_str:
                                date_str = date_str + '+00:00'
                            earliest_dt = datetime.fromisoformat(date_str)
                        else:
                            earliest_dt = pack_earliest
                        
                        if isinstance(pack_latest, str):
                            date_str = pack_latest.replace('Z', '+00:00')
                            if '+' not in date_str and 'T' in date_str:
                                date_str = date_str + '+00:00'
                            latest_dt = datetime.fromisoformat(date_str)
                        else:
                            latest_dt = pack_latest
                        
                        # Remove timezone for comparison
                        if earliest_dt.tzinfo:
                            earliest_dt = earliest_dt.replace(tzinfo=None)
                        if latest_dt.tzinfo:
                            latest_dt = latest_dt.replace(tzinfo=None)
                        
                        # Check if date range overlaps with Past Season
                        if past_season_games is None:
                            # If date range overlaps with Past Season, estimate games proportionally
                            if earliest_dt <= past_season_end and latest_dt >= past_season_start:
                                # Calculate overlap proportion
                                overlap_start = max(earliest_dt, past_season_start)
                                overlap_end = min(latest_dt, past_season_end)
                                total_range = (latest_dt - earliest_dt).total_seconds()
                                overlap_range = (overlap_end - overlap_start).total_seconds()
                                if total_range > 0:
                                    past_season_games = int(games * (overlap_range / total_range))
                                else:
                                    past_season_games = games if past_season_start <= earliest_dt <= past_season_end else 0
                            else:
                                past_season_games = 0
                        
                        # Check if date range overlaps with Past 365 Days
                        if past_365_days_games is None:
                            # If latest date is within past 365 days, all games count
                            if latest_dt >= past_365_days_start:
                                past_365_days_games = games
                            elif earliest_dt >= past_365_days_start:
                                # Partial overlap - estimate proportionally
                                total_range = (latest_dt - earliest_dt).total_seconds()
                                overlap_range = (latest_dt - past_365_days_start).total_seconds()
                                if total_range > 0:
                                    past_365_days_games = int(games * (overlap_range / total_range))
                                else:
                                    past_365_days_games = games
                            else:
                                past_365_days_games = 0
                    except Exception as e:
                        print(f"Warning: Error calculating time range games for patch {patch}: {e}")
                        if past_season_games is None:
                            past_season_games = 0
                        if past_365_days_games is None:
                            past_365_days_games = 0
                else:
                    # No match dates available (even after inference), set to 0
                    if past_season_games is None:
                        past_season_games = 0
                    if past_365_days_games is None:
                        past_365_days_games = 0
            
            # Track games by queue_id (after calculating past_season_games and past_365_days_games)
            if queue_id in queue_games:
                queue_games[queue_id] += games
                queue_past_season_games[queue_id] += past_season_games if past_season_games is not None else 0
                queue_past_365_days_games[queue_id] += past_365_days_games if past_365_days_games is not None else 0
            
            # Parse and track earliest/latest match dates
            if pack_earliest:
                try:
                    # Handle both ISO format strings and datetime objects
                    if isinstance(pack_earliest, str):
                        # Handle different ISO formats
                        date_str = pack_earliest.replace('Z', '+00:00')
                        if '+' not in date_str and 'T' in date_str:
                            # Add UTC timezone if missing
                            date_str = date_str + '+00:00'
                        pack_earliest_dt = datetime.fromisoformat(date_str)
                    else:
                        pack_earliest_dt = pack_earliest
                    
                    # Convert to naive datetime for comparison if needed
                    if pack_earliest_dt.tzinfo is not None:
                        pack_earliest_dt = pack_earliest_dt.replace(tzinfo=None)
                    
                    if earliest_match_date is None or pack_earliest_dt < earliest_match_date:
                        earliest_match_date = pack_earliest_dt
                except Exception as e:
                    print(f"Warning: Error parsing earliest_match_date for patch {patch}: {pack_earliest}, error: {e}")
                    pass
            
            if pack_latest:
                try:
                    # Handle both ISO format strings and datetime objects
                    if isinstance(pack_latest, str):
                        # Handle different ISO formats
                        date_str = pack_latest.replace('Z', '+00:00')
                        if '+' not in date_str and 'T' in date_str:
                            # Add UTC timezone if missing
                            date_str = date_str + '+00:00'
                        pack_latest_dt = datetime.fromisoformat(date_str)
                    else:
                        pack_latest_dt = pack_latest
                    
                    # Convert to naive datetime for comparison if needed
                    if pack_latest_dt.tzinfo is not None:
                        pack_latest_dt = pack_latest_dt.replace(tzinfo=None)
                    
                    if latest_match_date is None or pack_latest_dt > latest_match_date:
                        latest_match_date = pack_latest_dt
                except Exception as e:
                    print(f"Warning: Error parsing latest_match_date for patch {patch}: {pack_latest}, error: {e}")
                    pass
            
            # Ensure pack_earliest and pack_latest are strings for JSON serialization
            if pack_earliest and not isinstance(pack_earliest, str):
                pack_earliest = pack_earliest.isoformat() if hasattr(pack_earliest, 'isoformat') else str(pack_earliest)
            if pack_latest and not isinstance(pack_latest, str):
                pack_latest = pack_latest.isoformat() if hasattr(pack_latest, 'isoformat') else str(pack_latest)

            patches.append({
                "patch": patch,
                "games": games,
                "earliest_match_date": pack_earliest,
                "latest_match_date": pack_latest,
                "past_season_games": past_season_games if past_season_games is not None else 0,
                "past_365_days_games": past_365_days_games if past_365_days_games is not None else 0
            })
            total_games += games

        # Sort by patch version
        patches_sorted = sorted(patches, key=lambda x: x["patch"])

        # Format earliest/latest match dates for JSON serialization
        earliest_match_date_str = None
        latest_match_date_str = None
        if earliest_match_date:
            try:
                earliest_match_date_str = earliest_match_date.isoformat()
            except:
                pass
        if latest_match_date:
            try:
                latest_match_date_str = latest_match_date.isoformat()
            except:
                pass

        # Calculate total games in Past Season and Past 365 Days
        total_past_season_games = sum(p.get("past_season_games", 0) for p in patches_sorted)
        total_past_365_days_games = sum(p.get("past_365_days_games", 0) for p in patches_sorted)

        return {
            "success": True,
            "puuid": puuid,
            "game_name": game_name,
            "tag_line": tag_line,
            "has_data": True,
            "total_patches": len(patches_sorted),
            "total_games": total_games,
            "total_past_season_games": total_past_season_games,
            "total_past_365_days_games": total_past_365_days_games,
            "earliest_patch": patches_sorted[0]["patch"] if patches_sorted else None,
            "latest_patch": patches_sorted[-1]["patch"] if patches_sorted else None,
            "earliest_match_date": earliest_match_date_str,
            "latest_match_date": latest_match_date_str,
            "patches": patches_sorted,
            "rank_types": {
                "solo_duo": {
                    "total_games": queue_games[420],
                    "past_season_games": queue_past_season_games[420],
                    "past_365_days_games": queue_past_365_days_games[420]
                },
                "flex": {
                    "total_games": queue_games[440],
                    "past_season_games": queue_past_season_games[440],
                    "past_365_days_games": queue_past_365_days_games[440]
                },
                "normal": {
                    "total_games": queue_games[400],
                    "past_season_games": queue_past_season_games[400],
                    "past_365_days_games": queue_past_365_days_games[400]
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting data status: {str(e)}")


@app.get("/api/player/{game_name}/{tag_line}/progress")
async def get_player_progress(game_name: str, tag_line: str):
    """
    Get player's progress data across patches (time series)

    Returns metrics progression for visualization:
    - Combat Power
    - KDA
    - Win Rate
    - Objective Rate
    - Gold Per Minute
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    try:
        # Get account info
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, region='americas')
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        puuid = account['puuid']

        # Get player packs directory
        player_dir = Path("data/player_packs") / puuid

        if not player_dir.exists():
            return {
                "success": True,
                "data": []
            }

        # Read all pack files
        pack_files = sorted(player_dir.glob("pack_*.json"))

        if not pack_files:
            return {
                "success": True,
                "data": []
            }

        # Collect progress data across patches
        progress_data = []

        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                pack = json.load(f)

            patch = pack.get("patch", "unknown")

            # Calculate aggregated metrics from by_cr (champion-role combinations)
            by_cr = pack.get("by_cr", [])

            if not by_cr:
                continue

            total_games = 0
            total_wins = 0
            total_combat_power = 0
            total_kda = 0
            total_obj_rate = 0
            total_gold = 0

            for cr in by_cr:
                games = cr.get("games", 0)
                total_games += games
                total_wins += cr.get("wins", 0)

                # Weight by games
                total_combat_power += cr.get("combat_power", 0) * games
                total_kda += cr.get("kda_adj", 0) * games
                total_obj_rate += cr.get("obj_rate", 0) * games
                total_gold += cr.get("gold_per_min", 0) * games

            if total_games == 0:
                continue

            # Calculate averages
            avg_combat_power = total_combat_power / total_games
            avg_kda = total_kda / total_games
            avg_obj_rate = total_obj_rate / total_games
            avg_gold = total_gold / total_games
            win_rate = total_wins / total_games

            progress_data.append({
                "patch": patch,
                "combat_power": round(avg_combat_power, 2),
                "kda": round(avg_kda, 2),
                "win_rate": round(win_rate, 3),
                "objective_rate": round(avg_obj_rate, 3),
                "gold_per_min": round(avg_gold, 1),
                "games": total_games
            })

        # Sort by patch version
        progress_data.sort(key=lambda x: x["patch"])

        return {
            "success": True,
            "data": progress_data
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Progress API error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting progress data: {str(e)}")


@app.get("/api/player/{game_name}/{tag_line}/skills")
async def get_player_skills(game_name: str, tag_line: str, top_n: int = 3):
    """
    Get player's skill analysis (5-dimensional radar chart data)

    Returns top N champions with skill scores:
    - Offense: damage output, kills, combat power
    - Defense: damage taken mitigation, death rate, survival
    - Teamwork: assists, objective participation
    - Economy: gold efficiency, CS per minute
    - Vision: vision score, ward placement

    Each skill is normalized to 0-100 scale
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    try:
        # Load champion ID to name mapping
        champion_mapping = {}
        mapping_file = Path("data/static/mappings/champions.json")
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                champion_mapping = json.load(f)

        # Get account info
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, region='americas')
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        puuid = account['puuid']

        # Get player packs directory
        player_dir = Path("data/player_packs") / puuid

        if not player_dir.exists():
            return {
                "success": True,
                "data": []
            }

        # Read all pack files to aggregate champion data
        pack_files = sorted(player_dir.glob("pack_*.json"))

        if not pack_files:
            return {
                "success": True,
                "data": []
            }

        # Aggregate data by champion across all patches
        champion_data = {}

        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                pack = json.load(f)

            by_cr = pack.get("by_cr", [])

            for cr in by_cr:
                # Get champion ID and map to name
                champ_id = cr.get("champ_id")
                if champ_id is None:
                    continue

                champion = champion_mapping.get(str(champ_id), "Unknown")
                champion_id_value = champ_id  # Store for response
                role = cr.get("role", "")
                games = cr.get("games", 0)

                if games == 0:
                    continue

                # Create unique key for champion-role
                key = f"{champion}_{role}" if role else champion

                if key not in champion_data:
                    champion_data[key] = {
                        "champion": champion,
                        "champion_id": champion_id_value,
                        "role": role,
                        "games": 0,
                        "wins": 0,
                        "kills": 0,
                        "deaths": 0,
                        "assists": 0,
                        "damage_dealt": 0,
                        "damage_taken": 0,
                        "gold": 0,
                        "combat_power": 0,
                        "obj_rate": 0,
                        "vision_score": 0
                    }

                # Aggregate metrics (weighted by games)
                champion_data[key]["games"] += games
                champion_data[key]["wins"] += cr.get("wins", 0)
                champion_data[key]["kills"] += cr.get("kills", 0) * games
                champion_data[key]["deaths"] += cr.get("deaths", 0) * games
                champion_data[key]["assists"] += cr.get("assists", 0) * games
                champion_data[key]["damage_dealt"] += cr.get("damage_dealt", 0) * games
                champion_data[key]["damage_taken"] += cr.get("damage_taken", 0) * games
                champion_data[key]["gold"] += cr.get("gold_per_min", 0) * games
                champion_data[key]["combat_power"] += cr.get("combat_power", 0) * games
                champion_data[key]["obj_rate"] += cr.get("obj_rate", 0) * games
                champion_data[key]["vision_score"] += cr.get("vision_score", 0) * games

        # Calculate averages and skill scores
        skills_data = []

        for key, data in champion_data.items():
            games = data["games"]
            if games == 0:
                continue

            # Calculate averages
            avg_kills = data["kills"] / games
            avg_deaths = data["deaths"] / games
            avg_assists = data["assists"] / games
            avg_damage_dealt = data["damage_dealt"] / games
            avg_damage_taken = data["damage_taken"] / games
            avg_gold = data["gold"] / games
            avg_combat_power = data["combat_power"] / games
            avg_obj_rate = data["obj_rate"] / games
            avg_vision = data["vision_score"] / games
            kda = (avg_kills + avg_assists) / max(avg_deaths, 1)
            win_rate = data["wins"] / games

            # Calculate 5 skill dimensions (0-100 scale)

            # 1. Offense: damage dealt, kills, combat power
            offense_score = min(100, (
                (avg_damage_dealt / 600) * 40 +  # Normalize damage (assume 600 avg)
                (avg_kills / 8) * 30 +             # Normalize kills (assume 8 avg)
                (avg_combat_power / 1200) * 30    # Normalize combat power
            ))

            # 2. Defense: survival (inverse deaths), damage taken mitigation
            # Lower deaths = higher defense score
            death_score = max(0, 100 - (avg_deaths / 8) * 100)  # Assume 8 deaths = 0 score
            defense_score = min(100, (
                death_score * 0.6 +                              # 60% weight on survival
                min(100, (avg_damage_taken / 25000) * 100) * 0.4  # 40% weight on tankiness
            ))

            # 3. Teamwork: assists, objective rate
            teamwork_score = min(100, (
                (avg_assists / 10) * 60 +          # Normalize assists (assume 10 avg)
                (avg_obj_rate) * 100 * 0.4         # obj_rate already 0-1
            ))

            # 4. Economy: gold per minute
            # Assume 400 gold/min = 100 score
            economy_score = min(100, (avg_gold / 400) * 100)

            # 5. Vision: vision score
            # Assume 60 vision score = 100 score
            vision_score = min(100, (avg_vision / 60) * 100)

            skills_data.append({
                "champion": data["champion"],
                "champion_id": data["champion_id"],
                "role": data["role"],
                "games": games,
                "win_rate": round(win_rate, 3),
                "skills": [
                    {"subject": "Offense", "value": round(offense_score, 1), "fullMark": 100},
                    {"subject": "Defense", "value": round(defense_score, 1), "fullMark": 100},
                    {"subject": "Teamwork", "value": round(teamwork_score, 1), "fullMark": 100},
                    {"subject": "Economy", "value": round(economy_score, 1), "fullMark": 100},
                    {"subject": "Vision", "value": round(vision_score, 1), "fullMark": 100}
                ]
            })

        # Sort by games played (descending)
        skills_data.sort(key=lambda x: x["games"], reverse=True)

        # Return top N champions
        return {
            "success": True,
            "data": skills_data[:top_n]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Skills API error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting skills data: {str(e)}")


@app.get("/api/player/{game_name}/{tag_line}/matches")
async def get_player_matches(game_name: str, tag_line: str, limit: int = 20):
    """
    Get player's recent matches list (for timeline analysis)

    Args:
        game_name: Player's game name
        tag_line: Player's tag line
        limit: Number of matches to return (default: 20)

    Returns:
        List of match information including:
        - match_id: Match identifier
        - game_creation: Timestamp
        - game_duration: Duration in seconds
        - champion_id, champion_name: Champion info
        - role: Position played
        - win: Win/loss
        - kills, deaths, assists: KDA stats
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    try:
        # Get account info
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, region='americas')
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        puuid = account['puuid']

        # Get matches from PlayerDataManager
        matches = player_data_manager.get_recent_matches(puuid, limit=limit)

        return {
            "success": True,
            "puuid": puuid,
            "game_name": game_name,
            "tag_line": tag_line,
            "total": len(matches),
            "matches": matches
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting matches: {str(e)}")


# ============================================================================
# DDragon Static Data Proxy APIs
# ============================================================================

@app.get("/api/v1/static/champions")
async def get_static_champions():
    """
    Get DDragon champion data

    Returns:
        Champion data from DDragon (latest version)

    Note:
        For detailed DDragon data, consider using the CDN directly:
        https://ddragon.leagueoflegends.com/cdn/15.1.1/data/en_US/champion.json
    """
    try:
        champion_data = data_dragon.get_champions()

        return {
            "success": True,
            "data": champion_data,
            "note": "For complete DDragon data with version control, use https://ddragon.leagueoflegends.com"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching champion data: {str(e)}")


@app.get("/api/v1/static/items")
async def get_static_items():
    """
    Get DDragon item data

    Returns:
        Item data from DDragon (latest version)

    Note:
        For detailed DDragon data, consider using the CDN directly:
        https://ddragon.leagueoflegends.com/cdn/15.1.1/data/en_US/item.json
    """
    try:
        item_data = data_dragon.get_items()

        return {
            "success": True,
            "data": item_data,
            "note": "For complete DDragon data with version control, use https://ddragon.leagueoflegends.com"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching item data: {str(e)}")


@app.get("/api/v1/static/runes")
async def get_static_runes():
    """
    Get DDragon rune data

    Returns:
        Rune data from DDragon (latest version)

    Note:
        For detailed DDragon data, consider using the CDN directly:
        https://ddragon.leagueoflegends.com/cdn/15.1.1/data/en_US/runesReforged.json
    """
    try:
        rune_data = data_dragon.get_runes()

        return {
            "success": True,
            "data": rune_data,
            "note": "For complete DDragon data with version control, use https://ddragon.leagueoflegends.com"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rune data: {str(e)}")


# ============================================================================
# Player Info APIs
# ============================================================================

@app.get("/api/v1/player/{game_name}/{tag_line}/rank")
async def get_player_rank(game_name: str, tag_line: str, platform: str = "na1"):
    """
    Get player's basic summoner information

    NOTE: For detailed rank information (tier, division, LP), please use the OP.GG profile
    endpoint which provides comprehensive rank data.

    Args:
        game_name: Player's game name (e.g., "s1ne")
        tag_line: Player's tag line (e.g., "na1")
        platform: Platform/region (default: "na1")

    Returns:
        Player's basic summoner information
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    try:
        # Get account info
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, region='americas')
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        puuid = account['puuid']

        # Get summoner info
        summoner = await riot_client.get_summoner_by_puuid(puuid, platform=platform)
        if not summoner:
            raise HTTPException(status_code=404, detail="Summoner not found")

        return {
            "success": True,
            "puuid": puuid,
            "summoner": summoner,
            "note": "For detailed rank information, use the /api/player/{game_name}/{tag_line}/summary endpoint which includes OP.GG profile data with complete rank details."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting player rank: {str(e)}")


@app.get("/api/v1/player/{game_name}/{tag_line}/recent-matches")
async def get_player_recent_matches(
    game_name: str,
    tag_line: str,
    platform: str = "na1",
    count: int = 20
):
    """
    Get player's recent match IDs

    Args:
        game_name: Player's game name (e.g., "s1ne")
        tag_line: Player's tag line (e.g., "na1")
        platform: Platform/region (default: "na1")
        count: Number of recent matches to fetch (default: 20, max: 100)

    Returns:
        List of recent match IDs
    """
    try:
        # Get account info
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, region='americas')
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        puuid = account['puuid']

        # Limit count
        count = min(count, 100)

        # Get match IDs
        # Convert platform to region for API call
        region = 'americas' if platform in ['na1', 'br1', 'la1', 'la2'] else 'europe' if platform in ['euw1', 'eun1'] else 'asia'
        match_ids = await riot_client.get_match_history(
            puuid=puuid,
            region=region,
            count=count,
            queue=420  # Ranked Solo/Duo
        )

        return {
            "success": True,
            "puuid": puuid,
            "game_name": game_name,
            "tag_line": tag_line,
            "platform": platform,
            "count": len(match_ids),
            "match_ids": match_ids
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recent matches: {str(e)}")


# ============================================================================
# Chat Endpoint - SSE Streaming
# ============================================================================

from fastapi.responses import StreamingResponse
from src.agents.chat.meta_chat_agent import MetaChatAgent


async def execute_agent(agent_id: str, packs_dir: str, puuid: str, region: str, **params):
    """
    Execute a specific agent and yield SSE messages

    Args:
        agent_id: Agent identifier (e.g., "weakness-analysis", "annual-summary")
        packs_dir: Path to player pack directory
        puuid: Player PUUID
        region: Player region
        **params: Additional agent-specific parameters (role, champion_id, match_id, etc.)

    Yields:
        SSE formatted messages
    """
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    # Default parameters
    recent_count = params.get('recent_count', 5)
    time_range = params.get('time_range', None)
    queue_id = params.get('queue_id', None)

    # Agent-specific execution logic (unified interface)
    if agent_id == "weakness-analysis":
        from src.agents.player_analysis.weakness_analysis.agent import WeaknessAnalysisAgent

        agent = WeaknessAnalysisAgent(model="haiku")
        for message in agent.run_stream(packs_dir, recent_count, time_range, queue_id):
            yield message

    elif agent_id == "annual-summary":
        from src.agents.player_analysis.annual_summary.agent import AnnualSummaryAgent

        agent = AnnualSummaryAgent(model="haiku")
        for message in agent.run_stream(packs_dir, time_range, queue_id):
            yield message

    elif agent_id == "champion-recommendation":
        from src.agents.player_analysis.champion_recommendation.agent import ChampionRecommendationAgent
        agent = ChampionRecommendationAgent(model="haiku")
        for message in agent.run_stream(packs_dir, time_range, queue_id):
            yield message

    elif agent_id == "role-specialization":
        role = params.get('role')
        if not role:
            yield f"data: {{\"error\": \"Role specialization requires a role parameter (TOP/JUNGLE/MID/ADC/SUPPORT).\"}}\n\n"
            return

        from src.agents.player_analysis.role_specialization.agent import RoleSpecializationAgent
        agent = RoleSpecializationAgent(model="haiku")
        for message in agent.run_stream(packs_dir, role.upper(), recent_count, time_range, queue_id):
            yield message

    elif agent_id == "champion-mastery":
        champion_id = params.get('champion_id')
        if not champion_id:
            yield f"data: {{\"error\": \"Champion mastery requires a champion_id parameter.\"}}\n\n"
            return

        from src.agents.player_analysis.champion_mastery.agent import ChampionMasteryAgent
        agent = ChampionMasteryAgent(model="haiku")
        for message in agent.run_stream(packs_dir, int(champion_id), recent_count, time_range, queue_id):
            yield message

    elif agent_id == "timeline-deep-dive":
        match_id = params.get('match_id')
        if not match_id:
            yield f"data: {{\"error\": \"Timeline analysis requires a match_id parameter.\"}}\n\n"
            return

        from src.agents.player_analysis.timeline_deep_dive.agent import TimelineDeepDiveAgent
        agent = TimelineDeepDiveAgent(model="haiku")
        for message in agent.run_stream(packs_dir, match_id, recent_count, time_range, queue_id):
            yield message

    elif agent_id == "version-trends":
        from src.agents.player_analysis.multi_version.agent import MultiVersionAgent
        agent = MultiVersionAgent(model="haiku")
        for message in agent.run_stream(packs_dir, time_range, queue_id):
            yield message

    elif agent_id == "friend-comparison":
        friend_name = params.get('friend_name')
        if not friend_name:
            yield f"data: {{\"error\": \"Friend comparison requires friend_name parameter (name#tag).\"}}\n\n"
            return

        # Parse friend name (format: "name#tag")
        try:
            friend_game_name, friend_tag = friend_name.split('#', 1)
        except ValueError:
            yield f"data: {{\"error\": \"Invalid friend name format. Expected format: name#tag\"}}\n\n"
            return

        # Get friend's PUUID and packs_dir
        friend_account = await riot_client.get_account_by_riot_id(friend_game_name, friend_tag, region)
        if not friend_account:
            yield f"data: {{\"error\": \"Friend player {friend_name} not found\"}}\n\n"
            return

        friend_puuid = friend_account['puuid']
        friend_packs_dir = player_data_manager.get_packs_dir(friend_puuid)
        if not friend_packs_dir:
            yield f"data: {{\"error\": \"Friend player data not available\"}}\n\n"
            return

        from src.agents.player_analysis.friend_comparison.agent import FriendComparisonAgent
        agent = FriendComparisonAgent(model="haiku")

        # Get current player name from PUUID
        from services.riot_client import get_summoner_name_by_puuid
        player_name = f"Player#{region}"  # Fallback

        for message in agent.run_stream(
            packs_dir=packs_dir,
            friend_packs_dir=friend_packs_dir,
            player_name=player_name,
            friend_name=friend_name,
            recent_count=recent_count,
            time_range=time_range,
            queue_id=queue_id
        ):
            yield message

    elif agent_id == "build-simulator":
        champion_id = params.get('champion_id')
        if not champion_id:
            yield f"data: {{\"error\": \"Build simulator requires champion_id parameter.\"}}\n\n"
            return

        build_a = params.get('build_a')
        build_b = params.get('build_b')
        role = params.get('role', 'TOP')

        from src.agents.player_analysis.build_simulator.agent import BuildSimulatorAgent
        agent = BuildSimulatorAgent(model_id="haiku")
        for message in agent.run_stream(
            packs_dir=packs_dir,
            champion_id=int(champion_id),
            build_a=build_a,
            build_b=build_b,
            role=role,
            recent_count=recent_count,
            time_range=time_range,
            queue_id=queue_id
        ):
            yield message

    else:
        yield f"data: {{\"error\": \"Unknown agent: {agent_id}\"}}\n\n"


async def get_player_summary_data(puuid: str, packs_dir: str) -> Dict[str, Any]:
    """
    Load player summary data for ChatMasterAgent context

    Returns basic statistics needed for decision making:
    - Total games
    - Recent match count
    - Patches played
    - Recent match list (for match ID extraction)

    Args:
        puuid: Player PUUID
        packs_dir: Path to player packs directory

    Returns:
        Dict with player context data
    """
    import os
    import json
    from pathlib import Path

    try:
        # Load all available pack files
        packs_path = Path(packs_dir)
        if not packs_path.exists():
            return {
                "total_games": 0,
                "recent_match_count": 0,
                "patches": [],
                "recent_matches": []
            }

        pack_files = sorted(packs_path.glob("pack_*.json"))

        total_games = 0
        patches = []
        all_matches = []

        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                pack_data = json.load(f)

            # Extract patch
            patch = pack_file.stem.replace("pack_", "")
            patches.append(patch)

            # Count games
            by_champion = pack_data.get("by_champion_role", {})
            for champ_data in by_champion.values():
                for role_data in champ_data.values():
                    total_games += role_data.get("total_games", 0)

        # Get recent match list from matches_data.json if available
        matches_data_file = packs_path / "matches_data.json"
        if matches_data_file.exists():
            with open(matches_data_file, 'r') as f:
                matches_data = json.load(f)
                all_matches = matches_data.get("matches", [])[:20]  # Last 20 matches

        return {
            "total_games": total_games,
            "recent_match_count": len(all_matches),
            "patches": patches,
            "recent_matches": all_matches  # List of match objects with match_id, champion, outcome, etc.
        }

    except Exception as e:
        print(f"⚠️ Error loading player summary data: {e}")
        return {
            "total_games": 0,
            "recent_match_count": 0,
            "patches": [],
            "recent_matches": []
        }


# ============================================================================
# Share API Endpoints
# ============================================================================

class ShareCreateRequest(BaseModel):
    """Request model for creating a share"""
    agent_type: str
    gameName: str
    tagLine: str
    region: str = "na1"
    report_content: str
    total_games: Optional[int] = None
    time_range: Optional[str] = None
    model: str = "haiku"


@app.post("/api/share/create")
async def create_share(request: ShareCreateRequest):
    """
    Create shareable link for agent report

    Args:
        request: ShareCreateRequest with agent type, player info, and report content

    Returns:
        JSON with success status and share_id
    """
    try:
        print(f"[ShareAPI] Creating share for {request.gameName}#{request.tagLine}")
        print(f"[ShareAPI] Agent type: {request.agent_type}")
        print(f"[ShareAPI] Report content length: {len(request.report_content) if request.report_content else 0}")

        # Generate unique share ID (8 characters)
        import uuid
        share_id = str(uuid.uuid4())[:8]

        # Prepare share data
        share_data = {
            "share_id": share_id,
            "agent_type": request.agent_type,
            "player": {
                "gameName": request.gameName,
                "tagLine": request.tagLine,
                "region": request.region
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_content": request.report_content,
            "metadata": {
                "total_games": request.total_games,
                "time_range": request.time_range,
                "model": request.model
            }
        }

        # Save to file (use absolute path)
        backend_dir = Path(__file__).parent.parent
        share_dir = backend_dir / "data" / "shared_reports"
        share_dir.mkdir(parents=True, exist_ok=True)

        share_file = share_dir / f"{share_id}.json"

        print(f"[ShareAPI] Saving to: {share_file}")

        with open(share_file, 'w', encoding='utf-8') as f:
            json.dump(share_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Created share: {share_id} for {request.gameName}#{request.tagLine}")

        return {"success": True, "share_id": share_id}

    except Exception as e:
        print(f"❌ Error creating share: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create share: {str(e)}")


@app.get("/api/share/{share_id}")
async def get_share(share_id: str):
    """
    Get shared report content

    Args:
        share_id: Unique share identifier

    Returns:
        JSON with share data including report content and player info
    """
    try:
        # Use absolute path
        backend_dir = Path(__file__).parent.parent
        share_file = backend_dir / "data" / "shared_reports" / f"{share_id}.json"

        if not share_file.exists():
            raise HTTPException(status_code=404, detail="Share not found")

        with open(share_file, 'r', encoding='utf-8') as f:
            share_data = json.load(f)

        print(f"✅ Retrieved share: {share_id}")

        return share_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting share: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Chat API Endpoint
# ============================================================================

@app.get("/v1/chat")
async def chat_endpoint(
    message: str,
    game_name: str,
    tag_line: str,
    session_id: Optional[str] = None,
    region: str = "na1"
):
    """
    SSE streaming chat endpoint with multi-turn conversation support

    Workflow:
    1. Get or create chat session
    2. ChatMasterAgent decides action (answer, ask, call subagent, custom)
    3. Execute action and stream response
    4. Update session history

    Query Parameters:
        message: User's message
        game_name: Player game name
        tag_line: Player tag line
        session_id: Optional session ID for conversation continuity
        region: Player region (default: na1)
    """
    async def event_generator():
        try:
            # Format SSE message
            def sse(event_type: str, content: str) -> str:
                return f"data: {json.dumps({'type': event_type, 'content': content})}\n\n"

            yield sse("thinking", "Processing your request...")

            # Step 1: Get player PUUID
            account = await riot_client.get_account_by_riot_id(game_name, tag_line, region)
            if not account:
                yield sse("error", f"Player {game_name}#{tag_line} not found")
                return

            puuid = account["puuid"]

            # Step 2: Get or create session
            from src.agents.chat.session_manager import get_session_manager

            session_manager = get_session_manager()

            if not session_id:
                # Generate new session ID
                import time
                new_session_id = f"{game_name}_{tag_line}_{int(time.time())}"
            else:
                new_session_id = session_id

            session = session_manager.get_or_create_session(
                session_id=new_session_id,
                puuid=puuid,
                game_name=game_name,
                tag_line=tag_line,
                region=region
            )

            yield sse("routing", f"Session: {session.session_id[:8]}... (Turn {len(session.history) // 2 + 1})")

            # Step 3: Wait for data preparation
            yield sse("executing", "Preparing player data...")
            await player_data_manager.wait_for_data(puuid=puuid, timeout=120)

            packs_dir = player_data_manager.get_packs_dir(puuid)
            if not packs_dir:
                yield sse("error", "Player data not ready")
                return

            # Step 4: Load player data for context
            player_data = await get_player_summary_data(puuid, packs_dir)

            # Step 5: ChatMasterAgent decision
            from src.agents.chat.chat_master_agent import ChatMasterAgent

            chat_master = ChatMasterAgent(model="haiku")
            decision = chat_master.process_message(
                user_message=message,
                session_history=session.get_history(),
                player_data=player_data
            )

            # Add user message to session
            session.add_message("user", message)

            # Step 6: Execute decision
            if decision.action == "answer_directly":
                # Direct answer without calling sub-agent
                session.add_message("assistant", decision.content)
                yield sse("report", decision.content)
                yield sse("done", "")

            elif decision.action == "ask_user":
                # Ask clarification question
                session.add_message("assistant", decision.content)
                yield sse("question", decision.content)
                if decision.options:
                    yield sse("options", json.dumps(decision.options))
                yield sse("done", "")

            elif decision.action == "call_subagent":
                # Call analysis sub-agent
                subagent_id = decision.subagent_id
                params = decision.params or {}

                schema = chat_master.get_subagent_schema(subagent_id)
                if not schema:
                    yield sse("error", f"Unknown sub-agent: {subagent_id}")
                    return

                agent_name = schema["name"]
                yield sse("routing", f"Using {agent_name}...")

                # Execute sub-agent with streaming
                try:
                    async for agent_message in execute_agent(subagent_id, packs_dir, puuid, region, **params):
                        yield agent_message
                except Exception as e:
                    yield sse("error", f"Sub-agent execution error: {str(e)}")
                    return

                yield sse("done", "")

            elif decision.action == "custom_analysis":
                # Custom analysis using quantitative metrics
                yield sse("planning", "📋 Parsing analysis request...")

                try:
                    from src.agents.chat.custom_analysis.agent import CustomAnalysisAgent
                    from src.agents.chat.custom_analysis.query_parser import parse_query_with_llm
                    from src.agents.shared.bedrock_adapter import BedrockLLM

                    # Parse query into two GroupFilters
                    parser_llm = BedrockLLM(model="haiku")
                    group1_filter, group2_filter = parse_query_with_llm(message, parser_llm)

                    yield sse("planning", f"✅ Comparing: {group1_filter.name} vs {group2_filter.name}")

                    # Initialize custom analysis agent
                    custom_agent = CustomAnalysisAgent(model="haiku")

                    # Stream custom analysis
                    full_report = ""
                    for message_data in custom_agent.run_stream(
                        user_query=message,
                        packs_dir=packs_dir,
                        group1_filter=group1_filter,
                        group2_filter=group2_filter
                    ):
                        yield message_data
                        # Accumulate report content
                        if '"type": "chunk"' in message_data:
                            import json
                            try:
                                msg_json = json.loads(message_data.split("data: ")[1])
                                full_report += msg_json.get("content", "")
                            except:
                                pass

                    # Store in session
                    session.add_message("assistant", full_report)

                except Exception as e:
                    print(f"❌ Custom analysis error: {e}")
                    import traceback
                    traceback.print_exc()
                    yield sse("error", f"Custom analysis error: {str(e)}")
                    return

                yield sse("done", "")

            else:
                yield sse("error", f"Unknown action type: {decision.action}")

        except Exception as e:
            print(f"❌ Chat endpoint error: {e}")
            import traceback
            traceback.print_exc()
            yield sse("error", f"Error: {str(e)}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Rift Rewind API Server...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔄 ReDoc: http://localhost:8000/redoc")
    print("\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
