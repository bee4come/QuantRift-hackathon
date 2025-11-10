'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Trophy,
  Users,
  Target,
  Lightbulb,
  Boxes,
  Clock,
  BarChart3,
  Zap,
  FileText,
  UserPlus,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2
} from 'lucide-react';
import AgentCard, { AgentStatus } from './AgentCard';
import DetailedAnalysisModal from './DetailedAnalysisModal';
import DataStatusChecker from './DataStatusChecker';
import ChampionSelectorModal from './ChampionSelectorModal';
import FriendInputModal from './FriendInputModal';
import RoleSelectorModal from './RoleSelectorModal';
import RankSelectorModal from './RankSelectorModal';
import MatchSelectorModal from './MatchSelectorModal';
import ShinyText from './ui/ShinyText';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import type { TimeRangeOption, RankTypeOption } from './AgentCard';

interface SubOption {
  id: string;
  label: string;
  description: string;
  icon: any;
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
  rankTypeOptions?: RankTypeOption[];
  selectedRankType?: number | null;
  analysisData?: any; // For widgets (Annual Summary, Progress Tracker)
  subOptions?: SubOption[];
  reportsByTimeRange?: Record<string, { detailedReport?: string; analysisData?: any; status: AgentStatus }>; // Store reports by time range
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
  // Early return if puuid is not defined
  if (!puuid) {
    console.error('AICoachAnalysis: puuid is required but not provided');
    return null;
  }

