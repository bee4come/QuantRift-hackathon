'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, TrendingUp, Target, Zap, Eye, Share2, Check } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';

interface HighlightMatch {
  id: string;
  title: string;
  champion: string;
  kda: string;
  result: 'Victory' | 'Defeat';
  date: string;
  gameMode: string;
  thumbnail: string;
  stats: {
    kills: number;
    deaths: number;
    assists: number;
    cs: number;
    gold: string;
    damage: string;
  };
}

const mockHighlights: HighlightMatch[] = [
  {
    id: '1',
    title: 'Pentakill Perfection',
    champion: 'Yasuo',
    kda: '18/2/7',
    result: 'Victory',
    date: '2025-10-10',
    gameMode: 'Ranked Solo',
    thumbnail: '🗡️',
    stats: {
      kills: 18,
      deaths: 2,
      assists: 7,
      cs: 287,
      gold: '18.5k',
      damage: '42.3k'
    }
  },
  {
    id: '2',
    title: 'Comeback King',
    champion: 'Lee Sin',
    kda: '12/4/19',
    result: 'Victory',
    date: '2025-10-08',
    gameMode: 'Ranked Solo',
    thumbnail: '👊',
    stats: {
      kills: 12,
      deaths: 4,
      assists: 19,
      cs: 156,
      gold: '14.2k',
      damage: '28.7k'
    }
  },
  {
    id: '3',
    title: 'Flawless Carry',
    champion: 'Jinx',
    kda: '15/0/8',
    result: 'Victory',
    date: '2025-10-05',
    gameMode: 'Ranked Solo',
    thumbnail: '🎯',
    stats: {
      kills: 15,
      deaths: 0,
      assists: 8,
      cs: 324,
      gold: '21.8k',
      damage: '52.1k'
    }
  },
  {
    id: '4',
    title: 'Epic Outplay',
    champion: 'Zed',
    kda: '22/5/6',
    result: 'Victory',
    date: '2025-10-03',
    gameMode: 'Ranked Solo',
    thumbnail: '⚡',
    stats: {
      kills: 22,
      deaths: 5,
      assists: 6,
      cs: 245,
      gold: '19.4k',
      damage: '38.9k'
    }
  }
];

interface HoverCardProps {
  match: HighlightMatch;
  position: { x: number; y: number };
}

function HoverCard({ match, position }: HoverCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: 10 }}
      transition={{ duration: 0.2 }}
      className="fixed pointer-events-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        zIndex: 9999,
        transform: 'translate(-50%, -120%)'
      }}
    >
      <div 
        className="fluid-glass rounded-2xl p-6 shadow-2xl"
        style={{
          width: '320px',
          border: '2px solid rgba(255, 255, 255, 0.2)',
          background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.8) 0%, rgba(20, 20, 30, 0.9) 100%)',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8), 0 0 1px rgba(255, 255, 255, 0.3) inset'
        }}
      >
        {/* Champion Header */}
        <div className="flex items-center gap-3 mb-4">
          <div 
            className="text-4xl"
            style={{
              filter: 'drop-shadow(0 0 10px rgba(255, 255, 255, 0.5))'
            }}
          >
            {match.thumbnail}
          </div>
          <div>
            <h4 
              className="text-lg font-bold"
              style={{ color: '#F5F5F7' }}
            >
              {match.champion}
            </h4>
            <p 
              className="text-sm font-mono"
              style={{ color: match.result === 'Victory' ? '#32D74B' : '#FF453A' }}
            >
              {match.result}
            </p>
          </div>
        </div>

        {/* KDA Display */}
        <div 
          className="mb-4 p-3 rounded-xl"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.4)' }}
        >
          <div className="flex justify-between items-center">
            <span className="text-xs uppercase tracking-wider" style={{ color: '#8E8E93' }}>
              KDA
            </span>
            <span className="text-2xl font-bold font-mono" style={{ color: '#FFD60A' }}>
              {match.kda}
            </span>
          </div>
          <div className="mt-2 text-xs" style={{ color: '#AEAEB2' }}>
            {match.stats.kills} Kills • {match.stats.deaths} Deaths • {match.stats.assists} Assists
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div 
            className="p-2 rounded-lg"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
          >
            <div className="text-xs mb-1" style={{ color: '#8E8E93' }}>CS</div>
            <div className="text-lg font-bold font-mono" style={{ color: '#F5F5F7' }}>
              {match.stats.cs}
            </div>
          </div>
          <div 
            className="p-2 rounded-lg"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
          >
            <div className="text-xs mb-1" style={{ color: '#8E8E93' }}>Gold</div>
            <div className="text-lg font-bold font-mono" style={{ color: '#FFD60A' }}>
              {match.stats.gold}
            </div>
          </div>
          <div 
            className="p-2 rounded-lg col-span-2"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
          >
            <div className="text-xs mb-1" style={{ color: '#8E8E93' }}>Damage Dealt</div>
            <div className="text-lg font-bold font-mono" style={{ color: '#FF453A' }}>
              {match.stats.damage}
            </div>
          </div>
        </div>

        {/* Date & Mode */}
        <div 
          className="mt-4 pt-3 border-t text-xs text-center"
          style={{ 
            borderColor: 'rgba(255, 255, 255, 0.1)',
            color: '#8E8E93'
          }}
        >
          {match.gameMode} • {match.date}
        </div>
      </div>
    </motion.div>
  );
}

