'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Search } from 'lucide-react';
import { useSearch } from '../context/SearchContext';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
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
  const colors = useAdaptiveColors();

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
      // Fetch player data
      const response = await fetch(
        `/api/summoner/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?count=20`
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error(`Failed to fetch data for ${display}:`, response.status, errorData);
        
        // Handle 404 - player not found
        if (response.status === 404) {
          throw new Error(`Invalid ID, please double check: ${display}`);
        }
        
        // Bubble up helpful backend messages
        if (response.status === 401 || response.status === 403) {
          throw new Error('Riot API Unauthorized. Please set RIOT_API_KEY in combatpower/.env and restart the backend.');
        }
        
        if ((response.status === 500 || response.status === 400) && errorData?.error) {
          throw new Error(errorData.error);
        }

        if (response.status === 503 && errorData.error) {
          throw new Error(errorData.error);
        }
        
        throw new Error('Failed to fetch player data');
      }

      const data = await response.json();
      
      if (!data.success) {
        console.error(`Error for ${display}:`, data.error);
        throw new Error(data.error || 'Failed to fetch player data');
      }

      // Trigger background year data fetch (non-blocking)
      fetch('/api/player/fetch-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gameName: gameName,
          tagLine: tagLine,
          region: data.player?.region || 'na1',
          days: 365,
          includeTimeline: true,
        }),
      }).then(res => res.json())
        .then(result => {
          console.log(`Background data fetch started for ${display}:`, result.task_id);
        })
        .catch(err => {
          console.warn(`Failed to start background fetch for ${display}:`, err);
        });

      // Navigate to player profile page
      setTimeout(() => {
        router.push(`/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`);
      }, 100);
    } catch (error) {
      console.error('Search error:', error);
      const errorMessage = error instanceof Error ? error.message : 'An error occurred while searching. Please try again.';
      setError(errorMessage);
      // Show "Invalid ID" messages longer
      const timeout = errorMessage.includes('Invalid ID') ? 5000 : 3000;
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
      className="w-full max-w-2xl mx-auto px-4"
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
          className="fluid-glass rounded-2xl p-6 shadow-2xl overflow-hidden"
        >
        <div className="flex items-center gap-3 mb-4 relative z-10">
          <Search className="w-6 h-6" style={{ color: colors.accentBlue }} />
          <ShinyText 
            text="Search Players" 
            speed={4}
            className="text-2xl font-bold"
          />
        </div>

        {/* Search Input with Button */}
        <div className="flex gap-3 relative z-10">
          <div className="flex-[4] relative">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter Riot ID (e.g., Hide on bush#KR1)"
              className="w-full px-6 py-4 rounded-xl border focus:outline-none transition-all backdrop-blur-sm"
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
          </div>
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
              className="flex-1 px-6 py-4 rounded-xl font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg backdrop-blur-sm border"
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
                className="font-semibold"
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

