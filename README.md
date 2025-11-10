<div align="center" style="color: black;">

<img src="frontend/public/quantrift-logo.svg" alt="QuantRift" style="width: 100%; max-width: 600px; height: auto;"/>

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

<h4 align="center">
  Quantitative analysis and AI-powered coaching agents for League of Legends.
</h4>

## 📑 Table of Contents

- [💡 Motivation](#-motivation)
  - [Our Approach](#our-approach)
- [🎯 Project Overview](#-project-overview)
  - [Key Features](#key-features)
- [🚀 Quick Start](#-quick-start)
- [📊 AI Module System & Filter Support](#-ai-module-system--filter-support)
- [🛠️ Technology Stack](#️-technology-stack)
  - [🎨 Frontend](#-frontend)
  - [⚙️ Backend](#️-backend)
  - [📊 Data Processing](#-data-processing)
    - [Bronze → Silver → Gold Pipeline](#bronze--silver--gold-pipeline)
  - [🌐 External Services](#-external-services)
  - [🚀 Deployment](#-deployment)
- [📚 Technical Documentation](#-technical-documentation)
- [🔮 Future Planning](#-future-planning)
- [👥 Authors](#-authors)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

## 💡 Motivation

OP.GG is undoubtedly the world's leading League of Legends analytics platform, and we love using it. It excels at providing comprehensive statistics, detailed match history, champion builds, tier lists, and real-time game data. The platform has become an essential tool for millions of players worldwide, and we genuinely appreciate the value it brings to the League of Legends community.

However, we noticed that while OP.GG excels at showing *what* happened in your games, it doesn't help players understand *why* they're performing a certain way or *what* they should do differently to improve. Traditional dashboards answer "what happened?" - QuantRift answers "why did it happen?" and "what should you do differently?"

This project started as our entry for the [Rift Rewind Hackathon](https://riftrewind.devpost.com/), but more importantly, **we wanted to build something we would actually want to use ourselves**. As League of Legends players, we were frustrated by the limitations of existing analytics tools - they show you numbers but don't help you understand what to do differently. So we set out to create a platform that provides real, actionable insights powered by AI.

QuantRift was built with a clear vision: **we don't want to recreate another OP.GG-style dashboard**. Instead, we leverage AI agents to provide deep, personalized insights that go beyond what traditional stat dashboards can show.

### Our Approach

- **Beyond Surface Stats**: While dashboards show KDA, win rates, and basic metrics, QuantRift's AI agents dive deep into *why* you're performing the way you are
- **Personalized Feedback**: Every analysis is tailored to your specific playstyle, champion pool, and performance patterns
- **Actionable Insights**: Instead of just showing numbers, our agents provide context, explanations, and concrete recommendations for improvement
- **Rank Climbing Focus**: Designed specifically to help players climb ranks with personalized, data-driven coaching feedback

## 🎯 Project Overview

QuantRift combines rigorous statistical methods, extensive match data processing, and advanced AI analysis to deliver actionable insights for League of Legends players. The platform processes over 107,000 match records across multiple patches to generate personalized performance reports, champion mastery analysis, and strategic recommendations.

### Key Features

- **🤖 9 Specialized AI Modules**: Comprehensive analysis covering annual summary, performance insights, comparison hub, match analysis, version trends, champion recommendation, role specialization, champion mastery, and build optimization
- **📊 Quantitative Metrics Engine**: 20+ statistical metrics powered by quantitative algorithms that integrate with AWS Bedrock agents to make data-driven decisions. Standout metric: **Combat Power Index (CP)** - a proprietary algorithm that combines damage, gold efficiency, objective control, and teamfight impact into a single performance score, used by AI agents to provide contextualized coaching feedback
- **🔗 Multi-Source Data Integration**: Seamless data fetching from Riot Games API, OP.GG MCP, Data Dragon, and Community Dragon with intelligent caching and rate limit management
- **⏱️ Time Range Analysis**: Support for "Past Season 2024" (Patches 14.1-14.25) and "Past 365 Days" filtering across all analysis agents
- **📡 Real-time Data Status**: Live monitoring of data availability with automatic background fetching and progress tracking
- **🎨 Modern Web Interface**: Next.js 15 + React 19 frontend with responsive design, WebGL animations, and glassmorphism UI
- **✅ Production Ready**: Fully containerized with Docker, pre-loaded player data, health monitoring, scalable architecture, and **tested on live match data with concurrent user sessions** - proven to handle real-world production workloads

## 🚀 Quick Start

**📦 First-time setup (install dependencies):**

```bash
./requirements.sh
```

**▶️ Start services:**

```bash
./start.sh
```

**⏹️ Stop services:**

```bash
./stop.sh
```

**🌐 Services will be available at:**

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>

## 📊 AI Module System & Filter Support

QuantRift includes **9 specialized AI modules** (powered by AWS Bedrock, Claude 3.5 Haiku & Claude 4.5 Sonnet), each offering focused performance analysis. _Currently, all filterable analysis is limited to the **past 365 days** due to platform constraints._

| Module                        | Description                                                                              | Filter Support                |
|-------------------------------|------------------------------------------------------------------------------------------|-------------------------------|
| 📅 **Annual Summary**         | Year-in-review performance highlights, with tri-period analysis                          | Past 365 days                 |
| 💡 **Performance Insights**   | Comprehensive strengths/weaknesses analysis and growth opportunities                     | _Requires meta_dir parameter_ |
| 📊 **Comparison Hub**         | Compare your performance to friends or players of similar rank                           | Past 365 days                 |
| 👥 **Friend Comparison**      | Head-to-head stats versus specific friends                                               | Past 365 days                 |
| 🎮 **Match Analysis**         | Detailed review of a single match timeline and post-game                                 | None (single match analysis)  |
| 📈 **Version Trends**         | Cross-patch performance analysis and adaptation tracking                                 | Past 365 days                 |
| ⭐ **Champion Recommendation** | Personalized suggestions based on trends, meta, and your playstyle                       | Past 365 days                 |
| 🎭 **Role Specialization**    | Role-specific performance insights and optimization                                     | Past 365 days                 |
| 🏆 **Champion Mastery**       | Deep analysis of champion expertise and mechanical skill                                 | Past 365 days (all queues)    |
| 🔧 **Build Simulator**        | Optimization of item builds and itemization strategies                                   | Past 365 days                 |
| 📈 **Progress Tracker**       | Track development and progress over time with customizable metrics                       | Past 365 days                 |

**Filter Details:**

- **Time Range**: All AI modules that support filtering operate on match data from the **past 365 days**.
- **Queue Type**: Where applicable, you can further filter by ranked queue type (Solo/Duo or Flex) or view all queues.

These modules and current filter support help you get actionable, personal analysis focused on your 1-year League of Legends history.


## 📚 Technical Documentation

For detailed technical implementation information, including agent algorithms, AWS Bedrock integration details, quantitative analysis methodologies, and development challenges, see [tech_detail.md](./tech_detail.md).

## 🛠️ Technology Stack

### 🎨 Frontend

- **Framework**: Next.js 15.5.5 with Turbopack
- **UI Library**: React 19.1.0
- **Styling**: Tailwind CSS 4.0, styled-components
- **Animation**: OGL (WebGL), Framer Motion
- **Visualization**: Recharts
- **Markdown**: react-markdown, remark-gfm
- **Language**: TypeScript 5

### ⚙️ Backend

- **API Framework**: FastAPI
- **Server**: Uvicorn with async support
- **AI Models**: AWS Bedrock (Claude 3.5 Haiku, Claude 4.5 Sonnet)
- **AWS SDK**: boto3
- **HTTP Clients**: aiohttp, requests
- **Database**: DuckDB for analytics, SQLite for caching
- **Validation**: Pydantic
- **Language**: Python 3.11

### 📊 Data Processing

- **Libraries**: NumPy, SciPy, Pandas
- **Similarity Analysis**: scikit-learn (StandardScaler, cosine similarity for champion similarity calculations)
- **Storage**: Parquet for efficient columnar storage
- **Pipeline**: Bronze → Silver → Gold medallion architecture

#### Bronze → Silver → Gold Pipeline

- **Bronze Layer**: Raw match data ingested directly from Riot Games API, stored as-is with minimal processing
- **Silver Layer**: Cleaned and transformed data with SCD2 (Slowly Changing Dimension Type 2) structure, including data validation, anonymization, and dimensional modeling
- **Gold Layer**: Business-ready aggregated analytics data optimized for AI agent consumption, featuring pre-calculated metrics and performance indicators

### 🌐 External Services

- **Riot Games API**: Match data and player information
- **OP.GG MCP Server**: Meta data and tier rankings
- **Data Dragon**: Static game data
- **Community Dragon**: Supplementary game data
- **AWS Bedrock**: AI model inference

### 🚀 Deployment

- **Containerization**: Docker multi-stage builds
- **Orchestration**: Docker Compose
- **Health Monitoring**: Container health checks
- **Scripts**: start.sh / stop.sh for local development

## 🔮 Future Planning

We initially considered adding ARAM (All Random All Mid) support, but we decided to focus on ranked gameplay improvement instead. Our primary goal is to help players climb ranks and improve their competitive performance. However, we may consider adding ARAM support in future updates based on community feedback and demand.

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

- **[Jayde Garrow](https://jaydegarrow.wixsite.com/jaydefonts)** for the PaybAck font used in titles
- The League of Legends community for inspiration and feedback
