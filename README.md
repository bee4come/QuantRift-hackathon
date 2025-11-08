# QuantRift - AI-Powered League of Legends Analytics Platform

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**QuantRift** is a comprehensive, production-ready analytics platform that provides deep insights into League of Legends player performance through quantitative analysis and AI-powered coaching agents.

## 📑 Table of Contents

- [💡 Motivation](#-motivation)
- [🎯 Project Overview](#-project-overview)
- [🚀 Quick Start](#-quick-start)
- [📊 AI Module System](#-ai-module-system)
- [🛠️ Technology Stack](#️-technology-stack)
- [👥 Authors](#-authors)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

## 💡 Motivation

QuantRift was built with a clear vision: **we don't want to recreate another OP.GG-style dashboard**. Instead, we leverage AI agents to provide deep, personalized insights that go beyond what traditional stat dashboards can show.

### Our Approach

- **Beyond Surface Stats**: While dashboards show KDA, win rates, and basic metrics, QuantRift's AI agents dive deep into *why* you're performing the way you are
- **Personalized Feedback**: Every analysis is tailored to your specific playstyle, champion pool, and performance patterns
- **Actionable Insights**: Instead of just showing numbers, our agents provide context, explanations, and concrete recommendations for improvement
- **Rank Climbing Focus**: Designed specifically to help players climb ranks with personalized, data-driven coaching feedback

Traditional dashboards answer "what happened?" - QuantRift answers "why did it happen?" and "what should you do differently?"

## 🎯 Project Overview

QuantRift combines rigorous statistical methods, extensive match data processing, and advanced AI analysis to deliver actionable insights for League of Legends players. The platform processes over 107,000 match records across multiple patches to generate personalized performance reports, champion mastery analysis, and strategic recommendations.

### Key Features

- **9 Specialized AI Modules**: Comprehensive analysis covering annual summary, performance insights, comparison hub, match analysis, version trends, champion recommendation, role specialization, champion mastery, and build optimization
- **Quantitative Metrics Engine**: 20+ statistical metrics including combat power index, Wilson confidence intervals, objective participation, and gold efficiency analysis
- **Multi-Source Data Integration**: Seamless data fetching from Riot Games API, OP.GG MCP, Data Dragon, and Community Dragon with intelligent caching and rate limit management
- **Time Range Analysis**: Support for "Past Season 2024" (Patches 14.1-14.25) and "Past 365 Days" filtering across all analysis agents
- **Real-time Data Status**: Live monitoring of data availability with automatic background fetching and progress tracking
- **Modern Web Interface**: Next.js 15 + React 19 frontend with responsive design, WebGL animations, and glassmorphism UI
- **Production Ready**: Fully containerized with Docker, pre-loaded player data, health monitoring, and scalable architecture

## 🚀 Quick Start

**First-time setup (install dependencies):**
   ```bash
./requirements.sh
   ```

**Start services:**
   ```bash
./start.sh
   ```

**Stop services:**
   ```bash
./stop.sh
   ```

Services will be available at:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 📊 AI Module System

QuantRift features **9 specialized AI modules** powered by AWS Bedrock (Claude 3.5 Haiku and Claude 4.5 Sonnet):

1. **Annual Summary**: Year-in-review performance highlights with tri-period analysis
2. **Performance Insights**: Comprehensive analysis of strengths, weaknesses, and growth opportunities
3. **Comparison Hub**: Compare performance with friends or players of similar rank
4. **Match Analysis**: Deep dive into recent match timeline and post-game review
5. **Version Trends**: Cross-patch performance analysis and adaptation tracking
6. **Champion Recommendation**: Personalized champion suggestions based on playstyle and meta
7. **Role Specialization**: Role-specific performance insights and optimization
8. **Champion Mastery**: Deep analysis of champion expertise and mechanics
9. **Build Simulator**: Optimize item builds and itemization strategies

## 🛠️ Technology Stack

### Frontend
- **Framework**: Next.js 15.5.5 with Turbopack
- **UI Library**: React 19.1.0
- **Styling**: Tailwind CSS 4.0, styled-components
- **Animation**: OGL (WebGL), Framer Motion
- **Visualization**: Recharts
- **Markdown**: react-markdown, remark-gfm
- **Language**: TypeScript 5

### Backend
- **API Framework**: FastAPI
- **Server**: Uvicorn with async support
- **AI Models**: AWS Bedrock (Claude 3.5 Haiku, Claude 4.5 Sonnet)
- **AWS SDK**: boto3
- **HTTP Clients**: aiohttp, requests
- **Database**: DuckDB for analytics, SQLite for caching
- **Validation**: Pydantic
- **Language**: Python 3.11

### Data Processing
- **Libraries**: NumPy, SciPy, Pandas
- **Machine Learning**: scikit-learn
- **Storage**: Parquet for efficient columnar storage
- **Pipeline**: Bronze → Silver → Gold medallion architecture

### External Services
- **Riot Games API**: Match data and player information
- **OP.GG MCP Server**: Meta data and tier rankings
- **Data Dragon**: Static game data
- **Community Dragon**: Supplementary game data
- **AWS Bedrock**: AI model inference

### Deployment
- **Containerization**: Docker multi-stage builds
- **Orchestration**: Docker Compose
- **Health Monitoring**: Container health checks
- **Scripts**: start.sh / stop.sh for local development

## 👥 Authors

- **[bee4come](https://github.com/bee4come)** - Architect, Data and Integration
- **[uzerone](https://github.com/uzerone)** - Product & UX/UI Design, Integration

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

This is an open source project developed for [Rift Rewind Hackathon](https://riftrewind.devpost.com/?ref_feature=challenge&ref_medium=your-open-hackathons&ref_content=Submissions+open).

- **Riot Games** for the official API and game data
- **AWS Bedrock** for AI model access
- **Anthropic** for Claude AI models
- **[Jayde Garrow](https://jaydegarrow.wixsite.com/jaydefonts)** for the PaybAck font used in titles
- The League of Legends community for inspiration and feedback

