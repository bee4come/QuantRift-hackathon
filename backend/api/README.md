# Rift Rewind REST API

Production-ready FastAPI server providing REST endpoints for League of Legends player analysis.

## Quick Start

```bash
# Start the API server
uvicorn api.server:app --reload

# Access interactive documentation
open http://localhost:8000/docs

# Run tests
python api/test_api.py
```

## Endpoints

### 1. Risk Forecaster Analysis
**Endpoint**: `POST /v1/risk-forecaster/analyze`

Analyzes team compositions to predict match outcomes with power curve visualization.

**Request**:
```json
{
  "match_id": "NA1_1234567890",
  "our_team": {
    "composition": [
      {"champion_id": 92, "role": "TOP"},
      {"champion_id": 64, "role": "JUNGLE"},
      {"champion_id": 103, "role": "MIDDLE"},
      {"champion_id": 498, "role": "BOTTOM"},
      {"champion_id": 432, "role": "UTILITY"}
    ]
  },
  "enemy_team": {
    "composition": [
      {"champion_id": 157, "role": "TOP"},
      {"champion_id": 120, "role": "JUNGLE"},
      {"champion_id": 238, "role": "MIDDLE"},
      {"champion_id": 222, "role": "BOTTOM"},
      {"champion_id": 412, "role": "UTILITY"}
    ]
  },
  "include_visualizations": true,
  "language": "en"
}
```

**Response** (key fields):
```json
{
  "power_curve": {
    "time_series": [
      {
        "minute": 0,
        "our_power": 45.2,
        "enemy_power": 48.1,
        "power_diff": -2.9,
        "risk_level": "medium"
      }
    ],
    "crossover_point": {
      "minute": 30,
      "description": "Power curves intersect - critical turning point"
    }
  },
  "key_milestones": [...],
  "phase_tactics": [...],
  "victory_path": {...}
}
```

**Processing Time**: ~2-3 minutes (includes LLM generation)

### 2. Annual Summary
**Endpoint**: `GET /v1/annual-summary/{summoner_id}`

Generates comprehensive season performance analysis with growth curves.

**Request**:
```
GET /v1/annual-summary/s1ne?region=na1&start_patch=15.12&end_patch=15.20
```

**Response** (key fields):
```json
{
  "season_overview": {
    "core_statistics": {
      "total_games": 287,
      "overall_winrate": 0.564,
      "winrate_confidence_interval": {
        "lower": 0.505,
        "upper": 0.621
      }
    },
    "season_keywords": [
      "Steady Growth",
      "Specialization Deepening",
      "Version Adaptation"
    ]
  },
  "temporal_evolution": {
    "growth_curve_visualization": {
      "time_series": [
        {
          "patch": "15.12",
          "games": 32,
          "winrate": 0.531,
          "phase": "early"
        }
      ]
    }
  },
  "champion_pool_evolution": {...},
  "future_outlook": {...}
}
```

**Processing Time**: ~30-60 seconds (includes data analysis + LLM generation)

### 3. Health Check
**Endpoint**: `GET /health`

Simple health check for monitoring.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-15T13:28:00.734095",
  "services": {
    "risk_forecaster": "ready",
    "annual_summary": "ready"
  }
}
```

## API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Frontend Design Specifications
Comprehensive UI component specifications with TypeScript implementations:

1. **Risk Forecaster UI** (`docs/API_DESIGN_RISK_FORECASTER.md`)
   - Power Curve Visualization (Recharts LineChart)
   - Phase Timeline Bar
   - Key Milestones Panel
   - Tactical Recommendations Card
   - Risk Alert System
   - Decision Checklist Widget

2. **Annual Summary UI** (`docs/API_DESIGN_ANNUAL_SUMMARY.md`)
   - Season Overview Hero Component
   - Temporal Evolution Chart (Growth Curve)
   - Three-Phase Comparison Cards
   - Version Adaptation Timeline
   - Champion Pool Evolution Grid
   - Highlights Showcase
   - Future Outlook Panel

## Project Structure

```
api/
├── server.py                      # FastAPI application (582 lines)
├── test_api.py                    # Comprehensive test suite
├── test_risk_forecaster.py        # Focused risk forecaster test
├── API_TEST_RESULTS.md            # Test results and performance metrics
└── README.md                      # This file

