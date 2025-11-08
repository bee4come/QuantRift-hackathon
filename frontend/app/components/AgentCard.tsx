'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon, Loader2, AlertCircle, ChevronRight } from 'lucide-react';
import styled from 'styled-components';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import BriefPopover from './BriefPopover';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

export type AgentStatus =
  | 'idle'
  | 'generating'
  | 'ready'
  | 'error';

export interface TimeRangeOption {
  id: string;
  label: string;
  value: string;
  description?: string;
}

interface SubOption {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
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
  subOptions?: SubOption[];
  onSubOptionClick?: (subOptionId: string) => void;
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
  onTimeRangeChange,
  subOptions,
  onSubOptionClick
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

  const getButtonText = () => {
    if (isLoading) return 'Generating...';
    if (canView) return 'View Report';
    if (canGenerate) return 'Generate Analysis';
    return 'More info';
  };

  return (
    <StyledWrapper $isLight={colors.isLight}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card"
        style={{
          borderColor: status === 'ready' ? '#32D74B' : status === 'error' ? '#FF453A' : status === 'generating' ? colors.accentBlue : 'rgba(255, 255, 255, 0.1)'
        }}
      >
        <div className="card-details">
          <div className="text-title-wrapper">
            <Icon className="card-icon" style={{ color: getStatusColor() }} />
            {isLoading && (
              <Loader2
                className="card-loading"
                style={{ color: colors.accentBlue }}
              />
            )}
            <p className="text-title">{name}</p>
          </div>
          <p className="text-body">{description}</p>

          {/* Error Display */}
          {error && status === 'error' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="error-display"
            >
              <div className="flex items-center gap-2 mb-1">
                <AlertCircle className="w-3 h-3" style={{ color: '#FF453A' }} />
                <p className="text-xs font-semibold" style={{ color: '#FF453A' }}>
                  Error
                </p>
              </div>
              <p className="text-xs" style={{ color: '#FF453A' }}>
                {error}
              </p>
            </motion.div>
          )}

