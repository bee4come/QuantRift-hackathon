'use client';

import { useMemo } from 'react';

type ServerStatus = 'online' | 'issues' | 'offline';

export function useServerStatus(_region: string = 'na1'): ServerStatus {
  // For now, always return 'online' status
  // In production, implement a backend proxy to check Riot's status API
  // as direct client-side calls are blocked by CORS
  const status = useMemo<ServerStatus>(() => 'online', []);

  return status;
}

