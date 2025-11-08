'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import Image from 'next/image';
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
  imageUrl: string;
  description: string;
}

const ROLE_OPTIONS: RoleOption[] = [
  {
    value: 'TOP',
    label: 'Top Lane',
    imageUrl: 'https://s-lol-web.op.gg/images/icon/icon-position-top.svg',
    description: 'Solo laner, tanks & fighters'
  },
  {
    value: 'JUNGLE',
    label: 'Jungle',
    imageUrl: 'https://s-lol-web.op.gg/images/icon/icon-position-jng.svg',
    description: 'Map control & ganks'
  },
  {
    value: 'MID',
    label: 'Mid Lane',
    imageUrl: 'https://s-lol-web.op.gg/images/icon/icon-position-mid.svg',
    description: 'Mages & assassins'
  },
  {
    value: 'ADC',
    label: 'Bot Lane (ADC)',
    imageUrl: 'https://s-lol-web.op.gg/images/icon/icon-position-bot.svg',
    description: 'Marksman carry'
  },
  {
    value: 'SUPPORT',
    label: 'Support',
    imageUrl: 'https://s-lol-web.op.gg/images/icon/icon-position-sup.svg',
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
  selectedRankType?: number | null;
  selectedTimeRange?: string;
}

export default function RoleSelectorModal({
  isOpen,
  onClose,
  onSelect,
  roleStats: initialRoleStats,
  gameName,
  tagLine,
  selectedRankType,
  selectedTimeRange
}: RoleSelectorModalProps) {
  const colors = useAdaptiveColors();
  const { setIsModalOpen } = useModal();
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [roleStats, setRoleStats] = useState<RoleStats[]>(initialRoleStats || []);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen, setIsModalOpen]);

  // Fetch filtered role stats when modal opens or filters change
  useEffect(() => {
    if (isOpen) {
      // Always fetch filtered stats when modal opens, even if filters are not set
      // This ensures we get the correct data based on current filters
      const fetchFilteredRoleStats = async () => {
        try {
          setLoading(true);
          // Clear role stats immediately when filters change to avoid showing stale data
          setRoleStats([]);
          
          const params = new URLSearchParams();
          if (selectedTimeRange) {
            params.append('time_range', selectedTimeRange);
          }
          if (selectedRankType !== null && selectedRankType !== undefined) {
            params.append('queue_id', selectedRankType.toString());
          }
          
          const response = await fetch(`/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/role-stats?${params.toString()}`);
          if (response.ok) {
            const data = await response.json();
            console.log(`[RoleSelectorModal] Fetched role stats:`, data);
            if (data.success && data.role_stats && data.role_stats.length > 0) {
              const filteredStats = data.role_stats.map((stat: any) => ({
                role: stat.role as 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT',
                games: stat.games || 0,
                wins: stat.wins || 0,
                win_rate: stat.win_rate || 0,
                avg_kda: stat.avg_kda || 0
              }));
              console.log(`[RoleSelectorModal] Setting role stats:`, filteredStats);
              setRoleStats(filteredStats);
            } else {
              // If no data returned, set empty array
              console.log(`[RoleSelectorModal] No role stats in response, setting empty array`);
              setRoleStats([]);
            }
          } else {
            const errorData = await response.json().catch(() => ({}));
            console.error('Failed to fetch filtered role stats:', response.status, errorData);
            // If 404 or no data, set empty array
            if (response.status === 404) {
              console.log(`[RoleSelectorModal] 404 - No data found, setting empty array`);
              setRoleStats([]);
            } else {
              // For other errors, set empty array
              setRoleStats([]);
            }
          }
        } catch (error) {
          console.error('Failed to fetch filtered role stats:', error);
          // Set empty array on error
          setRoleStats([]);
        } finally {
          setLoading(false);
        }
      };
      
      fetchFilteredRoleStats();
    }
  }, [isOpen, selectedRankType, selectedTimeRange, gameName, tagLine]);

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
  // Use useMemo to ensure it recalculates when roleStats changes
  const mostPlayedRole = useMemo(() => {
    if (roleStats.length === 0) {
      return null;
    }
        const mostPlayed = roleStats.reduce((prev, current) =>
          (current.games > prev.games) ? current : prev
        );
        // Map BOTTOM → ADC for display
        if ((mostPlayed.role as string) === 'BOTTOM') {
          return { ...mostPlayed, role: 'ADC' as Role };
        }
        return mostPlayed;
  }, [roleStats]);

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
                    text="Role Specialization Analysis"
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-2" style={{ color: '#8E8E93' }}>
                    Analyze your performance in a specific role
                  </p>
                  {loading ? (
                    <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                      Loading role statistics...
                    </p>
                  ) : mostPlayedRole ? (
                    <div className="mt-1">
                      <p className="text-xs" style={{ color: colors.accentBlue }}>
                      Most played: {mostPlayedRole.role} ({mostPlayedRole.games} games)
                      </p>
                      {(selectedRankType !== undefined || selectedTimeRange) && (
                        <p className="text-xs mt-0.5" style={{ color: '#8E8E93' }}>
                          Filter: {
                            selectedRankType === null || selectedRankType === undefined
                              ? 'Total'
                              : selectedRankType === 420
                              ? 'Rank Solo/Duo'
                              : selectedRankType === 440
                              ? 'Rank Flex'
                              : selectedRankType === 400
                              ? 'Normal'
                              : 'Total'
                          } • {
                            selectedTimeRange === '2024-01-01'
                              ? 'Season 2024'
                              : selectedTimeRange === 'past-365'
                              ? 'Past 365 Days'
                              : 'All Time'
                          }
                        </p>
                      )}
                    </div>
                  ) : roleStats.length === 0 && !loading ? (
                    <div className="mt-1">
                      <p className="text-xs" style={{ color: '#FF453A' }}>
                        No data found for the selected filter
                      </p>
                      {(selectedRankType !== undefined || selectedTimeRange) && (
                        <p className="text-xs mt-0.5" style={{ color: '#8E8E93' }}>
                          Filter: {
                            selectedRankType === null || selectedRankType === undefined
                              ? 'Total'
                              : selectedRankType === 420
                              ? 'Rank Solo/Duo'
                              : selectedRankType === 440
                              ? 'Rank Flex'
                              : selectedRankType === 400
                              ? 'Normal'
                              : 'Total'
                          } • {
                            selectedTimeRange === '2024-01-01'
                              ? 'Season 2024'
                              : selectedTimeRange === 'past-365'
                              ? 'Past 365 Days'
                              : 'All Time'
                          }
                    </p>
                  )}
                    </div>
                  ) : null}
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

              {/* Role Cards */}
              <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <p className="text-sm" style={{ color: '#8E8E93' }}>Loading role statistics...</p>
                  </div>
                ) : roleStats.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12">
                    <p className="text-sm mb-2" style={{ color: '#FF453A' }}>
                      No data found for the selected filter
                    </p>
                    <p className="text-xs" style={{ color: '#8E8E93' }}>
                      Please select a different filter or play some games in this mode
                    </p>
                  </div>
                ) : (
                  ROLE_OPTIONS.map((role) => {
                  const stats = getRoleStats(role.value);
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
                          className="p-5 rounded-xl cursor-pointer transition-all border-2"
                          style={{
                            backgroundColor: 'rgba(48, 48, 52, 0.9)',
                            backdropFilter: 'blur(20px)',
                            borderColor: selectedRole === role.value ? colors.accentBlue : 'rgba(255, 255, 255, 0.1)'
                          }}
                        >
                          <div className="flex items-center justify-between">
                            {/* Role Info */}
                            <div className="flex items-center gap-4">
                              <div
                                className="w-14 h-14 rounded-xl flex items-center justify-center"
                                style={{
                                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                                  border: '2px solid rgba(255, 255, 255, 0.15)'
                                }}
                              >
                                <Image
                                  src={role.imageUrl}
                                  alt={role.label}
                                  width={36}
                                  height={36}
                                  className="opacity-90"
                                />
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
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
                  })
                )}
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-white/10 space-y-3">
                <div className="flex items-center gap-2">
                  {selectedRole ? (
                    <>
                      <span className="text-sm" style={{ color: '#8E8E93' }}>Selected:</span>
                      <Image
                        src={ROLE_OPTIONS.find(r => r.value === selectedRole)?.imageUrl || ''}
                        alt={selectedRole}
                        width={20}
                        height={20}
                        className="opacity-90"
                      />
                      <span className="text-sm font-medium" style={{ color: '#F5F5F7' }}>
                        {ROLE_OPTIONS.find(r => r.value === selectedRole)?.label}
                      </span>
                    </>
                  ) : (
                    <span className="text-sm" style={{ color: '#8E8E93' }}>Select a role to continue</span>
                  )}
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <ClickSpark inline={true}>
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
