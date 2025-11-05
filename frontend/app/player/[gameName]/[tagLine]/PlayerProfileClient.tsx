'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAdaptiveColors } from '@/app/hooks/useAdaptiveColors';
import { ArrowLeft, TrendingUp, TrendingDown, Trophy, Target, Zap } from 'lucide-react';
import ShinyText from '@/app/components/ui/ShinyText';
import GlareHover from '@/app/components/ui/GlareHover';
import ClickSpark from '@/app/components/ui/ClickSpark';
import DynamicBackground from '@/app/components/DynamicBackground';
import Header from '@/app/components/Header';
import Footer from '@/app/components/Footer';
import AICoachAnalysis from '@/app/components/AICoachAnalysis';
import ProgressCurveChart from '@/app/components/charts/ProgressCurveChart';
import SkillRadarChart from '@/app/components/charts/SkillRadarChart';
import AnnualSummaryCard from '@/app/components/AnnualSummaryCard';
import AgentModal from '@/app/components/AgentModal';
// ChampionSelectorModal is now handled by AICoachAnalysis

interface PlayerProfileClientProps {
  gameName: string;
  tagLine: string;
}

interface PlayerData {
  success: boolean;
  player: {
    puuid: string;
    summonerId: string;
    accountId: string;
    name: string;
    profileIconId: number;
    summonerLevel: number;
    region: string;
  };
  analysis: {
    total_games: number;
    total_wins: number;
    total_losses: number;
    win_rate: number;
    avg_kda: number;
    best_champions: Array<{
      name: string;
      games: number;
      wins: number;
      win_rate: number;
      avg_kda: number;
    }>;
  };
  summary: string;
  match_range: {
    start_date: string;
    end_date: string;
    total_matches: number;
  };
  opgg?: {
    data: {
      summoner: {
        level: number;
        profile_image_url: string;
        league_stats: Array<{
          game_type: string;
          tier_info: {
            tier: string;
            division: number;
            lp: number;
            tier_image_url: string;
            border_image_url: string;
          };
          win: number;
          lose: number;
          is_hot_streak: boolean;
        }>;
        most_champions?: {
          champion_stats: Array<{
            id: number;
            play: number;
            win: number;
            lose: number;
            basic: {
              kill: number;
              death: number;
              assist: number;
              cs: number;
              gold: number;
              op_score: number;
              mvp: number;
              ace: number;
            };
          }>;
        };
        ladder_rank?: {
          rank: number;
          total: number;
        };
        previous_seasons?: Array<{
          season_id: number;
          tier_info: {
            tier: string;
            division: number;
            lp: number;
          };
        }>;
      };
    };
  };
}

