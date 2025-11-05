import os
import requests
from dotenv import load_dotenv

# Load .env from project root (shared across all services)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # /home/zty/rift_rewind/backend/src/combatpower
# Go up three levels: combatpower -> src -> backend -> project_root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path=DOTENV_PATH)


def get_latest_ddragon_version():
    """Get the latest Data Dragon version dynamically"""
    try:
        response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5)
        response.raise_for_status()
        versions = response.json()
        return versions[0]  # First element is the latest version
    except Exception as e:
        print(f"Warning: Could not fetch latest Data Dragon version: {e}")
        return '15.20.1'  # Fallback to known latest version

class Config:
    # Riot API
    RIOT_API_KEY = os.getenv('RIOT_API_KEY')

    # Rate limits
    RATE_LIMIT_PER_SECOND = 20
    RATE_LIMIT_PER_2_MINUTES = 100
    
    # API Endpoints
    RIOT_API_BASE = {
        'na1': 'https://na1.api.riotgames.com',
        'americas': 'https://americas.api.riotgames.com',
    }
    
    # Data Dragon
    DDRAGON_VERSION = get_latest_ddragon_version()
    DDRAGON_BASE = f'https://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}'
    DDRAGON_DATA = f'{DDRAGON_BASE}/data/en_US'
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TTL = 3600  # 1 hour
    
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    
    # Analysis
    DAYS_TO_ANALYZE = 365

