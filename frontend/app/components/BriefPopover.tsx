'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Info } from 'lucide-react';

interface BriefPopoverProps {
  /** The one-liner text to display */
  oneLiner: string;
  /** The brief summary to show in the popover */
  brief: string;
  /** Optional: Custom className for the trigger */
  className?: string;
  /** Optional: Position preference */
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export default function BriefPopover({
  oneLiner,
  brief,
  className = '',
  position = 'top'
}: BriefPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Calculate popover position based on trigger element
  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let top = 0;
      let left = 0;

      switch (position) {
        case 'top':
          top = triggerRect.top - 10; // Offset above trigger
          left = triggerRect.left + triggerRect.width / 2;
          break;
        case 'bottom':
          top = triggerRect.bottom + 10; // Offset below trigger
          left = triggerRect.left + triggerRect.width / 2;
          break;
        case 'left':
          top = triggerRect.top + triggerRect.height / 2;
          left = triggerRect.left - 10;
          break;
        case 'right':
          top = triggerRect.top + triggerRect.height / 2;
          left = triggerRect.right + 10;
          break;
      }

      // Ensure popover stays within viewport
      if (popoverRef.current) {
        const popoverRect = popoverRef.current.getBoundingClientRect();

        // Adjust horizontal position
        if (left + popoverRect.width / 2 > viewportWidth - 20) {
          left = viewportWidth - popoverRect.width / 2 - 20;
        }
        if (left - popoverRect.width / 2 < 20) {
          left = popoverRect.width / 2 + 20;
        }

        // Adjust vertical position
        if (top + popoverRect.height > viewportHeight - 20) {
          top = triggerRect.top - popoverRect.height - 10;
        }
        if (top < 20) {
          top = triggerRect.bottom + 10;
        }
      }

      setPopoverPosition({ top, left });
    }
  }, [isOpen, position]);

  return (
    <>
      {/* Trigger Element */}
      <div
        ref={triggerRef}
        className={`cursor-help inline-flex items-center gap-2 ${className}`}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
      >
        <span className="text-sm font-medium truncate">{oneLiner}</span>
        <Info className="w-3.5 h-3.5 flex-shrink-0 opacity-60" />
      </div>

      {/* Popover */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={popoverRef}
            initial={{ opacity: 0, scale: 0.95, y: position === 'top' ? 10 : -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: position === 'top' ? 10 : -10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="fixed z-50 pointer-events-none"
            style={{
              top: `${popoverPosition.top}px`,
              left: `${popoverPosition.left}px`,
              transform: 'translate(-50%, -100%)',
              maxWidth: '320px',
              width: 'max-content'
            }}
          >
            <div
              className="rounded-xl p-4 shadow-2xl backdrop-blur-xl border"
              style={{
                backgroundColor: 'rgba(20, 20, 30, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.15)',
                boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4), 0 0 1px rgba(255, 255, 255, 0.1) inset'
              }}
            >
              {/* Arrow */}
              <div
                className="absolute w-3 h-3 rotate-45"
                style={{
                  bottom: '-6px',
                  left: '50%',
                  transform: 'translateX(-50%) rotate(45deg)',
                  backgroundColor: 'rgba(20, 20, 30, 0.95)',
                  borderRight: '1px solid rgba(255, 255, 255, 0.15)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.15)'
                }}
              />

              {/* Content */}
              <div className="relative z-10">
                <p
                  className="text-sm leading-relaxed whitespace-pre-wrap"
                  style={{ color: '#F5F5F7' }}
                >
                  {brief}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
