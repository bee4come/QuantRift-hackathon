'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, X } from 'lucide-react';
import { useSearch } from '../context/SearchContext';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import GlareHover from './ui/GlareHover';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';

interface SearchBarProps {
  isSearched: boolean;
}

interface PlayerTag {
  gameName: string;
  tagLine: string;
  display: string;
}

export default function SearchBar({ isSearched }: SearchBarProps) {
  const [inputValue, setInputValue] = useState('');
  const [playerTags, setPlayerTags] = useState<PlayerTag[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { addPlayers, startProcessing } = useSearch();
  const colors = useAdaptiveColors();

  const handleAddPlayer = () => {
    const trimmedValue = inputValue.trim();
    
    if (!trimmedValue) return;
    
    // Parse Riot ID format: GameName#TagLine
    const parts = trimmedValue.split('#');
    if (parts.length !== 2 || !parts[0] || !parts[1]) {
      setError('Invalid format. Use: GameName#TagLine (e.g., Hide on bush#KR1)');
      setTimeout(() => setError(''), 3000);
      return;
    }

    // Trim leading/trailing spaces only, preserve internal spaces
    const gameName = parts[0].trim();
    const tagLine = parts[1].trim();
    const display = `${gameName}#${tagLine}`;
    
    if (playerTags.some(tag => tag.display === display)) {
      setError('Player already added');
      setTimeout(() => setError(''), 2000);
      return;
    }

    if (playerTags.length >= 5) {
      setError('Maximum 5 players allowed');
      setTimeout(() => setError(''), 2000);
      return;
    }

    setPlayerTags([...playerTags, { gameName, tagLine, display }]);
    setInputValue('');
    setError('');
  };

  const handleRemoveTag = (display: string) => {
    setPlayerTags(playerTags.filter((t) => t.display !== display));
  };

  const handleReset = () => {
    setPlayerTags([]);
    setInputValue('');
    setError('');
  };

  const handleSearch = async () => {
    if (playerTags.length === 0) {
      setError('Please add at least one player');
      setTimeout(() => setError(''), 2000);
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Fetch data for all players
      const playerPromises = playerTags.map(async (tag) => {
        try {
          // API 1: Fetch 20 matches with parallel processing (fast response)
          const response = await fetch(
            `/api/summoner/${encodeURIComponent(tag.gameName)}/${encodeURIComponent(tag.tagLine)}?count=20`
          );
          
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error(`Failed to fetch data for ${tag.display}:`, response.status, errorData);
            
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
            
            return null;
          }

          const data = await response.json();
          
          if (!data.success) {
            console.error(`Error for ${tag.display}:`, data.error);
            return null;
          }

          // Trigger background year data fetch (non-blocking)
          fetch('/api/player/fetch-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              gameName: tag.gameName,
              tagLine: tag.tagLine,
              region: data.player?.region || 'na1',
              days: 365,
              includeTimeline: true,
            }),
          }).then(res => res.json())
            .then(result => {
              console.log(`🚀 Background data fetch started for ${tag.display}:`, result.task_id);
            })
            .catch(err => {
              console.warn(`Failed to start background fetch for ${tag.display}:`, err);
            });

          return {
            username: tag.display,
            gameName: tag.gameName,
            tagLine: tag.tagLine,
            ...data.player,
            matches: data.matches || [],
            analytics: data.analysis || {}
          };
        } catch (error) {
          console.error(`Error fetching ${tag.display}:`, error);
          return null;
        }
      });

      const players = (await Promise.all(playerPromises)).filter(p => p !== null);

      if (players.length === 0) {
        setError('Cannot connect to backend server. Please make sure Flask backend is running (cd combatpower && python app.py)');
        setTimeout(() => setError(''), 5000);
        setIsLoading(false);
        return;
      }

      // If single player search, navigate to profile page
      if (players.length === 1) {
        const player = players[0];
        window.location.href = `/player/${encodeURIComponent(player.gameName)}/${encodeURIComponent(player.tagLine)}`;
        return;
      }

      // Show warning if some players weren't found
      if (players.length < playerTags.length) {
        const foundCount = players.length;
        const totalCount = playerTags.length;
        setError(`Found ${foundCount} of ${totalCount} players. Proceeding with found players...`);
        setTimeout(() => setError(''), 3000);
      }

      addPlayers(players);
      startProcessing();
    } catch (error) {
      console.error('Search error:', error);
      setError(error instanceof Error ? error.message : 'An error occurred while searching. Please try again.');
      setTimeout(() => setError(''), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (inputValue.trim()) {
        handleAddPlayer();
      } else if (playerTags.length > 0) {
        handleSearch();
      }
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
        <div className="flex items-center justify-between mb-4 relative z-10">
          <div className="flex items-center gap-3">
            <Search className="w-6 h-6" style={{ color: colors.accentBlue }} />
            <ShinyText 
              text="Search Players" 
              speed={4}
              className="text-2xl font-bold"
            />
          </div>
          {playerTags.length > 0 && (
            <ClickSpark
              sparkColor="#FF453A"
              sparkSize={8}
              sparkRadius={12}
              sparkCount={6}
              duration={300}
              inline={true}
            >
              <button
                onClick={handleReset}
                className="px-4 py-2 rounded-lg border font-medium transition-all backdrop-blur-sm text-sm"
                style={{
                  backgroundColor: 'rgba(255, 69, 58, 0.15)',
                  borderColor: 'rgba(255, 69, 58, 0.3)',
                  color: '#FF453A'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 69, 58, 0.25)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 69, 58, 0.15)';
                }}
              >
                <ShinyText text="Reset" speed={3} className="text-sm font-medium" />
              </button>
            </ClickSpark>
          )}
        </div>

        {/* Player Tags */}
        {playerTags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4 relative z-10">
            {playerTags.map((tag) => (
              <motion.div
                key={tag.display}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="fluid-glass-dark rounded-full px-4 py-2 flex items-center gap-2 overflow-hidden"
              >
                <ShinyText text={tag.display} speed={2} className="font-medium relative z-10" />
                <ClickSpark
                  sparkColor="#FF453A"
                  sparkSize={6}
                  sparkRadius={10}
                  sparkCount={4}
                  duration={250}
                  inline={true}
                >
                  <button
                    onClick={() => handleRemoveTag(tag.display)}
                    className="transition-colors relative z-10"
                    style={{ color: '#FF453A' }}
                    onMouseEnter={(e) => e.currentTarget.style.color = '#FF6961'}
                    onMouseLeave={(e) => e.currentTarget.style.color = '#FF453A'}
                    aria-label={`Remove ${tag.display}`}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </ClickSpark>
              </motion.div>
            ))}
          </div>
        )}

        {/* Search Input */}
        <div className="flex gap-3 relative z-10">
          <div className="flex-1 relative">
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
            sparkColor="#5AC8FA"
            sparkSize={10}
            sparkRadius={15}
            sparkCount={8}
            duration={400}
            inline={true}
          >
            <button
              onClick={handleAddPlayer}
              disabled={!inputValue.trim()}
              className="px-6 py-4 rounded-xl border font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed backdrop-blur-sm"
              style={{
                backgroundColor: 'rgba(10, 132, 255, 0.2)',
                borderColor: 'rgba(10, 132, 255, 0.4)',
                color: '#5AC8FA'
              }}
              onMouseEnter={(e) => !inputValue.trim() ? null : e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.3)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.2)'}
            >
              <ShinyText text="Add Player" speed={3} className="font-medium" />
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

        {/* Search Button */}
        <ClickSpark
          sparkColor="#FFFFFF"
          sparkSize={12}
          sparkRadius={20}
          sparkCount={12}
          duration={500}
        >
          <button
            onClick={handleSearch}
            disabled={playerTags.length === 0 || isLoading}
            className="w-full mt-4 px-6 py-4 rounded-xl font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg backdrop-blur-sm border relative z-10"
            style={{
              background: 'linear-gradient(90deg, rgba(10, 132, 255, 0.9) 0%, rgba(191, 90, 242, 0.9) 100%)',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: '#FFFFFF'
            }}
            onMouseEnter={(e) => (playerTags.length === 0 || isLoading) ? null : e.currentTarget.style.background = 'linear-gradient(90deg, #0A84FF 0%, #BF5AF2 100%)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'linear-gradient(90deg, rgba(10, 132, 255, 0.9) 0%, rgba(191, 90, 242, 0.9) 100%)'}
          >
            <ShinyText 
              text={isLoading ? 'Searching...' : `Search ${playerTags.length > 0 ? `(${playerTags.length})` : ''}`} 
              speed={3} 
              className="font-semibold"
            />
          </button>
        </ClickSpark>
        </motion.div>
      </GlareHover>
    </motion.div>
  );
}