docs/
├── API_DESIGN_RISK_FORECASTER.md  # Frontend spec for Risk Forecaster
└── API_DESIGN_ANNUAL_SUMMARY.md   # Frontend spec for Annual Summary
```

## Technical Stack

- **Framework**: FastAPI 0.104+
- **Validation**: Pydantic v2
- **CORS**: Enabled for frontend integration
- **Documentation**: Auto-generated with OpenAPI/Swagger
- **Python**: 3.10+

## Frontend Integration

### Required Dependencies
```bash
npm install @tanstack/react-query recharts framer-motion
npm install -D @types/react @types/node
```

### Example React Query Usage
```typescript
import { useQuery } from '@tanstack/react-query';

const { data, isLoading } = useQuery({
  queryKey: ['risk-forecast', matchId],
  queryFn: async () => {
    const response = await fetch('/v1/risk-forecaster/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    });
    return response.json();
  },
  staleTime: 5 * 60 * 1000, // 5 minutes
  cacheTime: 30 * 60 * 1000  // 30 minutes
});
```

### Timeout Configuration
```typescript
// Risk Forecaster: 3-minute timeout
const RISK_FORECASTER_TIMEOUT = 180_000;

// Annual Summary: 2-minute timeout
const ANNUAL_SUMMARY_TIMEOUT = 120_000;
```

## Performance Characteristics

| Endpoint | Avg Time | Max Time | Optimization Status |
|----------|----------|----------|---------------------|
| Health Check | 50ms | 100ms | ✅ Optimal |
| Risk Forecaster | 120s | 180s | ⚠️ Needs async queue |
| Annual Summary | 60s | 90s | ⚠️ Needs caching |
| Request Validation | 10ms | 50ms | ✅ Optimal |

## Known Limitations

1. **Long Processing Times**: Both analysis endpoints take 1-3 minutes due to:
   - Comprehensive data analysis
   - LLM generation (AWS Bedrock)
   - Real-time processing

2. **Synchronous Processing**: Current implementation is synchronous
   - Blocks request until completion
   - Can cause timeout issues
   - Suitable for demo/prototype

## Future Enhancements

### High Priority
- [ ] Async job queue (Celery + Redis)
- [ ] Response caching (Redis)
- [ ] Request rate limiting
- [ ] API key authentication

### Medium Priority
- [ ] WebSocket support for real-time updates
- [ ] Job status tracking endpoints
- [ ] Historical data caching
- [ ] Batch analysis endpoints

### Low Priority
- [ ] GraphQL alternative endpoint
- [ ] gRPC support
- [ ] Multi-language support
- [ ] Custom visualization exports

## Testing

### Run All Tests
```bash
python api/test_api.py
```

### Test Individual Endpoints
```bash
# Risk Forecaster only
python api/test_risk_forecaster.py

# Health check only
curl http://localhost:8000/health
```

### Expected Test Results
- ✅ Health check: PASS (instant)
- ✅ Request validation: PASS (instant)
- ⏳ Risk Forecaster: LONG-RUNNING (2-3 minutes)
- ⏳ Annual Summary: REQUIRES DATA (player packs must exist)

## Deployment

### Development
```bash
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

### Production (Future)
```bash
# With Gunicorn + Uvicorn workers
gunicorn api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

### Docker (Future)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Support

For frontend integration questions, refer to:
- `docs/API_DESIGN_RISK_FORECASTER.md` - Complete UI component specifications
- `docs/API_DESIGN_ANNUAL_SUMMARY.md` - Complete UI component specifications
- Interactive API docs at http://localhost:8000/docs

## License

Part of the Rift Rewind project. See main repository for license details.
