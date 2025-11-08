'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useSearch } from '../context/SearchContext';
import GlareHover from './ui/GlareHover';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';

interface SearchBarProps {
  isSearched: boolean;
}

export default function SearchBar({ isSearched }: SearchBarProps) {
  const router = useRouter();
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { addPlayers, startProcessing } = useSearch();

  const handleSearch = async () => {
    const trimmedValue = inputValue.trim();
    
    if (!trimmedValue) {
      setError('Please enter a Riot ID');
      setTimeout(() => setError(''), 2000);
      return;
    }

    // Parse Riot ID format: GameName#TagLine
    const parts = trimmedValue.split('#');
    if (parts.length !== 2 || !parts[0] || !parts[1]) {
      setError('Invalid format. Use: GameName#TagLine (e.g., Hide on bush#KR1)');
      setTimeout(() => setError(''), 3000);
      return;
    }

    const gameName = parts[0].trim();
    const tagLine = parts[1].trim();
    const display = `${gameName}#${tagLine}`;

    setIsLoading(true);
    setError('');

    try {
      // Create timeout promise (60 seconds)
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => {
          reject(new Error('Request timeout. The server is taking too long to respond. This may be due to high traffic. Please try again later.'));
        }, 60000); // 60 seconds timeout
      });

      // Fetch player data with timeout
      const fetchPromise = fetch(
        `/api/summoner/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?count=20`
      );
      
      const response = await Promise.race([fetchPromise, timeoutPromise]);
      
      // Check response status first - if successful, navigate immediately
      if (response.ok) {
        // Clone response to read it multiple times
        const clonedResponse = response.clone();
        
        // Navigate immediately after successful response
        router.push(`/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`);
        
        // Parse response and trigger background data fetch in background (non-blocking)
        clonedResponse.json().then(data => {
          if (data.success) {
      // Trigger background year data fetch (non-blocking)
      // Calculate days needed to cover both Past Season and Past 365 Days
      const today = new Date();
      const pastSeasonStart = new Date('2024-01-09'); // patch 14.1 start date
      const past365DaysStart = new Date(today);
      past365DaysStart.setDate(past365DaysStart.getDate() - 365);
      
      // Get the earlier date between Past Season start and Past 365 Days start
      const startDate = pastSeasonStart < past365DaysStart ? pastSeasonStart : past365DaysStart;
      
      // Calculate days from start date to today
      const daysDiff = Math.ceil((today.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
      
      fetch('/api/player/fetch-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gameName: gameName,
          tagLine: tagLine,
          region: data.player?.region || 'na1',
          days: daysDiff,
          includeTimeline: true,
        }),
      }).then(res => res.json())
        .then(result => {
          console.log(`Background data fetch started for ${display} (${daysDiff} days to cover Past Season 2024 and Past 365 Days):`, result.task_id);
          // Store task_id in localStorage for status checking
          const storageKey = `fetch_task_${gameName}_${tagLine}`;
          localStorage.setItem(storageKey, result.task_id);
        })
        .catch(err => {
          console.warn(`Failed to start background fetch for ${display}:`, err);
        });
          }
        }).catch(err => {
          console.warn(`Failed to parse response for ${display}:`, err);
        });
        
        // Exit early - navigation happens immediately
        setIsLoading(false);
        return;
      }
      
      // Handle errors - only show error if response is not ok
      let errorData: any = {};
      try {
        errorData = await response.json();
      } catch (e) {
        // If response is not JSON, use status text
        errorData = { error: response.statusText };
      }
      
      console.error(`Failed to fetch data for ${display}:`, response.status, errorData);
      
      // Handle 429 - Rate limit / Too many requests
      if (response.status === 429) {
        throw new Error('Request too frequent. Please wait a moment and try again later.');
      }
      
      // Handle 404 - player not found
      if (response.status === 404) {
        // Use error message from backend if available, otherwise use default
        const errorMsg = errorData.error || errorData.detail || `Invalid ID, please double check: ${display}`;
        throw new Error(errorMsg);
      }
      
      // Bubble up helpful backend messages
      if (response.status === 401 || response.status === 403) {
        throw new Error('Riot API Unauthorized. Please set RIOT_API_KEY in combatpower/.env and restart the backend.');
      }
      
      // Use error message from backend if available
      if (errorData?.error || errorData?.detail) {
        throw new Error(errorData.error || errorData.detail);
      }
      
      throw new Error('Failed to fetch player data');
    } catch (error) {
      console.error('Search error:', error);
      let errorMessage = error instanceof Error ? error.message : 'An error occurred while searching. Please try again.';
      
      // Check if it's a timeout or rate limit error
      if (errorMessage.includes('timeout') || errorMessage.includes('too long')) {
        errorMessage = 'Request timeout. The server is taking too long to respond. This may be due to high traffic. Please try again later.';
      } else if (errorMessage.includes('too frequent') || errorMessage.includes('429')) {
        errorMessage = 'Request too frequent. Please wait a moment and try again later.';
      }
      
      setError(errorMessage);
      // Show timeout/rate limit messages longer
      const timeout = errorMessage.includes('timeout') || errorMessage.includes('too frequent') ? 8000 : 
                      errorMessage.includes('Invalid ID') ? 5000 : 3000;
      setTimeout(() => setError(''), timeout);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <motion.div
      initial={false}
      animate={{
        scale: isSearched ? 0.95 : 1,
      }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 30,
      }}
      className="w-full max-w-xl mx-auto px-4"
    >
      <GlareHover
        width="100%"
        height="auto"
        background="rgba(0, 0, 0, 0.2)"
        borderRadius="16px"
        borderColor="rgba(255, 255, 255, 0.1)"
        glareColor="#ffffff"
        glareOpacity={0.2}
        glareAngle={-45}
        glareSize={200}
        transitionDuration={500}
      >
        <motion.div
          layout
          className="fluid-glass rounded-2xl p-4 shadow-2xl overflow-hidden"
        >
        {/* Search Input with Button Beside */}
        <div className="flex gap-3 relative z-10">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter Riot ID (e.g., Hide on bush#KR1)"
            className="flex-1 px-5 py-3 rounded-xl border focus:outline-none transition-all backdrop-blur-sm"
            style={{
              backgroundColor: 'rgba(44, 44, 46, 0.6)',
              borderColor: 'rgba(255, 255, 255, 0.1)',
              color: '#F5F5F7'
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'rgba(10, 132, 255, 0.5)';
              e.currentTarget.style.backgroundColor = 'rgba(44, 44, 46, 0.7)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.backgroundColor = 'rgba(44, 44, 46, 0.6)';
            }}
          />
          <ClickSpark
            sparkColor="#FFFFFF"
            sparkSize={12}
            sparkRadius={20}
            sparkCount={12}
            duration={500}
            inline={true}
          >
            <button
              onClick={handleSearch}
              disabled={!inputValue.trim() || isLoading}
              className="px-6 py-3 rounded-xl font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg backdrop-blur-sm border"
              style={{
                background: 'linear-gradient(90deg, rgba(10, 132, 255, 0.9) 0%, rgba(191, 90, 242, 0.9) 100%)',
                borderColor: 'rgba(255, 255, 255, 0.2)',
                color: '#FFFFFF'
              }}
              onMouseEnter={(e) => (!inputValue.trim() || isLoading) ? null : e.currentTarget.style.background = 'linear-gradient(90deg, #0A84FF 0%, #BF5AF2 100%)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'linear-gradient(90deg, rgba(10, 132, 255, 0.9) 0%, rgba(191, 90, 242, 0.9) 100%)'}
            >
              <ShinyText 
                text={isLoading ? 'Searching...' : 'Search'} 
                speed={3} 
                className="font-semibold text-sm"
              />
            </button>
          </ClickSpark>
        </div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 text-sm relative z-10"
            style={{ color: '#FF453A' }}
          >
            <ShinyText text={error} speed={2} className="text-sm" />
          </motion.div>
        )}
        </motion.div>
      </GlareHover>
    </motion.div>
  );
}

