'use client';

import { useState, useEffect } from 'react';

export function useAdaptiveColors() {
  const [isLight, setIsLight] = useState(() => {
    // Initialize with proper theme check
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('light');
    }
    return false;
  });
  
  useEffect(() => {
    // Check current theme
    const checkTheme = () => {
      const isLightMode = document.documentElement.classList.contains('light');
      setIsLight(isLightMode);
    };
    
    // Initial check
    checkTheme();
    
    // Watch for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
    
    return () => observer.disconnect();
  }, []);
  
  return {
    // Text colors - white for both modes
    textPrimary: '#F5F5F7',
    textSecondary: '#E8E8ED',
    textMuted: '#AEAEB2',
    
    // Accent colors
    accentBlue: isLight ? '#007AFF' : '#0A84FF',
    accentGreen: isLight ? '#34C759' : '#32D74B',
    accentRed: isLight ? '#FF3B30' : '#FF453A',
    accentYellow: isLight ? '#FFCC00' : '#FFD60A',
    accentPurple: isLight ? '#AF52DE' : '#BF5AF2',
    
    // UI elements
    borderColor: 'rgba(255, 255, 255, 0.1)',
    glassBg: isLight ? 'rgba(255, 255, 255, 0.1)' : 'rgba(28, 28, 30, 0.7)',
    glassBorder: 'rgba(255, 255, 255, 0.15)',
    
    // Status
    isLight,
  };
}

