# Backend Dockerfile for Rift Rewind FastAPI Server
# Includes pre-loaded player pack data for deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/api/ ./api/
COPY backend/services/ ./services/
COPY backend/src/ ./src/

# Create data directories (player packs will be generated at runtime)
RUN mkdir -p data/player_packs data/bronze data/silver data/gold

# Create test_agents directory if needed
RUN mkdir -p test_agents

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD uvicorn api.server:app --host 0.0.0.0 --port $PORT
