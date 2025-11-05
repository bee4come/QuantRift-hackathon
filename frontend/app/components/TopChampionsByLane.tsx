'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trophy, Sword, Zap, ExternalLink } from 'lucide-react';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import Link from 'next/link';

interface Champion {
  name: string;
  title: string;
  image: string;
  tags: string[];
  combatPower: number;
  tier: string;
  tier_category?: string;
  rank: number;
  lastChanged: string;
  optimalBuild: {
    items: number[];
  };
  role: string;
  lane?: string;
  win_rate?: number;
  pick_rate?: number;
  ban_rate?: number;
}

interface LaneData {
  lane: string;
  champions: Champion[];
}

const RANK_COLORS = ['#FFD700', '#C0C0C0', '#CD7F32'];

const DD_BASE_URL = 'https://ddragon.leagueoflegends.com/cdn';

const TIER_COLORS: Record<string, { color: string; label: string }> = {
  'S': { color: '#FF6B6B', label: 'META' },
  'A': { color: '#FF6B6B', label: 'META' },
  'B': { color: '#4ECDC4', label: 'Normal' },
  'C': { color: '#4ECDC4', label: 'Normal' },
  'D': { color: '#4ECDC4', label: 'Normal' }
};

type ViewMode = 'combat-power' | 'popularity' | 'both';

// Convert API version (15.20.1) to actual patch notes format (25.20)
const convertToActualPatch = (apiVersion: string): string => {
  const parts = apiVersion.split('.');
  if (parts.length >= 2) {
    const major = parseInt(parts[0]);
    const minor = parts[1];
    // Data Dragon uses 15.X but actual patches are 25.X since 2025
    if (major === 15) {
      return `25.${minor}`;
    }
  }
  return apiVersion;
};

