'use client';

import { useState, useEffect } from 'react';

export type TimeOfDay = 'midnight' | 'before-dawn' | 'dawn' | 'sunrise' | 'morning' | 'late-morning' | 'noon' | 'early-afternoon' | 'late-afternoon' | 'sunset' | 'early-evening' | 'night';

interface TimeGradient {
  gradient: string;
  ambientLight: string;
}

// Determine if the background is light or dark for each time period
export const isLightBackground: Record<TimeOfDay, boolean> = {
  midnight: false,
  'before-dawn': false,
  dawn: false,
  sunrise: false,
  morning: false,
  'late-morning': false,
  noon: false,
  'early-afternoon': false,
  'late-afternoon': false,
  sunset: false,
  'early-evening': false,
  night: false,
};

export const timeGradients: Record<TimeOfDay, TimeGradient> = {
  midnight: {
    gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)',
    ambientLight: 'radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%)',
  },
  'before-dawn': {
    gradient: 'linear-gradient(135deg, #000000 0%, #0A0A0C 30%, #1C1C1E 70%, #0A0A0C 100%)',
    ambientLight: 'radial-gradient(circle at 20% 50%, rgba(10, 132, 255, 0.06) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(191, 90, 242, 0.05) 0%, transparent 50%)',
  },
  dawn: {
    gradient: 'linear-gradient(135deg, #000000 0%, #0A0A0C 30%, #1C1C1E 70%, #0A0A0C 100%)',
    ambientLight: 'radial-gradient(circle at 20% 50%, rgba(10, 132, 255, 0.06) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(191, 90, 242, 0.05) 0%, transparent 50%)',
  },
  sunrise: {
    gradient: 'linear-gradient(135deg, #334155 0%, #475569 40%, #64748b 70%, #94a3b8 100%)',
    ambientLight: 'radial-gradient(circle at 30% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
  },
  morning: {
    gradient: 'linear-gradient(135deg, #334155 0%, #475569 40%, #64748b 70%, #94a3b8 100%)',
    ambientLight: 'radial-gradient(circle at 30% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
  },
  'late-morning': {
    gradient: 'linear-gradient(135deg, #334155 0%, #475569 40%, #64748b 70%, #94a3b8 100%)',
    ambientLight: 'radial-gradient(circle at 30% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
  },
  noon: {
    gradient: 'linear-gradient(135deg, #334155 0%, #475569 40%, #64748b 70%, #94a3b8 100%)',
    ambientLight: 'radial-gradient(circle at 30% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
  },
  'early-afternoon': {
    gradient: 'linear-gradient(135deg, #334155 0%, #475569 40%, #64748b 70%, #94a3b8 100%)',
    ambientLight: 'radial-gradient(circle at 30% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
  },
  'late-afternoon': {
    gradient: 'linear-gradient(135deg, #334155 0%, #475569 40%, #64748b 70%, #94a3b8 100%)',
    ambientLight: 'radial-gradient(circle at 30% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%)',
  },
  sunset: {
    gradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)',
    ambientLight: 'radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%)',
  },
  'early-evening': {
    gradient: 'linear-gradient(135deg, #000000 0%, #0A0A0C 30%, #1C1C1E 70%, #0A0A0C 100%)',
    ambientLight: 'radial-gradient(circle at 20% 50%, rgba(10, 132, 255, 0.06) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(191, 90, 242, 0.05) 0%, transparent 50%)',
  },
  night: {
    gradient: 'linear-gradient(135deg, #000000 0%, #0A0A0C 30%, #1C1C1E 70%, #0A0A0C 100%)',
    ambientLight: 'radial-gradient(circle at 20% 50%, rgba(10, 132, 255, 0.06) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(191, 90, 242, 0.05) 0%, transparent 50%)',
  },
};

function getTimeOfDay(hour: number): TimeOfDay {
  if ((hour >= 23 && hour < 24) || (hour >= 0 && hour < 1)) return 'midnight';
  if (hour >= 1 && hour < 3) return 'before-dawn';
  if (hour >= 3 && hour < 5) return 'dawn';
  if (hour >= 5 && hour < 7) return 'sunrise';
  if (hour >= 7 && hour < 9) return 'morning';
  if (hour >= 9 && hour < 11) return 'late-morning';
  if (hour >= 11 && hour < 13) return 'noon';
  if (hour >= 13 && hour < 15) return 'early-afternoon';
  if (hour >= 15 && hour < 17) return 'late-afternoon';
  if (hour >= 17 && hour < 19) return 'sunset';
  if (hour >= 19 && hour < 21) return 'early-evening';
  if (hour >= 21 && hour < 23) return 'night';
  return 'midnight';
}

export function useTimeOfDay(timezone?: string) {
  const [timeOfDay, setTimeOfDay] = useState<TimeOfDay>('night');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      let hour: number;
      
      if (timezone) {
        // Get hour in the specified timezone
        const formatter = new Intl.DateTimeFormat('en-US', {
          timeZone: timezone,
          hour: 'numeric',
          hour12: false
        });
        hour = parseInt(formatter.format(now));
      } else {
        // Use local hour
        hour = now.getHours();
      }
      
      setTimeOfDay(getTimeOfDay(hour));
    };

    updateTime();
    const interval = setInterval(updateTime, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [timezone]);

  return timeOfDay;
}

