'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trophy, ArrowLeft, Flame } from 'lucide-react';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import Header from '../components/Header';
import Footer from '../components/Footer';
import GlareHover from '../components/ui/GlareHover';
import ClickSpark from '../components/ui/ClickSpark';
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
  lane: string;
  win_rate?: number;
  pick_rate?: number;
  ban_rate?: number;
}

interface LaneData {
  lane: string;
  champions: Champion[];
}

const TIER_COLORS: Record<string, { bg: string; border: string; text: string; label: string }> = {
  'S': { bg: 'rgba(255, 107, 107, 0.3)', border: '#FF6B6B', text: '#FF6B6B', label: 'META' },
  'A': { bg: 'rgba(255, 107, 107, 0.3)', border: '#FF6B6B', text: '#FF6B6B', label: 'META' },
  'B': { bg: 'rgba(78, 205, 196, 0.25)', border: '#4ECDC4', text: '#4ECDC4', label: 'Normal' },
  'C': { bg: 'rgba(78, 205, 196, 0.25)', border: '#4ECDC4', text: '#4ECDC4', label: 'Normal' },
  'D': { bg: 'rgba(78, 205, 196, 0.25)', border: '#4ECDC4', text: '#4ECDC4', label: 'Normal' }
};

const DD_BASE_URL = 'https://ddragon.leagueoflegends.com/cdn';

type ViewMode = 'combat-power' | 'popularity' | 'both';
type SelectedLane = 'ALL' | 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT';

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

const LANE_ICONS: Record<string, string | null> = {
  'ALL': null,
  'TOP': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-champ-select/global/default/svg/position-top.svg',
  'JUNGLE': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-champ-select/global/default/svg/position-jungle.svg',
  'MID': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-champ-select/global/default/svg/position-middle.svg',
  'ADC': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-champ-select/global/default/svg/position-bottom.svg',
  'SUPPORT': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-champ-select/global/default/svg/position-utility.svg'
};

