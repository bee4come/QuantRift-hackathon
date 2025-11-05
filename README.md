# QuantRift - AI-Powered League of Legends Analytics Platform

**QuantRift** is a comprehensive, production-ready analytics platform that provides deep insights into League of Legends player performance through quantitative analysis and AI-powered coaching agents.

## 🎯 Project Overview

QuantRift combines rigorous statistical methods, extensive match data processing, and advanced AI analysis to deliver actionable insights for League of Legends players. The platform processes over 107,000 match records across multiple patches to generate personalized performance reports, champion mastery analysis, and strategic recommendations.

### Key Features

- **18 Specialized AI Agents**: Comprehensive analysis covering weakness diagnosis, champion mastery, progress tracking, peer comparison, and more
- **Quantitative Metrics Engine**: 20+ statistical metrics including combat power, KDA adjustments, objective participation, and Wilson confidence intervals
- **Real-time Data Pipeline**: Asynchronous data fetching from Riot Games API with intelligent caching and 5-key rotation
- **Modern Web Interface**: Next.js 15 + React 19 frontend with responsive design and WebGL animations
- **Production Deployment**: Fully containerized with Docker, pre-loaded player data, and health monitoring

## 🏗️ Architecture

### Three-Tier System

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (Next.js 15)                     │
│  - Player search & profiles                                 │
│  - Real-time data status polling                            │
│  - 18 agent analysis interfaces                             │
│  - WebGL background animations                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 Backend API (FastAPI)                       │
│  - Riot API client (5-key rotation, 1800 req/10s)          │
│  - Player data manager (async preparation & caching)        │
│  - 18 AI agent endpoints (AWS Bedrock Claude 3.5/4.5)      │
│  - Combat power calculation service                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Analytics Engine (Python)                      │
│  - Bronze → Silver → Gold data pipeline                    │
│  - 20 quantitative metrics with Wilson CI                   │
│  - Multi-agent analysis system                              │
│  - Statistical modeling & data aggregation                  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Riot Games API Key (get from [Riot Developer Portal](https://developer.riotgames.com/))
- AWS Bedrock access (for AI agents)

### Running with Docker

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/QuantRift_hackathon.git
   cd QuantRift_hackathon
   ```

2. **Configure environment variables**:
   ```bash
   # Create backend .env
   cat > backend/.env << EOF
   RIOT_API_KEY=your_riot_api_key_here
   AWS_REGION=us-west-2
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   EOF

   # Create frontend .env.local
   cat > frontend/.env.local << EOF
   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
   EOF
   ```

3. **Build and start services**:
   ```bash
   docker compose up -d
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Development Mode

**Backend** (port 8000):
```bash
cd backend
export PYTHONPATH=$(pwd)/..
python -m uvicorn api.server:app --reload
```

**Frontend** (port 3000):
```bash
cd frontend
npm install
npm run dev
```

## 📊 AI Agent System

QuantRift features **18 specialized AI agents** powered by AWS Bedrock (Claude 3.5 Haiku and Claude 4.5 Sonnet):

### Player Analysis Agents (11)
- **Weakness Analysis**: Diagnoses performance weaknesses and provides improvement recommendations
- **Champion Mastery**: Deep analysis of champion expertise and mechanics
- **Progress Tracker**: Tracks improvement over time with statistical validation
- **Detailed Analysis**: Comprehensive multi-dimensional performance review
- **Peer Comparison**: Benchmarks against players of similar rank
- **Role Specialization**: Analyzes role-specific strengths and weaknesses
- **Timeline Deep Dive**: Minute-by-minute game analysis for pattern detection
- **Annual Summary**: Year-in-review with tri-period analysis
- **Risk Forecaster**: Predicts performance volatility and risk factors
- **Friend Comparison**: Compares performance with friends and teammates
- **Laning Phase**: Specialized early-game analysis

### Meta Analysis Agents (3)
- **Champion Recommendation**: Suggests champions based on playstyle and meta
- **Multi-Version Analysis**: Cross-patch performance comparison
- **Version Comparison**: Adaptation analysis across game updates

### Coach Tools (4)
- **Build Simulator**: Optimizes item builds for specific matchups
- **Drafting Coach**: Team composition and pick/ban strategy
- **Team Synergy**: Analyzes team composition effectiveness
- **Post-game Review**: Detailed game review with actionable feedback

## 🔬 Quantitative Analysis System

### 20 Statistical Metrics

**Behavioral Metrics** (1-5):
- Pick rate, attach rate, rune diversity, synergy, counter matchups

**Win Rate Metrics** (6-10):
- Baseline win rate, confidence intervals (Wilson), effective sample size, data governance tier

**Objective Metrics** (11-13):
- Objective participation rate, Baron control, Dragon control

**Gold Efficiency Metrics** (14-16):
- Item efficiency, gold per minute, CS efficiency

**Combat Metrics** (17-20):
- Combat power index, damage efficiency, time to core items, shock impact

### Data Pipeline

```
Raw Match Data (Riot API)
    ↓
Bronze Layer (Raw JSON, 6.7GB)
    ↓
Silver Layer (Normalized, SCD2, 362MB)
    ↓
Gold Layer (Aggregated Metrics, 354MB)
    ↓
Player-Pack Format (Agent-ready)
```

### Statistical Methods

- **Wilson Confidence Intervals**: Robust win rate estimation with proper uncertainty quantification
- **Beta-Binomial Shrinkage**: Combats small sample bias
- **Combat Power Index**: Multi-dimensional strength metric combining damage, survival, and impact
- **Governance Framework**: CONFIDENT/CAUTION/CONTEXT quality tiers based on sample size

## 🛠️ Technology Stack

### Frontend
- **Framework**: Next.js 15.5.5 with Turbopack
- **UI Library**: React 19.1.0
- **Styling**: Tailwind CSS 4.0
- **Animation**: OGL (WebGL), Framer Motion
- **Language**: TypeScript 5

### Backend
- **API Framework**: FastAPI
- **Server**: Uvicorn with async support
- **AI Models**: AWS Bedrock (Claude 3.5 Haiku, Claude 4.5 Sonnet)
- **Database**: DuckDB for analytics, SQLite for caching
- **Language**: Python 3.11

### Data Processing
- **Pipeline**: Bronze → Silver → Gold medallion architecture
- **Statistics**: NumPy, SciPy, Pandas
- **Computation**: Wilson CI, Beta-Binomial models
- **Storage**: Parquet for efficient columnar storage

### Deployment
- **Containerization**: Docker multi-stage builds
- **Orchestration**: Docker Compose
- **Health Monitoring**: Container health checks
- **Data Pre-loading**: 393MB player packs included in images

## 📈 Production Data

- **Match Records**: 107,570 matches analyzed
- **Unique Matches**: 10,423 games
- **Patches Covered**: 25.17, 25.18, 25.19
- **Region**: NA1 (North America)
- **Data Size**: ~7.4GB total (6.7GB bronze, 362MB silver, 354MB gold)

## 🎨 User Experience

- **Instant Search**: Fast player lookup by Riot ID
- **Real-time Progress**: Live status polling during data preparation
- **Responsive Design**: Mobile-first approach with adaptive layouts
- **Interactive Visualizations**: Recharts-powered analytics dashboard
- **AI-Generated Insights**: Natural language analysis reports
- **One-click Analysis**: Simple interface for deep agent-powered insights

## 📝 Documentation

- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)**: Detailed system architecture and design
- **[QUANTITATIVE_ANALYSIS.md](./docs/QUANTITATIVE_ANALYSIS.md)**: Statistical methods and data pipeline
- **Agent DESIGN.md files**: Individual design documentation for each AI agent in `backend/src/agents/`

## 👥 Authors

- **uzerone** - System architecture, backend development, quantitative analysis
- **bee4come** - Frontend development, UI/UX design, agent integration

## 📄 License

This project is built for the League of Legends Analytics Hackathon 2025.

## 🙏 Acknowledgments

- Riot Games for the official API
- AWS Bedrock for AI model access
- The League of Legends community for inspiration

---

**QuantRift**: Quantitative insights that shift the rift in your favor.
