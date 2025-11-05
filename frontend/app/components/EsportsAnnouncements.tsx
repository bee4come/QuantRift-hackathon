'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Clock, ExternalLink, Calendar, ChevronDown, ChevronUp, MapPin } from 'lucide-react';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import GlareHover from './ui/GlareHover';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';

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
  venue?: {
    name?: string;
    city?: string;
    country?: string;
  };
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

    // Process upcoming matches
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
        venue: undefined, // Venue data not available in simplified query
      };
    });

    return matches.sort((a: MatchInfo, b: MatchInfo) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime());
  } catch (error) {
    console.error('Error fetching esports matches:', error);
    throw error;
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
      return 'LIVE';
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

const getLocationText = (venue?: { name?: string; city?: string; country?: string }) => {
  if (!venue) return null;
  
  const parts = [];
  if (venue.city) parts.push(venue.city);
  if (venue.country) parts.push(venue.country);
  
  return parts.length > 0 ? parts.join(', ') : null;
};

export default function EsportsAnnouncements() {
  const [matches, setMatches] = useState<MatchInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const colors = useAdaptiveColors();

  useEffect(() => {
    const loadMatches = async () => {
      try {
        const upcomingMatches = await fetchMatches();
        // Show the next 5 upcoming matches
        setMatches(upcomingMatches.slice(0, 5));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load matches');
      } finally {
        setLoading(false);
      }
    };

    loadMatches();
  }, []);

  if (loading) {
    return (
      <GlareHover
        width="100%"
        height="auto"
        background="rgba(0, 0, 0, 0.2)"
        borderRadius="12px"
        borderColor="rgba(255, 255, 255, 0.1)"
        glareColor="#ffffff"
        glareOpacity={0.15}
        glareAngle={-45}
        glareSize={180}
        transitionDuration={450}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fluid-glass rounded-xl p-4 shadow-xl"
        >
        <div className="flex items-center gap-2 mb-4">
          <Trophy className="w-5 h-5" style={{ color: colors.accentBlue }} />
          <ShinyText text="Esports Matches" speed={4} className="text-lg font-bold" />
        </div>
        <div className="flex justify-center py-6">
          <div className="animate-spin rounded-full h-6 w-6 border-4 border-t-4" 
               style={{ borderColor: colors.accentBlue, borderTopColor: 'transparent' }}></div>
        </div>
        </motion.div>
      </GlareHover>
    );
  }

  if (error) {
    return (
      <GlareHover
        width="100%"
        height="auto"
        background="rgba(0, 0, 0, 0.2)"
        borderRadius="12px"
        borderColor="rgba(255, 255, 255, 0.1)"
        glareColor="#ffffff"
        glareOpacity={0.15}
        glareAngle={-45}
        glareSize={180}
        transitionDuration={450}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fluid-glass rounded-xl p-4 shadow-xl"
        >
        <div className="flex items-center gap-2 mb-4">
          <Trophy className="w-5 h-5" style={{ color: colors.accentBlue }} />
          <ShinyText text="Esports Matches" speed={4} className="text-lg font-bold" />
        </div>
        <p className="text-center">
          <ShinyText text="Unable to load esports matches" speed={3} className="text-sm" />
        </p>
        </motion.div>
      </GlareHover>
    );
  }

  return (
    <GlareHover
      width="100%"
      height="auto"
      background="rgba(0, 0, 0, 0.2)"
      borderRadius="12px"
      borderColor="rgba(255, 255, 255, 0.1)"
      glareColor="#ffffff"
      glareOpacity={0.15}
      glareAngle={-45}
      glareSize={180}
      transitionDuration={450}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="fluid-glass rounded-xl p-4 shadow-xl"
      >
             <div className="flex items-center gap-2 mb-4">
               <Trophy className="w-5 h-5" style={{ color: colors.accentBlue }} />
               <h3 className="text-lg font-bold" style={{ color: colors.textPrimary }}>
                 Esports Matches
               </h3>
             </div>

      <div className="space-y-3">
               {/* First match - always visible */}
               {matches.length > 0 && (
                 <motion.a
                   href={`https://esports.op.gg/matches/${matches[0].id}`}
                   target="_blank"
                   rel="noopener noreferrer"
                   initial={{ opacity: 0, x: -20 }}
                   animate={{ opacity: 1, x: 0 }}
                   className="block p-3 rounded-lg border transition-all hover:scale-[1.02] cursor-pointer"
                   style={{
                     backgroundColor: 'rgba(255, 255, 255, 0.05)',
                     borderColor: 'rgba(255, 255, 255, 0.1)',
                   }}
                 >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span
                  className="px-2 py-0.5 rounded text-xs font-bold"
                  style={{
                    backgroundColor: `${getStatusColor(matches[0].status)}20`,
                    color: getStatusColor(matches[0].status),
                    border: `1px solid ${getStatusColor(matches[0].status)}40`,
                    animation: matches[0].status === 'LIVE' ? 'pulse 1.5s ease-in-out infinite' : 'none',
                  }}
                >
                  <ShinyText text={getStatusText(matches[0].status)} speed={2} className="text-xs font-bold" />
                </span>
                <ShinyText text={matches[0].league} speed={2} className="text-xs font-medium" />
              </div>
              <div className="flex items-center gap-1 text-xs" style={{ color: colors.textSecondary }}>
                <Calendar className="w-3 h-3" />
                <ShinyText 
                  text={new Date(matches[0].scheduledAt).toLocaleDateString()} 
                  speed={2} 
                  className="text-xs"
                />
              </div>
            </div>

            <div className="mb-2">
              <ShinyText text={matches[0].name} speed={3} className="font-bold text-lg" />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" style={{ color: colors.textSecondary }} />
                  <span className="text-xs" style={{ color: colors.textSecondary }}>
                    {formatMatchTime(matches[0].scheduledAt)}
                  </span>
                </div>
                       {matches[0].venue && getLocationText(matches[0].venue) && (
                         <div className="flex items-center gap-1">
                           <MapPin className="w-3 h-3" style={{ color: colors.textSecondary }} />
                           <span className="text-xs" style={{ color: colors.textSecondary }}>
                             {getLocationText(matches[0].venue)}
                           </span>
                         </div>
                       )}
              </div>
              
                     {matches[0].status === 'LIVE' || matches[0].status === 'FINISHED' ? (
                       <div className="flex items-center gap-2">
                         <span className="text-sm font-bold" style={{ color: colors.textPrimary }}>
                           {matches[0].homeScore} - {matches[0].awayScore}
                         </span>
                       </div>
                     ) : null}
            </div>
                 </motion.a>
               )}

        {/* Expand/Collapse button */}
        {matches.length > 1 && (
          <ClickSpark
            sparkColor="#FFFFFF"
            sparkSize={8}
            sparkRadius={12}
            sparkCount={6}
            duration={300}
            inline={true}
          >
            <motion.button
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full p-2 rounded-lg border transition-all hover:scale-[1.02] flex items-center justify-center gap-2"
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                color: colors.textSecondary,
              }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <span className="text-xs font-medium">
                {isExpanded ? 'Show Less' : `Show ${matches.length - 1} More Match${matches.length - 1 > 1 ? 'es' : ''}`}
              </span>
              {isExpanded ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </motion.button>
          </ClickSpark>
        )}

        {/* Additional matches - shown when expanded */}
        <AnimatePresence>
          {isExpanded && matches.length > 1 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-3"
            >
                     {matches.slice(1).map((match, index) => (
                       <motion.a
                         key={match.id}
                         href={`https://esports.op.gg/matches/${match.id}`}
                         target="_blank"
                         rel="noopener noreferrer"
                         initial={{ opacity: 0, x: -20 }}
                         animate={{ opacity: 1, x: 0 }}
                         transition={{ delay: index * 0.1 }}
                         className="block p-3 rounded-lg border transition-all hover:scale-[1.02] cursor-pointer"
                         style={{
                           backgroundColor: 'rgba(255, 255, 255, 0.05)',
                           borderColor: 'rgba(255, 255, 255, 0.1)',
                         }}
                       >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="px-2 py-0.5 rounded text-xs font-bold"
                        style={{
                          backgroundColor: `${getStatusColor(match.status)}20`,
                          color: getStatusColor(match.status),
                          border: `1px solid ${getStatusColor(match.status)}40`,
                          animation: match.status === 'LIVE' ? 'pulse 1.5s ease-in-out infinite' : 'none',
                        }}
                      >
                        {getStatusText(match.status)}
                      </span>
                      <span className="text-xs font-medium" style={{ color: colors.textSecondary }}>
                        {match.league}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-xs" style={{ color: colors.textSecondary }}>
                      <Calendar className="w-3 h-3" />
                      <span>
                        {new Date(match.scheduledAt).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <div className="mb-2">
                    <h4 className="font-bold text-lg" style={{ color: colors.textPrimary }}>
                      {match.name}
                    </h4>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" style={{ color: colors.textSecondary }} />
                        <span className="text-xs" style={{ color: colors.textSecondary }}>
                          {formatMatchTime(match.scheduledAt)}
                        </span>
                      </div>
                             {match.venue && getLocationText(match.venue) && (
                               <div className="flex items-center gap-1">
                                 <MapPin className="w-3 h-3" style={{ color: colors.textSecondary }} />
                                 <span className="text-xs" style={{ color: colors.textSecondary }}>
                                   {getLocationText(match.venue)}
                                 </span>
                               </div>
                             )}
                    </div>
                    
                           {match.status === 'LIVE' || match.status === 'FINISHED' ? (
                             <div className="flex items-center gap-2">
                               <span className="text-sm font-bold" style={{ color: colors.textPrimary }}>
                                 {match.homeScore} - {match.awayScore}
                               </span>
                             </div>
                           ) : null}
                  </div>
                       </motion.a>
                     ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {matches.length === 0 && (
        <div className="text-center py-8">
          <p style={{ color: colors.textSecondary }}>
            No matches available
          </p>
        </div>
      )}
      </motion.div>
    </GlareHover>
  );
}
