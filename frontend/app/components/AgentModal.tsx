'use client';

import React from 'react';
import { X, Sparkles } from 'lucide-react';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import ShinyText from './ui/ShinyText';
import GlareHover from './ui/GlareHover';

interface AgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  agentData?: {
    one_liner?: string;
    brief?: string;
    detailed?: string;
  };
  loading?: boolean;
  children?: React.ReactNode;
}

export default function AgentModal({
  isOpen,
  onClose,
  title,
  agentData,
  loading = false,
  children
}: AgentModalProps) {
  const colors = useAdaptiveColors();

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-6xl max-h-[90vh] overflow-y-auto rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
          <div className="fluid-glass p-6 md:p-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Sparkles size={24} style={{ color: colors.accentBlue }} />
                <ShinyText text={title} speed={3} className="text-2xl md:text-3xl font-bold" />
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg transition-all hover:bg-white/10"
                style={{ color: colors.textSecondary }}
              >
                <X size={24} />
              </button>
            </div>

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <div
                    className="w-12 h-12 border-4 border-t-transparent rounded-full animate-spin mx-auto mb-4"
                    style={{ borderColor: colors.accentBlue, borderTopColor: 'transparent' }}
                  />
                  <p style={{ color: colors.textSecondary }}>Generating analysis...</p>
                </div>
              </div>
            )}

            {/* Content */}
            {!loading && (
              <div className="space-y-6">
                {/* AI Analysis Section */}
                {agentData && (
                  <div className="space-y-4">
                    {/* One-liner */}
                    {agentData.one_liner && (
                      <div
                        className="p-4 rounded-lg"
                        style={{ backgroundColor: 'rgba(10, 132, 255, 0.1)' }}
                      >
                        <p
                          style={{ color: colors.accentBlue }}
                          className="font-semibold text-lg"
                        >
                          {agentData.one_liner}
                        </p>
                      </div>
                    )}

                    {/* Detailed Report (collapsible) */}
                    {agentData.detailed && (
                      <details className="group">
                        <summary
                          className="cursor-pointer font-semibold p-3 rounded-lg transition-all hover:bg-white/5"
                          style={{ color: colors.accentBlue }}
                        >
                          📄 View Detailed Analysis
                        </summary>
                        <div
                          className="p-4 rounded-lg mt-2 whitespace-pre-wrap"
                          style={{
                            backgroundColor: 'rgba(0, 0, 0, 0.3)',
                            color: colors.textSecondary,
                            fontSize: '0.9rem',
                            lineHeight: '1.6'
                          }}
                        >
                          {agentData.detailed}
                        </div>
                      </details>
                    )}
                  </div>
                )}

                {/* Additional Content (Charts, etc.) */}
                {children && (
                  <div className="mt-6">
                    {children}
                  </div>
                )}
              </div>
            )}
          </div>
        </GlareHover>
      </div>
    </div>
  );
}
