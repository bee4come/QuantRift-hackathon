'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, MapPin, ChevronDown, X, Sun, Moon, Info, Github } from 'lucide-react';
import { useTimeOfDay, type TimeOfDay } from '../hooks/useTimeOfDay';
import { useServerStatus } from '../hooks/useServerStatus';
import { useServerContext } from '../context/ServerContext';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import { useSearch } from '../context/SearchContext';
import { useModal } from '../context/ModalContext';
import AboutModal from './AboutModal';
import EsportsAnnouncements from './EsportsAnnouncements';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import Card from './Card';
import DarkModeSwitch from './DarkModeSwitch';

const TIME_LABELS: Record<TimeOfDay, string> = {
  midnight: 'Midnight',
  'before-dawn': 'Before Dawn',
  dawn: 'Daybreak',
  sunrise: 'Sunrise',
  morning: 'Morning',
  'late-morning': 'Late Morning',
  noon: 'Noon',
  'early-afternoon': 'Early Afternoon',
  'late-afternoon': 'Late Afternoon',
  sunset: 'Sunset',
  'early-evening': 'Early Evening',
  night: 'Night',
};

const IS_DAYTIME: Record<TimeOfDay, boolean> = {
  midnight: false,
  'before-dawn': false,
  dawn: false,
  sunrise: true,
  morning: true,
  'late-morning': true,
  noon: true,
  'early-afternoon': true,
  'late-afternoon': true,
  sunset: false,
  'early-evening': false,
  night: false,
};

interface HeaderProps {
  hideServerAndEsports?: boolean;
}

