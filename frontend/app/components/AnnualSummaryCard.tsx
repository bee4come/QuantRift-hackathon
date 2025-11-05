'use client';

import React, { useState } from 'react';
import { Trophy, TrendingUp, TrendingDown, Star, Share2, Copy, Download } from 'lucide-react';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';
import ShinyText from './ui/ShinyText';
import GlareHover from './ui/GlareHover';
import ClickSpark from './ui/ClickSpark';
import ReactMarkdown from 'react-markdown';

interface AnnualCardData {
  season: string;
  fun_tags: string[];
  stats: {
    total_games: number;
    win_rate: number;
    unique_champions: number;
  };
  most_played: {
    champion_name: string;
    games: number;
    win_rate: number;
  };
  best_performance: {
    champion_name: string;
    role: string;
    games: number;
    win_rate: number;
  };
  core_champions: Array<{
    champion_name: string;
    games: number;
    winrate: number;
  }>;
  progress: {
    early_winrate: number;
    late_winrate: number;
    improvement: number;
  };
  share_texts: {
    twitter: string;
    casual: string;
    formal: string;
  };
  detailed_analysis?: {
    time_segments: any;
    annual_highlights: any;
    version_adaptation: any;
    champion_pool_evolution: any;
    growth_metrics?: {
      kda_adj: { early: number; late: number; growth: number; trend: string };
      obj_rate: { early: number; late: number; growth: number; trend: string };
      time_to_core: { early: number; late: number; improvement: number; trend: string };
    };
    consistency_profile?: {
      monthly_variance: number;
      variance_grade: string;
      governance_distribution: {
        CONFIDENT: { count: number; percentage: number };
        CAUTION: { count: number; percentage: number };
        CONTEXT: { count: number; percentage: number };
      };
      stability_trend: {
        early_variance: number;
        late_variance: number;
        improving: boolean;
      };
    };
    narrative_report?: string | null;  // LLM-generated comprehensive report
  };
}

interface AnnualSummaryCardProps {
  cardData: AnnualCardData;
  onShare?: (style: 'twitter' | 'casual' | 'formal') => void;
  onDownload?: () => void;
}

