'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Trophy, TrendingUp, Target, Star } from 'lucide-react';
import { Player } from '../data/mockPlayers';

interface PlayerCardProps {
  player: Player;
  index: number;
}

export default function PlayerCard({ player, index }: PlayerCardProps) {
  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'challenger':
        return { from: '#FFD60A', to: '#FF9F0A' };
      case 'grandmaster':
        return { from: '#FF453A', to: '#FF375F' };
      case 'master':
        return { from: '#BF5AF2', to: '#5E5CE6' };
      default:
        return { from: '#0A84FF', to: '#5AC8FA' };
    }
  };

  const tierColors = getTierColor(player.tier);

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      className="fluid-glass rounded-2xl p-6 hover:scale-[1.02] transition-all duration-300 shadow-xl hover:shadow-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-6 relative z-10">
        <div>
          <h3 className="text-2xl font-bold mb-2" style={{ color: '#F5F5F7' }}>{player.username}</h3>
          <div 
            className="inline-block px-4 py-1 rounded-full font-semibold text-sm shadow-lg"
            style={{ 
              background: `linear-gradient(90deg, ${tierColors.from} 0%, ${tierColors.to} 100%)`,
              color: '#FFFFFF'
            }}
          >
            {player.tier} {player.rank} - {player.lp} LP
          </div>
        </div>
        <Trophy className="w-8 h-8" style={{ color: '#FFD60A' }} />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-6 relative z-10">
        <div className="fluid-glass-dark rounded-xl p-4 shadow-md overflow-hidden">
          <div className="flex items-center gap-2 mb-2 relative z-10">
            <TrendingUp className="w-5 h-5" style={{ color: '#32D74B' }} />
            <span className="text-sm" style={{ color: '#AEAEB2' }}>Win Rate</span>
          </div>
          <p className="text-2xl font-bold relative z-10" style={{ color: '#F5F5F7' }}>{player.winRate}%</p>
        </div>
        
        <div className="fluid-glass-dark rounded-xl p-4 shadow-md overflow-hidden">
          <div className="flex items-center gap-2 mb-2 relative z-10">
            <Target className="w-5 h-5" style={{ color: '#0A84FF' }} />
            <span className="text-sm" style={{ color: '#AEAEB2' }}>Games</span>
          </div>
          <p className="text-2xl font-bold relative z-10" style={{ color: '#F5F5F7' }}>{player.totalGames}</p>
        </div>
      </div>

      {/* Win/Loss */}
      <div className="flex gap-2 mb-6 relative z-10">
        <div className="flex-1 fluid-glass-dark rounded-lg p-3 text-center shadow-md overflow-hidden">
          <p className="font-semibold text-lg relative z-10" style={{ color: '#32D74B' }}>{player.wins}W</p>
        </div>
        <div className="flex-1 fluid-glass-dark rounded-lg p-3 text-center shadow-md overflow-hidden">
          <p className="font-semibold text-lg relative z-10" style={{ color: '#FF453A' }}>{player.losses}L</p>
        </div>
      </div>

      {/* Favorite Champions */}
      <div className="mb-6 relative z-10">
        <div className="flex items-center gap-2 mb-3">
          <Star className="w-5 h-5" style={{ color: '#FFD60A' }} />
          <h4 className="font-semibold" style={{ color: '#F5F5F7' }}>Top Champions</h4>
        </div>
        <div className="space-y-2">
          {player.favoriteChampions.map((champion, idx) => (
            <div
              key={idx}
              className="fluid-glass-dark rounded-lg p-3 flex items-center justify-between shadow-sm hover:shadow-md transition-shadow overflow-hidden"
            >
              <span className="font-medium relative z-10" style={{ color: '#F5F5F7' }}>{champion.name}</span>
              <div className="flex items-center gap-3 relative z-10">
                <span className="text-sm" style={{ color: '#AEAEB2' }}>{champion.gamesPlayed} games</span>
                <span className="font-semibold" style={{ color: '#32D74B' }}>{champion.winRate}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Matches */}
      <div className="relative z-10">
        <h4 className="font-semibold mb-3" style={{ color: '#F5F5F7' }}>Recent Matches</h4>
        <div className="space-y-2">
          {player.recentMatches.map((match, idx) => (
            <div
              key={idx}
              className="fluid-glass-dark rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow overflow-hidden"
              style={{
                borderLeft: `4px solid ${match.result === 'win' ? '#32D74B' : '#FF453A'}`
              }}
            >
              <div className="flex items-center justify-between relative z-10">
                <div>
                  <span className="font-medium" style={{ color: '#F5F5F7' }}>{match.champion}</span>
                  <p className="text-sm" style={{ color: '#AEAEB2' }}>{match.kda}</p>
                </div>
                <div className="text-right">
                  <p 
                    className="font-semibold uppercase text-sm"
                    style={{ color: match.result === 'win' ? '#32D74B' : '#FF453A' }}
                  >
                    {match.result}
                  </p>
                  <p className="text-xs" style={{ color: '#8E8E93' }}>{match.timestamp}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

