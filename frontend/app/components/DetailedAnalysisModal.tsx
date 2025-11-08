'use client';

import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import { useModal } from '../context/ModalContext';

// Annual Summary Widget Component
function AnnualSummaryWidget({ data }: { data: any }) {
  if (!data) return null;

  const { metadata, summary, time_segments, annual_highlights, version_adaptation, champion_pool_evolution, growth_metrics } = data;

  // Calculate average KDA from growth_metrics if available
  const avgKDA = growth_metrics?.kda_adj ?
    ((growth_metrics.kda_adj.early + growth_metrics.kda_adj.late) / 2) :
    null;

  // Convert tri_period data to array format for display
  const timeSegmentsList = time_segments?.tri_period ? [
    {
      label: `Early (${time_segments.tri_period.early?.patches?.length || 0} patches)`,
      games: time_segments.tri_period.early?.total_games || 0,
      winrate: (time_segments.tri_period.early?.winrate || 0) * 100
    },
    {
      label: `Mid (${time_segments.tri_period.mid?.patches?.length || 0} patches)`,
      games: time_segments.tri_period.mid?.total_games || 0,
      winrate: (time_segments.tri_period.mid?.winrate || 0) * 100
    },
    {
      label: `Late (${time_segments.tri_period.late?.patches?.length || 0} patches)`,
      games: time_segments.tri_period.late?.total_games || 0,
      winrate: (time_segments.tri_period.late?.winrate || 0) * 100
    }
  ] : [];

  // Extract highlight strings from annual_highlights object
  const highlightStrings: string[] = [];
  if (annual_highlights?.best_champion_role) {
    const bcr = annual_highlights.best_champion_role;
    highlightStrings.push(`🏆 Best Performance: Champion ID ${bcr.champion_id} (${bcr.role}) - ${(bcr.winrate * 100).toFixed(1)}% WR in ${bcr.games} games`);
  }
  if (annual_highlights?.most_played_champion) {
    const mpc = annual_highlights.most_played_champion;
    highlightStrings.push(`🎮 Most Played: Champion ID ${mpc.champion_id} - ${mpc.total_games} games`);
  }
  if (annual_highlights?.best_quarter) {
    const bq = annual_highlights.best_quarter;
    highlightStrings.push(`📈 Best Quarter: ${bq.quarter} - ${(bq.winrate * 100).toFixed(1)}% WR in ${bq.games} games`);
  }

  return (
    <div className="mb-6 space-y-4">
      {/* Summary Header */}
      <div className="fluid-glass rounded-xl p-6 border border-white/10">
        <h3 className="text-xl font-bold mb-4" style={{ color: '#5AC8FA' }}>
          📊 Annual Overview
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
                <div className="text-2xl font-bold" style={{ color: (summary.overall_winrate || 0) * 100 >= 50 ? '#34C759' : '#FF453A' }}>
                  {summary.overall_winrate ? `${(summary.overall_winrate * 100).toFixed(1)}%` : 'N/A'}
                </div>
                <div className="text-sm text-gray-400 mt-1">Win Rate</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }}>
                <div className="text-2xl font-bold" style={{ color: '#5AC8FA' }}>
                  {avgKDA ? avgKDA.toFixed(2) : 'N/A'}
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
      {timeSegmentsList.length > 0 && (
        <div className="fluid-glass rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-bold mb-4" style={{ color: '#5AC8FA' }}>
            📅 Time Period Analysis
          </h3>
          <div className="space-y-3">
            {timeSegmentsList.map((segment: any, idx: number) => (
              <div key={idx} className="flex items-center gap-4 p-3 rounded-lg" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
                <div className="flex-1">
                  <div className="font-medium" style={{ color: '#F5F5F7' }}>
                    {segment.label}
                  </div>
                  <div className="text-sm text-gray-400">
                    {segment.games} games • {segment.winrate.toFixed(1)}% WR
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${segment.winrate}%`,
                        backgroundColor: segment.winrate >= 50 ? '#34C759' : '#FF453A'
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
      {highlightStrings.length > 0 && (
        <div className="fluid-glass rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-bold mb-4" style={{ color: '#5AC8FA' }}>
            ⭐ Annual Highlights
          </h3>
          <div className="space-y-2">
            {highlightStrings.map((highlight: string, idx: number) => (
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

  // Convert winrate from decimal to percentage if needed
  const earlyWinrate = early_half?.winrate !== undefined ? (early_half.winrate * 100) :
                       early_half?.win_rate !== undefined ? early_half.win_rate : null;
  const lateWinrate = late_half?.winrate !== undefined ? (late_half.winrate * 100) :
                      late_half?.win_rate !== undefined ? late_half.win_rate : null;

  return (
    <div className="mb-6 space-y-4">
      {/* Early vs Late Comparison */}
      {early_half && late_half && (
        <div className="fluid-glass rounded-xl p-6 border border-white/10">
          <h3 className="text-xl font-bold mb-4" style={{ color: '#5AC8FA' }}>
            📈 Progress Tracker
          </h3>
          <div className="grid grid-cols-2 gap-6">
            {/* Early Half */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'rgba(90, 200, 250, 0.1)' }}>
              <div className="text-lg font-bold mb-3" style={{ color: '#5AC8FA' }}>
                Early Period
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Win Rate</span>
                  <span className="font-medium" style={{ color: earlyWinrate && earlyWinrate >= 50 ? '#34C759' : '#FF453A' }}>
                    {earlyWinrate ? `${earlyWinrate.toFixed(1)}%` : 'N/A'}
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
                Late Period
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Win Rate</span>
                  <span className="font-medium" style={{ color: lateWinrate && lateWinrate >= 50 ? '#34C759' : '#FF453A' }}>
                    {lateWinrate ? `${lateWinrate.toFixed(1)}%` : 'N/A'}
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
            💪 Improvement Metrics
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
              <div className="text-2xl font-bold" style={{
                color: (improvement.win_rate_delta || improvement.winrate_delta || 0) >= 0 ? '#34C759' : '#FF453A'
              }}>
                {(improvement.win_rate_delta || improvement.winrate_delta || 0) >= 0 ? '+' : ''}
                {(improvement.win_rate_delta || improvement.winrate_delta) ?
                  (improvement.win_rate_delta || improvement.winrate_delta).toFixed(1) : '0.0'}%
              </div>
              <div className="text-sm text-gray-400 mt-1">Win Rate Change</div>
            </div>
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
              <div className="text-2xl font-bold" style={{
                color: (improvement.kda_delta || 0) >= 0 ? '#34C759' : '#FF453A'
              }}>
                {(improvement.kda_delta || 0) >= 0 ? '+' : ''}
                {improvement.kda_delta ? improvement.kda_delta.toFixed(2) : '0.00'}
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
  const { setIsModalOpen } = useModal();

  useEffect(() => {
    setIsModalOpen(isOpen);
    // Ensure state is reset when component unmounts
    return () => {
      setIsModalOpen(false);
    };
  }, [isOpen, setIsModalOpen]);

  const handleClose = () => {
    setIsModalOpen(false);
    onClose();
  };

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
            onClick={handleClose}
            className="fixed inset-0 bg-black/80 backdrop-blur-md z-50"
          />

              {/* Modal */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
                style={{ zIndex: 9999 }}
              >
            <div
              className="rounded-2xl shadow-2xl max-w-4xl w-full max-h-[85vh] flex flex-col pointer-events-auto overflow-hidden"
              onClick={(e) => e.stopPropagation()}
              style={{
                backgroundColor: 'rgba(28, 28, 30, 0.98)',
                backdropFilter: 'blur(40px)',
                border: '1px solid rgba(255, 255, 255, 0.15)'
              }}
            >
              {/* Header */}
              <div className="relative p-6 border-b border-white/10 z-10">
                <div className="text-center pointer-events-none">
                  <ShinyText
                    text={agentName}
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-1" style={{ color: '#8E8E93' }}>
                    {agentDescription}
                  </p>
                </div>

                {/* Close Button */}
                <button
                  onClick={handleClose}
                  className="absolute top-6 right-6 p-2 rounded-lg border transition-all backdrop-blur-sm hover:opacity-80"
                  style={{
                    backgroundColor: 'rgba(255, 69, 58, 0.15)',
                    borderColor: 'rgba(255, 69, 58, 0.3)',
                    color: '#FF453A',
                    zIndex: 20
                  }}
                  title="Close"
                >
                  <X className="w-5 h-5" />
                </button>
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

            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
