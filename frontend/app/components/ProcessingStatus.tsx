'use client';

import { motion } from 'framer-motion';
import { Loader2, Cpu, Brain, BarChart3 } from 'lucide-react';

const processingSteps = [
  { icon: Cpu, label: 'Fetching match data', color: '#0A84FF' },
  { icon: Brain, label: 'AI analysis in progress', color: '#5AC8FA' },
  { icon: BarChart3, label: 'Generating insights', color: '#32D74B' },
];

export default function ProcessingStatus() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-2xl mx-auto px-4 py-8"
    >
      <div 
        className="fluid-glass rounded-3xl p-8"
        style={{
          border: '2px solid rgba(255, 255, 255, 0.15)',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)'
        }}
      >
        {/* Main Loading Indicator */}
        <div className="flex items-center justify-center mb-8">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          >
            <Loader2 
              className="w-16 h-16" 
              style={{ color: '#0A84FF' }}
            />
          </motion.div>
        </div>

        {/* Title */}
        <h3 
          className="text-3xl font-bold text-center mb-3"
          style={{ 
            color: '#F5F5F7',
            fontFamily: 'var(--font-geist-mono), monospace'
          }}
        >
          Parallel Processing
        </h3>
        
        <p 
          className="text-center text-sm mb-8"
          style={{ color: '#8E8E93' }}
        >
          Analyzing player data with advanced AI algorithms
        </p>

        {/* Processing Steps */}
        <div className="space-y-4">
          {processingSteps.map((step, index) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.label}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.2, duration: 0.4 }}
                className="flex items-center gap-4 p-4 rounded-xl"
                style={{
                  background: 'linear-gradient(90deg, rgba(0, 0, 0, 0.3) 0%, rgba(0, 0, 0, 0.1) 100%)',
                  border: '1px solid rgba(255, 255, 255, 0.1)'
                }}
              >
                <motion.div
                  animate={{ 
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.5]
                  }}
                  transition={{ 
                    duration: 1.5, 
                    repeat: Infinity,
                    delay: index * 0.3
                  }}
                >
                  <Icon className="w-6 h-6" style={{ color: step.color }} />
                </motion.div>
                
                <div className="flex-1">
                  <div 
                    className="text-sm font-medium"
                    style={{ color: '#F5F5F7' }}
                  >
                    {step.label}
                  </div>
                </div>

                {/* Animated Progress Dots */}
                <div className="flex gap-1">
                  {[0, 1, 2].map((dot) => (
                    <motion.div
                      key={dot}
                      animate={{
                        opacity: [0.3, 1, 0.3],
                        scale: [0.8, 1, 0.8]
                      }}
                      transition={{
                        duration: 1,
                        repeat: Infinity,
                        delay: dot * 0.2 + index * 0.3
                      }}
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: step.color }}
                    />
                  ))}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Progress Bar */}
        <div 
          className="mt-8 h-2 rounded-full overflow-hidden"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
        >
          <motion.div
            className="h-full rounded-full"
            style={{
              background: 'linear-gradient(90deg, #0A84FF 0%, #5AC8FA 50%, #32D74B 100%)'
            }}
            initial={{ width: '0%' }}
            animate={{ width: '100%' }}
            transition={{ 
              duration: 3,
              ease: 'easeInOut'
            }}
          />
        </div>
      </div>
    </motion.div>
  );
}

