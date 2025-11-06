"""
Rift Rewind API Server - FastAPI Implementation
Provides RESTful API endpoints for Risk Forecaster and Annual Summary agents
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
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
        "timestamp": datetime.now().isoformat(),
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
            "timestamp": datetime.now().isoformat(),
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
    Fetch a year's worth of match data for a player (matches + timelines)

    This endpoint triggers a background task to fetch all matches and timelines
    for a player over the specified time period. Use the task_id to check status.

    **Processing time**: 5-30 minutes depending on match count

    **Parameters**:
    - game_name: Player's game name (e.g., "S1NE")
    - tag_line: Player's tag line (e.g., "NA1")
    - region: Region code (na1, euw1, kr, etc.)
    - days: Number of days to fetch (default: 365)
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
        print(f"   Region: {request.region}, Days: {request.days}")
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
                "created_at": datetime.now().isoformat(),
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
                    fetch_tasks[task_id]["started_at"] = datetime.now().isoformat()

                # Step 2: Use PlayerDataManager to prepare data
                print(f"🚀 Starting PlayerDataManager.prepare_player_data()...")
                job = await player_data_manager.prepare_player_data(
                    puuid=puuid,
                    region=request.region,
                    game_name=request.game_name,
                    tag_line=request.tag_line,
                    days=request.days
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
                    fetch_tasks[task_id]["completed_at"] = datetime.now().isoformat()
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
                    fetch_tasks[task_id]["failed_at"] = datetime.now().isoformat()

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
    time_range: Optional[str] = Field(None, description="Time range filter: '2024-01-01' for 2024 full year, 'past-365' for past 365 days")

class AgentResponse(BaseModel):
    """Generic Agent Response Model"""
    success: bool
    agent: str
    detailed: Optional[str] = Field(None, description="Complete detailed report")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured data (backward compatibility)")
    error: Optional[str] = None


@app.post("/v1/agents/weakness-analysis")
async def weakness_analysis(request: AgentRequest):
    """Weakness Diagnosis - Weakness diagnosis analysis (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎯 Weakness Analysis Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Load data and build prompt
            from src.agents.player_analysis.weakness_analysis.tools import (
                load_recent_data,
                identify_weaknesses,
                format_analysis_for_prompt
            )
            from src.agents.player_analysis.weakness_analysis.prompts import build_narrative_prompt
            from src.agents.shared.insight_detector import InsightDetector

            recent_data = load_recent_data(packs_dir, request.recent_count or 5)
            weaknesses = identify_weaknesses(recent_data)

            # Automated insight detection
            insight_detector = InsightDetector()
            insights = insight_detector.detect_insights(weaknesses)
            weaknesses['automated_insights'] = [insight.to_dict() for insight in insights]
            weaknesses['insight_summary'] = insight_detector.generate_summary(insights)

            formatted_data = format_analysis_for_prompt(weaknesses)
            prompts = build_narrative_prompt(weaknesses, formatted_data)

            # Step 2: Use generic stream helper (supports model switching)
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
async def _extract_postgame_features(timeline_data: dict, target_puuid: str, match_id: str, packs_dir: str) -> tuple:
    """Extract match_features and timeline_features from timeline data and match data"""
    import json
    from pathlib import Path

    # Read match data from local matches directory (avoid PUUID mismatch issues)
    matches_dir = Path(packs_dir) / "matches"
    match_file = matches_dir / f"{match_id}.json"

    if not match_file.exists():
        raise ValueError(f"Match data file not found: {match_file}")

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
    """Annual Summary - Annual summary analysis (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n📅 Annual Summary Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Load player pack data and build prompt
            from src.agents.player_analysis.annual_summary.tools import (
                load_all_annual_packs,
                format_analysis_for_prompt,
                generate_comprehensive_annual_analysis
            )
            from src.agents.player_analysis.annual_summary.prompts import build_narrative_prompt

            # Load packs with optional time range filter
            time_range = getattr(request, 'time_range', None)
            all_packs_dict = load_all_annual_packs(packs_dir, time_range=time_range)

            print(f"📊 Loaded {len(all_packs_dict)} patches" + (f" (time_range: {time_range})" if time_range else ""))

            analysis = generate_comprehensive_annual_analysis(all_packs_dict)
            formatted_analysis = format_analysis_for_prompt(analysis)
            prompts = build_narrative_prompt(analysis, formatted_analysis)

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
                format_analysis_for_prompt
            )
            from src.agents.player_analysis.champion_mastery.prompts import build_narrative_prompt

            analysis = generate_comprehensive_mastery_analysis(
                champion_id=request.champion_id,
                packs_dir=packs_dir
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
            recent_packs = load_recent_packs(packs_dir, window_size=window_size, time_range=time_range)

            print(f"📊 Loaded {len(recent_packs)} patches" + (f" (time_range: {time_range})" if time_range else ""))

            analysis = analyze_progress(recent_packs)
            formatted_data = format_analysis_for_prompt(analysis)
            prompts = build_narrative_prompt(analysis, formatted_data)

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
                days=30
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

            player1_data = load_player_data(current_player_packs_dir)
            player2_data = load_player_data(friend_packs_dir)
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
                format_analysis_for_prompt
            )
            from src.agents.player_analysis.role_specialization.prompts import build_narrative_prompt

            role = request.role.upper()
            # Map ADC → BOTTOM for backend compatibility
            if role == 'ADC':
                role = 'BOTTOM'
            analysis = generate_comprehensive_role_analysis(role, packs_dir)
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
    """Champion Recommendation - Champion recommendation (SSE Stream output, supports extended thinking + model switching)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎯 Champion Recommendation Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Load player pack data and build prompt
            from src.agents.player_analysis.champion_recommendation.tools import (
                analyze_champion_pool,
                generate_recommendations,
                format_analysis_for_prompt
            )
            from src.agents.player_analysis.champion_recommendation.prompts import build_narrative_prompt

            champion_pool = analyze_champion_pool(packs_dir)
            recommendations = generate_recommendations(champion_pool)
            formatted_data = format_analysis_for_prompt(champion_pool, recommendations)
            prompts = build_narrative_prompt(champion_pool, recommendations, formatted_data)

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


@app.post("/v1/agents/multi-version")
async def multi_version_comparison(request: AgentRequest):
    """Multi-Version Analysis - Cross-version performance trend analysis (SSE Stream output)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n🎮 Multi-Version Analysis Stream (Model: {request.model or 'haiku'})\n{'='*60}")

            # Step 0: Wait for data preparation to complete
            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)

            # Get packs directory
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            print(f"✅ Player data ready: {packs_dir}")

            # Step 1: Load player pack data and build prompt
            from src.agents.player_analysis.multi_version.tools import (
                load_all_packs,
                analyze_trends,
                identify_key_transitions,
                generate_comprehensive_analysis
            )
            from src.agents.player_analysis.multi_version.prompts import build_multi_version_prompt

            # Load all patch data
            all_packs = load_all_packs(packs_dir)

            # Analyze trends
            trends = analyze_trends(all_packs)

            # Identify key turning points
            transitions = identify_key_transitions(trends)

            # Generate comprehensive analysis
            analysis = generate_comprehensive_analysis(trends, transitions)

            # Build AI prompt
            prompt = build_multi_version_prompt(analysis)
            print(f"✅ Prompt constructed ({len(prompt)} chars)")

            # Step 2: Stream generate AI analysis
            for message in stream_agent_with_thinking(
                prompt=prompt,
                model="haiku",  # Force use of Haiku 4.5
                enable_thinking=False  # Multi-version analysis does not show thinking
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

            analysis = generate_player_build_analysis(packs_dir)

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
            matches_dir = Path(packs_dir) / "matches"
            match_files = sorted(matches_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

            if not match_files:
                yield f"data: {{\"error\": \"No match data available for analysis\"}}\n\n"
                return

            # Read recent matches
            with open(match_files[0], 'r', encoding='utf-8') as f:
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

            # Load all patch data
            all_packs = load_all_packs(packs_dir)

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
                player_data = load_player_data(packs_dir)
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
                friend_puuid = await riot_client.get_puuid(request.friend_game_name, request.friend_tag_line, request.region)
                if not friend_puuid:
                    yield f"data: {{\"error\": \"Could not find friend {request.friend_game_name}#{request.friend_tag_line}\"}}\n\n"
                    return

                # Trigger friend data preparation (20 days like current player)
                print(f"📊 Preparing friend data...")
                friend_job = await player_data_manager.prepare_player_data(
                    request.friend_game_name,
                    request.friend_tag_line,
                    request.region,
                    days=20
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

                player_data = load_player_data(player_packs_dir)
                friend_data = load_player_data(friend_packs_dir)

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
    """Version Trends - Version trend analysis (Multi-Version + Version Comparison merged) (SSE Stream output)"""
    from fastapi.responses import StreamingResponse
    from src.agents.shared.stream_helper import stream_agent_with_thinking

    async def generate_stream():
        try:
            print(f"\n{'='*60}\n📊 Version Trends Stream\n{'='*60}")

            await player_data_manager.wait_for_data(puuid=request.puuid, timeout=120)
            packs_dir = player_data_manager.get_packs_dir(request.puuid)
            if not packs_dir:
                yield f"data: {{\"error\": \"Player data not ready\"}}\n\n"
                return

            # Use Multi-Version complete analysis tools
            from src.agents.player_analysis.multi_version.tools import (
                load_all_packs, analyze_trends, identify_key_transitions, generate_comprehensive_analysis
            )
            from src.agents.player_analysis.multi_version.prompts import build_multi_version_prompt

            all_packs = load_all_packs(packs_dir)
            trends = analyze_trends(all_packs)
            transitions = identify_key_transitions(trends)
            analysis = generate_comprehensive_analysis(trends, transitions)

            prompt = build_multi_version_prompt(analysis)

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

            recent_data = load_recent_data(packs_dir, request.recent_count or 20)
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
    - time_range: Time range preset ("2024-01-01" or "past-365")

    Priority: count > time_range > days (default 365)

    Example: /api/player/s1ne/na1/summary?time_range=2024-01-01
    """
    # Strip whitespace from URL parameters
    game_name = game_name.strip()
    tag_line = tag_line.strip()

    import time
    from datetime import datetime, timedelta
    start_time = time.time()

    # Calculate days based on priority: time_range > count > days > default
    # Note: count parameter is legacy and should be converted to days
    if time_range:
        if time_range == "2024-01-01":
            # Calculate days from 2024-01-01 to today
            start_date = datetime(2024, 1, 1)
            days_calculated = (datetime.now() - start_date).days
            days = days_calculated
            print(f"📅 Time range '2024-01-01' → {days} days")
        elif time_range == "past-365":
            days = 365
            print(f"📅 Time range 'past-365' → {days} days")
    elif count:
        # Convert count to days (assume ~1 match per day)
        days = count
        print(f"📅 Count {count} → {days} days")
    elif days is None:
        # Default to 365 days if nothing specified
        days = 365
        print(f"📅 Using default → {days} days")

    try:
        print(f"\n{'='*60}")
        if count:
            print(f"🔍 Player Summary Request: {game_name}#{tag_line} (count={count})")
        else:
            print(f"🔍 Player Summary Request: {game_name}#{tag_line} (days={days})")
        print(f"⏱️  Start time: {time.strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")

        # Step 1: Get account info
        step_start = time.time()
        account = await riot_client.get_account_by_riot_id(game_name=game_name, tag_line=tag_line, region='americas')
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        puuid = account['puuid']
        print(f"✅ [1/2] Got PUUID ({time.time()-step_start:.2f}s): {puuid[:20]}...")

        # Step 2: Get summoner info
        step_start = time.time()
        summoner = await riot_client.get_summoner_by_puuid(puuid=puuid, platform='na1')
        if not summoner:
            raise HTTPException(status_code=404, detail="Summoner not found")
        print(f"✅ [2/2] Got summoner info ({time.time()-step_start:.2f}s)")

        # Step 3: Start background data preparation (non-blocking)
        print(f"\n🔄 Starting background data preparation for past {days} days...")
        job = await player_data_manager.prepare_player_data(
            puuid=puuid,
            region='na1',
            game_name=game_name,
            tag_line=tag_line,
            days=days
        )

        # Step 4: Try to get role stats and champion stats if Player-Pack exists
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
                'region': 'na1'
            },
            'analysis': analysis,  # Add analysis summary data
            'role_stats': role_stats,  # Add role statistics data
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
        account = await riot_client.get_account_by_riot_id(game_name, tag_line, region='americas')
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
                "patches": []
            }

        # Read all pack files
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
                "patches": []
            }

        # Collect patch information
        patches = []
        total_games = 0

        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                pack = json.load(f)

            patch = pack.get("patch", "unknown")
            games = pack.get("total_games", 0)

            patches.append({
                "patch": patch,
                "games": games
            })
            total_games += games

        # Sort by patch version
        patches_sorted = sorted(patches, key=lambda x: x["patch"])

        return {
            "success": True,
            "puuid": puuid,
            "game_name": game_name,
            "tag_line": tag_line,
            "has_data": True,
            "total_patches": len(patches_sorted),
            "total_games": total_games,
            "earliest_patch": patches_sorted[0]["patch"] if patches_sorted else None,
            "latest_patch": patches_sorted[-1]["patch"] if patches_sorted else None,
            "patches": patches_sorted
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
