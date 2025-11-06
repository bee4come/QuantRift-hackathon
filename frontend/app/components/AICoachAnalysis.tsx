'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Trophy,
  Users,
  Target,
  Lightbulb,
  Boxes,
  Clock,
  BarChart3,
  Zap,
  FileText
} from 'lucide-react';
import AgentCard, { AgentStatus } from './AgentCard';
import DetailedAnalysisModal from './DetailedAnalysisModal';
import PlayerComparisonInput from './PlayerComparisonInput';
import DataStatusChecker from './DataStatusChecker';
import ChampionSelectorModal from './ChampionSelectorModal';
import FriendInputModal from './FriendInputModal';
import RoleSelectorModal from './RoleSelectorModal';
import MatchSelectorModal from './MatchSelectorModal';
import ShinyText from './ui/ShinyText';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

interface TimeRangeOption {
  id: string;
  label: string;
  value: string;
  description: string;
}

interface AgentState {
  id: string;
  name: string;
  description: string;
  icon: any;
  endpoint: string;
  status: AgentStatus;
  detailedReport?: string;
  error?: string;
  timeRangeOptions?: TimeRangeOption[];
  selectedTimeRange?: string;
}

interface AICoachAnalysisProps {
  puuid: string;
  gameName: string;
  tagLine: string;
  region?: string;
  playerData?: any; // Optional: for extracting champion/rank/role data
  onCustomAgentHandle?: (agentId: string, agent: AgentState) => Promise<boolean> | boolean; // Return true if handled
}

