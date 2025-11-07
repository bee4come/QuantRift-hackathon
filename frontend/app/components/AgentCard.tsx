'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon, Loader2, AlertCircle, ChevronRight } from 'lucide-react';
import GlareHover from './ui/GlareHover';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import BriefPopover from './BriefPopover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

export type AgentStatus =
  | 'idle'
  | 'generating'
  | 'ready'
  | 'error';

interface TimeRangeOption {
  id: string;
  label: string;
  value: string;
  description: string;
}

interface AgentCardProps {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  status: AgentStatus;
  detailedReport?: string;
  error?: string;
  onGenerate: () => void;
  timeRangeOptions?: TimeRangeOption[];
  selectedTimeRange?: string;
  onTimeRangeChange?: (timeRange: string) => void;
}

export default function AgentCard({
  id,
  name,
  description,
  icon: Icon,
  status,
  detailedReport,
  error,
  onGenerate,
  timeRangeOptions,
  selectedTimeRange,
  onTimeRangeChange
}: AgentCardProps) {
  const colors = useAdaptiveColors();

  const getStatusColor = () => {
    switch (status) {
      case 'generating':
        return colors.accentBlue;
      case 'ready':
        return '#32D74B'; // Green
      case 'error':
        return '#FF453A'; // Red
      default:
        return '#8E8E93'; // Gray
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'generating':
        return 'Generating Analysis...';
      case 'ready':
        return 'Analysis Ready';
      case 'error':
        return 'Analysis Failed';
      default:
        return 'Click to Analyze';
    }
  };

  const isLoading = status === 'generating';
  const canGenerate = status === 'idle' || status === 'error';
  const canView = status === 'ready';

  return (
    <GlareHover
      width="100%"
      height="100%"
      background="rgba(0, 0, 0, 0.2)"
      borderRadius="16px"
      borderColor="rgba(255, 255, 255, 0.1)"
      glareColor="#ffffff"
      glareOpacity={0.15}
      glareAngle={-45}
      glareSize={150}
      transitionDuration={400}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="fluid-glass rounded-2xl p-5 h-full flex flex-col shadow-xl hover:shadow-2xl transition-all duration-300"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-3 relative z-10">
          <div className="flex items-center gap-3">
            <div
              className="p-2 rounded-lg"
              style={{
                backgroundColor: `${getStatusColor()}20`,
                border: `1px solid ${getStatusColor()}40`
              }}
            >
              <Icon className="w-5 h-5" style={{ color: getStatusColor() }} />
            </div>
            <div>
              <ShinyText
                text={name}
                speed={3}
                className="text-base font-bold"
              />
              <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                {description}
              </p>
            </div>
          </div>

          {/* Status indicator */}
          {isLoading && (
            <Loader2
              className="w-4 h-4 animate-spin"
              style={{ color: colors.accentBlue }}
            />
          )}
        </div>


        {/* Error Display */}
        {error && status === 'error' && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="rounded-xl p-3 mb-3 relative z-10"
            style={{
              backgroundColor: 'rgba(255, 69, 58, 0.15)',
              border: '1px solid rgba(255, 69, 58, 0.3)'
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle className="w-4 h-4" style={{ color: '#FF453A' }} />
              <p className="text-xs font-semibold" style={{ color: '#FF453A' }}>
                Error
              </p>
            </div>
            <p className="text-xs" style={{ color: '#FF453A' }}>
              {error}
            </p>
          </motion.div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Time Range Selector */}
        {timeRangeOptions && timeRangeOptions.length > 0 && (
          <div className="mb-3 relative z-10">
            <label className="text-xs font-medium mb-2 block" style={{ color: '#8E8E93' }}>
              Time Range
            </label>
            <select
              value={selectedTimeRange || ''}
              onChange={(e) => onTimeRangeChange?.(e.target.value)}
              disabled={status === 'generating'}
              className="w-full px-3 py-2 rounded-lg text-sm border backdrop-blur-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                color: '#FFFFFF'
              }}
            >
              {timeRangeOptions.map((option) => (
                <option key={option.id} value={option.value} style={{ backgroundColor: '#1C1C1E', color: '#FFFFFF' }}>
                  {option.label}
                </option>
              ))}
            </select>
            {selectedTimeRange && timeRangeOptions.find(opt => opt.value === selectedTimeRange) && (
              <p className="text-xs mt-1" style={{ color: '#8E8E93' }}>
                {timeRangeOptions.find(opt => opt.value === selectedTimeRange)?.description}
              </p>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-2 relative z-10">

          {/* Generate/View Analysis Button */}
          {canGenerate && (
            <ClickSpark
              sparkColor={colors.accentBlue}
              sparkSize={8}
              sparkRadius={12}
              sparkCount={6}
              duration={300}
            >
              <button
                onClick={onGenerate}
                disabled={isLoading}
                className="w-full px-4 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed backdrop-blur-sm text-sm"
                style={{
                  backgroundColor: 'rgba(10, 132, 255, 0.2)',
                  borderColor: 'rgba(10, 132, 255, 0.4)',
                  color: '#5AC8FA'
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.3)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.2)';
                }}
              >
                <ShinyText text="Generate Analysis" speed={2} className="text-sm font-medium" />
              </button>
            </ClickSpark>
          )}

          {/* View Report Button */}
          {canView && (
            <ClickSpark
              sparkColor="#32D74B"
              sparkSize={8}
              sparkRadius={12}
              sparkCount={6}
              duration={300}
            >
              <button
                onClick={onGenerate}
                disabled={isLoading}
                className="w-full px-4 py-2.5 rounded-lg border font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed backdrop-blur-sm text-sm flex items-center justify-center gap-2"
                style={{
                  backgroundColor: 'rgba(50, 215, 75, 0.2)',
                  borderColor: 'rgba(50, 215, 75, 0.4)',
                  color: '#32D74B'
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.backgroundColor = 'rgba(50, 215, 75, 0.3)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(50, 215, 75, 0.2)';
                }}
              >
                <ShinyText text="View Report" speed={2} className="text-sm font-medium" />
                <ChevronRight className="w-4 h-4" />
              </button>
            </ClickSpark>
          )}
        </div>
      </motion.div>
    </GlareHover>
  );
}
