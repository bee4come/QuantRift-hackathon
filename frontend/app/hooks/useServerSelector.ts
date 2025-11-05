'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';

export interface Server {
  code: string;
  name: string;
  timezone: string;
  offset: number; // UTC offset in hours
}

const SERVERS: readonly Server[] = [
  { code: 'NA1', name: 'North America', timezone: 'America/Los_Angeles', offset: -8 },
  { code: 'EUW1', name: 'EU West', timezone: 'Europe/London', offset: 0 },
  { code: 'EUN1', name: 'EU Nordic & East', timezone: 'Europe/Warsaw', offset: 1 },
  { code: 'KR1', name: 'Korea', timezone: 'Asia/Seoul', offset: 9 },
  { code: 'BR1', name: 'Brazil', timezone: 'America/Sao_Paulo', offset: -3 },
  { code: 'JP1', name: 'Japan', timezone: 'Asia/Tokyo', offset: 9 },
  { code: 'LA1', name: 'Latin America North', timezone: 'America/Mexico_City', offset: -6 },
  { code: 'LA2', name: 'Latin America South', timezone: 'America/Santiago', offset: -4 },
  { code: 'OC1', name: 'Oceania', timezone: 'Australia/Sydney', offset: 11 },
  { code: 'TR1', name: 'Turkey', timezone: 'Europe/Istanbul', offset: 3 },
  { code: 'RU', name: 'Russia', timezone: 'Europe/Moscow', offset: 3 },
  { code: 'PH2', name: 'Philippines', timezone: 'Asia/Manila', offset: 8 },
  { code: 'SG2', name: 'Singapore', timezone: 'Asia/Singapore', offset: 8 },
  { code: 'TH2', name: 'Thailand', timezone: 'Asia/Bangkok', offset: 7 },
  { code: 'TW2', name: 'Taiwan', timezone: 'Asia/Taipei', offset: 8 },
  { code: 'VN2', name: 'Vietnam', timezone: 'Asia/Ho_Chi_Minh', offset: 7 },
] as const;

export const servers = SERVERS as unknown as Server[];

// Detect best server based on user's timezone
function detectServerFromTimezone(): Server {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  
  // Map timezones to servers
  if (timezone.includes('America')) {
    if (timezone.includes('Sao_Paulo') || timezone.includes('Buenos_Aires')) return servers.find(s => s.code === 'BR1')!;
    if (timezone.includes('Mexico') || timezone.includes('Guatemala')) return servers.find(s => s.code === 'LA1')!;
    if (timezone.includes('Santiago') || timezone.includes('Lima')) return servers.find(s => s.code === 'LA2')!;
    return servers.find(s => s.code === 'NA1')!; // Default to NA
  }
  
  if (timezone.includes('Europe')) {
    if (timezone.includes('Istanbul')) return servers.find(s => s.code === 'TR1')!;
    if (timezone.includes('Moscow')) return servers.find(s => s.code === 'RU')!;
    if (timezone.includes('Warsaw') || timezone.includes('Prague')) return servers.find(s => s.code === 'EUN1')!;
    return servers.find(s => s.code === 'EUW1')!; // Default to EUW
  }
  
  if (timezone.includes('Asia')) {
    if (timezone.includes('Seoul')) return servers.find(s => s.code === 'KR1')!;
    if (timezone.includes('Tokyo')) return servers.find(s => s.code === 'JP1')!;
    if (timezone.includes('Manila')) return servers.find(s => s.code === 'PH2')!;
    if (timezone.includes('Singapore')) return servers.find(s => s.code === 'SG2')!;
    if (timezone.includes('Bangkok')) return servers.find(s => s.code === 'TH2')!;
    if (timezone.includes('Taipei')) return servers.find(s => s.code === 'TW2')!;
    if (timezone.includes('Ho_Chi_Minh')) return servers.find(s => s.code === 'VN2')!;
  }
  
  if (timezone.includes('Australia') || timezone.includes('Pacific')) {
    return servers.find(s => s.code === 'OC1')!;
  }
  
  return servers[0]; // Default to NA
}

export function useServerSelector() {
  // Always start with the default server to ensure consistent SSR/client rendering
  const [selectedServer, setSelectedServer] = useState<Server>(servers[0]);
  const [customTimezone, setCustomTimezone] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [showLocationModal, setShowLocationModal] = useState(false);

  // Load saved server from localStorage after mount to avoid hydration mismatch
  useEffect(() => {
    if (!isInitialized) {
      const saved = localStorage.getItem('selectedServer');
      const locationPermission = localStorage.getItem('locationPermission');
      
      if (saved) {
        // User has already selected a server
        const server = servers.find(s => s.code === saved);
        if (server) {
          setSelectedServer(server);
        }
      } else if (!locationPermission) {
        // First time user - show location permission modal
        setShowLocationModal(true);
      } else if (locationPermission === 'allowed') {
        // User previously allowed - auto-detect server
        const detectedServer = detectServerFromTimezone();
        setSelectedServer(detectedServer);
        localStorage.setItem('selectedServer', detectedServer.code);
      }
      // If locationPermission === 'denied', keep default (NA1)
      
      setIsInitialized(true);
    }
  }, [isInitialized]);

  const currentTimezone = customTimezone || selectedServer.timezone;

  // Calculate time difference between current server and user's local time
  const timeDiff = useMemo(() => {
    const now = new Date();
    const localOffset = -now.getTimezoneOffset() / 60; // Convert to hours
    const serverOffset = selectedServer.offset;
    return serverOffset - localOffset;
  }, [selectedServer.offset]);

  const selectServer = useCallback((serverCode: string) => {
    const server = servers.find(s => s.code === serverCode);
    if (server) {
      setSelectedServer(server);
      setCustomTimezone(null); // Reset custom timezone when changing servers
      if (typeof window !== 'undefined') {
        localStorage.setItem('selectedServer', serverCode);
      }
    }
  }, []);

  const setTimezone = useCallback((timezone: string) => {
    setCustomTimezone(timezone);
  }, []);

  const handleLocationAllow = useCallback(() => {
    const detectedServer = detectServerFromTimezone();
    setSelectedServer(detectedServer);
    localStorage.setItem('selectedServer', detectedServer.code);
    localStorage.setItem('locationPermission', 'allowed');
    setShowLocationModal(false);
  }, []);

  const handleLocationDeny = useCallback(() => {
    localStorage.setItem('locationPermission', 'denied');
    localStorage.setItem('selectedServer', servers[0].code);
    setShowLocationModal(false);
  }, []);

  return {
    selectedServer,
    servers,
    selectServer,
    currentTimezone,
    setTimezone,
    timeDiff,
    showLocationModal,
    handleLocationAllow,
    handleLocationDeny,
  };
}