export default function TopChampionsByLane() {
  const [lanesData, setLanesData] = useState<LaneData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('both');
  const colors = useAdaptiveColors();

  useEffect(() => {
    const loadTopChampions = async () => {
      setLoading(true);
      setError('');
      
      try {
        console.log('Fetching top champions from API...');
        const leaderboardResponse = await fetch('/api/combatpower/champions/leaderboard?position=all');
        
        console.log('Response status:', leaderboardResponse.status);
        
        if (!leaderboardResponse.ok) {
          throw new Error(`HTTP error! Leaderboard: ${leaderboardResponse.status}`);
        }
        
        const leaderboardData = await leaderboardResponse.json();
        console.log('Received data:', leaderboardData);
        
        if (!leaderboardData.success) {
          throw new Error('Failed to fetch data');
        }
        
        // Process leaderboard data into lanes format
        const lanesMap = new Map<string, Champion[]>();
        
        // Group champions by position
        leaderboardData.leaderboard.data.forEach((entry: any) => {
          const position = entry.position;
          if (!lanesMap.has(position)) {
            lanesMap.set(position, []);
          }
          
          lanesMap.get(position)!.push({
            name: entry.champion_name,
            tier: entry.tier,
            tier_category: entry.tier_category,
            rank: entry.rank,
            win_rate: entry.win_rate,
            pick_rate: entry.pick_rate,
            ban_rate: entry.ban_rate,
            combatPower: entry.combat_power || 0,
            image: `${entry.champion_name}.png`,
            lane: position,
            role: entry.role || 'Unknown',
            tags: entry.tags || [],
            title: entry.title || '',
            lastChanged: entry.last_changed || 'Unknown',
            optimalBuild: entry.optimal_build || null
          });
        });
        
        // Convert to lanes array format
        const lanes = Array.from(lanesMap.entries()).map(([lane, champions]) => ({
          lane,
          champions: champions.sort((a, b) => (a.rank || 999) - (b.rank || 999))
        }));
        
        // Add ALL lane with all champions
        const allChampions = leaderboardData.leaderboard.data.map((entry: any) => ({
          name: entry.champion_name,
          champion_name: entry.champion_name,
          tier: entry.tier,
          tier_category: entry.tier_category,
          rank: entry.rank,
          win_rate: entry.win_rate,
          pick_rate: entry.pick_rate,
          ban_rate: entry.ban_rate,
          combatPower: entry.combat_power || 0,
          combat_power: entry.combat_power || 0,
          image: `${entry.champion_name}.png`,
          lane: entry.position,
          role: entry.role || 'Unknown',
          tags: entry.tags || [],
          title: entry.title || '',
          lastChanged: entry.last_changed || 'Unknown',
          optimalBuild: entry.optimal_build || null
        }));
        
        lanes.unshift({
          lane: 'ALL',
          champions: allChampions.sort((a: Champion, b: Champion) => (a.rank || 999) - (b.rank || 999))
        });
        
        setVersion(leaderboardData.patch || '15.1.1');
        setLanesData(lanes);
        console.log('Successfully loaded', lanes.length, 'lanes');
      } catch (err) {
        console.error('Error loading champion data:', err);
        setError(`Unable to load champion data: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    };

    loadTopChampions();
  }, []);

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-6xl mx-auto px-4 py-8"
      >
        <div className="fluid-glass rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center justify-center gap-3 mb-6">
            <Trophy className="w-6 h-6 animate-pulse" style={{ color: colors.accentBlue }} />
            <h2 className="text-2xl font-bold" style={{ color: colors.textPrimary }}>
              Top Champions by Lane
            </h2>
          </div>
          <div className="text-center" style={{ color: colors.textSecondary }}>
            Loading...
          </div>
        </div>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-6xl mx-auto px-4 py-8"
      >
        <div className="fluid-glass rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center justify-center gap-3 mb-6">
            <Trophy className="w-6 h-6" style={{ color: colors.accentBlue }} />
            <h2 className="text-2xl font-bold" style={{ color: colors.textPrimary }}>
              Top Champions by Lane
            </h2>
          </div>
          <div className="text-center" style={{ color: '#FF453A' }}>
            {error}
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-7xl mx-auto px-4 py-8"
    >
      <div className="fluid-glass rounded-2xl p-8 shadow-2xl">
        {/* Portal Button - Above Title */}
        <div className="flex justify-center mb-6">
          <Link 
            href="/champions" 
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-semibold text-base transition-all hover:scale-105 hover:shadow-lg"
            style={{
              background: 'linear-gradient(135deg, rgba(10, 132, 255, 0.4) 0%, rgba(191, 90, 242, 0.4) 100%)',
              borderWidth: '2px',
              borderStyle: 'solid',
              borderColor: 'rgba(255, 255, 255, 0.3)',
              color: colors.textPrimary,
              boxShadow: '0 4px 12px rgba(10, 132, 255, 0.2)'
            }}
          >
            <ExternalLink className="w-5 h-5" />
            View All Champions
          </Link>
        </div>

        <div className="flex items-center justify-center gap-3 mb-6">
          <Trophy className="w-7 h-7" style={{ color: colors.accentBlue }} />
          <h2 className="text-3xl font-bold" style={{ color: colors.textPrimary }}>
            Top Champions by Lane
          </h2>
          <Trophy className="w-7 h-7" style={{ color: colors.accentPurple }} />
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <button
            onClick={() => setViewMode('combat-power')}
            className="px-4 py-2 rounded-lg font-medium transition-all"
              style={{
                backgroundColor: viewMode === 'combat-power' ? 'rgba(10, 132, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)',
                borderWidth: '1px',
                borderStyle: 'solid',
                borderColor: viewMode === 'combat-power' ? 'rgba(10, 132, 255, 0.5)' : 'rgba(255, 255, 255, 0.2)',
                color: viewMode === 'combat-power' ? colors.accentBlue : colors.textSecondary
              }}
          >
            Combat Power
          </button>
          <button
            onClick={() => setViewMode('popularity')}
            className="px-4 py-2 rounded-lg font-medium transition-all"
            style={{
              backgroundColor: viewMode === 'popularity' ? 'rgba(191, 90, 242, 0.3)' : 'rgba(255, 255, 255, 0.1)',
              borderWidth: '1px',
              borderStyle: 'solid',
              borderColor: viewMode === 'popularity' ? 'rgba(191, 90, 242, 0.5)' : 'rgba(255, 255, 255, 0.2)',
              color: viewMode === 'popularity' ? colors.accentPurple : colors.textSecondary
            }}
          >
            Live Tier
          </button>
          <button
            onClick={() => setViewMode('both')}
            className="px-4 py-2 rounded-lg font-medium transition-all"
            style={{
              backgroundColor: viewMode === 'both' ? 'rgba(255, 214, 10, 0.3)' : 'rgba(255, 255, 255, 0.1)',
              borderWidth: '1px',
              borderStyle: 'solid',
              borderColor: viewMode === 'both' ? 'rgba(255, 214, 10, 0.5)' : 'rgba(255, 255, 255, 0.2)',
              color: viewMode === 'both' ? '#FFD60A' : colors.textSecondary
            }}
          >
            Both
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          {lanesData.map((laneData, laneIndex) => {
            const sortedChampions = viewMode === 'popularity' 
              ? [...laneData.champions].sort((a, b) => {
                  // META champions first
                  if (a.tier_category === 'META' && b.tier_category !== 'META') return -1;
                  if (a.tier_category !== 'META' && b.tier_category === 'META') return 1;
                  
                  // Within same category, sort by rank (lower rank = better)
                  return (a.rank || 999) - (b.rank || 999);
                })
              : viewMode === 'combat-power'
              ? [...laneData.champions].sort((a, b) => b.combatPower - a.combatPower)
              : [...laneData.champions].sort((a, b) => {
                  // META champions first, then by combat power (highest first)
                  if (a.tier_category === 'META' && b.tier_category !== 'META') return -1;
                  if (a.tier_category !== 'META' && b.tier_category === 'META') return 1;
                  
                  // Within same category, sort by combat power (highest first)
                  return (b.combatPower || 0) - (a.combatPower || 0);
                });
            
            return (
              <motion.div
                key={laneData.lane}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: laneIndex * 0.1 }}
                className="fluid-glass-dark rounded-xl p-5"
                style={{
                  background: 'linear-gradient(135deg, rgba(10, 132, 255, 0.1) 0%, rgba(191, 90, 242, 0.1) 100%)',
                  border: '1px solid rgba(255, 255, 255, 0.1)'
                }}
              >
                {/* Lane Header */}
                <div className="flex items-center justify-between mb-4 pb-3 border-b" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }}>
                  <div className="text-sm uppercase tracking-wider font-bold" style={{ color: colors.textPrimary }}>
                    {laneData.lane}
                  </div>
                  <Sword className="w-4 h-4" style={{ color: colors.accentBlue }} />
                </div>
                
                {/* Top 3 Champions */}
                <div className="space-y-3">
                  {sortedChampions.slice(0, 3).map((champion, index) => (
                  <motion.div
                    key={`${laneData.lane}-${index}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: laneIndex * 0.1 + index * 0.05 }}
                    className="fluid-glass rounded-lg p-3 hover:scale-102 transition-all duration-200 relative overflow-hidden"
                    style={{
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: `1px solid ${RANK_COLORS[index]}40`
                    }}
                  >
                    {/* Background Champion Image */}
                    <div 
                      className="absolute top-0 right-0 w-20 h-20 opacity-10"
                      style={{
                        backgroundImage: `url(${DD_BASE_URL}/${version}/img/champion/${champion.image})`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                        filter: 'blur(2px)'
                      }}
                    />
                    
                    {/* Rank Badge and Champion Info */}
                    <div className="flex items-start gap-2 mb-2 relative z-10">
                      <div 
                        className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs"
                        style={{
                          backgroundColor: `${RANK_COLORS[index]}30`,
                          color: RANK_COLORS[index],
                          border: `2px solid ${RANK_COLORS[index]}`
                        }}
                      >
                        {index + 1}
                      </div>
                      
                      {/* Champion Portrait */}
                      <div 
                        className="flex-shrink-0 w-10 h-10 rounded-lg border-2 overflow-hidden"
                        style={{
                          borderColor: RANK_COLORS[index],
                          backgroundImage: `url(${DD_BASE_URL}/${version}/img/champion/${champion.image})`,
                          backgroundSize: 'cover',
                          backgroundPosition: 'center'
                        }}
                      />
                      
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-bold truncate" style={{ color: colors.textPrimary }}>
                          {champion.name}
                        </div>
                      </div>
                    </div>

                    {/* Build Items */}
                    <div className="flex items-center gap-1 mb-2 relative z-10">
                      {champion.optimalBuild.items.slice(0, 3).map((itemId, itemIndex) => (
                        <div
                          key={itemIndex}
                          className="w-6 h-6 rounded border"
                          style={{
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                            backgroundImage: `url(${DD_BASE_URL}/${version}/img/item/${itemId}.png)`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center'
                          }}
                        />
                      ))}
                      {champion.optimalBuild.items.length > 3 && (
                        <div 
                          className="w-6 h-6 rounded border flex items-center justify-center text-xs font-bold"
                          style={{
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                            backgroundColor: 'rgba(0, 0, 0, 0.5)',
                            color: colors.textSecondary
                          }}
                        >
                          +{champion.optimalBuild.items.length - 3}
                        </div>
                      )}
                    </div>

                    {/* Metrics Display */}
                    <div className="space-y-2 mt-2 pt-2 border-t relative z-10" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }}>
                      {/* Last Changed Patch */}
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-xs" style={{ color: colors.textSecondary }}>Updated:</span>
                        {(() => {
                          const currentPatch = convertToActualPatch(version);
                          const championPatch = champion.lastChanged.replace('V', '');
                          const isCurrentPatch = championPatch === currentPatch;
                          return (
                            <span 
                              className="font-bold text-xs px-2 py-0.5 rounded"
                              style={{ 
                                color: isCurrentPatch ? '#34C759' : '#FF9500',
                                backgroundColor: isCurrentPatch ? 'rgba(52, 199, 89, 0.2)' : 'rgba(255, 149, 0, 0.2)',
                                border: isCurrentPatch ? '1px solid rgba(52, 199, 89, 0.3)' : '1px solid rgba(255, 149, 0, 0.3)'
                              }}
                            >
                              {championPatch}
                            </span>
                          );
                        })()}
                      </div>

                      {(viewMode === 'combat-power' || viewMode === 'both') && (
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-1">
                            <Zap className="w-3 h-3" style={{ color: '#FFD60A' }} />
                            <span className="text-xs" style={{ color: colors.textSecondary }}>CP:</span>
                          </div>
                          <span className="font-bold" style={{ color: '#FFD60A' }}>
                            {champion.combatPower.toLocaleString()}
                          </span>
                        </div>
                      )}
                      
                      {(viewMode === 'popularity' || viewMode === 'both') && (
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-xs" style={{ color: colors.textSecondary }}>Live Meta:</span>
                          <span 
                            className="font-bold text-xs px-2 py-0.5 rounded"
                            style={{ 
                              color: champion.tier_category === 'META' ? '#FF6B6B' : '#4ECDC4',
                              backgroundColor: champion.tier_category === 'META' ? 'rgba(255, 107, 107, 0.3)' : 'rgba(78, 205, 196, 0.3)',
                              border: champion.tier_category === 'META' ? '1px solid rgba(255, 107, 107, 0.6)' : '1px solid rgba(78, 205, 196, 0.6)'
                            }}
                          >
                            {champion.tier_category || 'Normal'}
                          </span>
                        </div>
                      )}
                      
                      {/* Hidden Gem Indicator */}
                      {viewMode === 'both' && champion.tier_category === 'Normal' && index === 0 && (
                        <div 
                          className="flex items-center gap-1 text-xs px-2 py-1 rounded animate-pulse"
                          style={{
                            backgroundColor: 'rgba(255, 214, 10, 0.2)',
                            border: '1px solid rgba(255, 214, 10, 0.4)',
                            color: '#FFD60A'
                          }}
                        >
                          <Trophy className="w-3 h-3" />
                          <span className="font-bold">Hidden Gem!</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
            );
          })}
        </div>

        <div className="mt-6 text-center space-y-2">
          <div className="text-sm" style={{ color: colors.textSecondary }}>
            {viewMode === 'combat-power' && 'Combat Power: Mathematical analysis of champion stats with optimal builds'}
            {viewMode === 'popularity' && 'Live Tier: Official OP.GG tier rankings (META/Normal)'}
            {viewMode === 'both' && 'Dual Metrics: Compare theoretical power vs real-world meta'}
          </div>
          <div className="text-xs flex items-center justify-center gap-2 flex-wrap" style={{ color: colors.textSecondary }}>
            <span>Patch {convertToActualPatch(version)}</span>
            <span>•</span>
            <span>Based on 6-item builds</span>
            {viewMode === 'both' && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Trophy className="w-3 h-3" style={{ color: '#FFD60A' }} />
                  Hidden Gem = High CP + Normal Tier
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

