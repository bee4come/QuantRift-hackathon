'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Trophy, TrendingUp, TrendingDown, Clock, Swords } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import GlareHover from './ui/GlareHover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import { useModal } from '../context/ModalContext';

interface MatchData {
  match_id: string;
  game_creation: number;
  game_duration: number;
  champion_id: number;
  champion_name?: string;
  role: string;
  win: boolean;
  kills: number;
  deaths: number;
  assists: number;
  kda?: number;
}

interface MatchSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (matchId: string) => void;
  matches: MatchData[];
  gameName: string;
  tagLine: string;
}

export default function MatchSelectorModal({
  isOpen,
  onClose,
  onSelect,
  matches,
  gameName,
  tagLine
}: MatchSelectorModalProps) {
  const colors = useAdaptiveColors();
  const { setIsModalOpen } = useModal();
  const [selectedMatch, setSelectedMatch] = useState<string | null>(null);

  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen, setIsModalOpen]);

  const handleConfirm = () => {
    if (selectedMatch) {
      onSelect(selectedMatch);
      onClose();
    }
  };

  // Format timestamp
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  // Format game duration
  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m`;
  };

  // Calculate KDA
  const calculateKDA = (match: MatchData) => {
    if (match.deaths === 0) return (match.kills + match.assists).toFixed(1);
    return ((match.kills + match.assists) / match.deaths).toFixed(2);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div
              className="fluid-glass rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] flex flex-col pointer-events-auto overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <div>
                  <ShinyText
                    text="📊 Timeline Deep Dive - Select Match"
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-2" style={{ color: '#8E8E93' }}>
                    Choose a match for detailed timeline analysis
                  </p>
                  {matches.length > 0 && (
                    <p className="text-xs mt-1" style={{ color: colors.accentBlue }}>
                      {matches.length} recent matches available
                    </p>
                  )}
                </div>

                {/* Close Button */}
                <ClickSpark inline={true}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onClose();
                    }}
                    className="p-2 rounded-lg border transition-all hover:opacity-80"
                    style={{
                      backgroundColor: 'rgba(255, 69, 58, 0.15)',
                      borderColor: 'rgba(255, 69, 58, 0.3)',
                      color: '#FF453A'
                    }}
                  >
                    <X className="w-5 h-5" />
                  </button>
                </ClickSpark>
              </div>

              {/* Match List */}
              <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {matches.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-lg" style={{ color: '#8E8E93' }}>
                      No matches available for analysis
                    </p>
                    <p className="text-sm mt-2" style={{ color: '#8E8E93' }}>
                      Please load player data first
                    </p>
                  </div>
                ) : (
                  matches.map((match) => {
                    const kda = calculateKDA(match);
                    const isWin = match.win;

                    return (
                      <GlareHover
                        key={match.match_id}
                        width="100%"
                        height="auto"
                        background="transparent"
                        borderRadius="12px"
                      >
                        <ClickSpark>
                          <motion.div
                            whileHover={{ scale: 1.01 }}
                            whileTap={{ scale: 0.99 }}
                            onClick={() => setSelectedMatch(match.match_id)}
                            className="fluid-glass-dark p-5 rounded-xl cursor-pointer transition-all border-2"
                            style={{
                              borderColor: selectedMatch === match.match_id ? colors.accentBlue : 'transparent'
                            }}
                          >
                            <div className="flex items-center justify-between">
                              {/* Match Info */}
                              <div className="flex items-center gap-4">
                                {/* Win/Loss Indicator */}
                                <div
                                  className="w-16 h-16 rounded-xl flex items-center justify-center font-bold text-lg"
                                  style={{
                                    backgroundColor: isWin ? `${colors.accentGreen}30` : `${colors.accentRed}30`,
                                    border: `2px solid ${isWin ? colors.accentGreen : colors.accentRed}60`,
                                    color: isWin ? colors.accentGreen : colors.accentRed
                                  }}
                                >
                                  {isWin ? (
                                    <Trophy className="w-8 h-8" />
                                  ) : (
                                    <X className="w-8 h-8" />
                                  )}
                                </div>

                                {/* Match Details */}
                                <div>
                                  <div className="flex items-center gap-3">
                                    <ShinyText
                                      text={match.champion_name || `Champion ${match.champion_id}`}
                                      speed={2}
                                      className="text-lg font-semibold"
                                    />
                                    <span className="text-sm px-2 py-1 rounded" style={{
                                      backgroundColor: 'rgba(142, 142, 147, 0.2)',
                                      color: '#8E8E93'
                                    }}>
                                      {match.role}
                                    </span>
                                    {selectedMatch === match.match_id && (
                                      <span style={{ color: colors.accentBlue }}>✓</span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-3 mt-2 text-sm" style={{ color: '#8E8E93' }}>
                                    <span className="flex items-center gap-1">
                                      <Swords className="w-4 h-4" />
                                      {match.kills}/{match.deaths}/{match.assists}
                                    </span>
                                    <span>•</span>
                                    <span>{kda} KDA</span>
                                    <span>•</span>
                                    <span className="flex items-center gap-1">
                                      <Clock className="w-4 h-4" />
                                      {formatDuration(match.game_duration)}
                                    </span>
                                    <span>•</span>
                                    <span>{formatTime(match.game_creation)}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Win/Loss Badge */}
                              <div className="text-right">
                                <div className="flex items-center gap-2">
                                  {isWin ? (
                                    <TrendingUp className="w-5 h-5" style={{ color: colors.accentGreen }} />
                                  ) : (
                                    <TrendingDown className="w-5 h-5" style={{ color: colors.accentRed }} />
                                  )}
                                  <span className="text-xl font-bold" style={{
                                    color: isWin ? colors.accentGreen : colors.accentRed
                                  }}>
                                    {isWin ? 'Victory' : 'Defeat'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        </ClickSpark>
                      </GlareHover>
                    );
                  })
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between gap-3 p-6 border-t border-white/10">
                <p className="text-sm" style={{ color: '#8E8E93' }}>
                  {selectedMatch
                    ? `Selected match: ${matches.find(m => m.match_id === selectedMatch)?.champion_name || 'Match'}`
                    : 'Select a match to analyze its timeline'}
                </p>

                <ClickSpark>
                  <button
                    onClick={handleConfirm}
                    disabled={!selectedMatch}
                    className="px-6 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      backgroundColor: 'rgba(10, 132, 255, 0.2)',
                      borderColor: 'rgba(10, 132, 255, 0.4)',
                      color: '#5AC8FA'
                    }}
                  >
                    <ShinyText text="Analyze" speed={2} />
                  </button>
                </ClickSpark>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
