'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UserPlus, Search } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

interface FriendInputModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (friendGameName: string, friendTagLine: string, rank?: string) => void;
  currentPlayerName: string;
  currentPlayerTag: string;
}

export default function FriendInputModal({
  isOpen,
  onClose,
  onConfirm,
  currentPlayerName,
  currentPlayerTag
}: FriendInputModalProps) {
  const colors = useAdaptiveColors();
  const [mode, setMode] = useState<'friend' | 'rank'>('friend');
  const [friendGameName, setFriendGameName] = useState('');
  const [friendTagLine, setFriendTagLine] = useState('');
  const [selectedRank, setSelectedRank] = useState('');
  const [error, setError] = useState('');

  const ranks = [
    { value: 'iron', label: 'Iron', color: '#6B4A3A' },
    { value: 'bronze', label: 'Bronze', color: '#CD7F32' },
    { value: 'silver', label: 'Silver', color: '#C0C0C0' },
    { value: 'gold', label: 'Gold', color: '#FFD700' },
    { value: 'platinum', label: 'Platinum', color: '#00B4D8' },
    { value: 'emerald', label: 'Emerald', color: '#50C878' },
    { value: 'diamond', label: 'Diamond', color: '#B9F2FF' },
    { value: 'master', label: 'Master', color: '#9333EA' },
    { value: 'grandmaster', label: 'Grandmaster', color: '#DC2626' },
    { value: 'challenger', label: 'Challenger', color: '#F59E0B' }
  ];

  const handleConfirm = () => {
    // Validation based on mode
    if (mode === 'friend') {
      if (!friendGameName.trim()) {
        setError('Please enter friend\'s game name');
        return;
      }
      if (!friendTagLine.trim()) {
        setError('Please enter friend\'s tag line');
        return;
      }

      // Check not comparing with self
      if (friendGameName.toLowerCase() === currentPlayerName.toLowerCase() &&
          friendTagLine.toLowerCase() === currentPlayerTag.toLowerCase()) {
        setError('Cannot compare with yourself!');
        return;
      }

      setError('');
      onConfirm(friendGameName.trim(), friendTagLine.trim());
    } else {
      // Rank mode
      if (!selectedRank) {
        setError('Please select a rank');
        return;
      }

      setError('');
      onConfirm('', '', selectedRank);
    }

    onClose();

    // Reset after close
    setTimeout(() => {
      setFriendGameName('');
      setFriendTagLine('');
      setSelectedRank('');
      setMode('friend');
      setError('');
    }, 300);
  };

  const handleClose = () => {
    setFriendGameName('');
    setFriendTagLine('');
    setSelectedRank('');
    setMode('friend');
    setError('');
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
            onClick={handleClose}
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
              className="fluid-glass rounded-2xl shadow-2xl max-w-lg w-full pointer-events-auto overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <div>
                  <ShinyText
                    text="👥 Friend Comparison"
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-2" style={{ color: '#8E8E93' }}>
                    Compare your performance with a friend
                  </p>
                  <p className="text-xs mt-1" style={{ color: colors.accentBlue }}>
                    You: {currentPlayerName}#{currentPlayerTag}
                  </p>
                </div>

                {/* Close Button */}
                <ClickSpark inline={true}>
                  <button
                    onClick={handleClose}
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

              {/* Input Fields */}
              <div className="p-6 space-y-4">
                {/* Mode Toggle */}
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setMode('friend');
                      setError('');
                    }}
                    className="flex-1 py-3 rounded-lg border font-medium transition-all"
                    style={{
                      backgroundColor: mode === 'friend' ? 'rgba(10, 132, 255, 0.2)' : 'rgba(142, 142, 147, 0.1)',
                      borderColor: mode === 'friend' ? 'rgba(10, 132, 255, 0.4)' : 'rgba(142, 142, 147, 0.2)',
                      color: mode === 'friend' ? '#5AC8FA' : '#8E8E93'
                    }}
                  >
                    👥 Friend Comparison
                  </button>
                  <button
                    onClick={() => {
                      setMode('rank');
                      setError('');
                    }}
                    className="flex-1 py-3 rounded-lg border font-medium transition-all"
                    style={{
                      backgroundColor: mode === 'rank' ? 'rgba(10, 132, 255, 0.2)' : 'rgba(142, 142, 147, 0.1)',
                      borderColor: mode === 'rank' ? 'rgba(10, 132, 255, 0.4)' : 'rgba(142, 142, 147, 0.2)',
                      color: mode === 'rank' ? '#5AC8FA' : '#8E8E93'
                    }}
                  >
                    🏆 Rank Comparison
                  </button>
                </div>

                {/* Friend Mode */}
                {mode === 'friend' && (
                  <>
                    {/* Friend Info Banner */}
                    <div
                      className="p-4 rounded-lg border"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.1)',
                        borderColor: 'rgba(10, 132, 255, 0.2)'
                      }}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <UserPlus className="w-5 h-5" style={{ color: colors.accentBlue }} />
                        <p className="text-sm font-semibold" style={{ color: colors.accentBlue }}>
                          Enter Friend's Riot ID
                        </p>
                      </div>
                      <p className="text-xs" style={{ color: '#8E8E93' }}>
                        Format: GameName#TagLine (e.g., Faker#KR1)
                      </p>
                    </div>

                {/* Game Name Input */}
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: '#EBEBF5' }}>
                    Game Name
                  </label>
                  <input
                    type="text"
                    value={friendGameName}
                    onChange={(e) => {
                      setFriendGameName(e.target.value);
                      setError('');
                    }}
                    placeholder="Enter game name..."
                    className="w-full px-4 py-3 rounded-lg border font-medium transition-all outline-none"
                    style={{
                      backgroundColor: 'rgba(28, 28, 30, 0.8)',
                      borderColor: error ? 'rgba(255, 69, 58, 0.5)' : 'rgba(142, 142, 147, 0.3)',
                      color: '#EBEBF5'
                    }}
                    autoFocus
                  />
                </div>

                {/* Tag Line Input */}
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: '#EBEBF5' }}>
                    Tag Line
                  </label>
                  <div className="relative">
                    <span
                      className="absolute left-4 top-1/2 transform -translate-y-1/2 text-xl font-bold"
                      style={{ color: '#8E8E93' }}
                    >
                      #
                    </span>
                    <input
                      type="text"
                      value={friendTagLine}
                      onChange={(e) => {
                        setFriendTagLine(e.target.value);
                        setError('');
                      }}
                      placeholder="Enter tag line..."
                      className="w-full pl-8 pr-4 py-3 rounded-lg border font-medium transition-all outline-none"
                      style={{
                        backgroundColor: 'rgba(28, 28, 30, 0.8)',
                        borderColor: error ? 'rgba(255, 69, 58, 0.5)' : 'rgba(142, 142, 147, 0.3)',
                        color: '#EBEBF5'
                      }}
                    />
                  </div>
                </div>

                {/* Error Message */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 rounded-lg border"
                    style={{
                      backgroundColor: 'rgba(255, 69, 58, 0.1)',
                      borderColor: 'rgba(255, 69, 58, 0.3)'
                    }}
                  >
                    <p className="text-sm" style={{ color: '#FF453A' }}>
                      ⚠️ {error}
                    </p>
                  </motion.div>
                )}

                    {/* Example */}
                    <div
                      className="p-3 rounded-lg"
                      style={{
                        backgroundColor: 'rgba(142, 142, 147, 0.1)',
                      }}
                    >
                      <p className="text-xs" style={{ color: '#8E8E93' }}>
                        💡 <span className="font-semibold">Example:</span> GameName: <span className="font-mono">Faker</span> | TagLine: <span className="font-mono">KR1</span>
                      </p>
                    </div>
                  </>
                )}

                {/* Rank Mode */}
                {mode === 'rank' && (
                  <>
                    {/* Rank Info Banner */}
                    <div
                      className="p-4 rounded-lg border"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.1)',
                        borderColor: 'rgba(10, 132, 255, 0.2)'
                      }}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Search className="w-5 h-5" style={{ color: colors.accentBlue }} />
                        <p className="text-sm font-semibold" style={{ color: colors.accentBlue }}>
                          Select Rank for Comparison
                        </p>
                      </div>
                      <p className="text-xs" style={{ color: '#8E8E93' }}>
                        Compare with average performance of players in selected rank
                      </p>
                    </div>

                    {/* Rank Selector Grid */}
                    <div className="grid grid-cols-2 gap-3">
                      {ranks.map((rank) => (
                        <ClickSpark key={rank.value} inline={true}>
                          <button
                            onClick={() => {
                              setSelectedRank(rank.value);
                              setError('');
                            }}
                            className="p-4 rounded-lg border font-medium transition-all text-left"
                            style={{
                              backgroundColor: selectedRank === rank.value
                                ? 'rgba(10, 132, 255, 0.2)'
                                : 'rgba(28, 28, 30, 0.8)',
                              borderColor: selectedRank === rank.value
                                ? 'rgba(10, 132, 255, 0.4)'
                                : 'rgba(142, 142, 147, 0.3)',
                              borderWidth: selectedRank === rank.value ? '2px' : '1px'
                            }}
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: rank.color }}
                              />
                              <span style={{ color: selectedRank === rank.value ? '#5AC8FA' : '#EBEBF5' }}>
                                {rank.label}
                              </span>
                            </div>
                          </button>
                        </ClickSpark>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between gap-3 p-6 border-t border-white/10">
                <div className="flex items-center gap-2">
                  <Search className="w-4 h-4" style={{ color: '#8E8E93' }} />
                  <p className="text-sm" style={{ color: '#8E8E93' }}>
                    {mode === 'friend'
                      ? (friendGameName && friendTagLine
                          ? `${friendGameName}#${friendTagLine}`
                          : 'Enter friend details')
                      : (selectedRank
                          ? `Compare with ${ranks.find(r => r.value === selectedRank)?.label || ''}`
                          : 'Select a rank')}
                  </p>
                </div>

                <div className="flex gap-3">
                  <ClickSpark>
                    <button
                      onClick={handleClose}
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
                      disabled={mode === 'friend'
                        ? (!friendGameName.trim() || !friendTagLine.trim())
                        : !selectedRank}
                      className="px-6 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.2)',
                        borderColor: 'rgba(10, 132, 255, 0.4)',
                        color: '#5AC8FA'
                      }}
                    >
                      <ShinyText text="Compare →" speed={2} />
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
