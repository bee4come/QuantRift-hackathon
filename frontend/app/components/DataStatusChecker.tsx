'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle2, AlertCircle, Download } from 'lucide-react';

interface DataStatus {
  success: boolean;
  puuid: string;
  game_name: string;
  tag_line: string;
  has_data: boolean;
  total_patches: number;
  total_games: number;
  earliest_patch?: string;
  latest_patch?: string;
  patches?: Array<{ patch: string; games: number }>;
}

interface DataStatusCheckerProps {
  gameName: string;
  tagLine: string;
  onDataReady: () => void;
  onError?: (error: string) => void;
}

export default function DataStatusChecker({
  gameName,
  tagLine,
  onDataReady,
  onError,
}: DataStatusCheckerProps) {
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [fetchProgress, setFetchProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkDataStatus();
  }, [gameName, tagLine]);

  const checkDataStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      const url = `/api/player/${gameName}/${tagLine}/data-status`;
      console.log('[DataStatusChecker] Fetching:', url);

      // Create a timeout promise
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Request timed out. Backend took too long to respond.')), 60000); // 60 second timeout
      });

      // Race between fetch and timeout
      const response = await Promise.race([
        fetch(url),
        timeoutPromise
      ]);

      console.log('[DataStatusChecker] Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: response.statusText }));
        throw new Error(errorData.error || `Failed to check data status: ${response.statusText}`);
      }

      const data: DataStatus = await response.json();
      console.log('[DataStatusChecker] Data received:', data);
      setStatus(data);

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

      // Check if patch is in Season 2024 range (14.1 - 14.24)
      const isSeason2024Patch = (patch: string): boolean => {
        if (!patch) return false;
        
        // Check if patch starts with 14.
        if (!patch.startsWith('14.')) return false;
        
        // Extract minor version
        const parts = patch.split('.');
        if (parts.length < 2) return false;
        
        const minor = parseInt(parts[1]) || 0;
        // Season 2024 is patches 14.1 to 14.24
        return minor >= 1 && minor <= 24;
      };

      // Check if match date is within past 365 days from today
      const isMatchDateWithinPast365Days = (matchDate: string): boolean => {
        if (!matchDate) return false;
        
        try {
          const matchDateTime = new Date(matchDate);
          const today = new Date();
          const daysDiff = Math.floor((today.getTime() - matchDateTime.getTime()) / (1000 * 60 * 60 * 24));
          
          return daysDiff >= 0 && daysDiff <= 365;
        } catch {
          return false;
        }
      };
      
      // Helper function to get Past Season date range based on patch versions
      // Past Season 2024: patch 14.1 (2024-01-09) to patch 14.25 (2025-01-06)
      const getPastSeasonDateRange = (): { start: Date; end: Date } => {
        return {
          start: new Date('2024-01-09'), // patch 14.1 start date
          end: new Date('2025-01-06T23:59:59.999') // patch 14.25 end date
        };
      };

      // Check if match date is in Past Season (2024-01-09 to 2025-01-06, patch 14.1 to 14.25)
      const isMatchDateInPastSeason = (matchDate: string): boolean => {
        if (!matchDate) return false;
        
        try {
          const { start, end } = getPastSeasonDateRange();
          const matchDateTime = new Date(matchDate);
          
          return matchDateTime >= start && matchDateTime <= end;
        } catch {
          return false;
        }
      };

      // Check if data is sufficient
      const hasEnoughGames = data.has_data && data.total_games >= 10;
      
      // Use backend-calculated games counts for Past Season and Past 365 Days
      // Backend now provides accurate counts based on actual match dates
      const hasPastSeasonData = (data.total_past_season_games || 0) > 0;
      const hasPast365DaysData = (data.total_past_365_days_games || 0) > 0;
      
      // Data is sufficient only if:
      // 1. Has enough games (>=10)
      // 2. Has Past Season data (patch 14.1 to 14.25, 2024-01-09 to 2025-01-06) OR has data within past 365 days from today
      if (hasEnoughGames && (hasPastSeasonData || hasPast365DaysData)) {
        // Data is ready
        onDataReady();
      } else if (!data.has_data || data.total_games < 10) {
        // Insufficient data, trigger fetch
        await triggerDataFetch();
      } else {
        // Has games but no 2024/recent data - don't trigger fetch, just mark as insufficient
        // This will be handled by parent component
        onDataReady();
      }
    } catch (err) {
      console.error('[DataStatusChecker] Error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      const detailedError = `${errorMessage} (Check console for details)`;
      setError(detailedError);
      onError?.(detailedError);
    } finally {
      setLoading(false);
    }
  };

  const triggerDataFetch = async () => {
    try {
      setFetching(true);
      setFetchProgress(0);

      // Data fetching now always starts from patch 14.1 (2024-01-09) to today
      // time_range parameter is only used for filtering data in agents, not for fetching
      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const fetchResponse = await fetch(
        `${BACKEND_URL}/v1/player/fetch-data`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            game_name: gameName,
            tag_line: tagLine,
            region: 'na1',
            days: 365,  // Kept for compatibility but not used for fetching
            include_timeline: true
          })
        }
      );

      if (!fetchResponse.ok) {
        throw new Error(`Failed to start data fetch: ${fetchResponse.statusText}`);
      }

      const fetchData = await fetchResponse.json();
      const taskId = fetchData.task_id;

      // Poll for data availability every 5 seconds (18 minute max)
      let attempts = 0;
      const maxAttempts = 216; // 18 minutes (5s interval)

      const pollInterval = setInterval(async () => {
        attempts++;

        try {
          // Check task status
          const statusResponse = await fetch(
            `${BACKEND_URL}/v1/player/fetch-status/${taskId}`
          );

          if (statusResponse.ok) {
            const taskStatus = await statusResponse.json();

            // Update progress based on task status
            if (taskStatus.status === 'in_progress') {
              const progress = taskStatus.progress || {};
              const total = progress.total_matches || 100;
              const fetched = progress.fetched_matches || 0;
              const percentage = total > 0 ? (fetched / total) * 90 : (attempts / maxAttempts) * 90;
              setFetchProgress(Math.min(percentage, 95));
            } else if (taskStatus.status === 'completed') {
              // Task completed, check if data is now available
              const dataStatusResponse = await fetch(
                `/api/player/${gameName}/${tagLine}/data-status`
              );

              if (dataStatusResponse.ok) {
                const newStatus: DataStatus = await dataStatusResponse.json();
                setStatus(newStatus);

                if (newStatus.has_data && newStatus.total_games >= 10) {
                  // Data is ready!
                  clearInterval(pollInterval);
                  setFetchProgress(100);
                  setFetching(false);
                  onDataReady();
                  return;
                }
              }
            } else if (taskStatus.status === 'failed') {
              clearInterval(pollInterval);
              setFetching(false);
              throw new Error(taskStatus.error || 'Data fetch failed');
            }
          }

          if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            setFetching(false);
            throw new Error('Data fetch timeout - please try again later');
          }
        } catch (pollError) {
          clearInterval(pollInterval);
          setFetching(false);
          throw pollError;
        }
      }, 5000); // 5 second intervals for long-running task
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch data';
      setError(errorMessage);
      onError?.(errorMessage);
      setFetching(false);
    }
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center p-8 space-y-4"
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <p className="text-gray-400">Checking data availability...</p>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center p-8 space-y-4"
      >
        <AlertCircle className="w-12 h-12 text-red-500" />
        <div className="text-center space-y-2">
          <p className="text-xl font-semibold text-red-400">Error</p>
          <p className="text-gray-400">{error}</p>
          <button
            onClick={checkDataStatus}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </motion.div>
    );
  }

  if (fetching) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center p-8 space-y-6"
      >
        <Download className="w-12 h-12 text-blue-500 animate-bounce" />
        <div className="text-center space-y-2">
          <p className="text-xl font-semibold text-blue-400">
            Fetching Full Year Data
          </p>
          <p className="text-gray-400">
            Downloading 365 days of match history from Riot API...
          </p>
        </div>

        {/* Progress Bar */}
        <div className="w-full max-w-md space-y-2">
          <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${fetchProgress}%` }}
              transition={{ duration: 0.5 }}
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
            />
          </div>
          <p className="text-sm text-gray-500 text-center">
            {Math.round(fetchProgress)}% complete
          </p>
        </div>

        <p className="text-xs text-gray-500">
          This may take 15-20 minutes for a full year of matches...
        </p>
      </motion.div>
    );
  }

  if (status?.has_data) {
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

    // Check if patch is in Season 2024 range (14.1 - 14.24)
    const isSeason2024Patch = (patch: string): boolean => {
      if (!patch) return false;
      
      // Check if patch starts with 14.
      if (!patch.startsWith('14.')) return false;
      
      // Extract minor version
      const parts = patch.split('.');
      if (parts.length < 2) return false;
      
      const minor = parseInt(parts[1]) || 0;
      // Season 2024 is patches 14.1 to 14.24
      return minor >= 1 && minor <= 24;
    };

    // Check if match date is within past 365 days from today
    const isMatchDateWithinPast365Days = (matchDate: string): boolean => {
      if (!matchDate) return false;
      
      try {
        const matchDateTime = new Date(matchDate);
        const today = new Date();
        const daysDiff = Math.floor((today.getTime() - matchDateTime.getTime()) / (1000 * 60 * 60 * 24));
        
        return daysDiff >= 0 && daysDiff <= 365;
      } catch {
        return false;
      }
    };
    
    // Helper function to get Past Season date range based on patch versions
    // Past Season 2024: patch 14.1 (2024-01-09) to patch 14.25 (2025-01-06)
    const getPastSeasonDateRange = (): { start: Date; end: Date } => {
      return {
        start: new Date('2024-01-09'), // patch 14.1 start date
        end: new Date('2025-01-06T23:59:59.999') // patch 14.25 end date
      };
    };

    // Check if match date is in Past Season (2024-01-09 to 2025-01-06, patch 14.1 to 14.25)
    const isMatchDateInPastSeason = (matchDate: string): boolean => {
      if (!matchDate) return false;
      
      try {
        const { start, end } = getPastSeasonDateRange();
        const matchDateTime = new Date(matchDate);
        
        return matchDateTime >= start && matchDateTime <= end;
      } catch {
        return false;
      }
    };

    // Check if data is sufficient (has Past Season data or past 365 days data)
    const hasEnoughGames = status.total_games >= 10;
    const hasPastSeasonData = status.patches?.some((p: any) => {
      return (p.earliest_match_date && isMatchDateInPastSeason(p.earliest_match_date)) ||
             (p.latest_match_date && isMatchDateInPastSeason(p.latest_match_date));
    }) || (status.earliest_match_date && isMatchDateInPastSeason(status.earliest_match_date)) ||
          (status.latest_match_date && isMatchDateInPastSeason(status.latest_match_date)) || false;
    const hasPast365DaysData = (status.latest_match_date && isMatchDateWithinPast365Days(status.latest_match_date)) ||
                               (status.patches && status.patches.some((p: any) => {
                                 return (p.earliest_match_date && isMatchDateWithinPast365Days(p.earliest_match_date)) ||
                                        (p.latest_match_date && isMatchDateWithinPast365Days(p.latest_match_date));
                               }));
    const isSufficient = hasEnoughGames && (hasPastSeasonData || hasPast365DaysData);
    
    // Only show "Data Ready!" if data is sufficient
    if (isSufficient) {
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center justify-center p-8 space-y-4"
        >
          <CheckCircle2 className="w-12 h-12 text-green-500" />
          <div className="text-center space-y-2">
            <p className="text-xl font-semibold text-green-400">Data Ready!</p>
            <div className="text-sm text-gray-400 space-y-1">
              <p>
                <span className="text-blue-400">{status.total_patches}</span>{' '}
                patches analyzed
              </p>
              <p>
                <span className="text-blue-400">{status.total_games}</span> total
                games
              </p>
              {status.earliest_patch && status.latest_patch && (
                <p className="text-xs text-gray-500">
                  {status.earliest_patch} → {status.latest_patch}
                </p>
              )}
            </div>
          </div>
        </motion.div>
      );
    }
    // If data exists but is insufficient, return null (parent will show insufficient message)
    return null;
  }

  return null;
}