export default function AICoachAnalysis({
  puuid,
  gameName,
  tagLine,
  region = 'na1',
  playerData,
  onCustomAgentHandle
}: AICoachAnalysisProps) {
  const colors = useAdaptiveColors();
  const [comparisonPlayers, setComparisonPlayers] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentState | null>(null);
  const [dataReady, setDataReady] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);

  // Modal states for parameter selection
  const [championModalOpen, setChampionModalOpen] = useState(false);
  const [friendModalOpen, setFriendModalOpen] = useState(false);
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [matchModalOpen, setMatchModalOpen] = useState(false);
  const [matchesData, setMatchesData] = useState<any[]>([]);
  const [currentMatchAgent, setCurrentMatchAgent] = useState<string>('match-analysis'); // Track which agent is using match selector
  const [friendGameName, setFriendGameName] = useState('');
  const [friendTagLine, setFriendTagLine] = useState('');

  // Initialize all 9 agents (3x3 grid)
  const [agents, setAgents] = useState<AgentState[]>([
    // Row 1: Core Analysis
    {
      id: 'annual-summary',
      name: 'Annual Summary',
      description: 'Year-in-review performance highlights',
      icon: FileText,
      endpoint: '/v1/agents/annual-summary',
      status: 'idle',
      timeRangeOptions: [
        {
          id: '2024-full-year',
          label: '2024 Full Year',
          value: '2024-01-01',
          description: 'From January 1st, 2024 to today'
        },
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365',
          description: 'Most recent 365 days'
        }
      ],
      selectedTimeRange: '2024-01-01' // Default to 2024 full year
    },
    {
      id: 'comparison-hub',
      name: 'Comparison Hub',
      description: 'Compare with friends or peers',
      icon: Users,
      endpoint: '/v1/agents/friend-comparison', // Will handle both friend and peer
      status: 'idle'
    },
    {
      id: 'build-simulator',
      name: 'Build Simulator',
      description: 'Optimize builds and itemization',
      icon: Boxes,
      endpoint: '/v1/agents/build-simulator',
      status: 'idle'
    },

    // Row 2: Deep Dive
    {
      id: 'match-analysis',
      name: 'Match Analysis',
      description: 'Deep dive into match timeline',
      icon: Clock,
      endpoint: '/v1/agents/timeline-deep-dive', // Merges timeline + postgame
      status: 'idle'
    },
    {
      id: 'champion-mastery',
      name: 'Champion Mastery',
      description: 'Deep dive into champion performance',
      icon: Trophy,
      endpoint: '/v1/agents/champion-mastery',
      status: 'idle'
    },
    {
      id: 'role-specialization',
      name: 'Role Specialization',
      description: 'Role-specific performance insights',
      icon: Target,
      endpoint: '/v1/agents/role-specialization',
      status: 'idle'
    },

    // Row 3: Trends & Tools
    {
      id: 'version-trends',
      name: 'Version Trends',
      description: 'Cross-patch performance analysis',
      icon: Zap,
      endpoint: '/v1/agents/multi-version', // Merges multi-version + version-comparison
      status: 'idle'
    },
    {
      id: 'performance-insights',
      name: 'Performance Insights',
      description: 'Strengths, weaknesses & growth',
      icon: BarChart3,
      endpoint: '/v1/agents/weakness-analysis', // Merges weakness + detailed + progress
      status: 'idle',
      timeRangeOptions: [
        {
          id: '2024-full-year',
          label: '2024 Full Year',
          value: '2024-01-01',
          description: 'From January 1st, 2024 to today'
        },
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365',
          description: 'Most recent 365 days'
        }
      ],
      selectedTimeRange: '2024-01-01' // Default to 2024 full year
    },
    {
      id: 'champion-recommendation',
      name: 'Champion Recommendation',
      description: 'Best champions for your playstyle',
      icon: Lightbulb,
      endpoint: '/v1/agents/champion-recommendation',
      status: 'idle'
    }
  ]);

  const updateAgentStatus = (id: string, updates: Partial<AgentState>) => {
    setAgents((prev) =>
      prev.map((agent) => (agent.id === id ? { ...agent, ...updates } : agent))
    );
  };

  const handleTimeRangeChange = (agentId: string, timeRange: string) => {
    updateAgentStatus(agentId, { selectedTimeRange: timeRange });
  };

  const handleGenerate = async (agent: AgentState) => {
    console.log(`🔵 handleGenerate called for agent: ${agent.id}`);

    // If already generated, just show the report
    if (agent.status === 'ready' && agent.detailedReport) {
      setSelectedAgent(agent);
      return;
    }

    // Check for custom handling first (e.g., for charts integration)
    if (onCustomAgentHandle && await onCustomAgentHandle(agent.id, agent)) {
      console.log(`🟣 Custom handler took over for ${agent.id}`);
      return; // Custom handler took over
    }

    // Special handling: agents that need parameter selection
    if (agent.id === 'champion-mastery') {
      setChampionModalOpen(true);
      return;
    }
    if (agent.id === 'comparison-hub') {
      setFriendModalOpen(true);
      return;
    }
    if (agent.id === 'role-specialization') {
      setRoleModalOpen(true);
      return;
    }
    if (agent.id === 'match-analysis') {
      setCurrentMatchAgent(agent.id);
      await fetchMatches();
      setMatchModalOpen(true);
      return;
    }

    console.log(`🟢 Starting analysis generation for ${agent.id}`);
    updateAgentStatus(agent.id, { status: 'generating', error: undefined });

    try {
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agent.id}`;
      const body: any = {
        puuid,
        region,
        recent_count: 20,
        model: 'sonnet' // Use Sonnet for detailed analysis
      };

      // Add time range parameter if agent has time range options
      if (agent.selectedTimeRange) {
        body.time_range = agent.selectedTimeRange;
      }

      const result = await fetchAgentStream(url, body);
      const detailedReport = result.detailed || '';

      updateAgentStatus(agent.id, {
        status: 'ready',
        detailedReport: detailedReport
      });

      // Auto-open modal with report
      const updatedAgent = agents.find((a) => a.id === agent.id);
      if (updatedAgent) {
        setSelectedAgent({ ...updatedAgent, detailedReport });
      }
    } catch (error) {
      console.error(`❌ Error generating analysis for ${agent.id}:`, error);
      updateAgentStatus(agent.id, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Handler for champion selection
  const handleChampionSelect = async (championId: number, championName: string) => {
    const agentId = 'champion-mastery';
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agentId}`;
      const body = {
        puuid,
        region,
        recent_count: 20,
        model: 'sonnet',
        champion_id: championId
      };

      const result = await fetchAgentStream(url, body);
      const detailedReport = result.detailed || '';

      updateAgentStatus(agentId, {
        status: 'ready',
        detailedReport: detailedReport
      });

      // Auto-open modal
      const agent = agents.find((a) => a.id === agentId);
      if (agent) {
        setSelectedAgent({ ...agent, detailedReport });
      }
    } catch (error) {
      console.error('Champion mastery error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Handler for friend comparison or rank comparison (now part of comparison-hub)
  const handleFriendSelect = async (friendGameName: string, friendTagLine: string, rank?: string) => {
    const agentId = 'comparison-hub';
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agentId}`;
      const body: any = {
        puuid,
        region,
        game_name: gameName,
        tag_line: tagLine,
        recent_count: 20,
        model: 'sonnet'
      };

      // Add either friend info or rank parameter
      if (rank) {
        body.rank = rank;
      } else {
        body.friend_game_name = friendGameName;
        body.friend_tag_line = friendTagLine;
      }

      const result = await fetchAgentStream(url, body);
      const detailedReport = result.detailed || '';

      updateAgentStatus(agentId, {
        status: 'ready',
        detailedReport: detailedReport
      });

      // Auto-open modal
      const agent = agents.find((a) => a.id === agentId);
      if (agent) {
        setSelectedAgent({ ...agent, detailedReport });
      }
    } catch (error) {
      console.error('Comparison hub error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Handler for role selection
  const handleRoleSelect = async (role: string) => {
    const agentId = 'role-specialization';
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agentId}`;
      const body = {
        puuid,
        region,
        recent_count: 20,
        model: 'sonnet',
        role: role
      };

      const result = await fetchAgentStream(url, body);
      const detailedReport = result.detailed || '';

      updateAgentStatus(agentId, {
        status: 'ready',
        detailedReport: detailedReport
      });

      // Auto-open modal
      const agent = agents.find((a) => a.id === agentId);
      if (agent) {
        setSelectedAgent({ ...agent, detailedReport });
      }
    } catch (error) {
      console.error('Role specialization error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Fetch matches for timeline analysis
  const fetchMatches = async () => {
    try {
      const response = await fetch(`/api/player/${gameName}/${tagLine}/matches?limit=20`);
      const data = await response.json();
      if (data.success) {
        setMatchesData(data.matches);
      } else {
        console.error('Failed to fetch matches:', data.error);
        setMatchesData([]);
      }
    } catch (error) {
      console.error('Error fetching matches:', error);
      setMatchesData([]);
    }
  };

  // Handler for match selection
  const handleMatchSelect = async (matchId: string) => {
    const agentId = currentMatchAgent;  // Use the tracked agent ID
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      // Import stream utility
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      // Use SSE stream to get analysis
      const url = `/api/agents/${agentId}`;
      const body = {
        puuid,
        region,
        recent_count: 20,
        model: 'sonnet',
        match_id: matchId
      };

      const result = await fetchAgentStream(url, body);

      const detailedReport = result.detailed || '';

      updateAgentStatus(agentId, {
        status: 'ready',
        detailedReport: detailedReport
      });

      // Auto-open modal with report
      const agent = agents.find((a) => a.id === agentId);
      if (agent) {
        setSelectedAgent({ ...agent, detailedReport });
      }
    } catch (error) {
      console.error('Timeline deep dive error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Extract data from playerData for modals
  const playerChampions = playerData?.analysis?.best_champions?.map((champ: any) => ({
    champion_id: parseInt(champ.champion_id || '0'),
    champion_name: champ.name,
    games_played: champ.games,
    wins: champ.wins,
    win_rate: champ.win_rate,
    avg_kda: champ.avg_kda || 0
  })) || [];

  const currentRank = playerData?.opgg?.data?.summoner?.league_stats
    ?.find((stat: any) => stat.game_type === 'SOLORANKED')
    ?.tier_info?.tier || 'PLATINUM';

  // Extract role stats from playerData (from Player-Pack by_cr aggregation)
  const roleStats = (playerData?.role_stats || []).map((stat: any) => ({
    role: stat.role as 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT',
    games: stat.games || 0,
    wins: stat.wins || 0,
    win_rate: stat.win_rate || 0,
    avg_kda: stat.avg_kda || 0
  }));

  return (
    <div className="mt-8">
      {/* Section Header */}
      <div className="mb-6">
        <ShinyText text="🤖 AI Coach Analysis" speed={4} className="text-3xl font-bold mb-2" />
        <p className="text-sm" style={{ color: '#8E8E93' }}>
          Personalized insights powered by advanced AI analysis
        </p>
      </div>

      {/* Data Status Checker */}
      {!dataReady && (
        <div className="mb-6 p-6 rounded-lg border border-gray-700 bg-gray-800/50">
          <DataStatusChecker
            gameName={gameName}
            tagLine={tagLine}
            onDataReady={() => setDataReady(true)}
            onError={(error) => setDataError(error)}
          />
        </div>
      )}

      {/* Show error if data fetch failed */}
      {dataError && (
        <div className="mb-6 p-4 rounded-lg bg-red-900/20 border border-red-500/50">
          <p className="text-red-400">
            Failed to load data: {dataError}. Agents may not work properly.
          </p>
        </div>
      )}

      {/* Only show agents if data is ready or if there was an error (allow retry) */}
      {(dataReady || dataError) && (
        <>

      {/* Row 1: Core Analysis */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
        {agents.slice(0, 3).map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onGenerate={() => handleGenerate(agent)}
            onTimeRangeChange={(timeRange) => handleTimeRangeChange(agent.id, timeRange)}
          />
        ))}
      </div>

      {/* Row 2: Deep Dive */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
        {agents.slice(3, 6).map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onGenerate={() => handleGenerate(agent)}
            onTimeRangeChange={(timeRange) => handleTimeRangeChange(agent.id, timeRange)}
          />
        ))}
      </div>

      {/* Row 3: Trends & Tools */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.slice(6, 9).map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onGenerate={() => handleGenerate(agent)}
            onTimeRangeChange={(timeRange) => handleTimeRangeChange(agent.id, timeRange)}
          />
        ))}
      </div>

      {/* Detailed Analysis Modal */}
      {selectedAgent && (
        <DetailedAnalysisModal
          isOpen={!!selectedAgent}
          onClose={() => setSelectedAgent(null)}
          agentName={selectedAgent.name}
          agentDescription={selectedAgent.description}
          detailedReport={selectedAgent.detailedReport || ''}
        />
      )}

      {/* Parameter Selection Modals */}
      <ChampionSelectorModal
        isOpen={championModalOpen}
        onClose={() => setChampionModalOpen(false)}
        onSelect={handleChampionSelect}
        playerChampions={playerChampions}
        gameName={gameName}
        tagLine={tagLine}
      />

      <FriendInputModal
        isOpen={friendModalOpen}
        onClose={() => setFriendModalOpen(false)}
        onConfirm={handleFriendSelect}
        currentPlayerName={gameName}
        currentPlayerTag={tagLine}
      />

      <RoleSelectorModal
        isOpen={roleModalOpen}
        onClose={() => setRoleModalOpen(false)}
        onSelect={handleRoleSelect}
        roleStats={roleStats}
        gameName={gameName}
        tagLine={tagLine}
      />

      <MatchSelectorModal
        isOpen={matchModalOpen}
        onClose={() => setMatchModalOpen(false)}
        onSelect={handleMatchSelect}
        matches={matchesData}
        gameName={gameName}
        tagLine={tagLine}
      />
        </>
      )}
    </div>
  );
}
