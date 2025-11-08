'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import Image from 'next/image';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import GlareHover from './ui/GlareHover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import { useModal } from '../context/ModalContext';

type Rank = 'IRON' | 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM' |
            'EMERALD' | 'DIAMOND' | 'MASTER' | 'GRANDMASTER' | 'CHALLENGER';

interface RankOption {
  value: Rank;
  label: string;
  imageUrl: string;
  color: string;
  description: string;
}

const RANK_OPTIONS: RankOption[] = [
  { value: 'IRON', label: 'Iron', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/iron.png', color: '#664E4C', description: 'Learning fundamentals' },
  { value: 'BRONZE', label: 'Bronze', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/bronze.png', color: '#8B6535', description: 'Building basics' },
  { value: 'SILVER', label: 'Silver', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/silver.png', color: '#A8A8A8', description: 'Developing skills' },
  { value: 'GOLD', label: 'Gold', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/gold.png', color: '#FFD700', description: 'Above average play' },
  { value: 'PLATINUM', label: 'Platinum', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/platinum.png', color: '#41A8B3', description: 'Strong fundamentals' },
  { value: 'EMERALD', label: 'Emerald', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/emerald.png', color: '#00A86B', description: 'Advanced gameplay' },
  { value: 'DIAMOND', label: 'Diamond', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/diamond.png', color: '#3B5998', description: 'Elite player' },
  { value: 'MASTER', label: 'Master', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/master.png', color: '#9B30FF', description: 'Master level' },
  { value: 'GRANDMASTER', label: 'Grandmaster', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/grandmaster.png', color: '#FF4500', description: 'Top tier' },
  { value: 'CHALLENGER', label: 'Challenger', imageUrl: 'https://opgg-static.akamaized.net/images/medals_new/challenger.png', color: '#F4C430', description: 'The best' },
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
  const { setIsModalOpen } = useModal();
  const [selectedRank, setSelectedRank] = useState<Rank>(currentRank || 'PLATINUM');

  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen, setIsModalOpen]);

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
              className="rounded-2xl shadow-2xl max-w-2xl w-full max-h-[75vh] flex flex-col pointer-events-auto overflow-hidden"
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
                    text="Peer Comparison Analysis"
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
                <button
                  onClick={onClose}
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

              {/* Rank Grid */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="grid grid-cols-5 gap-3">
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
                          className="p-4 rounded-xl cursor-pointer transition-all text-center border-2"
                          style={{
                            backgroundColor: 'rgba(48, 48, 52, 0.9)',
                            backdropFilter: 'blur(20px)',
                            borderColor: selectedRank === rank.value
                              ? colors.accentBlue
                              : currentRank === rank.value
                              ? colors.accentGreen
                              : 'rgba(255, 255, 255, 0.1)'
                          }}
                        >
                          <div className="flex justify-center mb-2">
                            <Image
                              src={rank.imageUrl}
                              alt={rank.label}
                              width={64}
                              height={64}
                              className="object-contain"
                            />
                          </div>
                          <div className="flex items-center justify-center gap-2">
                            <ShinyText
                              text={rank.label}
                              speed={2}
                              className="font-semibold"
                            />
                            {selectedRank === rank.value && (
                              <span style={{ color: colors.accentBlue }}>✓</span>
                            )}
                          </div>
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
              <div className="flex flex-col gap-3 p-6 border-t border-white/10">
                <div className="flex items-center gap-2">
                  <p className="text-sm" style={{ color: '#8E8E93' }}>
                    Selected:
                  </p>
                  <Image
                    src={RANK_OPTIONS.find(r => r.value === selectedRank)?.imageUrl || ''}
                    alt={selectedRank}
                    width={24}
                    height={24}
                    className="object-contain"
                  />
                  <p className="text-sm font-semibold" style={{ color: '#EBEBF5' }}>
                    {selectedRank}
                  </p>
                </div>

                <div className="flex w-full">
                  <div className="ml-auto">
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
                        <ShinyText text="Compare" speed={2} />
                      </button>
                    </ClickSpark>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
