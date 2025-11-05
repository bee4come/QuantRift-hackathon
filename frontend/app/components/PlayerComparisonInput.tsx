'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { UserPlus, X } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import GlareHover from './ui/GlareHover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

interface PlayerTag {
  gameName: string;
  tagLine: string;
  display: string;
}

interface PlayerComparisonInputProps {
  onPlayersChange: (players: PlayerTag[]) => void;
}

export default function PlayerComparisonInput({ onPlayersChange }: PlayerComparisonInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [playerTags, setPlayerTags] = useState<PlayerTag[]>([]);
  const [error, setError] = useState('');
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

    const [gameName, tagLine] = parts;
    const display = `${gameName}#${tagLine}`;

    if (playerTags.some((tag) => tag.display === display)) {
      setError('Player already added');
      setTimeout(() => setError(''), 2000);
      return;
    }

    if (playerTags.length >= 5) {
      setError('Maximum 5 players allowed');
      setTimeout(() => setError(''), 2000);
      return;
    }

    const newPlayers = [...playerTags, { gameName, tagLine, display }];
    setPlayerTags(newPlayers);
    onPlayersChange(newPlayers);
    setInputValue('');
    setError('');
  };

  const handleRemoveTag = (display: string) => {
    const newPlayers = playerTags.filter((t) => t.display !== display);
    setPlayerTags(newPlayers);
    onPlayersChange(newPlayers);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddPlayer();
    }
  };

  return (
    <GlareHover
      width="100%"
      height="100%"
      background="rgba(0, 0, 0, 0.2)"
      borderRadius="16px"
      borderColor="rgba(255, 255, 255, 0.1)"
      glareColor="#ffffff"
      glareOpacity={0.15}
      glareAngle={-45}
      glareSize={150}
      transitionDuration={400}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="fluid-glass rounded-2xl p-5 h-full flex flex-col shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-3 relative z-10">
          <div
            className="p-2 rounded-lg"
            style={{
              backgroundColor: `${colors.accentBlue}20`,
              border: `1px solid ${colors.accentBlue}40`
            }}
          >
            <UserPlus className="w-5 h-5" style={{ color: colors.accentBlue }} />
          </div>
          <div>
            <ShinyText
              text="Add Players for Comparison"
              speed={3}
              className="text-base font-bold"
            />
            <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
              Compare with up to 5 players
            </p>
          </div>
        </div>

        {/* Player Tags */}
        {playerTags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3 relative z-10">
            {playerTags.map((tag) => (
              <motion.div
                key={tag.display}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="fluid-glass-dark rounded-full px-3 py-1.5 flex items-center gap-2 overflow-hidden"
              >
                <span className="text-xs font-medium relative z-10" style={{ color: '#F5F5F7' }}>
                  {tag.display}
                </span>
                <ClickSpark
                  sparkColor="#FF453A"
                  sparkSize={4}
                  sparkRadius={8}
                  sparkCount={3}
                  duration={200}
                  inline={true}
                >
                  <button
                    onClick={() => handleRemoveTag(tag.display)}
                    className="transition-colors relative z-10"
                    style={{ color: '#FF453A' }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = '#FF6961')}
                    onMouseLeave={(e) => (e.currentTarget.style.color = '#FF453A')}
                    aria-label={`Remove ${tag.display}`}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </ClickSpark>
              </motion.div>
            ))}
          </div>
        )}

        {/* Input Field */}
        <div className="flex gap-2 relative z-10 mb-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="e.g., Hide on bush#KR1"
              className="w-full px-4 py-2.5 rounded-lg border focus:outline-none transition-all backdrop-blur-sm text-sm"
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
            sparkColor={colors.accentBlue}
            sparkSize={6}
            sparkRadius={10}
            sparkCount={4}
            duration={250}
            inline={true}
          >
            <button
              onClick={handleAddPlayer}
              disabled={!inputValue.trim() || playerTags.length >= 5}
              className="px-4 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed backdrop-blur-sm text-sm whitespace-nowrap"
              style={{
                backgroundColor: 'rgba(10, 132, 255, 0.2)',
                borderColor: 'rgba(10, 132, 255, 0.4)',
                color: '#5AC8FA'
              }}
              onMouseEnter={(e) => {
                if (inputValue.trim() && playerTags.length < 5) {
                  e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.3)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.2)';
              }}
            >
              <ShinyText text="Add" speed={2} className="text-sm font-medium" />
            </button>
          </ClickSpark>
        </div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative z-10"
          >
            <p className="text-xs" style={{ color: '#FF453A' }}>
              {error}
            </p>
          </motion.div>
        )}

        {/* Player Count */}
        <div className="flex-1" />
        <div className="text-center mt-3 relative z-10">
          <p className="text-xs" style={{ color: '#8E8E93' }}>
            {playerTags.length} / 5 players added
          </p>
        </div>
      </motion.div>
    </GlareHover>
  );
}
