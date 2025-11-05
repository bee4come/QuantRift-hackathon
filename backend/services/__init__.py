"""
Shared backend services for data fetching and external API integration
"""
from .riot_client import riot_client, RiotAPIClient
from .player_data_manager import player_data_manager, PlayerDataManager

__all__ = ['riot_client', 'RiotAPIClient', 'player_data_manager', 'PlayerDataManager']