export default function AnnualReport() {
  const [hoveredMatch, setHoveredMatch] = useState<HighlightMatch | null>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [showShareMenu, setShowShareMenu] = useState(false);
  const [copied, setCopied] = useState(false);
  const shareMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (shareMenuRef.current && !shareMenuRef.current.contains(event.target as Node)) {
        setShowShareMenu(false);
      }
    };

    if (showShareMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showShareMenu]);

  const handleMouseEnter = (match: HighlightMatch, e: React.MouseEvent) => {
    setHoveredMatch(match);
    setMousePosition({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (hoveredMatch) {
      setMousePosition({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseLeave = () => {
    setHoveredMatch(null);
  };

  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleShareTwitter = () => {
    const text = "Check out my League of Legends 2025 Annual Report on QuantRift! 342 games, 58.2% win rate, 12 pentakills!";
    const url = window.location.href;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`, '_blank');
  };

  const handleShareFacebook = () => {
    const url = window.location.href;
    window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`, '_blank');
  };

  const handleShareReddit = () => {
    const title = "My League of Legends 2025 Annual Report";
    const url = window.location.href;
    window.open(`https://reddit.com/submit?title=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`, '_blank');
  };

  const handleShareDiscord = () => {
    handleCopyLink();
    // Discord doesn't have a direct share API, so we copy the link
  };

  return (
    <div className="relative" style={{ zIndex: 1 }}>
      {/* Share Button - Fixed Top Right */}
      <div className="fixed top-6 right-6" style={{ zIndex: 1001 }} ref={shareMenuRef}>
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.4 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowShareMenu(!showShareMenu)}
          className="p-4 rounded-2xl transition-all shadow-xl"
          style={{
            background: 'linear-gradient(135deg, rgba(10, 132, 255, 0.3) 0%, rgba(10, 132, 255, 0.15) 100%)',
            border: '2px solid rgba(10, 132, 255, 0.4)',
            backdropFilter: 'blur(20px)'
          }}
        >
          <Share2 className="w-6 h-6" style={{ color: '#0A84FF' }} />
        </motion.button>

        {/* Share Menu */}
        <AnimatePresence>
          {showShareMenu && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.2 }}
              className="absolute right-0 mt-2 fluid-glass rounded-2xl p-4 shadow-2xl"
              style={{
                width: '240px',
                border: '2px solid rgba(255, 255, 255, 0.15)',
              }}
            >
              <div className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: '#8E8E93' }}>
                Share Report
              </div>
              
              <div className="space-y-2">
                {/* Twitter */}
                <button
                  onClick={handleShareTwitter}
                  className="w-full flex items-center gap-3 p-3 rounded-xl transition-all"
                  style={{
                    background: 'rgba(29, 155, 240, 0.1)',
                    border: '1px solid rgba(29, 155, 240, 0.3)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(29, 155, 240, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(29, 155, 240, 0.1)'}
                >
                  <span className="text-xl">𝕏</span>
                  <span className="text-sm font-medium" style={{ color: '#F5F5F7' }}>Twitter</span>
                </button>

                {/* Facebook */}
                <button
                  onClick={handleShareFacebook}
                  className="w-full flex items-center gap-3 p-3 rounded-xl transition-all"
                  style={{
                    background: 'rgba(24, 119, 242, 0.1)',
                    border: '1px solid rgba(24, 119, 242, 0.3)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(24, 119, 242, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(24, 119, 242, 0.1)'}
                >
                  <span className="text-xl">f</span>
                  <span className="text-sm font-medium" style={{ color: '#F5F5F7' }}>Facebook</span>
                </button>

                {/* Reddit */}
                <button
                  onClick={handleShareReddit}
                  className="w-full flex items-center gap-3 p-3 rounded-xl transition-all"
                  style={{
                    background: 'rgba(255, 69, 0, 0.1)',
                    border: '1px solid rgba(255, 69, 0, 0.3)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 69, 0, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 69, 0, 0.1)'}
                >
                  <span className="text-xl">▶</span>
                  <span className="text-sm font-medium" style={{ color: '#F5F5F7' }}>Reddit</span>
                </button>

                {/* Discord */}
                <button
                  onClick={handleShareDiscord}
                  className="w-full flex items-center gap-3 p-3 rounded-xl transition-all"
                  style={{
                    background: 'rgba(88, 101, 242, 0.1)',
                    border: '1px solid rgba(88, 101, 242, 0.3)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(88, 101, 242, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(88, 101, 242, 0.1)'}
                >
                  <span className="text-xl">💬</span>
                  <span className="text-sm font-medium" style={{ color: '#F5F5F7' }}>Discord</span>
                </button>

                {/* Copy Link */}
                <button
                  onClick={handleCopyLink}
                  className="w-full flex items-center justify-between p-3 rounded-xl transition-all"
                  style={{
                    background: 'rgba(142, 142, 147, 0.1)',
                    border: '1px solid rgba(142, 142, 147, 0.3)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(142, 142, 147, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(142, 142, 147, 0.1)'}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">🔗</span>
                    <span className="text-sm font-medium" style={{ color: '#F5F5F7' }}>
                      {copied ? 'Copied!' : 'Copy Link'}
                    </span>
                  </div>
                  {copied && <Check className="w-4 h-4" style={{ color: '#32D74B' }} />}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="w-full max-w-6xl mx-auto px-4 pb-12 pt-8"
      >
        {/* Report Header */}
        <div className="fluid-glass rounded-3xl p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 
                className="text-3xl font-bold mb-1"
                style={{ 
                  color: '#F5F5F7',
                  fontFamily: 'var(--font-geist-mono), monospace'
                }}
              >
                2025 Annual Report
              </h2>
              <p className="text-xs" style={{ color: '#8E8E93' }}>
                Your League of Legends journey this year
              </p>
            </div>
            <div 
              className="text-4xl"
              style={{
                filter: 'drop-shadow(0 0 15px rgba(255, 214, 10, 0.5))'
              }}
            >
              🏆
            </div>
          </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-3">
          <div 
            className="p-3 rounded-xl"
            style={{ 
              background: 'linear-gradient(135deg, rgba(10, 132, 255, 0.2) 0%, rgba(10, 132, 255, 0.05) 100%)',
              border: '1px solid rgba(10, 132, 255, 0.3)'
            }}
          >
            <Trophy className="w-4 h-4 mb-2" style={{ color: '#FFD60A' }} />
            <div className="text-2xl font-bold mb-1" style={{ color: '#F5F5F7' }}>342</div>
            <div className="text-xs" style={{ color: '#8E8E93' }}>Games Played</div>
          </div>
          
          <div 
            className="p-3 rounded-xl"
            style={{ 
              background: 'linear-gradient(135deg, rgba(50, 215, 75, 0.2) 0%, rgba(50, 215, 75, 0.05) 100%)',
              border: '1px solid rgba(50, 215, 75, 0.3)'
            }}
          >
            <TrendingUp className="w-4 h-4 mb-2" style={{ color: '#32D74B' }} />
            <div className="text-2xl font-bold mb-1" style={{ color: '#F5F5F7' }}>58.2%</div>
            <div className="text-xs" style={{ color: '#8E8E93' }}>Win Rate</div>
          </div>
          
          <div 
            className="p-3 rounded-xl"
            style={{ 
              background: 'linear-gradient(135deg, rgba(255, 214, 10, 0.2) 0%, rgba(255, 214, 10, 0.05) 100%)',
              border: '1px solid rgba(255, 214, 10, 0.3)'
            }}
          >
            <Target className="w-4 h-4 mb-2" style={{ color: '#FFD60A' }} />
            <div className="text-2xl font-bold mb-1" style={{ color: '#F5F5F7' }}>3.8</div>
            <div className="text-xs" style={{ color: '#8E8E93' }}>Avg KDA</div>
          </div>
          
          <div 
            className="p-3 rounded-xl"
            style={{ 
              background: 'linear-gradient(135deg, rgba(255, 69, 58, 0.2) 0%, rgba(255, 69, 58, 0.05) 100%)',
              border: '1px solid rgba(255, 69, 58, 0.3)'
            }}
          >
            <Zap className="w-4 h-4 mb-2" style={{ color: '#FF453A' }} />
            <div className="text-2xl font-bold mb-1" style={{ color: '#F5F5F7' }}>12</div>
            <div className="text-xs" style={{ color: '#8E8E93' }}>Pentakills</div>
          </div>
        </div>
      </div>

      {/* Highlight Matches */}
      <div className="fluid-glass rounded-3xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Eye className="w-5 h-5" style={{ color: '#0A84FF' }} />
          <h3 
            className="text-xl font-bold"
            style={{ 
              color: '#F5F5F7',
              fontFamily: 'var(--font-geist-mono), monospace'
            }}
          >
            Highlight Matches
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {mockHighlights.map((match) => (
            <motion.div
              key={match.id}
              whileHover={{ scale: 1.02 }}
              onMouseEnter={(e) => handleMouseEnter(match, e)}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
              className="p-4 rounded-xl cursor-pointer transition-all duration-200"
              style={{
                background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.4) 0%, rgba(20, 20, 30, 0.5) 100%)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                boxShadow: hoveredMatch?.id === match.id ? '0 10px 40px rgba(10, 132, 255, 0.3)' : 'none'
              }}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="text-2xl">{match.thumbnail}</div>
                  <div>
                    <h4 className="font-bold text-xs mb-0.5" style={{ color: '#F5F5F7' }}>
                      {match.title}
                    </h4>
                    <p className="text-xs" style={{ color: '#8E8E93' }}>
                      {match.champion}
                    </p>
                  </div>
                </div>
                <div 
                  className="px-2 py-0.5 rounded text-xs font-bold"
                  style={{
                    backgroundColor: match.result === 'Victory' ? 'rgba(50, 215, 75, 0.2)' : 'rgba(255, 69, 58, 0.2)',
                    color: match.result === 'Victory' ? '#32D74B' : '#FF453A'
                  }}
                >
                  {match.result}
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-lg font-bold font-mono" style={{ color: '#FFD60A' }}>
                  {match.kda}
                </span>
                <span className="text-xs" style={{ color: '#8E8E93' }}>
                  {match.date}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Hover Preview Card */}
      <AnimatePresence>
        {hoveredMatch && (
          <HoverCard match={hoveredMatch} position={mousePosition} />
        )}
      </AnimatePresence>
      </motion.div>
    </div>
  );
}

