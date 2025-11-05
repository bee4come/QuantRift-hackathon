"""
Analytics service for player performance analysis
"""
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from .combat_power import combat_power_calculator
from .data_dragon import data_dragon


class PlayerAnalytics:
    """
    Analyze player performance and generate insights
    """

    def __init__(self):
        self.combat_power_calc = combat_power_calculator
        self._meta_power_cache = None  # Cache for avg meta power
        
    def extract_player_data_from_match(self, match: Dict[str, Any], puuid: str) -> Dict[str, Any]:
        """Extract relevant player data from a match"""
        participants = match['info']['participants']
        
        player_data = None
        for participant in participants:
            if participant['puuid'] == puuid:
                player_data = participant
                break
                
        if not player_data:
            return None
            
        return {
            'champion': player_data['championName'],
            'champion_id': player_data['championId'],
            'win': player_data['win'],
            'kills': player_data['kills'],
            'deaths': player_data['deaths'],
            'assists': player_data['assists'],
            'damage_dealt': player_data['totalDamageDealtToChampions'],
            'damage_taken': player_data['totalDamageTaken'],
            'gold_earned': player_data['goldEarned'],
            'cs': player_data['totalMinionsKilled'] + player_data.get('neutralMinionsKilled', 0),
            'vision_score': player_data['visionScore'],
            'game_duration': match['info']['gameDuration'],
            'items': [
                player_data.get(f'item{i}', 0) 
                for i in range(7) 
                if player_data.get(f'item{i}', 0) > 0
            ],
            'perks': player_data.get('perks', {}),
            'level': player_data.get('champLevel', 18),
            'game_mode': match['info']['gameMode'],
            'queue_id': match['info']['queueId'],
            'timestamp': match['info']['gameCreation']
        }
    
    def calculate_match_combat_power(self, match_data: Dict[str, Any]) -> float:
        """Calculate combat power for a single match"""
        champion = match_data['champion']
        level = match_data['level']
        items = match_data['items']
        
        perks = match_data.get('perks', {})
        styles = perks.get('styles', [])
        
        primary_style = None
        sub_style = None
        rune_ids = []
        
        if len(styles) >= 2:
            primary_style = styles[0].get('style')
            sub_style = styles[1].get('style')
            
            for style in styles:
                for selection in style.get('selections', []):
                    rune_ids.append(selection.get('perk'))
        
        try:
            power = self.combat_power_calc.calculate_total_combat_power(
                champion_name=champion,
                level=level,
                item_ids=items,
                rune_ids=rune_ids if rune_ids else None,
                primary_style=primary_style,
                sub_style=sub_style
            )
            return power
        except Exception as e:
            print(f"Error calculating combat power for {champion}: {e}")
            return 0.0
    
    def analyze_player_matches(self, matches: List[Dict[str, Any]], puuid: str, calculate_combat_power: bool = False) -> Dict[str, Any]:
        """
        Analyze all matches and generate comprehensive statistics

        Args:
            matches: List of match data dictionaries
            puuid: Player UUID
            calculate_combat_power: If False, skip expensive combat power calculations (faster for quick summaries)
        """
        if not matches:
            return {}

        # Extract player data from all matches
        match_data_list = []
        for match in matches:
            data = self.extract_player_data_from_match(match, puuid)
            if data:
                match_data_list.append(data)

        if not match_data_list:
            return {}

        # Calculate statistics
        total_games = len(match_data_list)
        total_wins = sum(1 for m in match_data_list if m['win'])
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0

        # Champion statistics
        champion_stats = defaultdict(lambda: {
            'games': 0, 'wins': 0, 'kills': 0, 'deaths': 0,
            'assists': 0, 'combat_power': []
        })

        total_combat_power = 0.0

        for match_data in match_data_list:
            champion = match_data['champion']
            champion_stats[champion]['games'] += 1
            champion_stats[champion]['wins'] += 1 if match_data['win'] else 0
            champion_stats[champion]['kills'] += match_data['kills']
            champion_stats[champion]['deaths'] += match_data['deaths']
            champion_stats[champion]['assists'] += match_data['assists']

            # Calculate combat power only if requested (expensive operation)
            if calculate_combat_power:
                combat_power = self.calculate_match_combat_power(match_data)
                champion_stats[champion]['combat_power'].append(combat_power)
                total_combat_power += combat_power

        # Calculate average combat power per game (use cached meta power if combat power not calculated)
        avg_combat_power_per_game = total_combat_power / total_games if (total_games > 0 and calculate_combat_power) else 0

        # Get average meta power (cached to avoid recalculating for every request)
        # For player classification, we only need base stats (fast), not full skill power (slow)
        if self._meta_power_cache is None:
            print("🔄 Computing avg meta power (base stats only, fast)...")
            all_champions_power = self.combat_power_calc.calculate_all_champions_base_stats_only()
            total_meta_power = sum(all_champions_power.values())
            num_champions = len(all_champions_power)
            self._meta_power_cache = total_meta_power / num_champions if num_champions > 0 else 0
            print(f"✅ Cached avg meta power: {self._meta_power_cache:.2f}")

        avg_meta_power = self._meta_power_cache

        # Determine player type (use estimated combat power if not calculated)
        if not calculate_combat_power:
            # Use a simple estimate based on KDA for quick classification
            avg_kda = sum((m['kills'] + m['assists']) / max(m['deaths'], 1) for m in match_data_list) / total_games
            avg_combat_power_per_game = avg_meta_power * (avg_kda / 3.0)  # Rough estimate

        is_meta_player = avg_combat_power_per_game >= avg_meta_power
        player_type = self._classify_player(avg_combat_power_per_game, avg_meta_power, win_rate)
        
        # Most played champions
        most_played = sorted(
            champion_stats.items(),
            key=lambda x: x[1]['games'],
            reverse=True
        )[:10]
        
        # Best performing champions (by win rate, min 3 games)
        best_champions = sorted(
            [(name, stats) for name, stats in champion_stats.items() if stats['games'] >= 3],
            key=lambda x: x[1]['wins'] / x[1]['games'],
            reverse=True
        )[:5]
        
        # Calculate KDA
        total_kills = sum(m['kills'] for m in match_data_list)
        total_deaths = sum(m['deaths'] for m in match_data_list)
        total_assists = sum(m['assists'] for m in match_data_list)
        avg_kda = (total_kills + total_assists) / max(total_deaths, 1)
        
        return {
            'total_games': total_games,
            'total_wins': total_wins,
            'total_losses': total_games - total_wins,
            'win_rate': round(win_rate, 2),
            'avg_combat_power_per_game': round(avg_combat_power_per_game, 2),
            'avg_meta_power': round(avg_meta_power, 2),
            'is_meta_player': is_meta_player,
            'player_type': player_type,
            'avg_kda': round(avg_kda, 2),
            'total_kills': total_kills,
            'total_deaths': total_deaths,
            'total_assists': total_assists,
            'most_played_champions': [
                {
                    'name': name,
                    'games': stats['games'],
                    'wins': stats['wins'],
                    'win_rate': round(stats['wins'] / stats['games'] * 100, 2),
                    'avg_kda': round((stats['kills'] + stats['assists']) / max(stats['deaths'], 1), 2),
                    'avg_combat_power': round(sum(stats['combat_power']) / len(stats['combat_power']), 2) if stats['combat_power'] else 0
                }
                for name, stats in most_played
            ],
            'best_champions': [
                {
                    'name': name,
                    'games': stats['games'],
                    'wins': stats['wins'],
                    'win_rate': round(stats['wins'] / stats['games'] * 100, 2),
                    'avg_kda': round((stats['kills'] + stats['assists']) / max(stats['deaths'], 1), 2)
                }
                for name, stats in best_champions
            ],
            'unique_champions_played': len(champion_stats),
            'champion_pool_diversity': round(len(champion_stats) / total_games * 100, 2)
        }
    
    def _classify_player(self, avg_combat_power: float, avg_meta_power: float, win_rate: float) -> str:
        """
        Classify player type based on combat power and win rate
        
        Logic:
        - If avg_combat_power < avg_meta_power AND win_rate > 50: "Skill Player" (pure skill)
        - If avg_combat_power >= avg_meta_power AND win_rate > 50: "Meta Player" (plays strong champions)
        - If avg_combat_power >= avg_meta_power AND win_rate <= 50: "Meta Follower" (plays meta but loses)
        - If avg_combat_power < avg_meta_power AND win_rate <= 50: "Off-Meta Player" (plays weak champions and loses)
        """
        is_high_power = avg_combat_power >= avg_meta_power
        is_positive_wr = win_rate > 50
        
        if not is_high_power and is_positive_wr:
            return "Skill Player"
        elif is_high_power and is_positive_wr:
            return "Meta Player"
        elif is_high_power and not is_positive_wr:
            return "Meta Follower"
        else:
            return "Off-Meta Player"
    
    def generate_shareable_summary(self, analysis: Dict[str, Any], player_name: str) -> Dict[str, Any]:
        """
        Generate a shareable year-end summary
        """
        if not analysis:
            return {}
            
        summary = {
            'player_name': player_name,
            'title': self._get_player_title(analysis),
            'stats': {
                'total_games': analysis['total_games'],
                'win_rate': analysis['win_rate'],
                'kda': analysis['avg_kda'],
                'player_type': analysis['player_type']
            },
            'highlights': {
                'most_played_champion': analysis['most_played_champions'][0] if analysis['most_played_champions'] else None,
                'best_champion': analysis['best_champions'][0] if analysis['best_champions'] else None,
                'unique_champions': analysis['unique_champions_played']
            },
            'insights': self._generate_insights(analysis),
            'shareable_text': self._generate_shareable_text(analysis, player_name)
        }
        
        return summary
    
    def _get_player_title(self, analysis: Dict[str, Any]) -> str:
        """Generate a fun title based on player stats"""
        player_type = analysis['player_type']
        win_rate = analysis['win_rate']
        
        if player_type == "Skill Player":
            return "The Underdog Champion"
        elif player_type == "Meta Player" and win_rate >= 60:
            return "The Meta Master"
        elif player_type == "Meta Player":
            return "The Tier List Follower"
        elif player_type == "Meta Follower":
            return "The Hopeful Meta Chaser"
        else:
            return "The Brave Innovator"
    
    def _generate_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate interesting insights about the player"""
        insights = []
        
        # Win rate insight
        if analysis['win_rate'] > 55:
            insights.append(f"Impressive {analysis['win_rate']}% win rate this year!")
        elif analysis['win_rate'] < 45:
            insights.append(f"Keep grinding! Your {analysis['win_rate']}% win rate has room to grow.")
        
        # Champion diversity
        if analysis['champion_pool_diversity'] > 30:
            insights.append("You're a flex player with a diverse champion pool!")
        elif analysis['champion_pool_diversity'] < 10:
            insights.append("You're a one-trick specialist!")
        
        # Player type insight
        if analysis['player_type'] == "Skill Player":
            insights.append("You win with skill, not just meta picks. Respect!")
        elif analysis['player_type'] == "Meta Player":
            insights.append("You know how to pick the strong champions!")
        
        # KDA insight
        if analysis['avg_kda'] > 3.0:
            insights.append(f"Excellent {analysis['avg_kda']} KDA - you're a force to be reckoned with!")
        
        return insights
    
    def _generate_shareable_text(self, analysis: Dict[str, Any], player_name: str) -> str:
        """Generate shareable social media text"""
        most_played = analysis['most_played_champions'][0] if analysis['most_played_champions'] else None
        
        text = f"My League of Legends Year in Review:\n\n"
        text += f"Player: {player_name}\n"
        text += f"Type: {analysis['player_type']}\n"
        text += f"Games Played: {analysis['total_games']}\n"
        text += f"Win Rate: {analysis['win_rate']}%\n"
        text += f"KDA: {analysis['avg_kda']}\n"
        
        if most_played:
            text += f"Most Played: {most_played['name']} ({most_played['games']} games)\n"
        
        text += f"\nUnique Champions: {analysis['unique_champions_played']}\n"
        
        return text


# Singleton instance
player_analytics = PlayerAnalytics()

