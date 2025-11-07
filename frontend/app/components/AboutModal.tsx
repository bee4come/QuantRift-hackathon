'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, Github, Sparkles, Code, Heart } from 'lucide-react';
import { useEffect } from 'react';
import { useModal } from '../context/ModalContext';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AboutModal({ isOpen, onClose }: AboutModalProps) {
  const { setIsModalOpen } = useModal();

  useEffect(() => {
    setIsModalOpen(isOpen);
  }, [isOpen, setIsModalOpen]);

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
            onClick={onClose}
          />

          {/* Modal */}
          <div className="fixed inset-0 flex items-center justify-center p-4" style={{ zIndex: 10000 }}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.3 }}
              className="rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden"
              style={{
                background: 'linear-gradient(135deg, rgba(20, 20, 30, 0.95) 0%, rgba(10, 10, 15, 0.98) 100%)',
                border: '2px solid rgba(255, 255, 255, 0.25)',
                backdropFilter: 'blur(30px)',
                boxShadow: '0 30px 80px rgba(0, 0, 0, 0.8), 0 0 1px rgba(255, 255, 255, 0.3) inset',
                maxHeight: '90vh',
                overflowY: 'auto'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div 
                className="px-8 py-6 border-b relative"
                style={{ 
                  background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.7) 0%, rgba(0, 0, 0, 0.4) 100%)',
                  borderColor: 'rgba(255, 255, 255, 0.15)'
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Sparkles className="w-7 h-7" style={{ color: '#0A84FF' }} />
                    <h2 
                      className="text-3xl font-bold"
                      style={{ 
                        color: '#F5F5F7',
                        fontFamily: 'var(--font-geist-mono), monospace'
                      }}
                    >
                      About QuantRift
                    </h2>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.1, rotate: 90 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={onClose}
                    className="p-2 rounded-xl transition-all"
                    style={{
                      background: 'rgba(255, 255, 255, 0.1)',
                      border: '1px solid rgba(255, 255, 255, 0.2)'
                    }}
                  >
                    <X className="w-5 h-5" style={{ color: '#8E8E93' }} />
                  </motion.button>
                </div>
              </div>

              {/* Content */}
              <div className="px-8 py-6 space-y-6">
                {/* Hackathon Info */}
                <div 
                  className="p-4 rounded-xl"
                  style={{
                    background: 'linear-gradient(135deg, rgba(10, 132, 255, 0.2) 0%, rgba(191, 90, 242, 0.2) 100%)',
                    border: '1px solid rgba(10, 132, 255, 0.3)'
                  }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4" style={{ color: '#5AC8FA' }} />
                    <h4 className="text-sm font-bold uppercase tracking-wider" style={{ color: '#5AC8FA' }}>
                      Hackathon Project
                    </h4>
                  </div>
                  <p className="text-sm leading-relaxed mb-2" style={{ color: '#F5F5F7' }}>
                    Created for the <strong>Rift Rewind Hackathon</strong> powered by AWS and Riot Games
                  </p>
                  <a 
                    href="https://riftrewind.devpost.com/?ref_feature=challenge&ref_medium=your-open-hackathons&ref_content=Submissions+open"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs hover:underline"
                    style={{ color: '#0A84FF' }}
                  >
                    View Hackathon Details →
                  </a>
                </div>

                {/* Project Description */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Code className="w-5 h-5" style={{ color: '#5AC8FA' }} />
                    <h3 className="text-xl font-bold" style={{ color: '#F5F5F7' }}>
                      About the Project
                    </h3>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: '#AEAEB2' }}>
                    QuantRift is an AI-powered League of Legends player analysis platform that provides 
                    intelligent insights and beautiful visualizations of your gaming journey. Built with 
                    cutting-edge web technologies and designed with a premium glassmorphism UI, QuantRift 
                    helps players understand their performance through advanced analytics and personalized 
                    annual reports. Leveraging AWS AI services and the League API, we transform raw gameplay 
                    data into meaningful, actionable insights.
                  </p>
                </div>


                {/* Developers */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <Heart className="w-5 h-5" style={{ color: '#FF453A' }} />
                    <h3 className="text-xl font-bold" style={{ color: '#F5F5F7' }}>
                      Developed and maintained by
                    </h3>
                  </div>
                  <div className="flex gap-3">
                    {/* Developer 1 - bee4come */}
                    <motion.a
                      href="https://github.com/bee4come"
                      target="_blank"
                      rel="noopener noreferrer"
                      whileHover={{ scale: 1.02 }}
                      className="flex-1 flex items-center gap-4 p-4 rounded-xl transition-all"
                      style={{
                        background: 'linear-gradient(135deg, rgba(255, 214, 10, 0.15) 0%, rgba(255, 214, 10, 0.05) 100%)',
                        border: '1px solid rgba(255, 214, 10, 0.3)'
                      }}
                    >
                      <div 
                        className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{
                          background: 'linear-gradient(135deg, #FFD60A 0%, #FFA500 100%)',
                          boxShadow: '0 4px 12px rgba(255, 214, 10, 0.3)'
                        }}
                      >
                        <span className="text-2xl">🐝</span>
                      </div>
                      <div className="flex-1">
                        <span className="font-bold text-base" style={{ color: '#F5F5F7' }}>
                          @bee4come
                        </span>
                        <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                          Architect, Data and Integration
                        </p>
                      </div>
                    </motion.a>

                    {/* Developer 2 - uzerone */}
                    <motion.a
                      href="https://github.com/uzerone"
                      target="_blank"
                      rel="noopener noreferrer"
                      whileHover={{ scale: 1.02 }}
                      className="flex-1 flex items-center gap-4 p-4 rounded-xl transition-all"
                      style={{
                        background: 'linear-gradient(135deg, rgba(88, 101, 242, 0.15) 0%, rgba(88, 101, 242, 0.05) 100%)',
                        border: '1px solid rgba(88, 101, 242, 0.3)'
                      }}
                    >
                      <div 
                        className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{
                          background: 'linear-gradient(135deg, #5865F2 0%, #7289DA 100%)',
                          boxShadow: '0 4px 12px rgba(88, 101, 242, 0.3)'
                        }}
                      >
                        <span className="text-2xl">👻</span>
                      </div>
                      <div className="flex-1">
                        <span className="font-bold text-base" style={{ color: '#F5F5F7' }}>
                          @uzerone
                        </span>
                        <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                          Product & UX/UI Design
                        </p>
                      </div>
                    </motion.a>
                  </div>
                </div>

              </div>

              {/* Footer */}
              <div 
                className="px-8 py-4 border-t text-center"
                style={{ 
                  background: 'rgba(0, 0, 0, 0.5)',
                  borderColor: 'rgba(255, 255, 255, 0.15)'
                }}
              >
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

