'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import GlareHover from './ui/GlareHover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

type Rank = 'IRON' | 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM' |
            'EMERALD' | 'DIAMOND' | 'MASTER' | 'GRANDMASTER' | 'CHALLENGER';

interface RankOption {
  value: Rank;
  label: string;
  emoji: string;
  color: string;
  description: string;
}

const RANK_OPTIONS: RankOption[] = [
  { value: 'IRON', label: 'Iron', emoji: '🥉', color: '#664E4C', description: 'Learning fundamentals' },
  { value: 'BRONZE', label: 'Bronze', emoji: '🥉', color: '#8B6535', description: 'Building basics' },
  { value: 'SILVER', label: 'Silver', emoji: '🥈', color: '#A8A8A8', description: 'Developing skills' },
  { value: 'GOLD', label: 'Gold', emoji: '🥇', color: '#FFD700', description: 'Above average play' },
  { value: 'PLATINUM', label: 'Platinum', emoji: '💎', color: '#41A8B3', description: 'Strong fundamentals' },
  { value: 'EMERALD', label: 'Emerald', emoji: '💚', color: '#00A86B', description: 'Advanced gameplay' },
  { value: 'DIAMOND', label: 'Diamond', emoji: '💠', color: '#3B5998', description: 'Elite player' },
  { value: 'MASTER', label: 'Master', emoji: '👑', color: '#9B30FF', description: 'Master level' },
  { value: 'GRANDMASTER', label: 'Grandmaster', emoji: '🏆', color: '#FF4500', description: 'Top tier' },
  { value: 'CHALLENGER', label: 'Challenger', emoji: '⭐', color: '#F4C430', description: 'The best' },
];

interface RankSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (rank: Rank) => void;
  currentRank?: Rank;
  gameName: string;
  tagLine: string;
}

export default function RankSelectorModal({
  isOpen,
  onClose,
  onSelect,
  currentRank,
  gameName,
  tagLine
}: RankSelectorModalProps) {
  const colors = useAdaptiveColors();
  const [selectedRank, setSelectedRank] = useState<Rank>(currentRank || 'PLATINUM');

  const handleConfirm = () => {
    onSelect(selectedRank);
    onClose();
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
              className="fluid-glass rounded-2xl shadow-2xl max-w-2xl w-full max-h-[75vh] flex flex-col pointer-events-auto overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <div>
                  <ShinyText
                    text="📊 Peer Comparison Analysis"
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-2" style={{ color: '#8E8E93' }}>
                    Compare your performance with players at different ranks
                  </p>
                  {currentRank && (
                    <p className="text-xs mt-1" style={{ color: colors.accentBlue }}>
                      Current rank: {currentRank}
                    </p>
                  )}
                </div>

                {/* Close Button */}
                <ClickSpark inline={true}>
                  <button
                    onClick={onClose}
                    className="p-2 rounded-lg border transition-all"
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

              {/* Rank Grid */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {RANK_OPTIONS.map((rank) => (
                    <GlareHover
                      key={rank.value}
                      width="100%"
                      height="auto"
                      background="transparent"
                      borderRadius="12px"
                    >
                      <ClickSpark>
                        <motion.div
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => setSelectedRank(rank.value)}
                          className="fluid-glass-dark p-4 rounded-xl cursor-pointer transition-all text-center border-2"
                          style={{
                            borderColor: selectedRank === rank.value
                              ? colors.accentBlue
                              : currentRank === rank.value
                              ? colors.accentGreen
                              : 'transparent'
                          }}
                        >
                          <div className="text-3xl mb-2">{rank.emoji}</div>
                          <div className="flex items-center justify-center gap-2 mb-1">
                            <ShinyText
                              text={rank.label}
                              speed={2}
                              className="font-semibold"
                            />
                            {selectedRank === rank.value && (
                              <span style={{ color: colors.accentBlue }}>✓</span>
                            )}
                          </div>
                          <p className="text-xs" style={{ color: '#8E8E93' }}>
                            {rank.description}
                          </p>
                          {currentRank === rank.value && (
                            <p className="text-xs mt-2 font-semibold" style={{ color: colors.accentGreen }}>
                              Current
                            </p>
                          )}
                        </motion.div>
                      </ClickSpark>
                    </GlareHover>
                  ))}
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between gap-3 p-6 border-t border-white/10">
                <p className="text-sm" style={{ color: '#8E8E93' }}>
                  Selected: {RANK_OPTIONS.find(r => r.value === selectedRank)?.emoji} {selectedRank}
                </p>

                <div className="flex gap-3">
                  <ClickSpark>
                    <button
                      onClick={onClose}
                      className="px-6 py-2.5 rounded-lg border font-medium transition-all"
                      style={{
                        backgroundColor: 'rgba(142, 142, 147, 0.15)',
                        borderColor: 'rgba(142, 142, 147, 0.3)',
                        color: '#8E8E93'
                      }}
                    >
                      Cancel
                    </button>
                  </ClickSpark>

                  <ClickSpark>
                    <button
                      onClick={handleConfirm}
                      className="px-6 py-2.5 rounded-lg border font-medium transition-all"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.2)',
                        borderColor: 'rgba(10, 132, 255, 0.4)',
                        color: '#5AC8FA'
                      }}
                    >
                      <ShinyText text="Compare Performance →" speed={2} />
                    </button>
                  </ClickSpark>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
