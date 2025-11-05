'use client';

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, TrendingUp, TrendingDown } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import GlareHover from './ui/GlareHover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

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

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChampion, setSelectedChampion] = useState<PlayerChampion | null>(null);

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
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div
              className="fluid-glass rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col pointer-events-auto overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <div>
                  <ShinyText
                    text="🏆 Champion Mastery Analysis"
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
                          className={`fluid-glass-dark p-4 rounded-xl cursor-pointer transition-all border-2`}
                          style={{
                            borderColor: selectedChampion?.champion_id === champ.champion_id
                              ? colors.accentBlue
                              : 'transparent'
                          }}
                        >
                          <div className="flex items-center justify-between">
                            {/* Champion Info */}
                            <div className="flex items-center gap-4">
                              <div
                                className="w-12 h-12 rounded-lg bg-cover bg-center"
                                style={{
                                  backgroundImage: `url(https://ddragon.leagueoflegends.com/cdn/15.1.1/img/champion/${champ.champion_name}.png)`,
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
              <div className="flex items-center justify-between gap-3 p-6 border-t border-white/10">
                <p className="text-sm" style={{ color: '#8E8E93' }}>
                  {selectedChampion
                    ? `Selected: ${selectedChampion.champion_name}`
                    : 'Select a champion to continue'}
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
                      disabled={!selectedChampion}
                      className="px-6 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.2)',
                        borderColor: 'rgba(10, 132, 255, 0.4)',
                        color: '#5AC8FA'
                      }}
                    >
                      <ShinyText text="Analyze Champion →" speed={2} />
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
