'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Player } from '../data/mockPlayers';

interface SearchContextType {
  searchedPlayers: Player[];
  isSearched: boolean;
  isProcessing: boolean;
  showReport: boolean;
  addPlayers: (players: Player[]) => void;
  removePlayer: (username: string) => void;
  clearPlayers: () => void;
  startProcessing: () => void;
}

const SearchContext = createContext<SearchContextType | undefined>(undefined);

export function SearchProvider({ children }: { children: ReactNode }) {
  const [searchedPlayers, setSearchedPlayers] = useState<Player[]>([]);
  const [isSearched, setIsSearched] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showReport, setShowReport] = useState(false);

  const addPlayers = (players: Player[]) => {
    setSearchedPlayers(players);
    setIsSearched(true);
  };

  const removePlayer = (username: string) => {
    setSearchedPlayers((prev) => prev.filter((p) => p.username !== username));
  };

  const clearPlayers = () => {
    setSearchedPlayers([]);
    setIsSearched(false);
    setIsProcessing(false);
    setShowReport(false);
  };

  const startProcessing = () => {
    setIsProcessing(true);
    setShowReport(false);
    // Simulate processing time
    setTimeout(() => {
      setIsProcessing(false);
      setShowReport(true);
    }, 3000);
  };

  return (
    <SearchContext.Provider
      value={{
        searchedPlayers,
        isSearched,
        isProcessing,
        showReport,
        addPlayers,
        removePlayer,
        clearPlayers,
        startProcessing,
      }}
    >
      {children}
    </SearchContext.Provider>
  );
}

export function useSearch() {
  const context = useContext(SearchContext);
  if (context === undefined) {
    throw new Error('useSearch must be used within a SearchProvider');
  }
  return context;
}

