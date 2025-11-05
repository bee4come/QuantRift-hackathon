'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface Champion {
  id: string;
  key: string;
  name: string;
  title: string;
  blurb: string;
  info: {
    attack: number;
    defense: number;
    magic: number;
    difficulty: number;
  };
  image: {
    full: string;
    sprite: string;
    group: string;
    x: number;
    y: number;
    w: number;
    h: number;
  };
  tags: string[];
  partype: string;
  stats: Record<string, number>;
}

interface Item {
  name: string;
  description: string;
  plaintext: string;
  gold: {
    base: number;
    total: number;
    sell: number;
    purchasable: boolean;
  };
  tags: string[];
  stats: Record<string, number>;
  image: {
    full: string;
    sprite: string;
    group: string;
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

interface RuneSlot {
  runes: Array<{
    id: number;
    key: string;
    icon: string;
    name: string;
    shortDesc: string;
    longDesc: string;
  }>;
}

interface RuneTree {
  id: number;
  key: string;
  icon: string;
  name: string;
  slots: RuneSlot[];
}

interface DDragonContextType {
  champions: Record<string, Champion> | null;
  items: Record<string, Item> | null;
  runes: RuneTree[] | null;
  loading: boolean;
  error: string | null;
  getChampionById: (id: string) => Champion | undefined;
  getChampionByKey: (key: string) => Champion | undefined;
  getItemById: (id: string) => Item | undefined;
  getRuneById: (id: number) => RuneTree | undefined;
}

const DDragonContext = createContext<DDragonContextType | undefined>(undefined);

interface DDragonProviderProps {
  children: ReactNode;
  useBackendProxy?: boolean; // Use backend proxy or direct DDragon CDN
}

export function DDragonProvider({
  children,
  useBackendProxy = false
}: DDragonProviderProps) {
  const [champions, setChampions] = useState<Record<string, Champion> | null>(null);
  const [items, setItems] = useState<Record<string, Item> | null>(null);
  const [runes, setRunes] = useState<RuneTree[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDDragonData();
  }, [useBackendProxy]);

  const loadDDragonData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (useBackendProxy) {
        // Use backend proxy APIs
        await Promise.all([
          loadChampionsFromBackend(),
          loadItemsFromBackend(),
          loadRunesFromBackend(),
        ]);
      } else {
        // Use direct DDragon CDN (recommended)
        const version = '15.1.1'; // Update this periodically
        await Promise.all([
          loadChampionsFromCDN(version),
          loadItemsFromCDN(version),
          loadRunesFromCDN(version),
        ]);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load DDragon data';
      setError(errorMessage);
      console.error('DDragon loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Backend proxy methods
  const loadChampionsFromBackend = async () => {
    const response = await fetch('http://localhost:8000/api/v1/static/champions');
    const data = await response.json();
    if (data.success) {
      setChampions(data.data);
    } else {
      throw new Error('Failed to load champions from backend');
    }
  };

  const loadItemsFromBackend = async () => {
    const response = await fetch('http://localhost:8000/api/v1/static/items');
    const data = await response.json();
    if (data.success) {
      setItems(data.data);
    } else {
      throw new Error('Failed to load items from backend');
    }
  };

  const loadRunesFromBackend = async () => {
    const response = await fetch('http://localhost:8000/api/v1/static/runes');
    const data = await response.json();
    if (data.success) {
      setRunes(data.data);
    } else {
      throw new Error('Failed to load runes from backend');
    }
  };

  // Direct CDN methods (recommended)
  const loadChampionsFromCDN = async (version: string) => {
    const response = await fetch(
      `https://ddragon.leagueoflegends.com/cdn/${version}/data/en_US/champion.json`
    );
    const data = await response.json();
    setChampions(data.data);
  };

  const loadItemsFromCDN = async (version: string) => {
    const response = await fetch(
      `https://ddragon.leagueoflegends.com/cdn/${version}/data/en_US/item.json`
    );
    const data = await response.json();
    setItems(data.data);
  };

  const loadRunesFromCDN = async (version: string) => {
    const response = await fetch(
      `https://ddragon.leagueoflegends.com/cdn/${version}/data/en_US/runesReforged.json`
    );
    const data = await response.json();
    setRunes(data);
  };

  // Helper methods
  const getChampionById = (id: string): Champion | undefined => {
    return champions?.[id];
  };

  const getChampionByKey = (key: string): Champion | undefined => {
    if (!champions) return undefined;
    return Object.values(champions).find((champ) => champ.key === key);
  };

  const getItemById = (id: string): Item | undefined => {
    return items?.[id];
  };

  const getRuneById = (id: number): RuneTree | undefined => {
    return runes?.find((rune) => rune.id === id);
  };

  const value: DDragonContextType = {
    champions,
    items,
    runes,
    loading,
    error,
    getChampionById,
    getChampionByKey,
    getItemById,
    getRuneById,
  };

  return (
    <DDragonContext.Provider value={value}>
      {children}
    </DDragonContext.Provider>
  );
}

export function useDDragon(): DDragonContextType {
  const context = useContext(DDragonContext);
  if (context === undefined) {
    throw new Error('useDDragon must be used within a DDragonProvider');
  }
  return context;
}
