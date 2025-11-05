'use client';

import { createContext, useContext, ReactNode } from 'react';
import { useServerSelector, Server } from '../hooks/useServerSelector';

interface ServerContextType {
  selectedServer: Server;
  servers: Server[];
  selectServer: (serverCode: string) => void;
  currentTimezone: string;
  setTimezone: (timezone: string) => void;
  timeDiff: number;
  showLocationModal: boolean;
  handleLocationAllow: () => void;
  handleLocationDeny: () => void;
}

const ServerContext = createContext<ServerContextType | undefined>(undefined);

export function ServerProvider({ children }: { children: ReactNode }) {
  const serverSelector = useServerSelector();

  return (
    <ServerContext.Provider value={serverSelector}>
      {children}
    </ServerContext.Provider>
  );
}

export function useServerContext() {
  const context = useContext(ServerContext);
  if (context === undefined) {
    throw new Error('useServerContext must be used within a ServerProvider');
  }
  return context;
}