export default function Header({ hideServerAndEsports = false }: HeaderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { selectedServer, servers, selectServer, currentTimezone, showLocationModal, handleLocationAllow, handleLocationDeny } = useServerContext();
  const { isSearched, clearPlayers } = useSearch();
  const { isModalOpen } = useModal();
  const timeOfDay = useTimeOfDay(currentTimezone);
  const serverStatus = useServerStatus(selectedServer.code.toLowerCase());
  const colors = useAdaptiveColors();
  const [currentTime, setCurrentTime] = useState('');
  const [isGatewayOpen, setIsGatewayOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [showAllServers, setShowAllServers] = useState(false);

  const formatters = useMemo(() => ({
    time: new Intl.DateTimeFormat('en-US', {
      timeZone: currentTimezone,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }),
    tz: new Intl.DateTimeFormat('en-US', {
      timeZone: currentTimezone,
      timeZoneName: 'short'
    })
  }), [currentTimezone]);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const timeString = formatters.time.format(now);
      const tzAbbr = formatters.tz.formatToParts(now).find(part => part.type === 'timeZoneName')?.value || '';
      setCurrentTime(`${timeString} ${tzAbbr}`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);

    return () => clearInterval(interval);
  }, [formatters]);

  // Fix hydration mismatch
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const handleServerSelect = (serverCode: string) => {
    selectServer(serverCode);
    setIsGatewayOpen(false);
    setShowAllServers(false);
  };

  const handleTitleClick = () => {
    // Always refresh to home page
    if (pathname !== '/') {
      window.location.href = '/';
    } else {
      window.location.reload();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -30 }}
      animate={{ 
        opacity: 1, 
        y: 0,
      }}
      transition={{ duration: 0.8, ease: 'easeOut' }}
      className={`w-full px-4 transition-all duration-500 ${
        (isSearched && pathname === '/') ? 'pt-4 pb-2' : hideServerAndEsports ? 'pt-4 pb-4' : 'pt-12 pb-6'
      }`}
      style={{ zIndex: 1000 }}
    >
      {/* Top Right Icons - Only on first page */}
      {!isSearched && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="absolute top-6 right-6 flex items-center gap-3"
          style={{ zIndex: 100 }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className={`${isModalOpen ? 'pointer-events-none' : ''}`}
            style={{
              filter: isModalOpen ? 'blur(4px)' : 'none',
              transition: 'filter 0.3s ease'
            }}
          >
            <DarkModeSwitch />
          </motion.div>
          
          <motion.a
            href="https://github.com/bee4come/QuantRift-hackathon"
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`p-3 rounded-xl transition-all ${isModalOpen ? 'pointer-events-none' : ''}`}
            style={{
              background: 'rgba(255, 255, 255, 0.1)',
              borderWidth: '1px',
              borderStyle: 'solid',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              backdropFilter: 'blur(10px)',
              filter: isModalOpen ? 'blur(4px)' : 'none',
              transition: 'filter 0.3s ease, background 0.2s ease'
            }}
            onMouseEnter={(e) => {
              if (!isModalOpen) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
              }
            }}
            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'}
          >
            <Github className="w-5 h-5" style={{ color: '#F5F5F7' }} />
          </motion.a>
          
          <ClickSpark
            sparkColor="#F5F5F7"
            sparkSize={8}
            sparkRadius={12}
            sparkCount={6}
            duration={300}
            inline={true}
          >
            <motion.button
              onClick={() => setIsAboutOpen(true)}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              disabled={isModalOpen}
              className={`p-3 rounded-xl transition-all ${isModalOpen ? 'pointer-events-none' : ''}`}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                borderWidth: '1px',
                borderStyle: 'solid',
                borderColor: 'rgba(255, 255, 255, 0.2)',
                backdropFilter: 'blur(10px)',
                filter: isModalOpen ? 'blur(4px)' : 'none',
                transition: 'filter 0.3s ease, background 0.2s ease'
              }}
              onMouseEnter={(e) => {
                if (!isModalOpen) {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
                }
              }}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'}
            >
              <Info className="w-5 h-5" style={{ color: '#F5F5F7' }} />
            </motion.button>
          </ClickSpark>
        </motion.div>
      )}

      {/* About Modal */}
      <AboutModal isOpen={isAboutOpen} onClose={() => setIsAboutOpen(false)} />

      <div className={`transition-all duration-500 ${
        (isSearched && pathname === '/')
          ? 'max-w-7xl mx-auto flex items-center justify-between' 
          : 'max-w-4xl mx-auto text-center'
      }`}>
        {/* Logo and Title */}
        <motion.div
          initial={{ scale: 0.9 }}
          animate={{ 
            scale: 1,
            justifyContent: (isSearched && pathname === '/') ? 'flex-start' : 'center'
          }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className={`flex items-center transition-all duration-500 ${
            (isSearched && pathname === '/') ? 'mb-0' : 'justify-center mb-3'
          }`}
        >
          {(isSearched || pathname !== '/') ? (
            <ClickSpark
              sparkColor="#FFFFFF"
              sparkSize={10}
              sparkRadius={15}
              sparkCount={8}
              duration={400}
            >
              <button 
                onClick={handleTitleClick}
                className={`hover:opacity-80 transition-opacity duration-300 ${isModalOpen ? 'pointer-events-none' : ''}`}
              >
                <Card isSearched={isSearched && pathname === '/'} isModalOpen={isModalOpen} />
              </button>
            </ClickSpark>
          ) : (
            <Link href="/" className={`hover:opacity-80 transition-opacity duration-300 ${isModalOpen ? 'pointer-events-none' : ''}`}>
              <Card isSearched={false} isModalOpen={isModalOpen} />
            </Link>
          )}
        </motion.div>

        {/* Season & Patch - Fixed Info */}
        {!isSearched && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25, duration: 0.6 }}
            className={`flex items-center justify-center gap-3 mb-4 transition-all duration-300 ${
              isModalOpen ? 'blur-sm pointer-events-none opacity-50' : ''
            }`}
          >
            <span className="text-base font-medium" style={{ color: colors.textSecondary }}>Season 2025</span>
            <div className="w-px h-4" style={{ backgroundColor: colors.borderColor }}></div>
            <a 
              href="https://www.leagueoflegends.com/en-us/news/game-updates/patch-25-22-notes/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-base font-medium hover:opacity-70 transition-opacity"
              style={{ color: colors.textSecondary }}
            >
              Patch 25.22
            </a>
          </motion.div>
        )}

        {/* Server & Time Info Block / Gateway */}
        {!isSearched && !hideServerAndEsports && (
          <div className="flex justify-center">
            <AnimatePresence mode="wait">
              {!isGatewayOpen ? (
              <motion.div
                key="info-bar"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="fluid-glass rounded-2xl px-6 py-3 inline-flex items-center gap-4 mb-3 overflow-hidden"
              >
              {/* Server Selector with Status */}
              <ClickSpark
                sparkColor="#32D74B"
                sparkSize={8}
                sparkRadius={12}
                sparkCount={6}
                duration={300}
                inline={true}
              >
                <button
                  onClick={() => setIsGatewayOpen(true)}
                  className="flex items-center gap-2 relative z-10 hover:opacity-80 transition-opacity"
                >
                <MapPin className="w-4 h-4" style={{ color: '#32D74B' }} />
                <ShinyText
                  text={`${selectedServer.code} Server`}
                  speed={3}
                  className="text-sm font-medium"
                />
                <ChevronDown className="w-3 h-3" style={{ color: '#AEAEB2' }} />
                <div 
                  className="w-2 h-2 rounded-full"
                  style={{ 
                    backgroundColor: serverStatus === 'online' ? '#32D74B' : serverStatus === 'issues' ? '#FF453A' : '#8E8E93',
                    animation: serverStatus === 'issues' ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none',
                    boxShadow: serverStatus === 'online' ? '0 0 8px rgba(50, 215, 75, 0.6)' : serverStatus === 'issues' ? '0 0 8px rgba(255, 69, 58, 0.6)' : 'none'
                  }}
                />
              </button>
              </ClickSpark>
              
              <div className="w-px h-4 relative z-10" style={{ backgroundColor: 'rgba(255, 255, 255, 0.2)' }}></div>
              
              {/* Time */}
              <div className="flex items-center gap-2 relative z-10">
                <Clock className="w-4 h-4" style={{ color: '#5AC8FA' }} />
                <ShinyText 
                  text={currentTime} 
                  speed={2} 
                  className="text-sm font-mono tabular-nums"
                />
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="gateway"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="fluid-glass rounded-3xl overflow-hidden mb-3"
              style={{ 
                width: '580px',
                maxHeight: '520px',
                border: '2px solid rgba(255, 255, 255, 0.15)',
                boxShadow: '0 25px 80px rgba(0, 0, 0, 0.6), 0 0 1px rgba(255, 255, 255, 0.2) inset'
              }}
            >
              {/* Gateway Header */}
              <div 
                className="px-8 py-5 border-b relative z-10"
                style={{ 
                  background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.5) 0%, rgba(0, 0, 0, 0.25) 100%)',
                  borderColor: 'rgba(255, 255, 255, 0.12)'
                }}
              >
                <div className="flex items-center justify-between relative">
                  <div className="flex-1 flex justify-center">
                <ShinyText 
                  text="SERVER GATEWAY" 
                  speed={4} 
                  className="text-2xl font-bold tracking-tight"
                />
                  </div>
                  <div className="absolute right-0">
                    <ClickSpark
                      sparkColor="#FF453A"
                      sparkSize={6}
                      sparkRadius={10}
                      sparkCount={4}
                      duration={250}
                      inline={true}
                    >
                      <button
                        onClick={() => setIsGatewayOpen(false)}
                        className="p-2 rounded border transition-all backdrop-blur-sm"
                        style={{
                          backgroundColor: 'rgba(255, 69, 58, 0.15)',
                          borderColor: 'rgba(255, 69, 58, 0.3)',
                          color: '#FF453A'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = 'rgba(255, 69, 58, 0.25)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'rgba(255, 69, 58, 0.15)';
                        }}
                        title="Close"
                        aria-label="Close"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </ClickSpark>
                  </div>
                </div>
              </div>

              {/* Gateway Grid Header */}
              <div 
                className="grid grid-cols-12 gap-4 px-8 py-3.5 text-xs font-bold tracking-widest uppercase border-b relative z-10"
                style={{ 
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  borderColor: 'rgba(255, 255, 255, 0.1)',
                  color: '#8E8E93',
                  fontFamily: 'var(--font-geist-mono), monospace'
                }}
              >
                <div className="col-span-2">GATE</div>
                <div className="col-span-7 text-center">DESTINATION</div>
                <div className="col-span-3 text-right">STATUS</div>
              </div>

              {/* Server List */}
              <div 
                className="overflow-y-auto" 
                style={{ 
                  maxHeight: '400px',
                  WebkitOverflowScrolling: 'touch',
                  scrollBehavior: 'smooth'
                }}
              >
                {servers.slice(0, showAllServers ? servers.length : 3).map((server) => {
                  const isSelected = selectedServer.code === server.code;
                  
                  return (
                    <ClickSpark
                      key={server.code}
                      sparkColor={isSelected ? "#0A84FF" : "#FFFFFF"}
                      sparkSize={6}
                      sparkRadius={10}
                      sparkCount={4}
                      duration={250}
                    >
                      <button
                        onClick={() => handleServerSelect(server.code)}
                        className="w-full grid grid-cols-12 gap-4 px-8 py-4 border-b relative z-10"
                        style={{ 
                          backgroundColor: isSelected ? 'rgba(10, 132, 255, 0.2)' : 'transparent',
                          borderColor: 'rgba(255, 255, 255, 0.06)',
                          fontFamily: 'var(--font-geist-mono), monospace',
                          transition: 'background-color 0.2s ease'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = isSelected ? 'rgba(10, 132, 255, 0.25)' : 'rgba(255, 255, 255, 0.08)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = isSelected ? 'rgba(10, 132, 255, 0.2)' : 'transparent';
                        }}
                      >
                      {/* Gate/Server Code */}
                      <div className="col-span-2 flex items-center">
                        <div 
                          className="font-mono text-lg font-black tracking-widest px-3 py-1.5 rounded"
                          style={{ 
                            color: isSelected ? '#0A84FF' : '#F5F5F7',
                            backgroundColor: isSelected ? 'rgba(10, 132, 255, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                            border: `1px solid ${isSelected ? 'rgba(10, 132, 255, 0.4)' : 'rgba(255, 255, 255, 0.15)'}`
                          }}
                        >
                          {server.code}
                        </div>
                      </div>

                      {/* Destination/Server Name */}
                      <div className="col-span-7 flex items-center justify-center">
                        <span 
                          className="text-sm font-semibold tracking-wide"
                          style={{ color: '#F5F5F7' }}
                        >
                          {server.name}
                        </span>
                      </div>

                      {/* Status Indicator */}
                      <div className="col-span-3 flex items-center justify-end gap-2">
                        <div 
                          className="w-2.5 h-2.5 rounded-full animate-pulse"
                          style={{ 
                            backgroundColor: '#32D74B',
                            boxShadow: '0 0 10px rgba(50, 215, 75, 0.8)'
                          }}
                        />
                        <span 
                          className="text-xs font-bold tracking-wider"
                          style={{ color: '#32D74B' }}
                        >
                          ONLINE
                        </span>
                      </div>
                      </button>
                    </ClickSpark>
                  );
                })}
              </div>

              {/* Show More/Less Button */}
              {servers.length > 3 && (
                <div className="px-8 py-4 border-t relative z-10" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }}>
                  <ClickSpark
                    sparkColor="#FFFFFF"
                    sparkSize={6}
                    sparkRadius={10}
                    sparkCount={4}
                    duration={250}
                  >
                    <button
                      onClick={() => setShowAllServers(!showAllServers)}
                      className="w-full py-2 rounded-lg font-semibold text-sm transition-all"
                      style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        borderWidth: '1px',
                        borderStyle: 'solid',
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                        color: '#FFFFFF'
                      }}
                    >
                      {showAllServers ? 'Show Less' : `Show More (${servers.length - 3} more servers)`}
                    </button>
                  </ClickSpark>
                </div>
              )}
            </motion.div>
            )}
            </AnimatePresence>
          </div>
        )}

      </div>
    </motion.div>
  );
}

