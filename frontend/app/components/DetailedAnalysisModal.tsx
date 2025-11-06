'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

// Annual Summary Widget Component
function AnnualSummaryWidget({ data }: { data: any }) {
  if (!data) return null;

  const { metadata, summary, time_segments, annual_highlights, version_adaptation, champion_pool_evolution } = data;

  return (
    <div className="mb-6 space-y-4">
      {/* Summary Header */}
      <div className="fluid-glass rounded-xl p-6 border border-white/10">
        <h3 className="text-xl font-bold mb-4" style={{ color: '#5AC8FA' }}>
          📊 年度数据总览 Annual Overview
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {summary && (
            <>
              <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }}>
                <div className="text-2xl font-bold" style={{ color: '#5AC8FA' }}>
                  {summary.total_games || 0}
                </div>
                <div className="text-sm text-gray-400 mt-1">Total Games</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }}>
                <div className="text-2xl font-bold" style={{ color: summary.win_rate >= 50 ? '#34C759' : '#FF453A' }}>
                  {summary.win_rate ? `${summary.win_rate.toFixed(1)}%` : 'N/A'}
                </div>
                <div className="text-sm text-gray-400 mt-1">Win Rate</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }}>
                <div className="text-2xl font-bold" style={{ color: '#5AC8FA' }}>
                  {summary.kda_avg ? summary.kda_avg.toFixed(2) : 'N/A'}
                </div>
                <div className="text-sm text-gray-400 mt-1">Avg KDA</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }}>
                <div className="text-2xl font-bold" style={{ color: '#5AC8FA' }}>
                  {summary.unique_champions || 0}
                </div>
                <div className="text-sm text-gray-400 mt-1">Champions Played</div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Time Segments Visualization */}
      {time_segments && time_segments.length > 0 && (
        <div className="fluid-glass rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-bold mb-4" style={{ color: '#5AC8FA' }}>
            📅 时间段分析 Time Period Analysis
          </h3>
          <div className="space-y-3">
            {time_segments.map((segment: any, idx: number) => (
              <div key={idx} className="flex items-center gap-4 p-3 rounded-lg" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
                <div className="flex-1">
                  <div className="font-medium" style={{ color: '#F5F5F7' }}>
                    {segment.label || `Period ${idx + 1}`}
                  </div>
                  <div className="text-sm text-gray-400">
                    {segment.games || 0} games • {segment.win_rate ? `${segment.win_rate.toFixed(1)}%` : 'N/A'} WR
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${segment.win_rate || 0}%`,
                        backgroundColor: segment.win_rate >= 50 ? '#34C759' : '#FF453A'
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Highlights */}
      {annual_highlights && annual_highlights.length > 0 && (
        <div className="fluid-glass rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-bold mb-4" style={{ color: '#5AC8FA' }}>
            ⭐ 年度亮点 Annual Highlights
          </h3>
          <div className="space-y-2">
            {annual_highlights.map((highlight: string, idx: number) => (
              <div key={idx} className="flex items-start gap-3 p-3 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.05)' }}>
                <span className="text-xl">✨</span>
                <span className="text-sm" style={{ color: '#F5F5F7' }}>{highlight}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Progress Tracker Widget Component
function ProgressTrackerWidget({ data }: { data: any }) {
  if (!data) return null;

  const { early_half, late_half, improvement, trend } = data;

  return (
    <div className="mb-6 space-y-4">
      {/* Early vs Late Comparison */}
      {early_half && late_half && (
        <div className="fluid-glass rounded-xl p-6 border border-white/10">
          <h3 className="text-xl font-bold mb-4" style={{ color: '#5AC8FA' }}>
            📈 进步追踪 Progress Tracker
          </h3>
          <div className="grid grid-cols-2 gap-6">
            {/* Early Half */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }}>
              <div className="text-lg font-bold mb-3" style={{ color: '#5AC8FA' }}>
                前半段 Early Period
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Win Rate</span>
                  <span className="font-medium" style={{ color: early_half.win_rate >= 50 ? '#34C759' : '#FF453A' }}>
                    {early_half.win_rate ? `${early_half.win_rate.toFixed(1)}%` : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Avg KDA</span>
                  <span className="font-medium" style={{ color: '#F5F5F7' }}>
                    {early_half.kda_avg ? early_half.kda_avg.toFixed(2) : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Games</span>
                  <span className="font-medium" style={{ color: '#F5F5F7' }}>
                    {early_half.games || 0}
                  </span>
                </div>
              </div>
            </div>

            {/* Late Half */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'rgba(52, 199, 89, 0.1)' }}>
              <div className="text-lg font-bold mb-3" style={{ color: '#34C759' }}>
                后半段 Late Period
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Win Rate</span>
                  <span className="font-medium" style={{ color: late_half.win_rate >= 50 ? '#34C759' : '#FF453A' }}>
                    {late_half.win_rate ? `${late_half.win_rate.toFixed(1)}%` : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Avg KDA</span>
                  <span className="font-medium" style={{ color: '#F5F5F7' }}>
                    {late_half.kda_avg ? late_half.kda_avg.toFixed(2) : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Games</span>
                  <span className="font-medium" style={{ color: '#F5F5F7' }}>
                    {late_half.games || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Improvement Metrics */}
      {improvement && (
        <div className="fluid-glass rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-bold mb-4" style={{ color: '#5AC8FA' }}>
            💪 进步指标 Improvement Metrics
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
              <div className="text-2xl font-bold" style={{
                color: improvement.win_rate_delta >= 0 ? '#34C759' : '#FF453A'
              }}>
                {improvement.win_rate_delta >= 0 ? '+' : ''}{improvement.win_rate_delta ? improvement.win_rate_delta.toFixed(1) : '0'}%
              </div>
              <div className="text-sm text-gray-400 mt-1">Win Rate Change</div>
            </div>
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
              <div className="text-2xl font-bold" style={{
                color: improvement.kda_delta >= 0 ? '#34C759' : '#FF453A'
              }}>
                {improvement.kda_delta >= 0 ? '+' : ''}{improvement.kda_delta ? improvement.kda_delta.toFixed(2) : '0.00'}
              </div>
              <div className="text-sm text-gray-400 mt-1">KDA Change</div>
            </div>
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
              <div className="text-2xl font-bold" style={{ color: '#5AC8FA' }}>
                {trend || 'Stable'}
              </div>
              <div className="text-sm text-gray-400 mt-1">Trend</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface DetailedAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId?: string;
  agentName: string;
  agentDescription: string;
  detailedReport: string;
  analysisData?: any;
}

export default function DetailedAnalysisModal({
  isOpen,
  onClose,
  agentId,
  agentName,
  agentDescription,
  detailedReport,
  analysisData
}: DetailedAnalysisModalProps) {
  const colors = useAdaptiveColors();

  const handleDownload = () => {
    const blob = new Blob([detailedReport], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${agentName.replace(/\s+/g, '_')}_Analysis.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div
              className="fluid-glass rounded-2xl shadow-2xl max-w-4xl w-full max-h-[85vh] flex flex-col pointer-events-auto overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-white/10">
                <div>
                  <ShinyText
                    text={agentName}
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-1" style={{ color: '#8E8E93' }}>
                    {agentDescription}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {/* Download Button */}
                  <ClickSpark
                    sparkColor={colors.accentBlue}
                    sparkSize={6}
                    sparkRadius={10}
                    sparkCount={4}
                    duration={250}
                    inline={true}
                  >
                    <button
                      onClick={handleDownload}
                      className="p-2 rounded-lg border transition-all backdrop-blur-sm"
                      style={{
                        backgroundColor: 'rgba(10, 132, 255, 0.15)',
                        borderColor: 'rgba(10, 132, 255, 0.3)',
                        color: '#5AC8FA'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.25)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(10, 132, 255, 0.15)';
                      }}
                      title="Download Report"
                    >
                      <Download className="w-5 h-5" />
                    </button>
                  </ClickSpark>

                  {/* Close Button */}
                  <ClickSpark
                    sparkColor="#FF453A"
                    sparkSize={6}
                    sparkRadius={10}
                    sparkCount={4}
                    duration={250}
                    inline={true}
                  >
                    <button
                      onClick={onClose}
                      className="p-2 rounded-lg border transition-all backdrop-blur-sm"
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
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </ClickSpark>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {/* Render Widgets Above Report (Annual Summary & Progress Tracker) */}
                {agentId === 'annual-summary' && analysisData && (
                  <AnnualSummaryWidget data={analysisData} />
                )}
                {agentId === 'progress-tracker' && analysisData && (
                  <ProgressTrackerWidget data={analysisData} />
                )}

                <div
                  className="prose prose-invert max-w-none markdown-body"
                  style={{
                    color: '#F5F5F7',
                    fontSize: '0.95rem',
                    lineHeight: '1.7'
                  }}
                >
                  {/* Render markdown content with proper table support */}
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ node, ...props }) => (
                        <h1 className="text-3xl font-bold mt-8 mb-4" style={{ color: '#5AC8FA' }} {...props} />
                      ),
                      h2: ({ node, ...props }) => (
                        <h2 className="text-2xl font-bold mt-8 mb-4" style={{ color: '#5AC8FA' }} {...props} />
                      ),
                      h3: ({ node, ...props }) => (
                        <h3 className="text-xl font-bold mt-6 mb-3" style={{ color: '#5AC8FA' }} {...props} />
                      ),
                      table: ({ node, ...props }) => (
                        <div className="overflow-x-auto my-6">
                          <table className="w-full border-collapse" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }} {...props} />
                        </div>
                      ),
                      thead: ({ node, ...props }) => (
                        <thead style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }} {...props} />
                      ),
                      th: ({ node, ...props }) => (
                        <th className="border px-4 py-2 text-left font-semibold" style={{
                          borderColor: 'rgba(255, 255, 255, 0.2)',
                          color: '#5AC8FA'
                        }} {...props} />
                      ),
                      td: ({ node, ...props }) => (
                        <td className="border px-4 py-2" style={{
                          borderColor: 'rgba(255, 255, 255, 0.1)',
                          color: '#F5F5F7'
                        }} {...props} />
                      ),
                      tr: ({ node, ...props }) => (
                        <tr className="hover:bg-white/5 transition-colors" {...props} />
                      ),
                      strong: ({ node, ...props }) => (
                        <strong style={{ color: '#5AC8FA', fontWeight: '600' }} {...props} />
                      ),
                      li: ({ node, ...props }) => (
                        <li className="ml-4 my-2" {...props} />
                      ),
                      code: ({ node, inline, ...props }: any) => (
                        inline ? (
                          <code className="px-1.5 py-0.5 rounded" style={{
                            backgroundColor: 'rgba(90, 200, 250, 0.15)',
                            color: '#5AC8FA',
                            fontSize: '0.9em'
                          }} {...props} />
                        ) : (
                          <code className="block p-4 rounded-lg my-4" style={{
                            backgroundColor: 'rgba(0, 0, 0, 0.3)',
                            color: '#F5F5F7'
                          }} {...props} />
                        )
                      ),
                    }}
                  >
                    {detailedReport}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-end gap-3 p-6 border-t border-white/10">
                <ClickSpark
                  sparkColor="#FF453A"
                  sparkSize={8}
                  sparkRadius={12}
                  sparkCount={6}
                  duration={300}
                >
                  <button
                    onClick={onClose}
                    className="px-6 py-2.5 rounded-lg border font-medium transition-all backdrop-blur-sm"
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
                  >
                    <ShinyText text="Close" speed={2} className="text-sm font-medium" />
                  </button>
                </ClickSpark>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
