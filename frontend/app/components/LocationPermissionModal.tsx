'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, X } from 'lucide-react';

interface LocationPermissionModalProps {
  isOpen: boolean;
  onAllow: () => void;
  onDeny: () => void;
}

export default function LocationPermissionModal({ isOpen, onAllow, onDeny }: LocationPermissionModalProps) {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-md"
            style={{ zIndex: 9999 }}
          />

          {/* Modal */}
          <div className="fixed inset-0 flex items-center justify-center p-4" style={{ zIndex: 10000 }}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.3 }}
              className="rounded-3xl shadow-2xl max-w-md w-full overflow-hidden"
              style={{
                background: 'linear-gradient(135deg, rgba(20, 20, 30, 0.95) 0%, rgba(10, 10, 15, 0.98) 100%)',
                border: '2px solid rgba(255, 255, 255, 0.25)',
                backdropFilter: 'blur(30px)',
                boxShadow: '0 30px 80px rgba(0, 0, 0, 0.8), 0 0 1px rgba(255, 255, 255, 0.3) inset'
              }}
            >
              {/* Header */}
              <div 
                className="px-6 py-5 border-b"
                style={{ 
                  background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.7) 0%, rgba(0, 0, 0, 0.4) 100%)',
                  borderColor: 'rgba(255, 255, 255, 0.15)'
                }}
              >
                <div className="flex items-center gap-3">
                  <MapPin className="w-6 h-6" style={{ color: '#0A84FF' }} />
                  <h2 
                    className="text-2xl font-bold"
                    style={{ 
                      color: '#F5F5F7',
                      fontFamily: 'var(--font-geist-mono), monospace'
                    }}
                  >
                    Server Selection
                  </h2>
                </div>
              </div>

              {/* Content */}
              <div className="px-6 py-6">
                <p className="text-sm leading-relaxed mb-4" style={{ color: '#AEAEB2' }}>
                  QuantRift would like to automatically select the best server for your region to provide 
                  optimal performance and accurate local time information.
                </p>
                
                <div 
                  className="p-4 rounded-xl mb-6"
                  style={{
                    background: 'rgba(10, 132, 255, 0.1)',
                    border: '1px solid rgba(10, 132, 255, 0.3)'
                  }}
                >
                  <div className="flex items-start gap-3">
                    <MapPin className="w-4 h-4 mt-0.5" style={{ color: '#5AC8FA' }} />
                    <div>
                      <h4 className="text-sm font-bold mb-1" style={{ color: '#5AC8FA' }}>
                        What we use
                      </h4>
                      <p className="text-xs" style={{ color: '#AEAEB2' }}>
                        We detect your timezone to select the nearest League of Legends server. 
                        No precise location data is collected or stored.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={onDeny}
                    className="flex-1 px-4 py-3 rounded-xl font-semibold transition-all"
                    style={{
                      background: 'rgba(142, 142, 147, 0.2)',
                      border: '1px solid rgba(142, 142, 147, 0.3)',
                      color: '#AEAEB2'
                    }}
                  >
                    Use Default (NA)
                  </motion.button>
                  
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={onAllow}
                    className="flex-1 px-4 py-3 rounded-xl font-semibold transition-all"
                    style={{
                      background: 'linear-gradient(90deg, rgba(10, 132, 255, 0.9) 0%, rgba(191, 90, 242, 0.9) 100%)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      color: '#FFFFFF'
                    }}
                  >
                    Allow
                  </motion.button>
                </div>

                <p className="text-xs text-center mt-4" style={{ color: '#8E8E93' }}>
                  You can change your server selection at any time
                </p>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