export default function ChampionsClient() {
  const [lanesData, setLanesData] = useState<LaneData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('both');
  const [selectedLane, setSelectedLane] = useState<SelectedLane>('ALL');
  const colors = useAdaptiveColors();

  useEffect(() => {
    const loadChampions = async () => {
      try {
        const leaderboardResponse = await fetch('/api/combatpower/champions/leaderboard?position=all');
        
        if (!leaderboardResponse.ok) {
          throw new Error(`HTTP error! Leaderboard: ${leaderboardResponse.status}`);
        }
        
        const leaderboardData = await leaderboardResponse.json();
        
        if (!leaderboardData.success) {
          throw new Error('Failed to fetch data');
        }
        
        // Process leaderboard data into lanes format
        const lanesMap = new Map<string, Champion[]>();
        
        // Group champions by position
        const leaderboardEntries = leaderboardData?.leaderboard?.data || leaderboardData?.data || [];
        leaderboardEntries.forEach((entry: any) => {
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
        const allChampions = leaderboardEntries.map((entry: any) => ({
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
      } catch (err) {
        console.error('Error loading champion data:', err);
        setError(`Unable to load champion data: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    };

    loadChampions();
  }, []);

  const getFilteredAndSortedChampions = () => {
    const champions = selectedLane === 'ALL' 
      ? (lanesData.find(l => l.lane === 'ALL')?.champions || [])
      : (lanesData.find(l => l.lane === selectedLane)?.champions || []);
    
    if (viewMode === 'popularity') {
      // Sort by tier category (META first), then by win rate (highest to lowest)
      return [...champions].sort((a, b) => {
        // META champions first
        if (a.tier_category === 'META' && b.tier_category !== 'META') return -1;
        if (a.tier_category !== 'META' && b.tier_category === 'META') return 1;
        
        // Within same category, sort by win rate (highest to lowest)
        return (b.win_rate || 0) - (a.win_rate || 0);
      });
    } else if (viewMode === 'combat-power') {
      return [...champions].sort((a, b) => b.combatPower - a.combatPower);
    } else {
      // For "both" view, sort by tier category (META first), then by combat power (highest first)
      return [...champions].sort((a, b) => {
        // META champions first
        if (a.tier_category === 'META' && b.tier_category !== 'META') return -1;
        if (a.tier_category !== 'META' && b.tier_category === 'META') return 1;
        
        // Within same category, sort by combat power (highest first)
        return (b.combatPower || 0) - (a.combatPower || 0);
      });
    }
  };

  const filteredChampions = getFilteredAndSortedChampions();

  if (loading) {
    return (
      <>
        <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
          <Header hideServerAndEsports={true} />
          <div className="flex-1 flex items-center justify-center">
            <motion.div className="frosted-glass rounded-2xl p-8 shadow-2xl max-w-md mx-4">
              <h2 className="text-3xl font-bold mb-4 text-center" style={{ color: colors.textPrimary }}>
                Loading Champions...
              </h2>
              <div className="mt-6 flex justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-4" style={{ borderColor: colors.accentBlue, borderTopColor: 'transparent' }}></div>
              </div>
            </motion.div>
          </div>
          <Footer />
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
          <Header hideServerAndEsports={true} />
          <div className="flex-1 flex items-center justify-center">
            <motion.div className="frosted-glass rounded-2xl p-8 shadow-2xl max-w-md mx-4">
              <h2 className="text-3xl font-bold mb-4 text-center" style={{ color: '#FF453A' }}>Error</h2>
              <p className="text-lg text-center" style={{ color: colors.textSecondary }}>{error}</p>
              <Link href="/" className="mt-6 flex items-center justify-center gap-2 px-4 py-2 rounded-lg" style={{ backgroundColor: 'rgba(10, 132, 255, 0.3)', color: colors.accentBlue }}>
                <ArrowLeft className="w-4 h-4" />
                Back to Home
              </Link>
            </motion.div>
          </div>
          <Footer />
        </div>
      </>
    );
  }

  return (
    <>
      <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
        <Header hideServerAndEsports={true} />
        
        <div className="flex-1 w-full max-w-7xl mx-auto px-4 py-6">
          <Link href="/" className="inline-flex items-center gap-2 mb-6 px-4 py-2 rounded-lg transition-all hover:scale-105" style={{ backgroundColor: 'rgba(10, 132, 255, 0.2)', color: colors.accentBlue }}>
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>

          <GlareHover
            width="100%"
            height="auto"
            background="rgba(0, 0, 0, 0.2)"
            borderRadius="16px"
            borderColor="rgba(255, 255, 255, 0.1)"
            glareColor="#ffffff"
            glareOpacity={0.3}
            glareAngle={-45}
            glareSize={200}
            transitionDuration={600}
          >
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="fluid-glass rounded-2xl p-6 shadow-2xl"
            >
            <div className="flex flex-col items-center mb-6">
              <Link href="/">
                <h1 className="text-4xl font-bold flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity" style={{ color: colors.textPrimary }}>
                  <Trophy className="w-8 h-8" style={{ color: colors.accentBlue }} />
                  Champion Tier List
                </h1>
              </Link>
              <p className="text-sm mt-2" style={{ color: colors.textSecondary }}>
                Patch {convertToActualPatch(version)} • Dual metrics: Combat Power & Live Tier
              </p>
            </div>

            <div className="flex items-center justify-center gap-2 mb-6 flex-wrap">
              {(['ALL', 'TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'] as SelectedLane[]).map((lane) => {
                const iconUrl = LANE_ICONS[lane];
                return (
                  <ClickSpark
                    key={lane}
                    sparkColor={selectedLane === lane ? "#0A84FF" : "#FFFFFF"}
                    sparkSize={8}
                    sparkRadius={12}
                    sparkCount={6}
                    duration={300}
                    inline={true}
                  >
                    <button
                      onClick={() => setSelectedLane(lane)}
                      className="px-4 py-2 rounded-lg font-medium transition-all text-sm flex items-center gap-2"
                      style={{
                        backgroundColor: selectedLane === lane ? 'rgba(10, 132, 255, 0.3)' : 'rgba(255, 255, 255, 0.05)',
                        borderWidth: '1px',
                        borderStyle: 'solid',
                        borderColor: selectedLane === lane ? 'rgba(10, 132, 255, 0.5)' : 'rgba(255, 255, 255, 0.1)',
                        color: selectedLane === lane ? colors.accentBlue : colors.textSecondary
                      }}
                    >
                      {iconUrl && (
                        <img 
                          src={iconUrl} 
                          alt={`${lane} icon`}
                          className="w-5 h-5"
                          style={{
                            filter: selectedLane === lane ? 'brightness(0) saturate(100%) invert(47%) sepia(96%) saturate(2742%) hue-rotate(194deg) brightness(102%) contrast(101%)' : 'brightness(0) saturate(100%) invert(70%)'
                          }}
                        />
                      )}
                      {lane}
                    </button>
                  </ClickSpark>
                );
              })}
            </div>

            <div className="flex items-center justify-center gap-2 mb-6">
              <ClickSpark
                sparkColor={viewMode === 'combat-power' ? "#0A84FF" : "#FFFFFF"}
                sparkSize={8}
                sparkRadius={12}
                sparkCount={6}
                duration={300}
                inline={true}
              >
                <button
                  onClick={() => setViewMode('combat-power')}
                  className="px-4 py-2 rounded-lg font-medium transition-all text-sm"
                  style={{
                    backgroundColor: viewMode === 'combat-power' ? 'rgba(10, 132, 255, 0.3)' : 'rgba(255, 255, 255, 0.05)',
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: viewMode === 'combat-power' ? 'rgba(10, 132, 255, 0.5)' : 'rgba(255, 255, 255, 0.1)',
                    color: viewMode === 'combat-power' ? colors.accentBlue : colors.textSecondary
                  }}
                >
                  Combat Power
                </button>
              </ClickSpark>
              <ClickSpark
                sparkColor={viewMode === 'popularity' ? "#BF5AF2" : "#FFFFFF"}
                sparkSize={8}
                sparkRadius={12}
                sparkCount={6}
                duration={300}
                inline={true}
              >
                <button
                  onClick={() => setViewMode('popularity')}
                  className="px-4 py-2 rounded-lg font-medium transition-all text-sm"
                  style={{
                    backgroundColor: viewMode === 'popularity' ? 'rgba(191, 90, 242, 0.3)' : 'rgba(255, 255, 255, 0.05)',
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: viewMode === 'popularity' ? 'rgba(191, 90, 242, 0.5)' : 'rgba(255, 255, 255, 0.1)',
                    color: viewMode === 'popularity' ? colors.accentPurple : colors.textSecondary
                  }}
                >
                  Live Tier
                </button>
              </ClickSpark>
              <ClickSpark
                sparkColor={viewMode === 'both' ? "#FFD60A" : "#FFFFFF"}
                sparkSize={8}
                sparkRadius={12}
                sparkCount={6}
                duration={300}
                inline={true}
              >
                <button
                  onClick={() => setViewMode('both')}
                  className="px-4 py-2 rounded-lg font-medium transition-all text-sm"
                  style={{
                    backgroundColor: viewMode === 'both' ? 'rgba(255, 214, 10, 0.3)' : 'rgba(255, 255, 255, 0.05)',
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: viewMode === 'both' ? 'rgba(255, 214, 10, 0.5)' : 'rgba(255, 255, 255, 0.1)',
                    color: viewMode === 'both' ? '#FFD60A' : colors.textSecondary
                  }}
                >
                  Both
                </button>
              </ClickSpark>
            </div>

            <div className="mb-4 text-xs" style={{ color: colors.textSecondary }}>
              {selectedLane === 'ALL' ? (
                <>
                  Total Champions: <span className="font-bold" style={{ color: colors.textPrimary }}>{filteredChampions.length}</span>
                  {' '}(showing primary lane for each champion)
                </>
              ) : (
                <>
                  Total Champions: <span className="font-bold" style={{ color: colors.textPrimary }}>{filteredChampions.length}</span>
                </>
              )}
            </div>

            <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <div className="grid grid-cols-12 gap-2 px-4 py-3 text-xs font-bold uppercase" style={{ backgroundColor: 'rgba(0, 0, 0, 0.4)', color: colors.textSecondary }}>
                <div className="col-span-1 text-center">Rank</div>
                <div className="col-span-2 text-center">Champion</div>
                <div className="col-span-2 text-center">Popular Build</div>
                <div className="col-span-1 text-center">Patch</div>
                {(viewMode === 'combat-power' || viewMode === 'both') && (
                  <div className="col-span-2 text-center">Combat Power</div>
                )}
                {(viewMode === 'popularity' || viewMode === 'both') && (
                  <div className="col-span-1 text-center">Tier</div>
                )}
                <div className="col-span-1 text-center">Pick Rate</div>
                <div className="col-span-1 text-center">Ban Rate</div>
                <div className="col-span-1 text-center"></div>
              </div>

              <div className="divide-y" style={{ borderColor: 'rgba(255, 255, 255, 0.05)' }}>
                {filteredChampions.map((champion, index) => (
                  <ClickSpark
                    key={`${champion.lane}-${champion.name}-${index}`}
                    sparkColor="#FFFFFF"
                    sparkSize={6}
                    sparkRadius={10}
                    sparkCount={4}
                    duration={250}
                  >
                    <GlareHover
                      width="100%"
                      height="auto"
                      background="transparent"
                      borderRadius="0px"
                      borderColor="transparent"
                      glareColor="#ffffff"
                      glareOpacity={0.1}
                      glareAngle={-45}
                      glareSize={150}
                      transitionDuration={400}
                    >
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.005 }}
                      className="grid grid-cols-12 gap-2 px-4 py-2 hover:bg-opacity-10 transition-all items-center group"
                      style={{ 
                        backgroundColor: index % 2 === 0 ? 'rgba(0, 0, 0, 0.2)' : 'transparent',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.1)'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = index % 2 === 0 ? 'rgba(0, 0, 0, 0.2)' : 'transparent'}
                    >
                    <div className="col-span-1 text-center">
                      <span 
                        className="font-bold text-base"
                        style={{ 
                          color: index < 3 ? ['#FFD700', '#C0C0C0', '#CD7F32'][index] : colors.textSecondary
                        }}
                      >
                        {index + 1}
                      </span>
                    </div>

                    <div className="col-span-2 flex items-center gap-2">
                      <div 
                        className="w-10 h-10 rounded-lg border-2 overflow-hidden flex-shrink-0"
                        style={{
                          borderColor: index < 3 ? ['#FFD700', '#C0C0C0', '#CD7F32'][index] : 'rgba(255, 255, 255, 0.2)',
                          backgroundImage: `url(${DD_BASE_URL}/${version}/img/champion/${champion.image})`,
                          backgroundSize: 'cover',
                          backgroundPosition: 'center'
                        }}
                      />
                      <div className="flex items-center gap-1">
                        <div className="font-bold text-sm" style={{ color: colors.textPrimary }}>{champion.name}</div>
                        {champion.lane && LANE_ICONS[champion.lane as keyof typeof LANE_ICONS] && (
                          <img 
                            src={LANE_ICONS[champion.lane as keyof typeof LANE_ICONS]!} 
                            alt={`${champion.lane} icon`}
                            className="w-4 h-4 opacity-60"
                            style={{
                              filter: 'brightness(0) saturate(100%) invert(70%)'
                            }}
                          />
                        )}
                      </div>
                    </div>

                    <div className="col-span-2">
                      {/* Show all 6 items */}
                      <div className="flex items-center gap-1 px-2">
                        {champion.optimalBuild?.items && champion.optimalBuild.items.length > 0 ? (
                          champion.optimalBuild.items.slice(0, 6).map((itemId, itemIndex) => (
                            <div
                              key={itemIndex}
                              className="w-7 h-7 rounded border flex-shrink-0"
                              style={{
                                borderColor: 'rgba(255, 255, 255, 0.2)',
                                backgroundImage: `url(${DD_BASE_URL}/${version}/img/item/${itemId}.png)`,
                                backgroundSize: 'cover',
                                backgroundPosition: 'center'
                              }}
                              title={`Item ${itemId}`}
                            />
                          ))
                        ) : (
                          <span className="text-xs" style={{ color: colors.textSecondary }}>No build data</span>
                        )}
                      </div>
                    </div>

                    <div className="col-span-1 text-center">
                      {(() => {
                        const currentPatch = convertToActualPatch(version);
                        const championPatch = champion.lastChanged.replace('V', '');
                        const isCurrentPatch = championPatch === currentPatch;
                        return (
                          <span 
                            className="text-xs px-1.5 py-0.5 rounded"
                            style={{ 
                              backgroundColor: isCurrentPatch ? 'rgba(52, 199, 89, 0.2)' : 'rgba(255, 149, 0, 0.2)',
                              color: isCurrentPatch ? '#34C759' : '#FF9500'
                            }}
                          >
                            {championPatch}
                          </span>
                        );
                      })()}
                    </div>

                    {(viewMode === 'combat-power' || viewMode === 'both') && (
                      <div className="col-span-2 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <Flame className="w-4 h-4" style={{ color: '#FF4500' }} />
                          <span className="font-bold text-sm" style={{ color: colors.textPrimary }}>
                            {champion.combatPower.toLocaleString()}
                          </span>
                        </div>
                      </div>
                    )}

                    {(viewMode === 'popularity' || viewMode === 'both') && (
                      <div className="col-span-1 text-center">
                        <span 
                          className="px-2 py-1 rounded font-bold text-xs"
                          style={{ 
                            color: champion.tier_category === 'META' ? '#FF6B6B' : '#4ECDC4',
                            backgroundColor: champion.tier_category === 'META' ? 'rgba(255, 107, 107, 0.3)' : 'rgba(78, 205, 196, 0.25)',
                            borderWidth: '1px',
                            borderStyle: 'solid',
                            borderColor: champion.tier_category === 'META' ? '#FF6B6B' : '#4ECDC4'
                          }}
                        >
                          {champion.tier || 'B'}
                        </span>
                      </div>
                    )}

                    <div className="col-span-1 text-center">
                      <span className="text-xs font-semibold" style={{ color: colors.textPrimary }}>
                        {champion.pick_rate ? `${(champion.pick_rate * 100).toFixed(1)}%` : 'N/A'}
                      </span>
                    </div>

                    <div className="col-span-1 text-center">
                      <span className="text-xs font-semibold" style={{ color: colors.textPrimary }}>
                        {champion.ban_rate ? `${(champion.ban_rate * 100).toFixed(1)}%` : 'N/A'}
                      </span>
                    </div>

                    <div className="col-span-1 text-center">
                    </div>
                    </motion.div>
                    </GlareHover>
                  </ClickSpark>
                ))}
              </div>
            </div>

            <div className="mt-6 text-center text-xs space-y-2" style={{ color: colors.textSecondary }}>
              <p>
                {viewMode === 'combat-power' && 'Combat Power: Mathematical analysis of champion stats with optimal builds'}
                {viewMode === 'popularity' && 'Live Tier: Official OP.GG tier rankings (Meta/Normal) with most popular builds'}
                {viewMode === 'both' && 'Dual Metrics: Combat power calculations with official OP.GG tier rankings'}
              </p>
              {selectedLane === 'ALL' && (
                <p className="text-xs font-semibold" style={{ color: colors.accentBlue }}>
                  Each champion shown in their primary lane (highest win rate × pick rate from OP.GG)
                </p>
              )}
              <p className="text-xs">
                Last Changed: Patch version from <a href="https://wiki.leagueoflegends.com/en-us/List_of_champions" target="_blank" rel="noopener noreferrer" className="underline hover:opacity-80" style={{ color: colors.accentBlue }}>League of Legends Wiki</a>
                {' • '}Popular builds, pick rate & ban rate from <a href="https://op.gg/lol/champions" target="_blank" rel="noopener noreferrer" className="underline hover:opacity-80" style={{ color: colors.accentBlue }}>OP.GG</a>
              </p>
            </div>
            </motion.div>
          </GlareHover>
        </div>
        <Footer />
      </div>
    </>
  );
}

