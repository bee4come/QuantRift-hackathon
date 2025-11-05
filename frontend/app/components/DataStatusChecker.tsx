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

      const response = await fetch(url);
      console.log('[DataStatusChecker] Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: response.statusText }));
        throw new Error(errorData.error || `Failed to check data status: ${response.statusText}`);
      }

      const data: DataStatus = await response.json();
      console.log('[DataStatusChecker] Data received:', data);
      setStatus(data);

      // Check if data is sufficient
      if (!data.has_data || data.total_games < 10) {
        // Insufficient data, trigger fetch
        await triggerDataFetch();
      } else {
        // Data is ready
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

      // Trigger FULL YEAR data fetch (365 days) via backend API
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
            days: 365,
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

  return null;
}
