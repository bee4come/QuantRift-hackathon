'use client';

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Trophy, Clock } from 'lucide-react';

interface MatchInfo {
  id: number;
  name: string;
  status: string;
  homeScore: number;
  awayScore: number;
  scheduledAt: string;
  league: string;
  leagueName?: string;
  tournamentName?: string;
  numberOfGames?: number;
}

const GRAPHQL_ENDPOINT = 'https://esports.op.gg/matches/graphql';

const UPCOMING_MATCHES_QUERY = `
  query MCPListUpcomingMatches {
    upcomingMatches {
      id
      name
      status
      awayScore
      homeScore
      scheduledAt
      numberOfGames
      tournament {
        serie {
          league {
            shortName
          }
        }
      }
    }
  }
`;

async function fetchMatches(): Promise<MatchInfo[]> {
  try {
    const response = await fetch(GRAPHQL_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'QuantRift-Esports',
      },
      body: JSON.stringify({
        query: UPCOMING_MATCHES_QUERY,
      }),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    if (data.errors) {
      throw new Error(`GraphQL error: ${JSON.stringify(data.errors)}`);
    }

    const matches = (data.data.upcomingMatches || []).map((match: any): MatchInfo => {
      const league = match.tournament?.serie?.league || {};
      return {
        id: match.id,
        name: match.name,
        status: match.status?.toUpperCase() || 'SCHEDULED',
        awayScore: match.awayScore || 0,
        homeScore: match.homeScore || 0,
        scheduledAt: match.scheduledAt,
        numberOfGames: match.numberOfGames,
        league: league.shortName || 'Unknown',
        leagueName: league.name,
        tournamentName: match.tournament?.name,
      };
    });

    return matches.sort((a: MatchInfo, b: MatchInfo) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime());
  } catch (error) {
    console.error('Error fetching esports matches:', error);
    return [];
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'LIVE':
      return '#FF453A';
    case 'SCHEDULED':
      return '#32D74B';
    case 'FINISHED':
      return '#8E8E93';
    default:
      return '#5AC8FA';
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'LIVE':
      return '🔴 LIVE';
    case 'SCHEDULED':
      return 'UPCOMING';
    case 'FINISHED':
      return 'FINISHED';
    case 'NOT_STARTED':
      return 'NOT STARTED';
    default:
      return status.replace(/_/g, ' ');
  }
};

const formatMatchTime = (scheduledAt: string) => {
  try {
    const date = new Date(scheduledAt);
    const timeString = date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      timeZoneName: 'short'
    });
    return timeString;
  } catch (error) {
    return new Date(scheduledAt).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  }
};

export default function EsportsBanner() {
  const [matches, setMatches] = useState<MatchInfo[]>([]);
  const pathname = usePathname();
  
  // Hide banner on player profile pages (after search)
  const isPlayerPage = pathname?.startsWith('/player/');
  
  useEffect(() => {
    const loadMatches = async () => {
      const upcomingMatches = await fetchMatches();
      // Get first 10 upcoming matches for the banner
      setMatches(upcomingMatches.slice(0, 10));
    };

    loadMatches();
    // Refresh every 5 minutes
    const interval = setInterval(loadMatches, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Don't show banner on player profile pages or if no matches
  if (isPlayerPage || matches.length === 0) {
    return null;
  }

  // Duplicate matches multiple times for seamless infinite scroll
  const duplicatedMatches = [...matches, ...matches, ...matches, ...matches, ...matches, ...matches];

  return (
    <div 
      className="w-full overflow-hidden py-2"
      style={{
        backgroundColor: 'rgba(0, 0, 0, 0.3)',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      }}
    >
      <style jsx>{`
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(-50%);
          }
        }
        
        .scrolling-banner {
          display: flex;
          animation: scroll 30s linear infinite;
          width: max-content;
        }
        
        .scrolling-banner:hover {
          animation-play-state: paused;
        }
      `}</style>
      
      <div className="scrolling-banner">
        {duplicatedMatches.map((match, index) => (
          <a
            key={`${match.id}-${index}`}
            href={`https://esports.op.gg/matches/${match.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-3 px-6 py-1.5 border-r transition-all hover:bg-white/5"
            style={{
              borderColor: 'rgba(255, 255, 255, 0.1)',
              whiteSpace: 'nowrap',
            }}
          >
            {/* Trophy Icon */}
            <Trophy className="w-4 h-4 flex-shrink-0" style={{ color: '#FFD60A' }} />
            
            {/* Status Badge */}
            <span
              className="px-2 py-0.5 rounded text-xs font-bold flex-shrink-0"
              style={{
                backgroundColor: `${getStatusColor(match.status)}20`,
                color: getStatusColor(match.status),
                border: `1px solid ${getStatusColor(match.status)}40`,
              }}
            >
              {getStatusText(match.status)}
            </span>
            
            {/* League */}
            <span 
              className="text-xs font-semibold flex-shrink-0"
              style={{ color: '#0A84FF' }}
            >
              {match.league}
            </span>
            
            {/* Match Name */}
            <span 
              className="text-sm font-bold flex-shrink-0"
              style={{ color: '#F5F5F7' }}
            >
              {match.name}
            </span>
            
            {/* Score (if live or finished) */}
            {(match.status === 'LIVE' || match.status === 'FINISHED') && (
              <span 
                className="text-sm font-bold flex-shrink-0"
                style={{ color: '#32D74B' }}
              >
                {match.homeScore} - {match.awayScore}
              </span>
            )}
            
            {/* Time */}
            <div className="flex items-center gap-1 flex-shrink-0">
              <Clock className="w-3 h-3" style={{ color: '#8E8E93' }} />
              <span className="text-xs" style={{ color: '#8E8E93' }}>
                {formatMatchTime(match.scheduledAt)}
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