          {/* Time Range Selector */}
          {timeRangeOptions && timeRangeOptions.length > 0 && (
            <div className="time-range-wrapper">
              <select
                value={selectedTimeRange || ''}
                onChange={(e) => onTimeRangeChange?.(e.target.value)}
                disabled={status === 'generating'}
                className="time-range-select"
              >
                {timeRangeOptions.map((option) => (
                  <option key={option.id} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Sub-Options */}
          {subOptions && subOptions.length > 0 && (
            <div className="sub-options-grid">
              {subOptions.map((subOption) => (
                <button
                  key={subOption.id}
                  onClick={() => onSubOptionClick?.(subOption.id)}
                  disabled={isLoading}
                  className="sub-option-button"
                >
                  <subOption.icon className="w-5 h-5" />
                  <span>{subOption.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Main Action Button - appears only on hover */}
        {!subOptions && (
          <button
            className="card-button"
            onClick={onGenerate}
            disabled={isLoading || (!canGenerate && !canView)}
            style={{
              backgroundColor: canView ? '#32D74B' : colors.accentBlue
            }}
          >
            {getButtonText()}
          </button>
        )}
      </motion.div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div<{ $isLight: boolean }>`
  .card {
    width: 100%;
    height: 180px;
    border-radius: 20px;
    background: ${props => props.$isLight 
      ? 'rgba(255, 255, 255, 0.15)' 
      : 'rgba(28, 28, 30, 0.8)'};
    position: relative;
    padding: 1.2rem;
    border: 2px solid ${props => props.$isLight 
      ? 'rgba(255, 255, 255, 0.2)' 
      : 'rgba(255, 255, 255, 0.1)'};
    transition: 0.5s ease-out;
    overflow: visible;
    backdrop-filter: blur(10px);
    box-shadow: ${props => props.$isLight
      ? `0 20px 60px 0 rgba(0, 0, 0, 0.5),
         0 4px 12px 0 rgba(0, 0, 0, 0.2),
         0 2px 0 0 rgba(255, 255, 255, 0.25) inset,
         0 -2px 0 0 rgba(0, 0, 0, 0.1) inset,
         0 0 0 1px rgba(255, 255, 255, 0.1) inset`
      : `0 20px 60px 0 rgba(0, 0, 0, 0.7),
         0 4px 12px 0 rgba(0, 0, 0, 0.3),
         0 2px 0 0 rgba(255, 255, 255, 0.15) inset,
         0 -2px 0 0 rgba(0, 0, 0, 0.2) inset,
         0 0 0 1px rgba(255, 255, 255, 0.08) inset`};
  }

  .card-details {
    color: #F5F5F7;
    height: 100%;
    gap: 0.5em;
    display: grid;
    place-content: start;
    text-align: left;
    width: 100%;
    box-sizing: border-box;
  }

  .text-title-wrapper {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .card-icon {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
  }

  .card-loading {
    width: 16px;
    height: 16px;
    animation: spin 1s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .card-button {
    transform: translate(-50%, 125%);
    width: 60%;
    border-radius: 1rem;
    border: none;
    color: #fff;
    font-size: 1rem;
    font-weight: 600;
    padding: 0.5rem 1rem;
    position: absolute;
    left: 50%;
    bottom: 0;
    opacity: 0;
    transition: 0.3s ease-out;
    cursor: pointer;
    pointer-events: auto;
  }

  .card-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .text-body {
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.875rem;
    margin-top: 0.25rem;
    text-align: left;
  }

  .text-title {
    font-size: 1.25em;
    font-weight: bold;
    color: #F5F5F7;
    margin: 0;
    text-align: left;
  }

  .error-display {
    margin-top: 0.5rem;
    padding: 0.5rem;
    border-radius: 0.5rem;
    background: rgba(255, 69, 58, 0.15);
    border: 1px solid rgba(255, 69, 58, 0.3);
  }

  .time-range-wrapper {
    margin-top: 0.75rem;
    width: 100%;
  }

  .time-range-select {
    width: 100%;
    padding: 0.5rem;
    border-radius: 0.5rem;
    background: ${props => props.$isLight 
      ? 'rgba(255, 255, 255, 0.1)' 
      : 'rgba(255, 255, 255, 0.05)'};
    border: 1px solid ${props => props.$isLight 
      ? 'rgba(255, 255, 255, 0.2)' 
      : 'rgba(255, 255, 255, 0.1)'};
    color: #F5F5F7;
    font-size: 0.875rem;
    text-align: center;
    text-align-last: center;
    box-sizing: border-box;
  }

  .time-range-select option {
    text-align: center;
  }

  .time-range-select:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .sub-options-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
    margin-top: 0.75rem;
    width: 100%;
    box-sizing: border-box;
    padding: 0;
  }

  .sub-option-button {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem;
    border-radius: 0.5rem;
    background: ${props => props.$isLight 
      ? 'rgba(0, 122, 255, 0.2)' 
      : 'rgba(10, 132, 255, 0.2)'};
    border: 1px solid ${props => props.$isLight 
      ? 'rgba(0, 122, 255, 0.4)' 
      : 'rgba(10, 132, 255, 0.4)'};
    color: #F5F5F7;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
    overflow: hidden;
    text-align: center;
    word-wrap: break-word;
    white-space: normal;
  }

  .sub-option-button svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }

  .sub-option-button span {
    width: auto;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    line-height: 1.2;
  }

  @media (max-width: 640px) {
    .sub-option-button {
      padding: 0.6rem 0.4rem;
      font-size: 0.65rem;
      gap: 0.4rem;
    }
    
    .sub-options-grid {
      gap: 0.4rem;
    }
  }

  .sub-option-button:hover:not(:disabled) {
    background: ${props => props.$isLight 
      ? 'rgba(0, 122, 255, 0.3)' 
      : 'rgba(10, 132, 255, 0.3)'};
  }

  .sub-option-button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  /* Hover effects */
  .card:hover {
    border-color: ${props => props.$isLight ? '#007AFF' : '#0A84FF'};
    transform: translateY(-2px);
    box-shadow: ${props => props.$isLight 
      ? `0 25px 80px 0 rgba(0, 0, 0, 0.6),
         0 6px 16px 0 rgba(0, 0, 0, 0.25),
         0 3px 0 0 rgba(255, 255, 255, 0.3) inset,
         0 -3px 0 0 rgba(0, 0, 0, 0.15) inset,
         0 0 0 1px rgba(255, 255, 255, 0.15) inset` 
      : `0 25px 80px 0 rgba(0, 0, 0, 0.8),
         0 6px 16px 0 rgba(0, 0, 0, 0.4),
         0 3px 0 0 rgba(255, 255, 255, 0.2) inset,
         0 -3px 0 0 rgba(0, 0, 0, 0.25) inset,
         0 0 0 1px rgba(255, 255, 255, 0.1) inset`};
  }

  .card:hover .card-button {
    transform: translate(-50%, 50%);
    opacity: 1;
  }
`;
