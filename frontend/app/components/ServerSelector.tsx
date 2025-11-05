'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { MapPin, ChevronDown } from 'lucide-react';
import { useServerContext } from '../context/ServerContext';
import GlareHover from './ui/GlareHover';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';

export default function ServerSelector() {
  const { selectedServer, servers, selectServer, timeDiff } = useServerContext();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    // Prevent body scroll when modal is open
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const formatTimeDiff = (diff: number) => {
    if (diff === 0) return '';
    const sign = diff > 0 ? '+' : '';
    return `${sign}${diff}h`;
  };

  const handleServerSelect = useCallback((serverCode: string) => {
    selectServer(serverCode);
    setIsOpen(false);
  }, [selectServer]);

  return (
    <div className="relative inline-flex" ref={dropdownRef}>
      <ClickSpark
        sparkColor="#32D74B"
        sparkSize={8}
        sparkRadius={12}
        sparkCount={6}
        duration={300}
        inline={true}
      >
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 relative z-10 hover:opacity-80 transition-opacity"
        >
          <MapPin className="w-4 h-4" style={{ color: '#32D74B' }} />
          <ShinyText 
            text={`${selectedServer.code} Server`} 
            speed={3} 
            className="text-sm font-medium"
          />
          {timeDiff !== 0 && (
            <span 
              className="text-xs font-mono px-1.5 py-0.5 rounded"
              style={{ 
                color: timeDiff > 0 ? '#32D74B' : '#FF453A',
                backgroundColor: 'rgba(255, 255, 255, 0.1)'
              }}
            >
              <ShinyText 
                text={formatTimeDiff(timeDiff)} 
                speed={2} 
                className="text-xs font-mono"
              />
            </span>
          )}
          <ChevronDown 
            className="w-3 h-3 transition-transform duration-200"
            style={{ 
              color: '#AEAEB2',
              transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)'
            }}
          />
        </button>
      </ClickSpark>

      {isOpen && (
        <>
          {/* Backdrop - Heavy Blur */}
          <div
            className="fixed inset-0 bg-black/40"
            style={{ 
              zIndex: 100,
              backdropFilter: 'blur(20px) saturate(120%) brightness(0.7)',
              WebkitBackdropFilter: 'blur(20px) saturate(120%) brightness(0.7)',
              transform: 'translateZ(0)'
            }}
            onClick={() => setIsOpen(false)}
          />
          
          {/* Airport Display Board */}
          <div 
            className="fixed"
            style={{ 
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 101,
              pointerEvents: 'auto'
            }}
          >
            <GlareHover
              width="580px"
              height="520px"
              background="rgba(0, 0, 0, 0.2)"
              borderRadius="24px"
              borderColor="rgba(255, 255, 255, 0.15)"
              glareColor="#ffffff"
              glareOpacity={0.1}
              glareAngle={-45}
              glareSize={200}
              transitionDuration={400}
            >
              <div
                className="fluid-glass rounded-3xl overflow-hidden"
                style={{ 
                  width: '580px',
                  maxHeight: '520px',
                  border: '2px solid rgba(255, 255, 255, 0.15)',
                  boxShadow: '0 25px 80px rgba(0, 0, 0, 0.6), 0 0 1px rgba(255, 255, 255, 0.2) inset',
                  transform: 'translateZ(0)'
                }}
              >
              {/* Header - Airport Style */}
              <div 
                className="px-8 py-5 border-b relative z-10"
                style={{ 
                  background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.5) 0%, rgba(0, 0, 0, 0.25) 100%)',
                  borderColor: 'rgba(255, 255, 255, 0.12)',
                  backdropFilter: 'blur(10px)',
                  WebkitBackdropFilter: 'blur(10px)',
                  transform: 'translateZ(0)'
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <ShinyText 
                      text="SERVER GATEWAY" 
                      speed={4} 
                      className="text-2xl font-bold tracking-tight mb-1"
                    />
                    <ShinyText 
                      text="League of Legends • Regional Selection" 
                      speed={3} 
                      className="text-xs tracking-wider uppercase"
                    />
                  </div>
                  <div 
                    className="text-right font-mono text-xs"
                    style={{ color: '#0A84FF' }}
                  >
                    <ShinyText text="LIVE" speed={2} className="text-sm font-semibold" />
                    <ShinyText 
                      text={new Date().toLocaleTimeString('en-US', { hour12: false })} 
                      speed={2} 
                      className="text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Airport Board Grid Header */}
              <div 
                className="grid grid-cols-12 gap-4 px-8 py-3.5 text-xs font-bold tracking-widest uppercase border-b relative z-10"
                style={{ 
                  backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  borderColor: 'rgba(255, 255, 255, 0.1)',
                  color: '#8E8E93',
                  fontFamily: 'var(--font-geist-mono), monospace',
                  backdropFilter: 'blur(5px)',
                  WebkitBackdropFilter: 'blur(5px)',
                  transform: 'translateZ(0)'
                }}
              >
                <div className="col-span-2">GATE</div>
                <div className="col-span-5">DESTINATION</div>
                <div className="col-span-2 text-center">TIME</div>
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
                {servers.map((server) => {
                  const localOffset = -new Date().getTimezoneOffset() / 60;
                  const serverTimeDiff = server.offset - localOffset;
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
                          transition: 'background-color 0.2s ease',
                          transform: 'translateZ(0)'
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
                      <div className="col-span-5 flex items-center">
                        <span 
                          className="text-sm font-semibold tracking-wide"
                          style={{ color: '#F5F5F7' }}
                        >
                          {server.name}
                        </span>
                      </div>

                      {/* Time Difference */}
                      <div className="col-span-2 flex items-center justify-center">
                        {serverTimeDiff !== 0 ? (
                          <span 
                            className="font-mono text-sm font-bold px-2.5 py-1 rounded"
                            style={{ 
                              color: serverTimeDiff > 0 ? '#32D74B' : '#FFD60A',
                              backgroundColor: 'rgba(0, 0, 0, 0.3)',
                              border: `1px solid ${serverTimeDiff > 0 ? 'rgba(50, 215, 75, 0.3)' : 'rgba(255, 214, 10, 0.3)'}`
                            }}
                          >
                            {formatTimeDiff(serverTimeDiff)}
                          </span>
                        ) : (
                          <span 
                            className="font-mono text-sm font-bold"
                            style={{ color: '#5AC8FA' }}
                          >
                            UTC
                          </span>
                        )}
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
              </div>
            </GlareHover>
          </div>
        </>
      )}
    </div>
  );
}

