'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, TrendingUp, TrendingDown } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import GlareHover from './ui/GlareHover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import { useModal } from '../context/ModalContext';

interface PlayerChampion {
  champion_id: number;
  champion_name: string;
  games_played: number;
  wins: number;
  win_rate: number;
  avg_kda: number;
}

interface ChampionSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (championId: number, championName: string) => void;
  playerChampions: PlayerChampion[];
  gameName: string;
  tagLine: string;
}

export default function ChampionSelectorModal({
  isOpen,
  onClose,
  onSelect,
  playerChampions,
  gameName,
  tagLine
}: ChampionSelectorModalProps) {
  const colors = useAdaptiveColors();
  const { setIsModalOpen } = useModal();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChampion, setSelectedChampion] = useState<PlayerChampion | null>(null);

  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen, setIsModalOpen]);

  // Filter and sort champions
  const filteredChampions = useMemo(() => {
    if (!playerChampions || playerChampions.length === 0) {
      return [];
    }
    return playerChampions
      .filter(champ =>
        champ.champion_name.toLowerCase().includes(searchQuery.toLowerCase())
      )
      .sort((a, b) => b.games_played - a.games_played);
  }, [playerChampions, searchQuery]);

  // Convert champion display name to Data Dragon image filename format
  // e.g., "Kai'Sa" -> "Kaisa", "Lee Sin" -> "LeeSin", "Dr. Mundo" -> "DrMundo"
  const getChampionImageName = (championName: string): string => {
    return championName
      .replace(/'/g, '')  // Remove apostrophes
      .replace(/\./g, '')  // Remove periods
      .replace(/\s+/g, '') // Remove spaces
      .replace(/&/g, '')   // Remove ampersands
      .replace(/-/g, '');  // Remove hyphens
  };

  const handleConfirm = () => {
    if (selectedChampion) {
      onSelect(selectedChampion.champion_id, selectedChampion.champion_name);
      onClose();
    }
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
                className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
                style={{ zIndex: 9999 }}
              >
            <div
              className="rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col pointer-events-auto overflow-hidden"
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
                    text="Champion Mastery Analysis"
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-2" style={{ color: '#8E8E93' }}>
                    Select a champion to analyze your mastery and performance patterns
                  </p>
                  <p className="text-xs mt-1" style={{ color: colors.accentBlue }}>
                    {gameName}#{tagLine} • {playerChampions.length} champions
                  </p>
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

              {/* Search Bar */}
              <div className="p-4 border-b border-white/10">
                <div className="relative">
                  <Search
                    className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5"
                    style={{ color: '#8E8E93' }}
                  />
                  <input
                    type="text"
                    placeholder="Search champions..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border bg-black/20 backdrop-blur-sm transition-all"
                    style={{
                      borderColor: 'rgba(255, 255, 255, 0.1)',
                      color: colors.textPrimary
                    }}
                  />
                </div>
              </div>

              {/* Champion List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {filteredChampions.length === 0 ? (
                  <div className="text-center py-12">
                    <p style={{ color: '#8E8E93' }}>No champions found</p>
                  </div>
                ) : (
                  filteredChampions.map((champ) => (
                    <GlareHover
                      key={champ.champion_id}
                      width="100%"
                      height="auto"
                      background="transparent"
                      borderRadius="12px"
                    >
                      <ClickSpark>
                        <motion.div
                          whileHover={{ scale: 1.02 }}
                          onClick={() => setSelectedChampion(champ)}
                          className={`p-4 rounded-xl cursor-pointer transition-all border-2`}
                          style={{
                            backgroundColor: 'rgba(28, 28, 30, 0.9)',
                            borderColor: selectedChampion?.champion_id === champ.champion_id
                              ? colors.accentBlue
                              : 'rgba(255, 255, 255, 0.1)',
                            borderWidth: '1px',
                            borderStyle: 'solid'
                          }}
                        >
                          <div className="flex items-center justify-between">
                            {/* Champion Info */}
                            <div className="flex items-center gap-4">
                              <div
                                className="w-12 h-12 rounded-lg bg-cover bg-center"
                                style={{
                                  backgroundImage: `url(https://ddragon.leagueoflegends.com/cdn/15.1.1/img/champion/${getChampionImageName(champ.champion_name)}.png)`,
                                  boxShadow: '0 0 10px rgba(0,0,0,0.5)'
                                }}
                              />
                              <div>
                                <div className="flex items-center gap-2">
                                  <ShinyText
                                    text={champ.champion_name}
                                    speed={2}
                                    className="font-semibold"
                                  />
                                  {selectedChampion?.champion_id === champ.champion_id && (
                                    <span style={{ color: colors.accentBlue }}>✓</span>
                                  )}
                                </div>
                                <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                                  {champ.games_played} games • {champ.avg_kda.toFixed(2)} KDA
                                </p>
                              </div>
                            </div>

                            {/* Stats */}
                            <div className="flex items-center gap-4">
                              <div className="text-right">
                                <div
                                  className="flex items-center gap-1 justify-end"
                                  style={{ color: champ.win_rate > 50 ? colors.accentGreen : colors.accentRed }}
                                >
                                  {champ.win_rate > 50 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                                  <span className="text-lg font-bold">
                                    {champ.win_rate.toFixed(1)}%
                                  </span>
                                </div>
                                <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                                  {champ.wins}W {champ.games_played - champ.wins}L
                                </p>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      </ClickSpark>
                    </GlareHover>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-white/10 space-y-3">
                <p className="text-sm" style={{ color: '#8E8E93' }}>
                  {selectedChampion
                    ? `Selected: ${selectedChampion.champion_name}`
                    : 'Select a champion to continue'}
                </p>

                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <ClickSpark inline={true}>
                    <button
                      onClick={handleConfirm}
                      disabled={!selectedChampion}
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
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
