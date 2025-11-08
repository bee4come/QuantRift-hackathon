'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UserPlus, Search } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import { useModal } from '../context/ModalContext';

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
  const { setIsModalOpen } = useModal();
  const [friendGameName, setFriendGameName] = useState('');
  const [friendTagLine, setFriendTagLine] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen, setIsModalOpen]);

  const handleConfirm = () => {
    if (!friendGameName.trim()) {
      setError('Please enter friend\'s user ID');
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
    onClose();

    // Reset after close
    setTimeout(() => {
      setFriendGameName('');
      setFriendTagLine('');
      setError('');
    }, 300);
  };

  const handleClose = () => {
    setFriendGameName('');
    setFriendTagLine('');
    setError('');
    onClose();
  };

  const handleClear = () => {
    setFriendGameName('');
    setFriendTagLine('');
    setError('');
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
            className="fixed inset-0 bg-black/80 backdrop-blur-md z-50"
          />

              {/* Modal */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
                style={{ zIndex: 9999 }}
              >
            <div
              className="rounded-2xl shadow-2xl max-w-lg w-full pointer-events-auto overflow-hidden"
              onClick={(e) => e.stopPropagation()}
              style={{
                backgroundColor: 'rgba(28, 28, 30, 0.98)',
                backdropFilter: 'blur(40px)',
                border: '1px solid rgba(255, 255, 255, 0.15)'
              }}
            >
              {/* Header */}
              <div className="relative p-6 border-b border-white/10 z-10">
                <div className="text-center pointer-events-none">
                  <ShinyText
                    text="Friend Comparison"
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
                <button
                  onClick={handleClose}
                  className="absolute top-6 right-6 p-2 rounded-lg border transition-all hover:opacity-80"
                  style={{
                    backgroundColor: 'rgba(255, 69, 58, 0.15)',
                    borderColor: 'rgba(255, 69, 58, 0.3)',
                    color: '#FF453A',
                    zIndex: 20
                  }}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Input Fields */}
              <div className="p-6 space-y-4">
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
                        Format: UserID#TagLine (e.g., Faker#KR1)
                      </p>
                    </div>

                {/* User ID Input */}
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: '#EBEBF5' }}>
                    User ID
                  </label>
                  <input
                    type="text"
                    value={friendGameName}
                    onChange={(e) => {
                      setFriendGameName(e.target.value);
                      setError('');
                    }}
                    placeholder="Enter user ID..."
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
                    💡 <span className="font-semibold">Example:</span> User ID: <span className="font-mono">Faker</span> | TagLine: <span className="font-mono">KR1</span>
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between gap-3 p-6 border-t border-white/10">
                <div className="flex items-center gap-2">
                  <Search className="w-4 h-4" style={{ color: '#8E8E93' }} />
                  <p className="text-sm" style={{ color: '#8E8E93' }}>
                    {friendGameName && friendTagLine
                      ? `${friendGameName}#${friendTagLine}`
                      : 'Enter friend details'}
                  </p>
                </div>

                <div className="flex gap-3">
                  <ClickSpark>
                    <button
                      onClick={handleClear}
                      className="px-6 py-2.5 rounded-lg border font-medium transition-all"
                      style={{
                        backgroundColor: 'rgba(142, 142, 147, 0.15)',
                        borderColor: 'rgba(142, 142, 147, 0.3)',
                        color: '#8E8E93'
                      }}
                    >
                      Clear
                    </button>
                  </ClickSpark>

                  <ClickSpark>
                    <button
                      onClick={handleConfirm}
                      disabled={!friendGameName.trim() || !friendTagLine.trim()}
                      className="px-6 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.2)',
                        borderColor: 'rgba(10, 132, 255, 0.4)',
                        color: '#5AC8FA'
                      }}
                    >
                      <ShinyText text="Compare" speed={2} />
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