export default function PlayerProfileClient({ gameName, tagLine }: PlayerProfileClientProps) {
  const router = useRouter();
  const colors = useAdaptiveColors();
  const [playerData, setPlayerData] = useState<PlayerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progressData, setProgressData] = useState<any[]>([]);
  const [progressLoading, setProgressLoading] = useState(false);
  const [skillsData, setSkillsData] = useState<any[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [annualSummaryData, setAnnualSummaryData] = useState<any>(null);
  const [annualSummaryLoading, setAnnualSummaryLoading] = useState(false);

  // Agent Modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalAgentData, setModalAgentData] = useState<any>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalContent, setModalContent] = useState<React.ReactNode>(null);

  // Champion selector is now handled by AICoachAnalysis component

  useEffect(() => {
    fetchPlayerData();
    fetchProgressData();
    fetchSkillsData();
    // Don't auto-fetch annual summary anymore - load on demand
  }, [gameName, tagLine]);

  const fetchPlayerData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `/api/summoner/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?count=20`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to fetch player data');
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch player data');
      }

      setPlayerData(data);
    } catch (err) {
      console.error('Error fetching player data:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchProgressData = async () => {
    try {
      setProgressLoading(true);

      const response = await fetch(
        `/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/progress`
      );

      if (!response.ok) {
        console.error('Failed to fetch progress data');
        return;
      }

      const data = await response.json();

      if (data.success && data.data) {
        setProgressData(data.data);
      }
    } catch (err) {
      console.error('Error fetching progress data:', err);
    } finally {
      setProgressLoading(false);
    }
  };

  const fetchSkillsData = async () => {
    try {
      setSkillsLoading(true);

      const response = await fetch(
        `/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/skills?top_n=3`
      );

      if (!response.ok) {
        console.error('Failed to fetch skills data');
        return;
      }

      const data = await response.json();

      if (data.success && data.data) {
        setSkillsData(data.data);
      }
    } catch (err) {
      console.error('Error fetching skills data:', err);
    } finally {
      setSkillsLoading(false);
    }
  };

  const fetchAnnualSummaryData = async () => {
    try {
      setAnnualSummaryLoading(true);

      // Use playerData that's already loaded instead of fetching again
      if (!playerData || !playerData.player?.puuid) {
        console.error('No playerData available for annual summary');
        return null;
      }

      const player = playerData.player;

      // Call Annual Summary Card API (returns structured JSON)
      // Pass best_champions data to avoid re-fetching
      const response = await fetch('/api/annual-summary-card', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          gameName: gameName,
          tagLine: tagLine,
          region: player.region || 'na1',
          bestChampions: playerData.analysis?.best_champions || [], // Pass existing data
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch annual summary: ${response.statusText}`);
      }

      const cardData = await response.json();
      setAnnualSummaryData(cardData);
      return cardData;

    } catch (err) {
      console.error('Error fetching annual summary data:', err);
      return null;
    } finally {
      setAnnualSummaryLoading(false);
    }
  };

  // Custom handler for agents with chart integration
  const handleCustomAgent = async (agentId: string, agent: any): Promise<boolean> => {
    if (!playerData) return false;

    const player = playerData.player;

    // Progress Tracker - use default handling (no modal, generate in card)
    // Annual Summary - use default handling (no modal, generate in card)
    // Champion Mastery - handled by AICoachAnalysis (opens champion selector, then generates in card)

    // Let all agents use default handling from AICoachAnalysis
    return false;
  };

  if (loading) {
    return (
      <>
        <DynamicBackground />
        <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
          <Header hideServerAndEsports={true} />
          <div className="flex-1 flex items-center justify-center p-4">
            <ShinyText text="Loading player data..." speed={3} className="text-xl" />
          </div>
          <Footer />
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <DynamicBackground />
        <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
          <Header hideServerAndEsports={true} />
          <div className="flex-1 flex items-center justify-center p-4">
            <GlareHover width="400px" height="auto" background="rgba(0, 0, 0, 0.3)" borderRadius="16px">
              <div className="fluid-glass p-8 rounded-2xl text-center">
                <ShinyText text="Error" speed={2} className="text-2xl font-bold mb-4" />
                <p style={{ color: colors.textSecondary }} className="mb-6">{error}</p>
                <ClickSpark inline={true}>
                  <button
                    onClick={() => router.push('/')}
                    className="px-6 py-3 rounded-xl font-semibold transition-all"
                    style={{
                      backgroundColor: 'rgba(10, 132, 255, 0.3)',
                      borderWidth: '1px',
                      borderStyle: 'solid',
                      borderColor: 'rgba(10, 132, 255, 0.5)',
                      color: colors.accentBlue
                    }}
                  >
                    <ShinyText text="Back to Home" speed={3} />
                  </button>
                </ClickSpark>
              </div>
            </GlareHover>
          </div>
          <Footer />
        </div>
      </>
    );
  }

  if (!playerData || !playerData.player) return null;

  const { player, analysis } = playerData;

  // Data Dragon profile icon URL
  const profileIconUrl = `https://ddragon.leagueoflegends.com/cdn/14.24.1/img/profileicon/${player.profileIconId}.png`;

  return (
    <>
      <DynamicBackground />
      <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
        <Header hideServerAndEsports={true} />

        <div className="flex-1 p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            {/* Player Header - Linear Layout */}
            <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
              <div className="fluid-glass p-8 rounded-2xl">
                <div className="flex items-center justify-between gap-12">
                  {/* 1. Summoner Name */}
                  <div className="flex items-center gap-4">
                    <div className="relative">
                      <img
                        src={profileIconUrl}
                        alt="Profile Icon"
                        className="w-16 h-16 rounded-full border-4"
                        style={{
                          borderColor: colors.accentBlue,
                          boxShadow: `0 0 20px ${colors.accentBlue}40`
                        }}
                        onError={(e) => {
                          e.currentTarget.src = 'https://ddragon.leagueoflegends.com/cdn/14.24.1/img/profileicon/29.png';
                        }}
                      />
                      <div
                        className="absolute -bottom-1 -right-1 px-2 py-0.5 rounded-full text-xs font-bold"
                        style={{
                          backgroundColor: colors.accentBlue,
                          color: 'white'
                        }}
                      >
                        {player?.summonerLevel || 1}
                      </div>
                    </div>
                    <div>
                      <ShinyText
                        text={`${gameName}#${tagLine}`}
                        speed={3}
                        className="text-2xl font-bold"
                      />
                      <p style={{ color: colors.textSecondary }} className="text-sm mt-1">
                        {player?.region?.toUpperCase() || 'N/A'}
                      </p>
                    </div>
                  </div>

                  {/* 2. Rank Tier */}
                  {playerData.opgg?.data?.summoner?.league_stats && (
                    <div className="flex items-center gap-4">
                      {playerData.opgg.data.summoner.league_stats
                        .filter(stat => stat.tier_info.tier && stat.game_type === 'SOLORANKED')
                        .slice(0, 1)
                        .map((stat, index) => (
                          <div key={index} className="flex items-center gap-4">
                            <img
                              src={stat.tier_info.tier_image_url}
                              alt={stat.tier_info.tier}
                              className="w-20 h-20"
                            />
                            <div>
                              <div className="text-3xl font-bold" style={{ color: colors.textPrimary }}>
                                {stat.tier_info.tier} {stat.tier_info.division}
                              </div>
                              <p style={{ color: colors.textSecondary }} className="text-base mt-1">
                                {stat.tier_info.lp} LP
                              </p>
                              <p style={{ color: colors.textSecondary }} className="text-sm">
                                {stat.win}W {stat.lose}L
                                {stat.is_hot_streak && (
                                  <span className="ml-1" style={{ color: colors.accentRed }}>🔥</span>
                                )}
                              </p>
                            </div>
                          </div>
                        ))}
                    </div>
                  )}

                  {/* 3. Ladder Ranking */}
                  {playerData.opgg?.data?.summoner?.ladder_rank && (
                    <div className="text-center">
                      <p style={{ color: colors.textSecondary }} className="text-sm mb-2">Global Ladder</p>
                      <div className="text-4xl font-bold" style={{ color: colors.accentBlue }}>
                        #{playerData.opgg.data.summoner.ladder_rank.rank.toLocaleString()}
                      </div>
                      <p style={{ color: colors.textSecondary }} className="text-sm mt-2">
                        Top {((playerData.opgg.data.summoner.ladder_rank.rank / playerData.opgg.data.summoner.ladder_rank.total) * 100).toFixed(2)}%
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </GlareHover>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
            <ClickSpark>
              <div className="fluid-glass p-6 rounded-2xl">
                <div className="flex items-center gap-3 mb-3">
                  <Trophy size={24} style={{ color: colors.accentBlue }} />
                  <ShinyText text="Win Rate" speed={3} className="text-lg font-semibold" />
                </div>
                <div className="text-4xl font-bold" style={{ color: colors.textPrimary }}>
                  {analysis.win_rate.toFixed(1)}%
                </div>
                <p style={{ color: colors.textSecondary }} className="text-sm mt-2">
                  {analysis.total_wins}W {analysis.total_losses}L
                </p>
              </div>
            </ClickSpark>
          </GlareHover>

          <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
            <ClickSpark>
              <div className="fluid-glass p-6 rounded-2xl">
                <div className="flex items-center gap-3 mb-3">
                  <Target size={24} style={{ color: colors.accentGreen }} />
                  <ShinyText text="Avg KDA" speed={3} className="text-lg font-semibold" />
                </div>
                <div className="text-4xl font-bold" style={{ color: colors.textPrimary }}>
                  {analysis.avg_kda.toFixed(2)}
                </div>
                <p style={{ color: colors.textSecondary }} className="text-sm mt-2">
                  {analysis.total_games} games played
                </p>
              </div>
            </ClickSpark>
          </GlareHover>

          <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
            <ClickSpark>
              <div className="fluid-glass p-6 rounded-2xl">
                <div className="flex items-center gap-3 mb-3">
                  <Zap size={24} style={{ color: colors.accentYellow }} />
                  <ShinyText text="Champion Pool" speed={3} className="text-lg font-semibold" />
                </div>
                <div className="text-4xl font-bold" style={{ color: colors.textPrimary }}>
                  {analysis.best_champions?.length || 0}
                </div>
                <p style={{ color: colors.textSecondary }} className="text-sm mt-2">
                  Unique champions
                </p>
              </div>
            </ClickSpark>
          </GlareHover>
        </div>

        {/* Charts are now displayed in Agent Modals instead of directly on page */}

        {/* Most Played Champions */}
        <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
          <div className="fluid-glass p-6 rounded-2xl">
            <ShinyText text="Best Champions" speed={3} className="text-2xl font-bold mb-6" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {analysis.best_champions?.slice(0, 6).map((champ, index) => (
                <GlareHover key={index} width="100%" height="auto" background="transparent" borderRadius="12px">
                  <ClickSpark>
                    <div className="fluid-glass-dark p-4 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <ShinyText text={champ.name} speed={3} className="font-semibold" />
                        <div
                          className="flex items-center gap-1"
                          style={{ color: champ.win_rate > 50 ? colors.accentGreen : colors.accentRed }}
                        >
                          {champ.win_rate > 50 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                          <span className="text-sm font-medium">
                            {champ.win_rate.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <p style={{ color: colors.textSecondary }} className="text-sm">
                        {champ.games} games • {champ.wins}W {champ.games - champ.wins}L
                      </p>
                    </div>
                  </ClickSpark>
                </GlareHover>
              ))}
            </div>
          </div>
        </GlareHover>

        {/* AI Coach Analysis - 16 Agent Cards */}
        <AICoachAnalysis
          puuid={player.puuid}
          gameName={gameName}
          tagLine={tagLine}
          region={player.region || 'na1'}
          playerData={playerData}
          onCustomAgentHandle={handleCustomAgent}
        />

        {/* Agent Modal for charts integration */}
        <AgentModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          title={modalTitle}
          agentData={modalAgentData}
          loading={modalLoading}
        >
          {modalContent}
        </AgentModal>

        {/* Champion Selector Modal is now handled by AICoachAnalysis component */}
          </div>
        </div>

        <Footer />
      </div>
    </>
  );
}
