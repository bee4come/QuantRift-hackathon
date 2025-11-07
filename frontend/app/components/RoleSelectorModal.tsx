'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Shield, TreePine, Swords, Target, Heart } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import GlareHover from './ui/GlareHover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import { useModal } from '../context/ModalContext';

type Role = 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT';

interface RoleStats {
  role: Role;
  games: number;
  wins: number;
  win_rate: number;
  avg_kda: number;
}

interface RoleOption {
  value: Role;
  label: string;
  emoji: string;
  icon: any;
  color: string;
  description: string;
}

const ROLE_OPTIONS: RoleOption[] = [
  {
    value: 'TOP',
    label: 'Top Lane',
    emoji: '🛡️',
    icon: Shield,
    color: '#FF6B6B',
    description: 'Solo laner, tanks & fighters'
  },
  {
    value: 'JUNGLE',
    label: 'Jungle',
    emoji: '🌲',
    icon: TreePine,
    color: '#51CF66',
    description: 'Map control & ganks'
  },
  {
    value: 'MID',
    label: 'Mid Lane',
    emoji: '⚔️',
    icon: Swords,
    color: '#FFD43B',
    description: 'Mages & assassins'
  },
  {
    value: 'ADC',
    label: 'Bot Lane (ADC)',
    emoji: '🏹',
    icon: Target,
    color: '#74C0FC',
    description: 'Marksman carry'
  },
  {
    value: 'SUPPORT',
    label: 'Support',
    emoji: '💚',
    icon: Heart,
    color: '#B197FC',
    description: 'Vision & protection'
  },
];

interface RoleSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (role: Role) => void;
  roleStats: RoleStats[];
  gameName: string;
  tagLine: string;
}

export default function RoleSelectorModal({
  isOpen,
  onClose,
  onSelect,
  roleStats,
  gameName,
  tagLine
}: RoleSelectorModalProps) {
  const colors = useAdaptiveColors();
  const { setIsModalOpen } = useModal();
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen, setIsModalOpen]);

  // Get stats for a role (with BOTTOM → ADC mapping)
  const getRoleStats = (role: Role) => {
    // Handle BOTTOM → ADC mapping
    if (role === 'ADC') {
      const bottomStats = roleStats.find(stat => (stat.role as string) === 'BOTTOM');
      if (bottomStats) {
        return { ...bottomStats, role: 'ADC' as Role };
      }
    }
    return roleStats.find(stat => stat.role === role);
  };

  // Get most played role (with BOTTOM → ADC mapping)
  const mostPlayedRole = roleStats.length > 0
    ? (() => {
        const mostPlayed = roleStats.reduce((prev, current) =>
          (current.games > prev.games) ? current : prev
        );
        // Map BOTTOM → ADC for display
        if ((mostPlayed.role as string) === 'BOTTOM') {
          return { ...mostPlayed, role: 'ADC' as Role };
        }
        return mostPlayed;
      })()
    : null;

  const handleConfirm = () => {
    if (selectedRole) {
      onSelect(selectedRole);
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
                    text="🎯 Role Specialization Analysis"
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-2" style={{ color: '#8E8E93' }}>
                    Analyze your performance in a specific role
                  </p>
                  {mostPlayedRole && (
                    <p className="text-xs mt-1" style={{ color: colors.accentBlue }}>
                      Most played: {mostPlayedRole.role} ({mostPlayedRole.games} games)
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

              {/* Role Cards */}
              <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {ROLE_OPTIONS.map((role) => {
                  const stats = getRoleStats(role.value);
                  const Icon = role.icon;
                  const isMostPlayed = mostPlayedRole?.role === role.value;

                  return (
                    <GlareHover
                      key={role.value}
                      width="100%"
                      height="auto"
                      background="transparent"
                      borderRadius="12px"
                    >
                      <ClickSpark>
                        <motion.div
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => setSelectedRole(role.value)}
                          className="fluid-glass-dark p-5 rounded-xl cursor-pointer transition-all border-2"
                          style={{
                            borderColor: selectedRole === role.value ? colors.accentBlue : 'transparent'
                          }}
                        >
                          <div className="flex items-center justify-between">
                            {/* Role Info */}
                            <div className="flex items-center gap-4">
                              <div
                                className="w-14 h-14 rounded-xl flex items-center justify-center"
                                style={{
                                  backgroundColor: `${role.color}30`,
                                  border: `2px solid ${role.color}60`
                                }}
                              >
                                <Icon className="w-7 h-7" style={{ color: role.color }} />
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-2xl">{role.emoji}</span>
                                  <ShinyText
                                    text={role.label}
                                    speed={2}
                                    className="text-lg font-semibold"
                                  />
                                  {selectedRole === role.value && (
                                    <span style={{ color: colors.accentBlue }}>✓</span>
                                  )}
                                  {isMostPlayed && (
                                    <span className="text-xs px-2 py-1 rounded-full" style={{
                                      backgroundColor: `${colors.accentGreen}30`,
                                      color: colors.accentGreen
                                    }}>
                                      Most Played
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm mt-1" style={{ color: '#8E8E93' }}>
                                  {role.description}
                                </p>
                              </div>
                            </div>

                            {/* Stats */}
                            {stats && stats.games > 0 ? (
                              <div className="text-right">
                                <div className="text-2xl font-bold" style={{
                                  color: stats.win_rate > 50 ? colors.accentGreen : colors.accentRed
                                }}>
                                  {stats.win_rate.toFixed(1)}%
                                </div>
                                <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                                  {stats.games} games • {stats.avg_kda.toFixed(2)} KDA
                                </p>
                                <p className="text-xs" style={{ color: '#8E8E93' }}>
                                  {stats.wins}W {stats.games - stats.wins}L
                                </p>
                              </div>
                            ) : (
                              <div className="text-right">
                                <p className="text-sm" style={{ color: '#8E8E93' }}>
                                  No games
                                </p>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      </ClickSpark>
                    </GlareHover>
                  );
                })}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between gap-3 p-6 border-t border-white/10">
                <p className="text-sm" style={{ color: '#8E8E93' }}>
                  {selectedRole
                    ? `Selected: ${ROLE_OPTIONS.find(r => r.value === selectedRole)?.emoji} ${selectedRole}`
                    : 'Select a role to continue'}
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
                      disabled={!selectedRole}
                      className="px-6 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.2)',
                        borderColor: 'rgba(10, 132, 255, 0.4)',
                        color: '#5AC8FA'
                      }}
                    >
                      <ShinyText text="Analyze Role →" speed={2} />
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