  const colors = useAdaptiveColors();
  const [comparisonPlayers, setComparisonPlayers] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentState | null>(null);
  const [dataReady, setDataReady] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);
  const [insufficientData, setInsufficientData] = useState(false);
  const [dataStatus, setDataStatus] = useState<any>(null);
  const [fetchTaskId, setFetchTaskId] = useState<string | null>(null);
  const [pastSeasonStatus, setPastSeasonStatus] = useState<'success' | 'failed' | 'pending' | 'unknown'>('unknown');
  const [past365Status, setPast365Status] = useState<'success' | 'failed' | 'pending' | 'unknown'>('unknown');
  const [pastSeasonMatchCount, setPastSeasonMatchCount] = useState<number>(0);
  const [past365MatchCount, setPast365MatchCount] = useState<number>(0);
  const [showDataTooltip, setShowDataTooltip] = useState(false);
  const dataIndicatorRef = useRef<HTMLDivElement>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // Rank type data status
  const [rankTypeStatus, setRankTypeStatus] = useState<{
    solo_duo: { past_season: number; past_365: number; status: 'success' | 'failed' | 'pending' | 'unknown' };
    flex: { past_season: number; past_365: number; status: 'success' | 'failed' | 'pending' | 'unknown' };
    normal: { past_season: number; past_365: number; status: 'success' | 'failed' | 'pending' | 'unknown' };
  }>({
    solo_duo: { past_season: 0, past_365: 0, status: 'unknown' },
    flex: { past_season: 0, past_365: 0, status: 'unknown' },
    normal: { past_season: 0, past_365: 0, status: 'unknown' }
  });
  const [showRankTooltip, setShowRankTooltip] = useState<{ [key: string]: boolean }>({});
  const rankIndicatorRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const [rankTooltipPositions, setRankTooltipPositions] = useState<{ [key: string]: { top: number; left: number } }>({});
  
  // Calculate combined status
  const getCombinedStatus = (): 'success' | 'failed' | 'pending' | 'unknown' => {
    if (pastSeasonStatus === 'pending' || past365Status === 'pending') {
      return 'pending';
    }
    if (pastSeasonStatus === 'success' || past365Status === 'success') {
      return 'success';
    }
    if (pastSeasonStatus === 'failed' && past365Status === 'failed') {
      return 'failed';
    }
    return 'unknown';
  };
  
  const combinedStatus = getCombinedStatus();
  const totalMatches = pastSeasonMatchCount + past365MatchCount;

  // Helper function to get Past Season date range based on patch versions
  // Past Season 2024: patch 14.1 (2024-01-09) to patch 14.25 (2025-01-06)
  const getPastSeasonDateRange = (): { start: Date; end: Date } => {
    return {
      start: new Date('2024-01-09'), // patch 14.1 start date
      end: new Date('2025-01-06T23:59:59.999') // patch 14.25 end date
    };
  };

  // Helper function to get patch release date
  const getPatchDate = (patch: string): Date | null => {
    if (!patch) return null;
    
    // Patch date mapping (from patch_manager.py)
    const patchDates: Record<string, string> = {
      // 2024 Season patches (14.1 - 14.25)
      '14.1': '2024-01-09', // Updated: patch 14.1 starts from 2024-01-09
      '14.2': '2024-01-24',
      '14.3': '2024-02-07',
      '14.4': '2024-02-21',
      '14.5': '2024-03-06',
      '14.6': '2024-03-20',
      '14.7': '2024-04-03',
      '14.8': '2024-04-17',
      '14.9': '2024-05-01',
      '14.10': '2024-05-15',
      '14.11': '2024-05-29',
      '14.12': '2024-06-12',
      '14.13': '2024-06-26',
      '14.14': '2024-07-17',
      '14.15': '2024-07-31',
      '14.16': '2024-08-14',
      '14.17': '2024-08-28',
      '14.18': '2024-09-11',
      '14.19': '2024-09-24',
      '14.20': '2024-10-08',
      '14.21': '2024-10-22',
      '14.22': '2024-11-05',
      '14.23': '2024-11-19',
      '14.24': '2024-12-10',
      '14.25': '2024-12-24', // patch 14.25 (ends 2025-01-06)
      // 2025 Season patches
      '25.S1.1': '2025-01-07',
      '25.S1.2': '2025-01-22',
      '2025.S1.3': '2025-02-05',
      '25.04': '2025-02-19',
      '25.05': '2025-03-04',
      '25.06': '2025-03-18',
      '25.07': '2025-04-01',
      '25.08': '2025-04-15',
      '25.09': '2025-04-29',
      '25.10': '2025-05-13',
      '25.11': '2025-05-27',
      '25.12': '2025-06-10',
      '25.13': '2025-06-24',
      '25.14': '2025-07-15',
      '25.15': '2025-07-29',
      '25.16': '2025-08-12',
      '25.17': '2025-08-26',
      '25.18': '2025-09-10',
      '25.19': '2025-09-23',
      '25.20': '2025-10-07',
    };
    
    // Try exact match first
    if (patchDates[patch]) {
      return new Date(patchDates[patch]);
    }
    
    // Try to match Data Dragon format (e.g., "14.1.1" -> "14.1")
    const parts = patch.split('.');
    if (parts.length >= 2) {
      const basePatch = `${parts[0]}.${parts[1]}`;
      if (patchDates[basePatch]) {
        return new Date(patchDates[basePatch]);
      }
    }
    
    return null;
  };

  // Helper function to compare patch versions
  const comparePatchVersion = (patch1: string, patch2: string): number => {
    const parsePatch = (patch: string): number[] => {
      // Handle formats like "14.24", "15.22", "13.24", "25.04" -> [14, 24], [15, 22], etc.
      const parts = patch.split('.');
      const major = parseInt(parts[0]) || 0;
      const minor = parseInt(parts[1]) || 0;
      return [major, minor];
    };
    
    const [major1, minor1] = parsePatch(patch1);
    const [major2, minor2] = parsePatch(patch2);
    
    if (major1 !== major2) return major1 - major2;
    return minor1 - minor2;
  };

  // Helper function to check if a patch is in Past Season (14.1 to 14.25)
  const isPastSeasonPatch = (patch: string): boolean => {
    if (!patch) return false;
    
    // Check if patch starts with 14.
    if (!patch.startsWith('14.')) return false;
    
    // Extract minor version
    const parts = patch.split('.');
    if (parts.length < 2) return false;
    
    const minor = parseInt(parts[1]) || 0;
    // Past Season 2024 is patches 14.1 to 14.25
    return minor >= 1 && minor <= 25;
  };

  // Check if match date is within past 365 days from today
  const isMatchDateWithinPast365Days = (matchDate: string): boolean => {
    if (!matchDate) return false;
    
    try {
      const matchDateTime = new Date(matchDate);
      const today = new Date();
      today.setHours(23, 59, 59, 999); // End of today
      const daysDiff = Math.floor((today.getTime() - matchDateTime.getTime()) / (1000 * 60 * 60 * 24));
      
      // Include matches from today (0 days) to 365 days ago
      return daysDiff >= 0 && daysDiff <= 365;
    } catch {
      return false;
    }
  };
  
  // Check if match date is in Past Season (2024-01-09 to 2025-01-06, patch 14.1 to 14.25)
  const isMatchDateInPastSeason = (matchDate: string): boolean => {
    if (!matchDate) return false;
    
    try {
      const { start, end } = getPastSeasonDateRange();
      
      // Handle ISO format with timezone (e.g., "2024-01-15T10:30:00+00:00" or "2024-01-15T10:30:00Z")
      let dateStr = matchDate;
      if (dateStr.includes('T')) {
        dateStr = dateStr.split('T')[0]; // Extract date part only
      }
      
      // Parse date string (YYYY-MM-DD format)
      const parts = dateStr.split('-');
      if (parts.length !== 3) {
        // Try parsing as Date object
        const matchDateTime = new Date(matchDate);
        if (isNaN(matchDateTime.getTime())) {
          console.warn(`[isMatchDateInPastSeason] Invalid date format: ${matchDate}`);
          return false;
        }
        const isInPastSeason = matchDateTime >= start && matchDateTime <= end;
        console.log(`[isMatchDateInPastSeason] Parsed ${matchDate} -> isInPastSeason=${isInPastSeason}`);
        return isInPastSeason;
      }
      
      const matchDateTime = new Date(matchDate);
      if (isNaN(matchDateTime.getTime())) {
        console.warn(`[isMatchDateInPastSeason] Invalid date format: ${matchDate}`);
        return false;
      }
      
      // Check if date is in Past Season range (2024-01-09 to 2025-01-06)
      const isInPastSeason = matchDateTime >= start && matchDateTime <= end;
      if (isInPastSeason) {
        console.log(`[isMatchDateInPastSeason] Date ${matchDate} is in Past Season (2024-01-09 to 2025-01-06)`);
        return true;
      }
      
      console.log(`[isMatchDateInPastSeason] Date ${matchDate} is NOT in Past Season`);
      return false;
    } catch (err) {
      console.warn(`[isMatchDateInPastSeason] Error parsing date: ${matchDate}`, err);
      return false;
    }
  };

  // Initial data check on mount
  // Handle page refresh/unload - abort all ongoing streams
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (abortControllerRef.current) {
        console.log('[AICoachAnalysis] Aborting stream on page unload');
        abortControllerRef.current.abort();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Also abort on component unmount
      if (abortControllerRef.current) {
        console.log('[AICoachAnalysis] Aborting stream on component unmount');
        abortControllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    const checkInitialDataStatus = async () => {
      try {
        const response = await fetch(`/api/player/${gameName}/${tagLine}/data-status`);
        if (response.ok) {
          const status = await response.json();
          setDataStatus(status);
          
          // Check if data is sufficient
          const hasEnoughGames = status.has_data && status.total_games >= 10;
          
          // Use backend-calculated games counts for Past Season and Past 365 Days
          // Backend now provides accurate counts based on actual match dates
          const pastSeasonGames = status.total_past_season_games || 0;
          const past365Games = status.total_past_365_days_games || 0;
          const hasPastSeasonData = pastSeasonGames > 0;
          const hasPast365DaysData = past365Games > 0;
          
          console.log(`[Past Season] Backend calculated: ${pastSeasonGames} games (hasData: ${hasPastSeasonData})`);
          console.log(`[Past 365] Backend calculated: ${past365Games} games (hasData: ${hasPast365DaysData})`);

          // Set indicator status and match counts
          // If data is insufficient (not enough games or no valid time range data), show failed (red)
          if (status.has_data && status.total_games > 0) {
            // Check if data is sufficient for analysis
            const isDataSufficient = hasEnoughGames && (hasPastSeasonData || hasPast365DaysData);
            
            if (isDataSufficient) {
              // Data is sufficient - show success/unknown based on actual data availability
              setPastSeasonStatus(hasPastSeasonData ? 'success' : 'unknown');
              setPast365Status(hasPast365DaysData ? 'success' : 'unknown');
            } else {
              // Data exists but is insufficient - show failed (red)
              setPastSeasonStatus('failed');
              setPast365Status('failed');
            }
            setPastSeasonMatchCount(pastSeasonGames);
            setPast365MatchCount(past365Games);
          } else {
            // No data at all - show failed (red)
            setPastSeasonStatus('failed');
            setPast365Status('failed');
            setPastSeasonMatchCount(0);
            setPast365MatchCount(0);
          }

          // Set rank type status from backend response
          if (status.rank_types) {
            setRankTypeStatus({
              solo_duo: {
                past_season: status.rank_types.solo_duo?.past_season_games || 0,
                past_365: status.rank_types.solo_duo?.past_365_days_games || 0,
                status: (status.rank_types.solo_duo?.past_season_games || 0) > 0 || (status.rank_types.solo_duo?.past_365_days_games || 0) > 0 ? 'success' : 'unknown'
              },
              flex: {
                past_season: status.rank_types.flex?.past_season_games || 0,
                past_365: status.rank_types.flex?.past_365_days_games || 0,
                status: (status.rank_types.flex?.past_season_games || 0) > 0 || (status.rank_types.flex?.past_365_days_games || 0) > 0 ? 'success' : 'unknown'
              },
              normal: {
                past_season: status.rank_types.normal?.past_season_games || 0,
                past_365: status.rank_types.normal?.past_365_days_games || 0,
                status: (status.rank_types.normal?.past_season_games || 0) > 0 || (status.rank_types.normal?.past_365_days_games || 0) > 0 ? 'success' : 'unknown'
              }
            });
          }

          // Data is sufficient only if:
          // 1. Has enough games (>=10)
          // 2. Has Past Season data (patch 14.1 to 14.25, 2024-01-09 to 2025-01-06) OR has data within past 365 days from today
          if (hasEnoughGames && (hasPastSeasonData || hasPast365DaysData)) {
            setDataReady(true);
            setInsufficientData(false);
          } else {
            setInsufficientData(true);
            setDataReady(false);
          }
        }
      } catch (err) {
        console.error('Error checking initial data status:', err);
      }
    };
    
    checkInitialDataStatus();
    checkFetchStatus();
  }, [gameName, tagLine]);

  const checkFetchStatus = async () => {
    try {
      // Check if there's a task_id stored in localStorage for this player
      const storageKey = `fetch_task_${gameName}_${tagLine}`;
      const storedTaskId = localStorage.getItem(storageKey);
      
      // Check data status for both time ranges
      const dataStatusResponse = await fetch(`/api/player/${gameName}/${tagLine}/data-status`);
      if (dataStatusResponse.ok) {
        const dataStatus = await dataStatusResponse.json();
        
        if (dataStatus.has_data && dataStatus.patches && dataStatus.patches.length > 0) {
          // Use backend-calculated games counts for Past Season and Past 365 Days
          // Backend now provides accurate counts based on actual match dates
          const pastSeasonGames = dataStatus.total_past_season_games || 0;
          const past365Games = dataStatus.total_past_365_days_games || 0;
          const hasPastSeasonData = pastSeasonGames > 0;
          const hasPast365DaysData = past365Games > 0;
          
          console.log(`[Past Season] Backend calculated: ${pastSeasonGames} games (hasData: ${hasPastSeasonData})`);
          console.log(`[Past 365] Backend calculated: ${past365Games} games (hasData: ${hasPast365DaysData})`);
          
          // Check if data is sufficient for analysis
          const hasEnoughGames = dataStatus.total_games >= 10;
          const isDataSufficient = hasEnoughGames && (hasPastSeasonData || hasPast365DaysData);
          
          // Set indicator status and match counts
          if (isDataSufficient) {
            // Data is sufficient - show success/unknown based on actual data availability
            setPastSeasonStatus(hasPastSeasonData ? 'success' : 'unknown');
            setPast365Status(hasPast365DaysData ? 'success' : 'unknown');
          } else {
            // Data exists but is insufficient - show failed (red)
            setPastSeasonStatus('failed');
            setPast365Status('failed');
          }
          setPastSeasonMatchCount(pastSeasonGames);
          setPast365MatchCount(past365Games);
          
          // Set rank type status from backend response
          if (dataStatus.rank_types) {
            setRankTypeStatus({
              solo_duo: {
                past_season: dataStatus.rank_types.solo_duo?.past_season_games || 0,
                past_365: dataStatus.rank_types.solo_duo?.past_365_days_games || 0,
                status: (dataStatus.rank_types.solo_duo?.past_season_games || 0) > 0 || (dataStatus.rank_types.solo_duo?.past_365_days_games || 0) > 0 ? 'success' : 'unknown'
              },
              flex: {
                past_season: dataStatus.rank_types.flex?.past_season_games || 0,
                past_365: dataStatus.rank_types.flex?.past_365_days_games || 0,
                status: (dataStatus.rank_types.flex?.past_season_games || 0) > 0 || (dataStatus.rank_types.flex?.past_365_days_games || 0) > 0 ? 'success' : 'unknown'
              },
              normal: {
                past_season: dataStatus.rank_types.normal?.past_season_games || 0,
                past_365: dataStatus.rank_types.normal?.past_365_days_games || 0,
                status: (dataStatus.rank_types.normal?.past_season_games || 0) > 0 || (dataStatus.rank_types.normal?.past_365_days_games || 0) > 0 ? 'success' : 'unknown'
              }
            });
          }
        } else {
          // No data at all - show failed (red)
          setPastSeasonStatus('failed');
          setPast365Status('failed');
          setPastSeasonMatchCount(0);
          setPast365MatchCount(0);
          
          // No data yet, check task status if exists
          if (storedTaskId) {
            setFetchTaskId(storedTaskId);
            
            // Check task status
            const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${BACKEND_URL}/v1/player/fetch-status/${storedTaskId}`);
            
            if (response.ok) {
              const taskStatus = await response.json();
              
              if (taskStatus.status === 'completed') {
                // Task completed, check data again
                const recheckResponse = await fetch(`/api/player/${gameName}/${tagLine}/data-status`);
                if (recheckResponse.ok) {
                  const recheckData = await recheckResponse.json();
                  if (recheckData.has_data && recheckData.patches) {
                    const hasPastSeason = recheckData.patches.some((p: any) => {
                      return (p.earliest_match_date && isMatchDateInPastSeason(p.earliest_match_date)) ||
                             (p.latest_match_date && isMatchDateInPastSeason(p.latest_match_date));
                    }) || (recheckData.earliest_match_date && isMatchDateInPastSeason(recheckData.earliest_match_date)) ||
                          (recheckData.latest_match_date && isMatchDateInPastSeason(recheckData.latest_match_date));
                    
                    const hasPast365 = recheckData.patches && recheckData.patches.some((p: any) => {
                      return (p.earliest_match_date && isMatchDateWithinPast365Days(p.earliest_match_date)) ||
                             (p.latest_match_date && isMatchDateWithinPast365Days(p.latest_match_date));
                    }) || (recheckData.latest_match_date && isMatchDateWithinPast365Days(recheckData.latest_match_date));
                    
                    setPastSeasonStatus(hasPastSeason ? 'success' : 'unknown');
                    setPast365Status(hasPast365 ? 'success' : 'unknown');
                  } else {
                    // Task completed but no data - might be failed
                    setPastSeasonStatus('unknown');
                    setPast365Status('unknown');
                  }
                } else {
                  setPastSeasonStatus('unknown');
                  setPast365Status('unknown');
                }
                localStorage.removeItem(storageKey);
              } else if (taskStatus.status === 'failed') {
                setPastSeasonStatus('failed');
                setPast365Status('failed');
              } else {
                setPastSeasonStatus('pending');
                setPast365Status('pending');
              }
            } else {
              // Task not found, check if data exists anyway
              const dataStatusResponse2 = await fetch(`/api/player/${gameName}/${tagLine}/data-status`);
              if (dataStatusResponse2.ok) {
                const dataStatus2 = await dataStatusResponse2.json();
                if (dataStatus2.has_data && dataStatus2.patches) {
                  const hasPastSeason = dataStatus2.patches.some((p: any) => {
                    return (p.earliest_match_date && isMatchDateInPastSeason(p.earliest_match_date)) ||
                           (p.latest_match_date && isMatchDateInPastSeason(p.latest_match_date));
                  }) || (dataStatus2.earliest_match_date && isMatchDateInPastSeason(dataStatus2.earliest_match_date)) ||
                        (dataStatus2.latest_match_date && isMatchDateInPastSeason(dataStatus2.latest_match_date));
                  
                  const hasPast365 = dataStatus2.patches && dataStatus2.patches.some((p: any) => {
                    return (p.earliest_match_date && isMatchDateWithinPast365Days(p.earliest_match_date)) ||
                           (p.latest_match_date && isMatchDateWithinPast365Days(p.latest_match_date));
                  }) || (dataStatus2.latest_match_date && isMatchDateWithinPast365Days(dataStatus2.latest_match_date));
                  
                  setPastSeasonStatus(hasPastSeason ? 'success' : 'unknown');
                  setPast365Status(hasPast365 ? 'success' : 'unknown');
                } else {
                  setPastSeasonStatus('unknown');
                  setPast365Status('unknown');
                }
              } else {
                setPastSeasonStatus('unknown');
                setPast365Status('unknown');
              }
            }
          } else {
            // No task_id and no data - check if data exists anyway
            setPastSeasonStatus('unknown');
            setPast365Status('unknown');
          }
        }
      } else {
        setPastSeasonStatus('unknown');
        setPast365Status('unknown');
      }
    } catch (err) {
      console.error('Error checking fetch status:', err);
      setPastSeasonStatus('unknown');
      setPast365Status('unknown');
    }
  };

  // Modal states for parameter selection
  const [championModalOpen, setChampionModalOpen] = useState(false);
  const [friendModalOpen, setFriendModalOpen] = useState(false);
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [rankModalOpen, setRankModalOpen] = useState(false);
  const [matchModalOpen, setMatchModalOpen] = useState(false);
  const [matchesData, setMatchesData] = useState<any[]>([]);
  const [currentMatchAgent, setCurrentMatchAgent] = useState<string>('match-analysis'); // Track which agent is using match selector
  const [friendGameName, setFriendGameName] = useState('');
  const [friendTagLine, setFriendTagLine] = useState('');

  // Initialize all 9 agents (3x3 grid)
  const [agents, setAgents] = useState<AgentState[]>([
    // Row 1
    {
      id: 'annual-summary',
      name: 'Annual Summary',
      description: 'Year-in-review performance highlights',
      icon: FileText,
      endpoint: '/v1/agents/annual-summary',
      status: 'idle',
      rankTypeOptions: [
        { id: 'total', label: 'Total', value: null },
        { id: 'solo-duo', label: 'Rank Solo/Duo', value: 420 },
        { id: 'flex', label: 'Rank Flex', value: 440 },
        { id: 'normal', label: 'Normal', value: 400 }
      ],
      selectedRankType: null, // Default to Total
      timeRangeOptions: [
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365'
        }
      ],
      selectedTimeRange: 'past-365' // Default to past 365 days
    },
    {
      id: 'performance-insights',
      name: 'Performance Insights',
      description: 'Strengths, weaknesses & growth',
      icon: BarChart3,
      endpoint: '/v1/agents/weakness-analysis', // Merges weakness + detailed + progress
      status: 'idle',
      rankTypeOptions: [
        { id: 'total', label: 'Total', value: null },
        { id: 'solo-duo', label: 'Rank Solo/Duo', value: 420 },
        { id: 'flex', label: 'Rank Flex', value: 440 },
        { id: 'normal', label: 'Normal', value: 400 }
      ],
      selectedRankType: null, // Default to Total
      timeRangeOptions: [
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365'
        }
      ],
      selectedTimeRange: 'past-365' // Default to past 365 days
    },
    {
      id: 'comparison-hub',
      name: 'Comparison Hub',
      description: 'Compare with friends or peers',
      icon: Users,
      endpoint: '/v1/agents/friend-comparison', // Will handle both friend and peer
      status: 'idle',
      timeRangeOptions: [
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365'
        }
      ],
      selectedTimeRange: 'past-365', // Default to past 365 days
      rankTypeOptions: [
        { id: 'total', label: 'Total', value: null },
        { id: 'solo-duo', label: 'Rank Solo/Duo', value: 420 },
        { id: 'flex', label: 'Rank Flex', value: 440 },
        { id: 'normal', label: 'Normal', value: 400 }
      ],
      selectedRankType: null, // Default to Total
      subOptions: [
        {
          id: 'friend-comparison',
          label: 'Friend',
          description: 'Compare with a specific player',
          icon: UserPlus
        },
        {
          id: 'rank-comparison',
          label: 'Leaderboard',
          description: 'Compare with rank tier',
          icon: TrendingUp
        }
      ]
    },

    // Row 2
    {
      id: 'match-analysis',
      name: 'Match Analysis',
      description: 'Deep dive into recent match timeline',
      icon: Clock,
      endpoint: '/v1/agents/timeline-deep-dive', // Merges timeline + postgame
      status: 'idle'
    },
    {
      id: 'version-trends',
      name: 'Version Trends',
      description: 'Cross-patch performance analysis',
      icon: Zap,
      endpoint: '/v1/agents/version-trends', // Merges multi-version + version-comparison
      status: 'idle',
      rankTypeOptions: [
        { id: 'total', label: 'Total', value: null },
        { id: 'solo-duo', label: 'Rank Solo/Duo', value: 420 },
        { id: 'flex', label: 'Rank Flex', value: 440 },
        { id: 'normal', label: 'Normal', value: 400 }
      ],
      selectedRankType: null, // Default to Total
      timeRangeOptions: [
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365'
        }
      ],
      selectedTimeRange: 'past-365' // Default to past 365 days
    },
    {
      id: 'champion-recommendation',
      name: 'Champion Recommendation',
      description: 'Best champions for your playstyle',
      icon: Lightbulb,
      endpoint: '/v1/agents/champion-recommendation',
      status: 'idle',
      rankTypeOptions: [
        { id: 'total', label: 'Total', value: null },
        { id: 'solo-duo', label: 'Rank Solo/Duo', value: 420 },
        { id: 'flex', label: 'Rank Flex', value: 440 },
        { id: 'normal', label: 'Normal', value: 400 }
      ],
      selectedRankType: null, // Default to Total
      timeRangeOptions: [
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365'
        }
      ],
      selectedTimeRange: 'past-365' // Default to past 365 days
    },

    // Row 3
    {
      id: 'role-specialization',
      name: 'Role Specialization',
      description: 'Role-specific performance insights',
      icon: Target,
      endpoint: '/v1/agents/role-specialization',
      status: 'idle',
      rankTypeOptions: [
        { id: 'total', label: 'Total', value: null },
        { id: 'solo-duo', label: 'Rank Solo/Duo', value: 420 },
        { id: 'flex', label: 'Rank Flex', value: 440 },
        { id: 'normal', label: 'Normal', value: 400 }
      ],
      selectedRankType: null, // Default to Total
      timeRangeOptions: [
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365'
        }
      ],
      selectedTimeRange: 'past-365' // Default to past 365 days
    },
    {
      id: 'champion-mastery',
      name: 'Champion Mastery',
      description: 'Deep dive into champion performance',
      icon: Trophy,
      endpoint: '/v1/agents/champion-mastery',
      status: 'idle',
      timeRangeOptions: [
        {
          id: 'past-365-days',
          label: 'Past 365 Days',
          value: 'past-365'
        }
      ],
      selectedTimeRange: 'past-365', // Default to past 365 days
      // No rankTypeOptions - uses all game modes by default
    },
    {
      id: 'build-simulator',
      name: 'Build Simulator',
      description: 'Optimize recent builds and itemization',
      icon: Boxes,
      endpoint: '/v1/agents/build-simulator',
      status: 'idle',
      // No rankTypeOptions - uses all game modes by default
      // No timeRangeOptions - uses recent games by default
    }
  ]);

  const updateAgentStatus = (id: string, updates: Partial<AgentState>) => {
    setAgents((prev) =>
      prev.map((agent) => (agent.id === id ? { ...agent, ...updates } : agent))
    );
  };

  // Helper function to generate report key from time range and queue_id
  const getReportKey = (agent: AgentState): string => {
    const timeRange = (agent.timeRangeOptions && agent.timeRangeOptions.length > 0)
      ? (agent.selectedTimeRange || 'default')
      : 'default';
    const queueId = agent.selectedRankType !== null && agent.selectedRankType !== undefined
      ? agent.selectedRankType.toString()
      : 'total';
    return `${timeRange}_${queueId}`;
  };

  const handleRankTypeChange = (agentId: string, rankType: number | null) => {
    setAgents((prev) =>
      prev.map((agent) => {
        if (agent.id === agentId) {
          const previousRankType = agent.selectedRankType;
          
          // If switching to a different rank type, check for existing report
          if (previousRankType !== rankType) {
            const reportsByTimeRange = agent.reportsByTimeRange || {};
            const updatedAgent = { ...agent, selectedRankType: rankType };
            const reportKey = getReportKey(updatedAgent);
            const existingReport = reportsByTimeRange[reportKey];
            
            if (existingReport) {
              // Load existing report for this filter combination
              const updatedAgentWithReport = {
                ...updatedAgent,
                status: existingReport.status,
                detailedReport: existingReport.detailedReport,
                analysisData: existingReport.analysisData,
                error: undefined
              };
              
              // Update selectedAgent if modal is open for this agent
              setSelectedAgent((currentSelected) => {
                if (currentSelected && currentSelected.id === agentId) {
                  return updatedAgentWithReport;
                }
                return currentSelected;
              });
              
              return updatedAgentWithReport;
            } else {
              // Reset to idle if no report exists for this filter combination
              const updatedAgentIdle = {
                ...updatedAgent,
                status: 'idle',
                detailedReport: undefined,
                analysisData: undefined,
                error: undefined
              };
              
              // Close modal if it's open for this agent
              setSelectedAgent((currentSelected) => {
                if (currentSelected && currentSelected.id === agentId) {
                  return null;
                }
                return currentSelected;
              });
              
              return updatedAgentIdle;
            }
          }
          
          return { ...agent, selectedRankType: rankType };
        }
        return agent;
      })
    );
  };

  const handleTimeRangeChange = (agentId: string, timeRange: string) => {
    setAgents((prev) =>
      prev.map((agent) => {
        if (agent.id === agentId) {
          const previousTimeRange = agent.selectedTimeRange;
          
          // If switching to a different time range, check for existing report
          if (previousTimeRange && previousTimeRange !== timeRange) {
            const reportsByTimeRange = agent.reportsByTimeRange || {};
            const updatedAgent = { ...agent, selectedTimeRange: timeRange };
            const reportKey = getReportKey(updatedAgent);
            const existingReport = reportsByTimeRange[reportKey];
            
            if (existingReport) {
              // Load existing report for this filter combination
              const updatedAgentWithReport = {
                ...updatedAgent,
                status: existingReport.status,
                detailedReport: existingReport.detailedReport,
                analysisData: existingReport.analysisData,
                error: undefined
              };
              
              // Update selectedAgent if modal is open for this agent
              setSelectedAgent((currentSelected) => {
                if (currentSelected && currentSelected.id === agentId) {
                  return updatedAgentWithReport;
                }
                return currentSelected;
              });
              
              return updatedAgentWithReport;
            } else {
              // Reset to idle if no report exists for this filter combination
              const updatedAgentIdle = {
                ...updatedAgent,
                status: 'idle',
                detailedReport: undefined,
                analysisData: undefined,
                error: undefined
              };
              
              // Close modal if it's open for this agent
              setSelectedAgent((currentSelected) => {
                if (currentSelected && currentSelected.id === agentId) {
                  return null;
                }
                return currentSelected;
              });
              
              return updatedAgentIdle;
            }
          }
          
          return { ...agent, selectedTimeRange: timeRange };
        }
        return agent;
      })
    );
  };

  const handleGenerate = async (agent: AgentState) => {
    console.log(`🔵 handleGenerate called for agent: ${agent.id}`);

    // If already generating, cancel it
    if (agent.status === 'generating') {
      console.log(`🛑 Cancelling generation for agent: ${agent.id}`);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      updateAgentStatus(agent.id, {
        status: 'idle',
        error: undefined
      });
      return;
    }

    // Check if puuid is available
    if (!puuid) {
      console.error('❌ PUUID is not available');
      updateAgentStatus(agent.id, {
        status: 'error',
        error: 'Player data not available'
      });
      return;
    }

    // Check if report exists for current filter combination (time_range + queue_id)
    // Champion Mastery and Build Simulator use all game modes and recent games, so use 'default' as key
    // Role Specialization reports are stored with role in the key, so skip check here (will be checked in handleRoleSelect)
    const reportsByTimeRange = agent.reportsByTimeRange || {};
    
    // Skip report check for Role Specialization since it requires role selection first
    if (agent.id !== 'role-specialization' && agent.id !== 'champion-mastery' && agent.id !== 'build-simulator') {
      const reportKey = getReportKey(agent);
      const existingReport = reportsByTimeRange[reportKey];
    
      // If already generated for current filter combination, just show the report
    if (existingReport && existingReport.status === 'ready' && existingReport.detailedReport) {
      setSelectedAgent({
        ...agent,
        detailedReport: existingReport.detailedReport,
        analysisData: existingReport.analysisData
      });
      return;
      }
    } else if (agent.id === 'champion-mastery' || agent.id === 'build-simulator') {
      const reportKey = agent.id === 'champion-mastery' ? (agent.selectedTimeRange || 'default') : 'default';
      const existingReport = reportsByTimeRange[reportKey];
      
      // If already generated for current filter combination, just show the report
      if (existingReport && existingReport.status === 'ready' && existingReport.detailedReport) {
        setSelectedAgent({
          ...agent,
          detailedReport: existingReport.detailedReport,
          analysisData: existingReport.analysisData
        });
        return;
      }
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
    // comparison-hub now uses sub-options, so no direct modal opening here
    if (agent.id === 'role-specialization') {
      setRoleModalOpen(true);
      return;
    }
    if (agent.id === 'match-analysis') {
      setCurrentMatchAgent(agent.id);

      // Show loading state
      updateAgentStatus(agent.id, { status: 'generating', error: undefined });

      try {
        await fetchMatches();
        // Reset status and open modal
        updateAgentStatus(agent.id, { status: 'idle', error: undefined });
        setMatchModalOpen(true);
      } catch (error) {
        console.error('❌ Failed to fetch matches:', error);
        updateAgentStatus(agent.id, {
          status: 'idle',
          error: error instanceof Error ? error.message : 'Failed to load matches'
        });
      }
      return;
    }

    console.log(`🟢 Starting analysis generation for ${agent.id}`);
    updateAgentStatus(agent.id, { status: 'generating', error: undefined });

    try {
      // Create new AbortController for this stream
      abortControllerRef.current = new AbortController();
      
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agent.id}`;
      const body: any = {
        puuid,
        region,
        recent_count: 20,
        model: 'sonnet' // Use Sonnet for detailed analysis
      };

      // Add time range parameter if agent has time range options
      // Get the latest agent state to ensure we have the correct selectedTimeRange
      // Use functional update to get the most recent state
      let latestAgent: AgentState | undefined;
      setAgents((prev) => {
        latestAgent = prev.find((a) => a.id === agent.id);
        return prev; // Don't modify, just read
      });
      
      // Only add time_range if agent has timeRangeOptions (Build Simulator doesn't have it)
      if (latestAgent?.timeRangeOptions && latestAgent.timeRangeOptions.length > 0 && latestAgent?.selectedTimeRange) {
        body.time_range = latestAgent.selectedTimeRange;
        console.log(`[${agent.id}] Using time_range: ${latestAgent.selectedTimeRange}`);
      } else if (latestAgent?.timeRangeOptions && latestAgent.timeRangeOptions.length > 0) {
        // If agent has timeRangeOptions but no selectedTimeRange, use the first option as default
        body.time_range = latestAgent.timeRangeOptions[0].value;
        console.log(`[${agent.id}] No time_range selected, using default: ${latestAgent.timeRangeOptions[0].value}`);
      } else {
        console.log(`[${agent.id}] No time_range (agent uses recent games by default)`);
      }

      // Champion Mastery and Build Simulator use all game modes, so don't add queue_id parameter
      // For other agents, add queue_id if they have rankTypeOptions and selectedRankType is not null
      if (agent.id !== 'champion-mastery' && agent.id !== 'build-simulator' && latestAgent?.selectedRankType !== undefined && latestAgent.selectedRankType !== null) {
        body.queue_id = latestAgent.selectedRankType;
        const queueNames: Record<number, string> = { 420: 'Solo/Duo', 440: 'Flex', 400: 'Normal' };
        console.log(`[${agent.id}] Using queue_id: ${latestAgent.selectedRankType} (${queueNames[latestAgent.selectedRankType] || 'Unknown'})`);
      } else if (agent.id !== 'champion-mastery' && agent.id !== 'build-simulator' && latestAgent?.selectedRankType === null) {
        console.log(`[${agent.id}] Using Total (all queue types)`);
      } else if (agent.id === 'champion-mastery' || agent.id === 'build-simulator') {
        console.log(`[${agent.id}] Using all game modes (uses recent games by default)`);
      }

      const result = await fetchAgentStream(url, body, abortControllerRef.current);
      const detailedReport = result.detailed || '';
      const analysisData = result.analysis; // Extract analysis data for widgets
      
      // Get the latest agent state to ensure we have the correct filters
      let finalAgent: AgentState | undefined;
      setAgents((prev) => {
        finalAgent = prev.find((a) => a.id === agent.id);
        return prev; // Don't modify, just read
      });
      
      // Champion Mastery and Build Simulator use all game modes and recent games, so use 'default' as key
      // Other agents use combined key (time_range + queue_id)
      const reportKey = (finalAgent && (finalAgent.id === 'champion-mastery' || finalAgent.id === 'build-simulator'))
        ? 'default'
        : (finalAgent ? getReportKey(finalAgent) : getReportKey(agent));
      
      console.log(`[${agent.id}] Storing report for filter combination: ${reportKey}`);

      // Store report by filter combination (time_range + queue_id) - use functional update to ensure we have the latest reportsByTimeRange
      setAgents((prev) => {
        const currentAgent = prev.find((a) => a.id === agent.id);
        const currentReportsByTimeRange = currentAgent?.reportsByTimeRange || {};
        currentReportsByTimeRange[reportKey] = {
          detailedReport,
          analysisData,
          status: 'ready'
        };

        // Update agent status
        updateAgentStatus(agent.id, {
          status: 'ready',
          detailedReport: detailedReport,
          analysisData: analysisData,
          reportsByTimeRange: currentReportsByTimeRange
        });

        // Auto-open modal with report and analysis data
        const updatedAgent = prev.find((a) => a.id === agent.id);
        if (updatedAgent) {
          setSelectedAgent({ ...updatedAgent, detailedReport, analysisData });
        }

        return prev;
      });
    } catch (error) {
      // Don't set error if aborted
      if (abortControllerRef.current?.signal.aborted) {
        console.log(`[${agent.id}] Stream aborted`);
        return;
      }
      console.error(`❌ Error generating analysis for ${agent.id}:`, error);
      updateAgentStatus(agent.id, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Handler for champion selection
  const handleChampionSelect = async (championId: number, championName: string) => {
    if (!puuid) {
      console.error('❌ PUUID is not available');
      return;
    }

    const agentId = 'champion-mastery';
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      // Create new AbortController for this stream
      abortControllerRef.current = new AbortController();
      
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agentId}`;
      const body: any = {
        puuid,
        region,
        recent_count: 20,
        model: 'sonnet',
        champion_id: championId
      };

      // Add time range parameter if agent has time range options
      // Get the latest agent state to ensure we have the correct selectedTimeRange
      // Use functional update to get the most recent state
      let latestAgent: AgentState | undefined;
      setAgents((prev) => {
        latestAgent = prev.find((a) => a.id === agentId);
        return prev; // Don't modify, just read
      });
      
      if (latestAgent?.selectedTimeRange) {
        body.time_range = latestAgent.selectedTimeRange;
        console.log(`[${agentId}] Using time_range: ${latestAgent.selectedTimeRange}`);
      } else {
        console.log(`[${agentId}] No time_range selected`);
      }

      // Champion Mastery uses all game modes, so don't add queue_id parameter
      // For other agents, add queue_id if they have rankTypeOptions
      if (agentId !== 'champion-mastery' && latestAgent?.selectedRankType !== undefined && latestAgent.selectedRankType !== null) {
        body.queue_id = latestAgent.selectedRankType;
        const queueNames: Record<number, string> = { 420: 'Solo/Duo', 440: 'Flex', 400: 'Normal' };
        console.log(`[${agentId}] Using queue_id: ${latestAgent.selectedRankType} (${queueNames[latestAgent.selectedRankType] || 'Unknown'})`);
      } else if (agentId !== 'champion-mastery' && latestAgent?.selectedRankType === null) {
        console.log(`[${agentId}] Using Total (all queue types)`);
      } else if (agentId === 'champion-mastery') {
        console.log(`[${agentId}] Using all game modes (Champion Mastery)`);
      }

      const result = await fetchAgentStream(url, body, abortControllerRef.current);
      const detailedReport = result.detailed || '';
      const analysisData = result.analysis; // Extract analysis data for widgets
      
      // Get the latest agent state to ensure we have the correct filters
      let finalAgent: AgentState | undefined;
      setAgents((prev) => {
        finalAgent = prev.find((a) => a.id === agentId);
        return prev; // Don't modify, just read
      });
      
      // Champion Mastery uses all game modes, so use time_range only as key
      // Other agents use combined key (time_range + queue_id)
      const reportKey = finalAgent && finalAgent.id === 'champion-mastery'
        ? (finalAgent.selectedTimeRange || 'default')
        : (finalAgent ? getReportKey(finalAgent) : 'default');
      
      console.log(`[${agentId}] Storing report for filter combination: ${reportKey}`);

      // Store report by filter combination (time_range + queue_id) - use functional update to ensure we have the latest reportsByTimeRange
      setAgents((prev) => {
        const currentAgent = prev.find((a) => a.id === agentId);
        const currentReportsByTimeRange = currentAgent?.reportsByTimeRange || {};
        currentReportsByTimeRange[reportKey] = {
          detailedReport,
          analysisData,
          status: 'ready'
        };

        // Update agent status
        updateAgentStatus(agentId, {
          status: 'ready',
          detailedReport: detailedReport,
          analysisData: analysisData,  // Store analysis data
          reportsByTimeRange: currentReportsByTimeRange
        });

        // Auto-open modal
        const updatedAgent = prev.find((a) => a.id === agentId);
        if (updatedAgent) {
          setSelectedAgent({ ...updatedAgent, detailedReport, analysisData });
        }

        return prev;
      });
    } catch (error) {
      // Don't set error if aborted
      if (abortControllerRef.current?.signal.aborted) {
        console.log(`[${agentId}] Stream aborted`);
        return;
      }
      console.error('Champion mastery error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Handler for friend comparison or rank comparison (now part of comparison-hub)
  const handleFriendSelect = async (friendGameName: string, friendTagLine: string, rank?: string) => {
    if (!puuid) {
      console.error('❌ PUUID is not available');
      return;
    }

    const agentId = 'comparison-hub';
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      // Create new AbortController for this stream
      abortControllerRef.current = new AbortController();
      
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

      // Add time range parameter if agent has time range options
      // Get the latest agent state to ensure we have the correct selectedTimeRange
      // Use functional update to get the most recent state
      let latestAgent: AgentState | undefined;
      setAgents((prev) => {
        latestAgent = prev.find((a) => a.id === agentId);
        return prev; // Don't modify, just read
      });
      
      if (latestAgent?.selectedTimeRange) {
        body.time_range = latestAgent.selectedTimeRange;
        console.log(`[${agentId}] Using time_range: ${latestAgent.selectedTimeRange}`);
      } else {
        console.log(`[${agentId}] No time_range selected`);
      }

      // Add queue_id parameter if agent has rankTypeOptions and selectedRankType is not null
      if (latestAgent?.selectedRankType !== undefined && latestAgent.selectedRankType !== null) {
        body.queue_id = latestAgent.selectedRankType;
        const queueNames: Record<number, string> = { 420: 'Solo/Duo', 440: 'Flex', 400: 'Normal' };
        console.log(`[${agentId}] Using queue_id: ${latestAgent.selectedRankType} (${queueNames[latestAgent.selectedRankType] || 'Unknown'})`);
      } else if (latestAgent?.selectedRankType === null) {
        console.log(`[${agentId}] Using Total (all queue types)`);
      }

      // Add either friend info or rank parameter
      if (rank) {
        body.rank = rank;
      } else {
        body.friend_game_name = friendGameName;
        body.friend_tag_line = friendTagLine;
      }

      const result = await fetchAgentStream(url, body, abortControllerRef.current);
      const detailedReport = result.detailed || '';
      const analysisData = result.analysis; // Extract analysis data for widgets

      updateAgentStatus(agentId, {
        status: 'ready',
        detailedReport: detailedReport,
        analysisData: analysisData  // Store analysis data
      });

      // Auto-open modal
      const agent = agents.find((a) => a.id === agentId);
      if (agent) {
        setSelectedAgent({ ...agent, detailedReport, analysisData });
      }
    } catch (error) {
      // Don't set error if aborted
      if (abortControllerRef.current?.signal.aborted) {
        console.log(`[${agentId}] Stream aborted`);
        return;
      }
      console.error('Comparison hub error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Handler for role selection
  const handleRoleSelect = async (role: string) => {
    if (!puuid) {
      console.error('❌ PUUID is not available');
      return;
    }

    const agentId = 'role-specialization';
    
    // Get the latest agent state to check for existing report
    let latestAgent: AgentState | undefined;
    setAgents((prev) => {
      latestAgent = prev.find((a) => a.id === agentId);
      return prev; // Don't modify, just read
    });
    
    // Check if report exists for current filter combination (role + time_range + queue_id)
    if (latestAgent) {
      const timeRange = latestAgent.selectedTimeRange || 'default';
      const queueId = latestAgent.selectedRankType !== null && latestAgent.selectedRankType !== undefined
        ? latestAgent.selectedRankType.toString()
        : 'total';
      const reportKey = `role_${role}_${timeRange}_${queueId}`;
      const reportsByTimeRange = latestAgent.reportsByTimeRange || {};
      const existingReport = reportsByTimeRange[reportKey];
      
      // If already generated for current filter combination, just show the report
      if (existingReport && existingReport.status === 'ready' && existingReport.detailedReport) {
        setSelectedAgent({
          ...latestAgent,
          detailedReport: existingReport.detailedReport,
          analysisData: existingReport.analysisData
        });
        return;
      }
    }
    
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      // Create new AbortController for this stream
      abortControllerRef.current = new AbortController();
      
      const { fetchAgentStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agentId}`;
      const body: any = {
        puuid,
        region,
        recent_count: 20,
        model: 'sonnet',
        role: role
      };

      // Add time range parameter if agent has time range options
      // Get the latest agent state to ensure we have the correct selectedTimeRange
      // Use functional update to get the most recent state
      let latestAgent: AgentState | undefined;
      setAgents((prev) => {
        latestAgent = prev.find((a) => a.id === agentId);
        return prev; // Don't modify, just read
      });
      
      if (latestAgent?.selectedTimeRange) {
        body.time_range = latestAgent.selectedTimeRange;
        console.log(`[${agentId}] Using time_range: ${latestAgent.selectedTimeRange}`);
      } else {
        console.log(`[${agentId}] No time_range selected`);
      }

      // Add queue_id parameter if selected
      if (latestAgent?.selectedRankType !== undefined && latestAgent.selectedRankType !== null) {
        body.queue_id = latestAgent.selectedRankType;
        const queueNames: Record<number, string> = { 420: 'Solo/Duo', 440: 'Flex', 400: 'Normal' };
        console.log(`[${agentId}] Using queue_id: ${latestAgent.selectedRankType} (${queueNames[latestAgent.selectedRankType] || 'Unknown'})`);
      } else if (latestAgent?.selectedRankType === null) {
        console.log(`[${agentId}] Using Total (all queue types)`);
      }

      const result = await fetchAgentStream(url, body, abortControllerRef.current);
      const detailedReport = result.detailed || '';
      const analysisData = result.analysis; // Extract analysis data for widgets
      
      // Get the latest agent state to ensure we have the correct filters
      let finalAgent: AgentState | undefined;
      setAgents((prev) => {
        finalAgent = prev.find((a) => a.id === agentId);
        return prev; // Don't modify, just read
      });
      
      // Role Specialization report key includes role, time_range, and queue_id
      const timeRange = finalAgent?.selectedTimeRange || 'default';
      const queueId = finalAgent?.selectedRankType !== null && finalAgent?.selectedRankType !== undefined
        ? finalAgent.selectedRankType.toString()
        : 'total';
      const reportKey = `role_${role}_${timeRange}_${queueId}`;
      
      console.log(`[${agentId}] Storing report for filter combination: ${reportKey}`);

      // Store report by filter combination (role + time_range + queue_id)
      setAgents((prev) => {
        const currentAgent = prev.find((a) => a.id === agentId);
        const currentReportsByTimeRange = currentAgent?.reportsByTimeRange || {};
        currentReportsByTimeRange[reportKey] = {
          detailedReport,
          analysisData,
          status: 'ready'
        };

        // Update agent status
        updateAgentStatus(agentId, {
          status: 'ready',
          detailedReport: detailedReport,
          analysisData: analysisData,  // Store analysis data
          reportsByTimeRange: currentReportsByTimeRange
        });

        // Auto-open modal
        const updatedAgent = prev.find((a) => a.id === agentId);
        if (updatedAgent) {
          setSelectedAgent({ ...updatedAgent, detailedReport, analysisData });
        }

        return prev;
      });
    } catch (error) {
      // Don't set error if aborted
      if (abortControllerRef.current?.signal.aborted) {
        console.log(`[${agentId}] Stream aborted`);
        return;
      }
      console.error('Role specialization error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Handler for sub-option clicks (for comparison hub)
  const handleSubOptionClick = (agentId: string, subOptionId: string) => {
    console.log(`Sub-option clicked: ${subOptionId} for agent: ${agentId}`);
    
    if (agentId === 'comparison-hub') {
      if (subOptionId === 'friend-comparison') {
        setFriendModalOpen(true);
      } else if (subOptionId === 'rank-comparison') {
        setRankModalOpen(true);
      }
    }
  };

  // Fetch matches for timeline analysis
  const fetchMatches = async () => {
    console.log('🔍 fetchMatches called for', gameName, tagLine);

    // Directly fetch matches without waiting for data preparation
    // The backend will return matches if timeline files exist
    try {
      const response = await fetch(`/api/player/${gameName}/${tagLine}/matches?limit=20`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        console.log(`✅ Fetched ${data.matches.length} matches with timelines`);
        setMatchesData(data.matches);

        if (data.matches.length === 0) {
          throw new Error('Timeline data is being prepared in the background. Please wait a few minutes and try again, or use other analysis features first.');
        }
      } else {
        throw new Error(data.error || 'Failed to fetch matches');
      }
    } catch (error) {
      console.error('❌ Error fetching matches:', error);
      setMatchesData([]);
      throw error; // Re-throw so the calling code can handle it
    }
  };

  // Handler for match selection
  const handleMatchSelect = async (matchId: string) => {
    if (!puuid) {
      console.error('❌ PUUID is not available');
      return;
    }

    const agentId = currentMatchAgent;  // Use the tracked agent ID
    updateAgentStatus(agentId, { status: 'generating', error: undefined });

    try {
      // Create new AbortController for this stream
      abortControllerRef.current = new AbortController();
      
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

      const result = await fetchAgentStream(url, body, abortControllerRef.current);

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
      // Don't set error if aborted
      if (abortControllerRef.current?.signal.aborted) {
        console.log(`[${agentId}] Stream aborted`);
        return;
      }
      console.error('Timeline deep dive error:', error);
      updateAgentStatus(agentId, {
        status: 'error',
        error: error instanceof Error ? error.message : 'Analysis failed'
      });
    }
  };

  // Extract data from playerData for modals
  const playerChampions = playerData?.analysis?.best_champions?.map((champ: any) => ({
    champion_id: parseInt(champ.champ_id || '0'),
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
      <div className="mb-6 text-center">
        <ShinyText text="AI Analysis Hub" speed={4} className="text-3xl font-bold mb-2" />
        {/* Data Fetch Status Indicator */}
        <div className="flex items-center justify-center gap-2 mt-2 flex-wrap">
          <div 
            ref={dataIndicatorRef}
            className="flex items-center gap-1 px-2 py-1 rounded cursor-help relative" 
            style={{ backgroundColor: combinedStatus === 'success' ? 'rgba(16, 185, 129, 0.2)' : combinedStatus === 'failed' ? 'rgba(239, 68, 68, 0.2)' : combinedStatus === 'pending' ? 'rgba(251, 191, 36, 0.2)' : 'rgba(107, 114, 128, 0.2)' }} 
            onMouseEnter={(e) => {
              if (dataIndicatorRef.current) {
                const rect = dataIndicatorRef.current.getBoundingClientRect();
                setTooltipPosition({
                  top: rect.bottom + 8,
                  left: rect.left + rect.width / 2
                });
              }
              setShowDataTooltip(true);
            }}
            onMouseLeave={() => setShowDataTooltip(false)}
          >
            {combinedStatus === 'success' && (
              <CheckCircle2 className="w-4 h-4" style={{ color: '#10B981' }} />
            )}
            {combinedStatus === 'failed' && (
              <XCircle className="w-4 h-4" style={{ color: '#EF4444' }} />
            )}
            {combinedStatus === 'pending' && (
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: '#FBBF24' }} />
            )}
            {combinedStatus === 'unknown' && (
              <XCircle className="w-4 h-4" style={{ color: '#6B7280' }} />
            )}
            <span className="text-xs" style={{ color: combinedStatus === 'success' ? '#10B981' : combinedStatus === 'failed' ? '#EF4444' : combinedStatus === 'pending' ? '#FBBF24' : '#6B7280' }}>
              Data Status
            </span>
            
            {/* Custom Tooltip */}
            <AnimatePresence>
              {showDataTooltip && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9, y: -5 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9, y: -5 }}
                  transition={{ duration: 0.15 }}
                  className="fixed z-50 pointer-events-none"
                  style={{
                    top: `${tooltipPosition.top}px`,
                    left: `${tooltipPosition.left}px`,
                    transform: 'translate(-50%, 0)',
                    marginTop: '0'
                  }}
                >
                  <div
                    className="px-3 py-2 rounded-lg shadow-lg border text-xs"
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.9)',
                      borderColor: 'rgba(255, 255, 255, 0.2)',
                      color: '#F5F5F7'
                    }}
                  >
                    {combinedStatus === 'success' ? (
                      <>
                        <div>Data available</div>
                        <div style={{ color: '#10B981', marginTop: '4px' }}>
                          <div>Past Season: {pastSeasonMatchCount} matches</div>
                          <div>Past 365 Days: {past365MatchCount} matches</div>
                          <div style={{ marginTop: '4px', borderTop: '1px solid rgba(255, 255, 255, 0.2)', paddingTop: '4px' }}>
                            Total: {totalMatches} matches
                          </div>
                        </div>
                      </>
                    ) : combinedStatus === 'failed' ? (
                      <>
                        <div>Data fetch failed</div>
                        <div style={{ marginTop: '4px', fontSize: '0.75rem', color: '#8E8E93' }}>
                          Past Season: {pastSeasonMatchCount} matches<br/>
                          Past 365 Days: {past365MatchCount} matches
                        </div>
                      </>
                    ) : combinedStatus === 'pending' ? (
                      <>
                        <div>Data fetch in progress</div>
                        <div style={{ marginTop: '4px', fontSize: '0.75rem', color: '#8E8E93' }}>
                          Past Season: {pastSeasonMatchCount} matches<br/>
                          Past 365 Days: {past365MatchCount} matches
                        </div>
                      </>
                    ) : (
                      <>
                        <div>Data not available</div>
                        <div style={{ marginTop: '4px', fontSize: '0.75rem', color: '#8E8E93' }}>
                          Past Season: {pastSeasonMatchCount} matches<br/>
                          Past 365 Days: {past365MatchCount} matches
                        </div>
                      </>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          {/* Rank Type Indicators */}
          {['solo_duo', 'flex', 'normal'].map((rankType) => {
            const rankData = rankTypeStatus[rankType as keyof typeof rankTypeStatus];
            const rankLabel = rankType === 'solo_duo' ? 'Rank Solo/Duo' : rankType === 'flex' ? 'Rank Flex' : 'Normal';
            const status = rankData.status;
            
            return (
          <div 
                key={rankType}
                ref={(el) => { rankIndicatorRefs.current[rankType] = el; }}
            className="flex items-center gap-1 px-2 py-1 rounded cursor-help relative" 
                style={{
                  backgroundColor: status === 'success' ? 'rgba(16, 185, 129, 0.2)' : status === 'failed' ? 'rgba(239, 68, 68, 0.2)' : status === 'pending' ? 'rgba(251, 191, 36, 0.2)' : 'rgba(107, 114, 128, 0.2)'
                }}
            onMouseEnter={(e) => {
                  const ref = rankIndicatorRefs.current[rankType];
                  if (ref) {
                    const rect = ref.getBoundingClientRect();
                    setRankTooltipPositions({
                      ...rankTooltipPositions,
                      [rankType]: {
                  top: rect.bottom + 8,
                  left: rect.left + rect.width / 2
                      }
                });
              }
                  setShowRankTooltip({ ...showRankTooltip, [rankType]: true });
            }}
                onMouseLeave={() => {
                  setShowRankTooltip({ ...showRankTooltip, [rankType]: false });
                }}
          >
                {status === 'success' && (
              <CheckCircle2 className="w-4 h-4" style={{ color: '#10B981' }} />
            )}
                {status === 'failed' && (
              <XCircle className="w-4 h-4" style={{ color: '#EF4444' }} />
            )}
                {status === 'pending' && (
              <Loader2 className="w-4 h-4 animate-spin" style={{ color: '#FBBF24' }} />
            )}
                {status === 'unknown' && (
              <XCircle className="w-4 h-4" style={{ color: '#6B7280' }} />
            )}
                <span className="text-xs" style={{ color: status === 'success' ? '#10B981' : status === 'failed' ? '#EF4444' : status === 'pending' ? '#FBBF24' : '#6B7280' }}>
                  {rankLabel}
            </span>
            
                {/* Rank Type Tooltip */}
            <AnimatePresence>
                  {showRankTooltip[rankType] && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9, y: -5 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9, y: -5 }}
                  transition={{ duration: 0.15 }}
                  className="fixed z-50 pointer-events-none"
                  style={{
                        top: `${rankTooltipPositions[rankType]?.top || 0}px`,
                        left: `${rankTooltipPositions[rankType]?.left || 0}px`,
                    transform: 'translate(-50%, 0)',
                    marginTop: '0'
                  }}
                >
                  <div
                        className="px-3 py-2 rounded-lg shadow-lg border text-xs"
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.9)',
                      borderColor: 'rgba(255, 255, 255, 0.2)',
                      color: '#F5F5F7'
                    }}
                  >
                        {status === 'success' ? (
                      <>
                            <div>{rankLabel} Data</div>
                            <div style={{ color: '#10B981', marginTop: '4px' }}>
                              <div>Past Season: {rankData.past_season} matches</div>
                              <div>Past 365 Days: {rankData.past_365} matches</div>
                            </div>
                          </>
                        ) : (
                          <>
                            <div>{rankLabel} Data</div>
                            <div style={{ marginTop: '4px', fontSize: '0.75rem', color: '#8E8E93' }}>
                              Past Season: {rankData.past_season} matches<br/>
                              Past 365 Days: {rankData.past_365} matches
                            </div>
                          </>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
            );
          })}
        </div>
      </div>

      {/* Data Status Checker */}
      {!dataReady && !insufficientData && (
        <div className="mb-6 p-6 rounded-lg border border-gray-700 bg-gray-800/50">
          <DataStatusChecker
            gameName={gameName}
            tagLine={tagLine}
            onDataReady={async () => {
              // Check if data is actually sufficient
              try {
                const response = await fetch(`/api/player/${gameName}/${tagLine}/data-status`);
                if (response.ok) {
                  const status = await response.json();
                  setDataStatus(status);
                  
                  // Check if data is sufficient
                  const hasEnoughGames = status.has_data && status.total_games >= 10;
                  
                  // Check if there's data from Past Season (patch 14.1 to 14.25, 2024-01-09 to 2025-01-06) - check match dates
                  const hasPastSeasonData = status.patches?.some((p: any) => {
                    return (p.earliest_match_date && isMatchDateInPastSeason(p.earliest_match_date)) ||
                           (p.latest_match_date && isMatchDateInPastSeason(p.latest_match_date));
                  }) || (status.earliest_match_date && isMatchDateInPastSeason(status.earliest_match_date)) ||
                        (status.latest_match_date && isMatchDateInPastSeason(status.latest_match_date)) || false;
                  
                  // Check if latest match date is within past 365 days from today
                  const hasPast365DaysData = (status.latest_match_date && isMatchDateWithinPast365Days(status.latest_match_date)) ||
                                             (status.patches && status.patches.some((p: any) => {
                                               return (p.earliest_match_date && isMatchDateWithinPast365Days(p.earliest_match_date)) ||
                                                      (p.latest_match_date && isMatchDateWithinPast365Days(p.latest_match_date));
                                             }));
                  
                  // Data is sufficient only if:
                  // 1. Has enough games (>=10)
                  // 2. Has Past Season data (patch 14.1 to 14.25, 2024-01-09 to 2025-01-06) OR has data within past 365 days from today
                  if (hasEnoughGames && (hasPastSeasonData || hasPast365DaysData)) {
                    setDataReady(true);
                    setInsufficientData(false);
                  } else {
                    setInsufficientData(true);
                    setDataReady(false);
                  }
                } else {
                  setDataReady(true);
                }
              } catch (err) {
                setDataReady(true);
              }
            }}
            onError={(error) => setDataError(error)}
          />
        </div>
      )}

      {/* Show insufficient data message */}
      {insufficientData && (
        <div className="mb-6 p-6 rounded-lg border border-yellow-500/50 bg-yellow-900/20">
          <div className="flex items-center gap-4">
            <AlertCircle className="w-8 h-8 text-yellow-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-lg font-semibold text-yellow-400 mb-2">
                Not Enough Data for Analysis
              </p>
              <p className="text-sm text-gray-300 mb-2">
                This player doesn't have sufficient match history data. AI analysis requires:
              </p>
              <ul className="text-sm text-gray-300 mb-2 list-disc list-inside space-y-1">
                <li>At least 10 games played</li>
                <li>Matches from Past Season (patch 14.1 to 14.25, 2024-01-09 to 2025-01-06) OR within past 365 days from today</li>
              </ul>
              {dataStatus && (
                <div className="text-xs text-gray-400 space-y-1">
                  <p>Current data: {dataStatus.total_games || 0} games across {dataStatus.total_patches || 0} patches</p>
                  {dataStatus.earliest_patch && dataStatus.latest_patch && (
                    <p>Patch range: {dataStatus.earliest_patch} → {dataStatus.latest_patch}</p>
                  )}
                </div>
              )}
            </div>
          </div>
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

      {/* Only show agents if data is ready and sufficient */}
      {dataReady && !insufficientData && (
        <div className="max-w-6xl mx-auto">
      {/* Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {agents.slice(0, 3).map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onGenerate={() => handleGenerate(agent)}
            onTimeRangeChange={(timeRange) => handleTimeRangeChange(agent.id, timeRange)}
            onRankTypeChange={(rankType) => handleRankTypeChange(agent.id, rankType)}
            onSubOptionClick={(subOptionId) => handleSubOptionClick(agent.id, subOptionId)}
          />
        ))}
      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {agents.slice(3, 6).map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onGenerate={() => handleGenerate(agent)}
            onTimeRangeChange={(timeRange) => handleTimeRangeChange(agent.id, timeRange)}
            onRankTypeChange={(rankType) => handleRankTypeChange(agent.id, rankType)}
            onSubOptionClick={(subOptionId) => handleSubOptionClick(agent.id, subOptionId)}
          />
        ))}
      </div>

      {/* Row 3 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.slice(6, 9).map((agent) => (
          <AgentCard
            key={agent.id}
            {...agent}
            onGenerate={() => handleGenerate(agent)}
            onTimeRangeChange={(timeRange) => handleTimeRangeChange(agent.id, timeRange)}
            onRankTypeChange={(rankType) => handleRankTypeChange(agent.id, rankType)}
            onSubOptionClick={(subOptionId) => handleSubOptionClick(agent.id, subOptionId)}
          />
        ))}
      </div>
        </div>
      )}

      {/* Detailed Analysis Modal */}
      {selectedAgent && (
        <DetailedAnalysisModal
          isOpen={!!selectedAgent}
          onClose={() => setSelectedAgent(null)}
          agentId={selectedAgent.id}
          agentName={selectedAgent.name}
          agentDescription={selectedAgent.description}
          detailedReport={selectedAgent.detailedReport || ''}
          analysisData={selectedAgent.analysisData}
          selectedRankType={selectedAgent.selectedRankType}
          selectedTimeRange={selectedAgent.selectedTimeRange}
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
        selectedTimeRange={agents.find(a => a.id === 'champion-mastery')?.selectedTimeRange}
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
        selectedRankType={agents.find(a => a.id === 'role-specialization')?.selectedRankType}
        selectedTimeRange={agents.find(a => a.id === 'role-specialization')?.selectedTimeRange}
      />

      <RankSelectorModal
        isOpen={rankModalOpen}
        onClose={() => setRankModalOpen(false)}
        onSelect={(rank: string) => handleFriendSelect('', '', rank)}
        currentRank={playerData?.rank || playerData?.tier}
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
    </div>
  );
}
