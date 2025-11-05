'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useTimeOfDay, timeGradients } from '../hooks/useTimeOfDay';
import { useServerContext } from '../context/ServerContext';
import Galaxy from './ui/Galaxy';

export default function DynamicBackground() {
  const { currentTimezone, selectedServer } = useServerContext();
  const timeOfDay = useTimeOfDay(currentTimezone);
  const { gradient, ambientLight } = timeGradients[timeOfDay];

  const [currentGradient, setCurrentGradient] = useState(gradient);
  const [currentAmbient, setCurrentAmbient] = useState(ambientLight);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    setCurrentGradient(gradient);
    setCurrentAmbient(ambientLight);
  }, [gradient, ambientLight, timeOfDay, selectedServer.code]);

  const isNightTime = timeOfDay === 'night' || timeOfDay === 'early-evening' || timeOfDay === 'midnight' || 
                      timeOfDay === 'before-dawn' || timeOfDay === 'dawn' || timeOfDay === 'sunrise';

  // Use black gradient for night time
  const displayGradient = isNightTime 
    ? 'linear-gradient(135deg, #000000 0%, #0a0a0c 50%, #000000 100%)'
    : currentGradient;
  
  const displayAmbient = isNightTime
    ? 'radial-gradient(circle at 50% 50%, transparent 0%, transparent 100%)'
    : currentAmbient;

  return (
    <>
      {/* Main background - smoothly transitions to black for night */}
      <motion.div
        key={`bg-${selectedServer.code}-${timeOfDay}`}
        className="fixed inset-0"
        style={{ zIndex: -20 }}
        initial={false}
        animate={{
          background: displayGradient
        }}
        transition={isMounted ? { duration: 3, ease: [0.4, 0, 0.2, 1] } : { duration: 0 }}
      />
      <motion.div
        key={`ambient-${selectedServer.code}-${timeOfDay}`}
        className="fixed inset-0 pointer-events-none"
        style={{ zIndex: -19 }}
        initial={false}
        animate={{
          background: displayAmbient
        }}
        transition={isMounted ? { duration: 3, ease: [0.4, 0, 0.2, 1] } : { duration: 0 }}
      />
      
      {/* Galaxy starfield layer - always rendered, fades in at night */}
      <motion.div 
        className="fixed inset-0"
        style={{ zIndex: -18 }}
        initial={false}
        animate={{ 
          opacity: isNightTime ? 1 : 0
        }}
        transition={{ 
          opacity: { duration: 3, ease: [0.4, 0, 0.2, 1] }
        }}
      >
        <div style={{ 
          width: '100%', 
          height: '100%',
          pointerEvents: isNightTime ? 'auto' : 'none'
        }}>
          <Galaxy
            density={1.2}
            starSpeed={0.3}
            glowIntensity={0}
            twinkleIntensity={0}
            rotationSpeed={0.05}
            mouseInteraction={true}
            mouseRepulsion={true}
            repulsionStrength={1.5}
            transparent={true}
            hueShift={200}
            saturation={0.1}
          />
        </div>
      </motion.div>
    </>
  );
}

