export interface Champion {
  name: string;
  gamesPlayed: number;
  winRate: number;
}

export interface Match {
  result: 'win' | 'loss';
  champion: string;
  kda: string;
  timestamp: string;
}

export interface Player {
  username: string;
  tier: string;
  rank: string;
  lp: number;
  winRate: number;
  totalGames: number;
  wins: number;
  losses: number;
  favoriteChampions: Champion[];
  recentMatches: Match[];
}

// Mock player database
export const mockPlayerDatabase: Record<string, Player> = {
  'Faker': {
    username: 'Faker',
    tier: 'Challenger',
    rank: 'I',
    lp: 1247,
    winRate: 68.5,
    totalGames: 324,
    wins: 222,
    losses: 102,
    favoriteChampions: [
      { name: 'Azir', gamesPlayed: 45, winRate: 73.3 },
      { name: 'LeBlanc', gamesPlayed: 38, winRate: 71.1 },
      { name: 'Orianna', gamesPlayed: 32, winRate: 68.8 },
    ],
    recentMatches: [
      { result: 'win', champion: 'Azir', kda: '8/2/12', timestamp: '2 hours ago' },
      { result: 'win', champion: 'LeBlanc', kda: '12/3/8', timestamp: '5 hours ago' },
      { result: 'loss', champion: 'Orianna', kda: '4/5/9', timestamp: '1 day ago' },
    ],
  },
  'Doublelift': {
    username: 'Doublelift',
    tier: 'Grandmaster',
    rank: 'I',
    lp: 892,
    winRate: 64.2,
    totalGames: 287,
    wins: 184,
    losses: 103,
    favoriteChampions: [
      { name: 'Jinx', gamesPlayed: 52, winRate: 69.2 },
      { name: 'Caitlyn', gamesPlayed: 48, winRate: 66.7 },
      { name: 'Ezreal', gamesPlayed: 41, winRate: 63.4 },
    ],
    recentMatches: [
      { result: 'win', champion: 'Jinx', kda: '14/1/7', timestamp: '1 hour ago' },
      { result: 'win', champion: 'Caitlyn', kda: '9/3/11', timestamp: '4 hours ago' },
      { result: 'win', champion: 'Ezreal', kda: '11/2/9', timestamp: '6 hours ago' },
    ],
  },
  'TheShy': {
    username: 'TheShy',
    tier: 'Challenger',
    rank: 'I',
    lp: 1089,
    winRate: 66.8,
    totalGames: 256,
    wins: 171,
    losses: 85,
    favoriteChampions: [
      { name: 'Fiora', gamesPlayed: 38, winRate: 71.1 },
      { name: 'Jayce', gamesPlayed: 35, winRate: 68.6 },
      { name: 'Camille', gamesPlayed: 29, winRate: 65.5 },
    ],
    recentMatches: [
      { result: 'win', champion: 'Fiora', kda: '7/1/4', timestamp: '3 hours ago' },
      { result: 'loss', champion: 'Jayce', kda: '5/4/6', timestamp: '7 hours ago' },
      { result: 'win', champion: 'Camille', kda: '9/2/8', timestamp: '12 hours ago' },
    ],
  },
  'Caps': {
    username: 'Caps',
    tier: 'Grandmaster',
    rank: 'I',
    lp: 945,
    winRate: 62.4,
    totalGames: 309,
    wins: 193,
    losses: 116,
    favoriteChampions: [
      { name: 'Sylas', gamesPlayed: 44, winRate: 70.5 },
      { name: 'Akali', gamesPlayed: 39, winRate: 64.1 },
      { name: 'Yasuo', gamesPlayed: 36, winRate: 61.1 },
    ],
    recentMatches: [
      { result: 'win', champion: 'Sylas', kda: '10/3/14', timestamp: '30 minutes ago' },
      { result: 'win', champion: 'Akali', kda: '13/4/7', timestamp: '2 hours ago' },
      { result: 'loss', champion: 'Yasuo', kda: '6/7/9', timestamp: '5 hours ago' },
    ],
  },
  'Rekkles': {
    username: 'Rekkles',
    tier: 'Master',
    rank: 'I',
    lp: 678,
    winRate: 59.8,
    totalGames: 294,
    wins: 176,
    losses: 118,
    favoriteChampions: [
      { name: 'Jhin', gamesPlayed: 56, winRate: 64.3 },
      { name: 'Kai\'Sa', gamesPlayed: 47, winRate: 61.7 },
      { name: 'Aphelios', gamesPlayed: 38, winRate: 57.9 },
    ],
    recentMatches: [
      { result: 'loss', champion: 'Jhin', kda: '7/4/8', timestamp: '1 hour ago' },
      { result: 'win', champion: 'Kai\'Sa', kda: '11/2/6', timestamp: '4 hours ago' },
      { result: 'win', champion: 'Jhin', kda: '9/3/12', timestamp: '8 hours ago' },
    ],
  },
};

export function getPlayerByUsername(username: string): Player | null {
  const player = mockPlayerDatabase[username];
  return player || null;
}

export function getAllPlayernames(): string[] {
  return Object.keys(mockPlayerDatabase);
}

