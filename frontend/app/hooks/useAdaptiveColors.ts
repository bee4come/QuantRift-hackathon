'use client';

import { useTimeOfDay, isLightBackground } from './useTimeOfDay';
import { useServerContext } from '../context/ServerContext';

export function useAdaptiveColors() {
  const { currentTimezone } = useServerContext();
  const timeOfDay = useTimeOfDay(currentTimezone);
  
  const isLight = isLightBackground[timeOfDay];
  
  return {
    // Text colors
    textPrimary: isLight ? '#0f172a' : '#f8fafc',
    textSecondary: isLight ? '#475569' : '#cbd5e1',
    textMuted: isLight ? '#64748b' : '#94a3b8',
    
    // Accent colors
    accentBlue: isLight ? '#0ea5e9' : '#38bdf8',
    accentGreen: isLight ? '#10b981' : '#34d399',
    accentRed: isLight ? '#ef4444' : '#f87171',
    accentYellow: isLight ? '#f59e0b' : '#fbbf24',
    accentPurple: isLight ? '#8b5cf6' : '#a78bfa',
    
    // UI elements
    borderColor: isLight ? 'rgba(15, 23, 42, 0.1)' : 'rgba(248, 250, 252, 0.1)',
    glassBg: isLight ? 'rgba(255, 255, 255, 0.7)' : 'rgba(15, 23, 42, 0.7)',
    glassBorder: isLight ? 'rgba(15, 23, 42, 0.15)' : 'rgba(248, 250, 252, 0.15)',
    
    // Status
    isLight,
  };
}