export default function AnnualSummaryCard({
  cardData,
  onShare,
  onDownload
}: AnnualSummaryCardProps) {
  const colors = useAdaptiveColors();
  const [selectedShareStyle, setSelectedShareStyle] = useState<'twitter' | 'casual' | 'formal'>('twitter');
  const [copySuccess, setCopySuccess] = useState(false);
  const [showFullReport, setShowFullReport] = useState(false);

  const handleCopyShareText = () => {
    const text = cardData.share_texts[selectedShareStyle];
    navigator.clipboard.writeText(text);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  const handleShare = () => {
    if (onShare) {
      onShare(selectedShareStyle);
    }
  };

  return (
    <div id="annual-summary-card" className="space-y-6">
      {/* Header - Season Info */}
      <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
        <div className="fluid-glass p-6 rounded-2xl text-center">
          <ShinyText
            text={`🎮 ${cardData.season} Season Review`}
            speed={3}
            className="text-3xl font-bold mb-4"
          />

          {/* Fun Tags */}
          <div className="flex flex-wrap justify-center gap-2 mb-6">
            {cardData.fun_tags.map((tag, index) => (
              <div
                key={index}
                className="px-4 py-2 rounded-full text-sm font-semibold"
                style={{
                  backgroundColor: 'rgba(10, 132, 255, 0.2)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  borderColor: 'rgba(10, 132, 255, 0.4)',
                  color: colors.accentBlue
                }}
              >
                {tag}
              </div>
            ))}
          </div>

          {/* Core Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-4xl font-bold mb-1" style={{ color: colors.textPrimary }}>
                {cardData.stats.total_games}
              </div>
              <p style={{ color: colors.textSecondary }} className="text-sm">Total Games</p>
            </div>
            <div>
              <div className="text-4xl font-bold mb-1" style={{ color: colors.accentGreen }}>
                {(cardData.stats.win_rate * 100).toFixed(1)}%
              </div>
              <p style={{ color: colors.textSecondary }} className="text-sm">Win Rate</p>
            </div>
            <div>
              <div className="text-4xl font-bold mb-1" style={{ color: colors.accentPurple }}>
                {cardData.stats.unique_champions}
              </div>
              <p style={{ color: colors.textSecondary }} className="text-sm">Champions</p>
            </div>
          </div>
        </div>
      </GlareHover>

      {/* Most Played & Best Performance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Most Played Champion */}
        <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
          <ClickSpark>
            <div className="fluid-glass p-6 rounded-2xl">
              <div className="flex items-center gap-2 mb-4">
                <Trophy size={20} style={{ color: colors.accentYellow }} />
                <ShinyText text="Most Played" speed={3} className="text-lg font-semibold" />
              </div>
              <div className="text-2xl font-bold mb-2" style={{ color: colors.textPrimary }}>
                {cardData.most_played.champion_name}
              </div>
              <div className="flex items-center justify-between">
                <p style={{ color: colors.textSecondary }} className="text-sm">
                  {cardData.most_played.games} games
                </p>
                <div
                  className="flex items-center gap-1"
                  style={{
                    color: cardData.most_played.win_rate > 0.5 ? colors.accentGreen : colors.accentRed
                  }}
                >
                  {cardData.most_played.win_rate > 0.5 ? (
                    <TrendingUp size={16} />
                  ) : (
                    <TrendingDown size={16} />
                  )}
                  <span className="text-sm font-medium">
                    {(cardData.most_played.win_rate * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          </ClickSpark>
        </GlareHover>

        {/* Best Performance */}
        <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
          <ClickSpark>
            <div className="fluid-glass p-6 rounded-2xl">
              <div className="flex items-center gap-2 mb-4">
                <Star size={20} style={{ color: colors.accentBlue }} />
                <ShinyText text="Best Performance" speed={3} className="text-lg font-semibold" />
              </div>
              <div className="text-2xl font-bold mb-2" style={{ color: colors.textPrimary }}>
                {cardData.best_performance.champion_name}
              </div>
              <div className="flex items-center justify-between">
                <p style={{ color: colors.textSecondary }} className="text-sm">
                  {cardData.best_performance.role} • {cardData.best_performance.games} games
                </p>
                <div
                  className="flex items-center gap-1"
                  style={{ color: colors.accentGreen }}
                >
                  <TrendingUp size={16} />
                  <span className="text-sm font-medium">
                    {(cardData.best_performance.win_rate * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          </ClickSpark>
        </GlareHover>
      </div>

      {/* Core Champions */}
      <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
        <div className="fluid-glass p-6 rounded-2xl">
          <ShinyText text="🏆 Core Champion Pool" speed={3} className="text-xl font-bold mb-4" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {cardData.core_champions.map((champ, index) => (
              <div
                key={index}
                className="fluid-glass-dark p-3 rounded-xl flex items-center justify-between"
              >
                <div>
                  <div className="font-semibold" style={{ color: colors.textPrimary }}>
                    {champ.champion_name}
                  </div>
                  <p style={{ color: colors.textSecondary }} className="text-xs">
                    {champ.games} games
                  </p>
                </div>
                <div
                  className="text-sm font-medium"
                  style={{
                    color: champ.winrate > 0.5 ? colors.accentGreen : colors.textSecondary
                  }}
                >
                  {(champ.winrate * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      </GlareHover>

      {/* Progress Comparison */}
      <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
        <div className="fluid-glass p-6 rounded-2xl">
          <ShinyText text="📈 Season Progress" speed={3} className="text-xl font-bold mb-4" />
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p style={{ color: colors.textSecondary }} className="text-sm mb-2">Early Season</p>
              <div className="text-3xl font-bold" style={{ color: colors.textPrimary }}>
                {(cardData.progress.early_winrate * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center">
              <div
                className="flex items-center justify-center gap-2 mb-2"
                style={{
                  color: cardData.progress.improvement >= 0 ? colors.accentGreen : colors.accentRed
                }}
              >
                {cardData.progress.improvement >= 0 ? (
                  <TrendingUp size={24} />
                ) : (
                  <TrendingDown size={24} />
                )}
                <span className="text-2xl font-bold">
                  {cardData.progress.improvement >= 0 ? '+' : ''}
                  {(cardData.progress.improvement * 100).toFixed(1)}%
                </span>
              </div>
              <p style={{ color: colors.textSecondary }} className="text-sm">Improvement</p>
            </div>
            <div className="text-center">
              <p style={{ color: colors.textSecondary }} className="text-sm mb-2">Late Season</p>
              <div className="text-3xl font-bold" style={{ color: colors.textPrimary }}>
                {(cardData.progress.late_winrate * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </GlareHover>

      {/* Share Section */}
      <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
        <div className="fluid-glass p-6 rounded-2xl">
          <ShinyText text="📢 Share Your Season" speed={3} className="text-xl font-bold mb-4" />

          {/* Share Style Selector */}
          <div className="flex gap-2 mb-4">
            {(['twitter', 'casual', 'formal'] as const).map((style) => (
              <button
                key={style}
                onClick={() => setSelectedShareStyle(style)}
                className="px-4 py-2 rounded-lg font-semibold transition-all"
                style={{
                  backgroundColor: selectedShareStyle === style
                    ? 'rgba(10, 132, 255, 0.3)'
                    : 'rgba(255, 255, 255, 0.1)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  borderColor: selectedShareStyle === style
                    ? 'rgba(10, 132, 255, 0.5)'
                    : 'rgba(255, 255, 255, 0.2)',
                  color: selectedShareStyle === style ? colors.accentBlue : colors.textSecondary
                }}
              >
                {style.charAt(0).toUpperCase() + style.slice(1)}
              </button>
            ))}
          </div>

          {/* Share Text Preview */}
          <div
            className="p-4 rounded-lg mb-4"
            style={{
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              borderWidth: '1px',
              borderStyle: 'solid',
              borderColor: 'rgba(255, 255, 255, 0.1)'
            }}
          >
            <p style={{ color: colors.textPrimary }} className="text-sm whitespace-pre-wrap">
              {cardData.share_texts[selectedShareStyle]}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <ClickSpark inline={true}>
              <button
                onClick={handleCopyShareText}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold transition-all"
                style={{
                  backgroundColor: copySuccess ? 'rgba(48, 209, 88, 0.3)' : 'rgba(10, 132, 255, 0.3)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  borderColor: copySuccess ? 'rgba(48, 209, 88, 0.5)' : 'rgba(10, 132, 255, 0.5)',
                  color: copySuccess ? colors.accentGreen : colors.accentBlue
                }}
              >
                <Copy size={18} />
                {copySuccess ? 'Copied!' : 'Copy Text'}
              </button>
            </ClickSpark>

            {onShare && (
              <ClickSpark inline={true}>
                <button
                  onClick={handleShare}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold transition-all"
                  style={{
                    backgroundColor: 'rgba(10, 132, 255, 0.3)',
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: 'rgba(10, 132, 255, 0.5)',
                    color: colors.accentBlue
                  }}
                >
                  <Share2 size={18} />
                  Share
                </button>
              </ClickSpark>
            )}

            {onDownload && (
              <ClickSpark inline={true}>
                <button
                  onClick={onDownload}
                  className="px-4 py-3 rounded-xl font-semibold transition-all"
                  style={{
                    backgroundColor: 'rgba(10, 132, 255, 0.3)',
                    borderWidth: '1px',
                    borderStyle: 'solid',
                    borderColor: 'rgba(10, 132, 255, 0.5)',
                    color: colors.accentBlue
                  }}
                >
                  <Download size={18} />
                </button>
              </ClickSpark>
            )}
          </div>
        </div>
      </GlareHover>

      {/* Detailed Analysis Section */}
      {cardData.detailed_analysis && (
        <>
          <div className="mt-6 flex justify-center">
            <ClickSpark inline={true}>
              <button
                onClick={() => setShowFullReport(!showFullReport)}
                className="px-6 py-3 rounded-xl font-semibold transition-all flex items-center gap-2"
                style={{
                  backgroundColor: 'rgba(10, 132, 255, 0.3)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  borderColor: 'rgba(10, 132, 255, 0.5)',
                  color: colors.accentBlue
                }}
              >
                {showFullReport ? '📖 Hide Details' : '📊 View Detailed Analysis'}
              </button>
            </ClickSpark>
          </div>

          {showFullReport && cardData.detailed_analysis && (
            <div className="mt-6 space-y-4">
              {/* Module 1: Growth Dashboard */}
              {cardData.detailed_analysis.growth_metrics && (
                <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
                  <div className="fluid-glass p-6 rounded-2xl">
                    <ShinyText text="📈 Season Growth" speed={3} className="text-xl font-bold mb-4" />
                    <div className="grid grid-cols-3 gap-4">
                      {/* KDA Growth */}
                      <div className="bg-black/30 p-4 rounded-lg">
                        <div className="text-3xl mb-2">⚔️</div>
                        <div className="text-sm" style={{ color: colors.textSecondary }}>Combat Skill</div>
                        <div className="flex items-baseline gap-2 mt-2">
                          <span className="text-gray-500 text-sm">{cardData.detailed_analysis.growth_metrics.kda_adj.early.toFixed(2)}</span>
                          <span className="text-gray-400">→</span>
                          <span className={`text-lg font-bold ${cardData.detailed_analysis.growth_metrics.kda_adj.growth > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {cardData.detailed_analysis.growth_metrics.kda_adj.late.toFixed(2)}
                          </span>
                        </div>
                        <div className={`text-xs mt-1 ${cardData.detailed_analysis.growth_metrics.kda_adj.growth > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {(cardData.detailed_analysis.growth_metrics.kda_adj.growth * 100 > 0 ? '+' : '')}
                          {(cardData.detailed_analysis.growth_metrics.kda_adj.growth * 100).toFixed(1)}%
                        </div>
                      </div>

                      {/* Objective Rate Growth */}
                      <div className="bg-black/30 p-4 rounded-lg">
                        <div className="text-3xl mb-2">🐉</div>
                        <div className="text-sm" style={{ color: colors.textSecondary }}>Objective Control</div>
                        <div className="flex items-baseline gap-2 mt-2">
                          <span className="text-gray-500 text-sm">{cardData.detailed_analysis.growth_metrics.obj_rate.early.toFixed(2)}</span>
                          <span className="text-gray-400">→</span>
                          <span className={`text-lg font-bold ${cardData.detailed_analysis.growth_metrics.obj_rate.growth > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {cardData.detailed_analysis.growth_metrics.obj_rate.late.toFixed(2)}
                          </span>
                        </div>
                        <div className={`text-xs mt-1 ${cardData.detailed_analysis.growth_metrics.obj_rate.growth > 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {(cardData.detailed_analysis.growth_metrics.obj_rate.growth * 100 > 0 ? '+' : '')}
                          {(cardData.detailed_analysis.growth_metrics.obj_rate.growth * 100).toFixed(1)}%
                        </div>
                      </div>

                      {/* Time to Core Improvement (inverted: lower is better) */}
                      <div className="bg-black/30 p-4 rounded-lg">
                        <div className="text-3xl mb-2">💰</div>
                        <div className="text-sm" style={{ color: colors.textSecondary }}>Economic Speed</div>
                        <div className="flex items-baseline gap-2 mt-2">
                          <span className="text-gray-500 text-sm">{cardData.detailed_analysis.growth_metrics.time_to_core.early.toFixed(1)}m</span>
                          <span className="text-gray-400">→</span>
                          <span className={`text-lg font-bold ${cardData.detailed_analysis.growth_metrics.time_to_core.improvement < 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {cardData.detailed_analysis.growth_metrics.time_to_core.late.toFixed(1)}m
                          </span>
                        </div>
                        <div className={`text-xs mt-1 ${cardData.detailed_analysis.growth_metrics.time_to_core.improvement < 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {(cardData.detailed_analysis.growth_metrics.time_to_core.improvement * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>
                </GlareHover>
              )}

              {/* Module 2: Adaptation Score */}
              {cardData.detailed_analysis.version_adaptation?.adaptation_score && (
                <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
                  <div className="fluid-glass p-6 rounded-2xl">
                    <ShinyText text="🔄 Meta Adaptation" speed={3} className="text-xl font-bold mb-4" />
                    {(() => {
                      const score = cardData.detailed_analysis.version_adaptation.adaptation_score;
                      return (
                        <>
                          {/* Progress Bar */}
                          <div className="mt-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-3xl font-bold" style={{ color: colors.textPrimary }}>{score.grade}</span>
                              <span className="text-gray-400">{score.score}/100</span>
                            </div>
                            <div className="w-full bg-gray-700 rounded-full h-3">
                              <div
                                className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all"
                                style={{ width: `${score.score}%` }}
                              />
                            </div>
                          </div>

                          {/* Strengths & Improvements */}
                          <div className="grid grid-cols-2 gap-4 mt-4">
                            <div>
                              <div className="text-sm mb-2" style={{ color: colors.textSecondary }}>✅ Strengths</div>
                              {score.strengths && score.strengths.map((s: string, i: number) => (
                                <div key={i} className="text-xs text-green-400 mb-1">• {s}</div>
                              ))}
                            </div>
                            <div>
                              <div className="text-sm mb-2" style={{ color: colors.textSecondary }}>⚠️ Improve</div>
                              {score.improvements && score.improvements.map((imp: string, idx: number) => (
                                <div key={idx} className="text-xs text-yellow-400 mb-1">• {imp}</div>
                              ))}
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </GlareHover>
              )}

              {/* Module 3: Champion Pool Maturity */}
              {cardData.detailed_analysis.champion_pool_evolution && (
                <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
                  <div className="fluid-glass p-6 rounded-2xl">
                    <ShinyText text="🎯 Champion Pool" speed={3} className="text-xl font-bold mb-4" />

                    {/* Core Champions */}
                    <div className="mt-4">
                      <div className="text-sm mb-2" style={{ color: colors.textSecondary }}>
                        Core (&gt;50% patches)
                      </div>
                      {cardData.detailed_analysis.champion_pool_evolution.core_champions
                        ?.slice(0, 3)
                        .map((champ: any, i: number) => (
                          <div key={i} className="mb-2">
                            <div className="flex justify-between text-sm mb-1">
                              <span style={{ color: colors.textPrimary }}>
                                {champ.champion_name || `Champion #${champ.champion_id}`}
                              </span>
                              <span className="text-gray-400">
                                {(champ.coverage * 100).toFixed(0)}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-700 rounded-full h-2">
                              <div
                                className="bg-green-500 h-2 rounded-full transition-all"
                                style={{ width: `${champ.coverage * 100}%` }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>

                    {/* Experimental Picks */}
                    <div className="mt-4">
                      <div className="text-sm mb-2" style={{ color: colors.textSecondary }}>
                        Experimental (&lt;10% patches)
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {cardData.detailed_analysis.champion_pool_evolution.experimental_champions
                          ?.slice(0, 6)
                          .map((champ: any, i: number) => (
                            <div
                              key={i}
                              className="bg-gray-700 px-3 py-1 rounded-full text-xs"
                              style={{ color: colors.textSecondary }}
                            >
                              {champ.champion_name || `#${champ.champion_id}`} ({champ.patch_count})
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>
                </GlareHover>
              )}

              {/* Module 4: Breakthrough Moments */}
              {cardData.detailed_analysis.version_adaptation?.key_transitions &&
                cardData.detailed_analysis.version_adaptation.key_transitions.length > 0 && (
                  <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
                    <div className="fluid-glass p-6 rounded-2xl">
                      <ShinyText text="⭐ Key Moments" speed={3} className="text-xl font-bold mb-4" />

                      <div className="space-y-3 mt-4">
                        {cardData.detailed_analysis.version_adaptation.key_transitions
                          .slice(0, 3)
                          .map((t: any, i: number) => (
                            <div key={i} className="bg-black/30 p-3 rounded-lg">
                              <div className="flex items-start gap-3">
                                <div className="text-2xl">📅</div>
                                <div className="flex-1">
                                  <div className="font-bold text-sm" style={{ color: colors.textPrimary }}>
                                    {t.from_patch} → {t.to_patch}
                                  </div>
                                  <div className="text-xs mt-1" style={{ color: colors.textSecondary }}>
                                    Games: {t.games_change_pct >= 0 ? '+' : ''}{t.games_change_pct.toFixed(1)}%
                                    {' • '}
                                    Pool: {t.pool_change_pct >= 0 ? '+' : ''}{t.pool_change_pct.toFixed(1)}%
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  </GlareHover>
                )}

              {/* Module 5: Consistency Profile */}
              {cardData.detailed_analysis.consistency_profile && (
                <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
                  <div className="fluid-glass p-6 rounded-2xl">
                    <ShinyText text="📊 Consistency" speed={3} className="text-xl font-bold mb-4" />

                    {(() => {
                      const profile = cardData.detailed_analysis.consistency_profile;
                      return (
                        <>
                          {/* Variance Grade */}
                          <div className="flex items-center justify-between mt-4">
                            <div>
                              <div className="text-xs" style={{ color: colors.textSecondary }}>
                                Monthly Variance
                              </div>
                              <div className="text-2xl font-bold" style={{ color: colors.textPrimary }}>
                                {profile.variance_grade}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-xs" style={{ color: colors.textSecondary }}>
                                Std Dev
                              </div>
                              <div className="text-lg" style={{ color: colors.textPrimary }}>
                                {(profile.monthly_variance * 100).toFixed(1)}%
                              </div>
                            </div>
                          </div>

                          {/* Governance Distribution */}
                          <div className="mt-4">
                            <div className="text-sm mb-2" style={{ color: colors.textSecondary }}>
                              Data Quality
                            </div>
                            <div className="space-y-2">
                              {Object.entries(profile.governance_distribution).map(([tag, data]: [string, any]) => (
                                <div key={tag}>
                                  <div className="flex justify-between text-xs mb-1">
                                    <span style={{ color: colors.textSecondary }}>
                                      {tag === 'CONFIDENT' ? '🟢' : tag === 'CAUTION' ? '🟡' : '⚪'} {tag}
                                    </span>
                                    <span style={{ color: colors.textSecondary }}>
                                      {data.percentage.toFixed(1)}%
                                    </span>
                                  </div>
                                  <div className="w-full bg-gray-700 rounded-full h-2">
                                    <div
                                      className={`h-2 rounded-full transition-all ${
                                        tag === 'CONFIDENT'
                                          ? 'bg-green-500'
                                          : tag === 'CAUTION'
                                          ? 'bg-yellow-500'
                                          : 'bg-gray-400'
                                      }`}
                                      style={{ width: `${data.percentage}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Stability Trend */}
                          <div className="mt-4 bg-black/30 p-3 rounded-lg">
                            <div className="text-xs mb-2" style={{ color: colors.textSecondary }}>
                              Stability Trend
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-sm" style={{ color: colors.textPrimary }}>
                                Early: ±{(profile.stability_trend.early_variance * 100).toFixed(1)}%
                              </span>
                              <span className="text-gray-400">→</span>
                              <span className="text-sm" style={{ color: colors.textPrimary }}>
                                Late: ±{(profile.stability_trend.late_variance * 100).toFixed(1)}%
                              </span>
                            </div>
                            {profile.stability_trend.improving && (
                              <div className="text-xs text-green-400 mt-1">
                                📈 Improving consistency
                              </div>
                            )}
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </GlareHover>
              )}

              {/* Module 6: LLM Generated Narrative Report */}
              {cardData.detailed_analysis.narrative_report && (
                <GlareHover width="100%" height="auto" background="transparent" borderRadius="16px">
                  <div className="fluid-glass p-6 rounded-2xl">
                    <ShinyText text="📝 AI Annual Summary Report" speed={3} className="text-xl font-bold mb-4" />
                    <div className="prose prose-invert max-w-none text-sm">
                      <ReactMarkdown>{cardData.detailed_analysis.narrative_report}</ReactMarkdown>
                    </div>
                  </div>
                </GlareHover>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
