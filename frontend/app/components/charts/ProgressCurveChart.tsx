'use client';

import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Brain, Sparkles, X } from 'lucide-react';
import { useAdaptiveColors } from '../../hooks/useAdaptiveColors';
import ShinyText from '../ui/ShinyText';
import ClickSpark from '../ui/ClickSpark';
import GlareHover from '../ui/GlareHover';

interface MetricData {
  patch: string;
  combat_power?: number;
  kda?: number;
  win_rate?: number;
  objective_rate?: number;
  gold_per_min?: number;
}

interface ProgressCurveChartProps {
  data: MetricData[];
  title?: string;
  showMetrics?: {
    combat_power?: boolean;
    kda?: boolean;
    win_rate?: boolean;
    objective_rate?: boolean;
    gold_per_min?: boolean;
  };
  puuid?: string;
  region?: string;
  hideAIAnalysis?: boolean;
}

export default function ProgressCurveChart({
  data,
  title = "📈 Performance Progress",
  showMetrics = { combat_power: true, kda: true, win_rate: true },
  puuid,
  region,
  hideAIAnalysis = false
}: ProgressCurveChartProps) {
  const colors = useAdaptiveColors();

  // Toggleable metrics display
  const [activeMetrics, setActiveMetrics] = useState({
    combat_power: showMetrics.combat_power ?? true,
    kda: showMetrics.kda ?? true,
    win_rate: showMetrics.win_rate ?? true,
    objective_rate: showMetrics.objective_rate ?? false,
    gold_per_min: showMetrics.gold_per_min ?? false
  });

  // AI Analysis states
  const [showAIAnalysis, setShowAIAnalysis] = useState(false);
  const [aiAnalysisLoading, setAIAnalysisLoading] = useState(false);
  const [aiAnalysisData, setAIAnalysisData] = useState<any>(null);

  const fetchAIAnalysis = async () => {
    if (!puuid || !region) {
      console.error('PUUID and region are required for AI analysis');
      return;
    }

    try {
      setAIAnalysisLoading(true);

      const response = await fetch('/api/agents/progress-tracker', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          puuid,
          region,
          model: 'haiku',
        }),
      });

      if (!response.ok) {
        console.error('Failed to fetch AI analysis');
        return;
      }

      const result = await response.json();

      if (result.success) {
        setAIAnalysisData(result);
        setShowAIAnalysis(true);
      }
    } catch (err) {
      console.error('Error fetching AI analysis:', err);
    } finally {
      setAIAnalysisLoading(false);
    }
  };

  const metricConfig = {
    combat_power: {
      name: 'Combat Power',
      color: '#5AC8FA',
      yAxisId: 'left'
    },
    kda: {
      name: 'KDA',
      color: '#FFD60A',
      yAxisId: 'left'
    },
    win_rate: {
      name: 'Win Rate (%)',
      color: '#30D158',
      yAxisId: 'right'
    },
    objective_rate: {
      name: 'Obj Rate (x)',
      color: '#FF9F0A',
      yAxisId: 'left'
    },
    gold_per_min: {
      name: 'Gold/min',
      color: '#BF5AF2',
      yAxisId: 'left'
    }
  };

  const toggleMetric = (metric: keyof typeof activeMetrics) => {
    setActiveMetrics(prev => ({ ...prev, [metric]: !prev[metric] }));
  };

  // Process data: Convert win_rate to percentage
  const chartData = data.map(item => ({
    ...item,
    win_rate: item.win_rate ? item.win_rate * 100 : undefined,
    objective_rate: item.objective_rate !== undefined ? item.objective_rate : undefined
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div
          className="fluid-glass-dark p-4 rounded-lg border"
          style={{ borderColor: 'rgba(255, 255, 255, 0.2)' }}
        >
          <p className="font-semibold mb-2" style={{ color: colors.accentBlue }}>
            Patch {label}
          </p>
          {payload.map((entry: any, index: number) => {
            // Format objective_rate with 'x' suffix
            const formattedValue = entry.dataKey === 'objective_rate'
              ? `${entry.value?.toFixed(2)}x`
              : entry.value?.toFixed(2);

            return (
              <p key={index} className="text-sm" style={{ color: entry.color }}>
                {entry.name}: {formattedValue}
              </p>
            );
          })}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="fluid-glass rounded-2xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <ShinyText text={title} speed={3} className="text-2xl font-bold" />

        {/* AI Analysis Button */}
        {puuid && region && !hideAIAnalysis && (
          <ClickSpark inline={true}>
            <button
              onClick={fetchAIAnalysis}
              disabled={aiAnalysisLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all"
              style={{
                backgroundColor: 'rgba(10, 132, 255, 0.3)',
                borderWidth: '1px',
                borderStyle: 'solid',
                borderColor: 'rgba(10, 132, 255, 0.5)',
                color: colors.accentBlue,
                opacity: aiAnalysisLoading ? 0.6 : 1
              }}
            >
              <Brain size={18} />
              {aiAnalysisLoading ? 'Analyzing...' : 'AI Analysis'}
            </button>
          </ClickSpark>
        )}
      </div>

      {/* Metric Toggles */}
      <div className="flex flex-wrap gap-2 mb-6">
        {Object.entries(metricConfig).map(([key, config]) => {
          const isActive = activeMetrics[key as keyof typeof activeMetrics];
          return (
            <button
              key={key}
              onClick={() => toggleMetric(key as keyof typeof activeMetrics)}
              className="px-4 py-2 rounded-lg border font-medium text-sm transition-all"
              style={{
                backgroundColor: isActive ? `${config.color}20` : 'rgba(28, 28, 30, 0.5)',
                borderColor: isActive ? config.color : 'rgba(142, 142, 147, 0.3)',
                color: isActive ? config.color : '#8E8E93'
              }}
            >
              {config.name}
            </button>
          );
        })}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
          <XAxis
            dataKey="patch"
            stroke="#8E8E93"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            yAxisId="left"
            stroke="#8E8E93"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#8E8E93"
            style={{ fontSize: '12px' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ color: '#EBEBF5' }}
            iconType="line"
          />

          {/* Lines for each metric */}
          {activeMetrics.combat_power && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="combat_power"
              stroke={metricConfig.combat_power.color}
              strokeWidth={2}
              dot={{ fill: metricConfig.combat_power.color, r: 4 }}
              activeDot={{ r: 6 }}
              name={metricConfig.combat_power.name}
            />
          )}
          {activeMetrics.kda && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="kda"
              stroke={metricConfig.kda.color}
              strokeWidth={2}
              dot={{ fill: metricConfig.kda.color, r: 4 }}
              activeDot={{ r: 6 }}
              name={metricConfig.kda.name}
            />
          )}
          {activeMetrics.win_rate && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="win_rate"
              stroke={metricConfig.win_rate.color}
              strokeWidth={2}
              dot={{ fill: metricConfig.win_rate.color, r: 4 }}
              activeDot={{ r: 6 }}
              name={metricConfig.win_rate.name}
            />
          )}
          {activeMetrics.objective_rate && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="objective_rate"
              stroke={metricConfig.objective_rate.color}
              strokeWidth={2}
              dot={{ fill: metricConfig.objective_rate.color, r: 4 }}
              activeDot={{ r: 6 }}
              name={metricConfig.objective_rate.name}
            />
          )}
          {activeMetrics.gold_per_min && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="gold_per_min"
              stroke={metricConfig.gold_per_min.color}
              strokeWidth={2}
              dot={{ fill: metricConfig.gold_per_min.color, r: 4 }}
              activeDot={{ r: 6 }}
              name={metricConfig.gold_per_min.name}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
        {Object.entries(metricConfig).map(([key, config]) => {
          if (!activeMetrics[key as keyof typeof activeMetrics]) return null;

          const values = chartData
            .map(d => d[key as keyof MetricData] as number)
            .filter(v => v !== undefined && v !== null);

          if (values.length === 0) return null;

          const latest = values[values.length - 1];
          const earliest = values[0];
          const change = latest - earliest;
          const changePercent = (change / earliest) * 100;

          return (
            <div
              key={key}
              className="fluid-glass-dark p-4 rounded-lg border"
              style={{ borderColor: `${config.color}40` }}
            >
              <p className="text-xs mb-1" style={{ color: '#8E8E93' }}>
                {config.name}
              </p>
              <p className="text-2xl font-bold" style={{ color: config.color }}>
                {latest.toFixed(2)}
              </p>
              <p
                className="text-xs mt-1"
                style={{ color: change >= 0 ? '#30D158' : '#FF453A' }}
              >
                {change >= 0 ? '↑' : '↓'} {Math.abs(changePercent).toFixed(1)}%
              </p>
            </div>
          );
        })}
      </div>

      {/* AI Analysis Section */}
      {!hideAIAnalysis && showAIAnalysis && aiAnalysisData && (
        <div className="mt-6">
          <GlareHover width="100%" height="auto" background="transparent" borderRadius="12px">
            <div className="fluid-glass-dark p-6 rounded-xl border" style={{ borderColor: 'rgba(10, 132, 255, 0.3)' }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Sparkles size={20} style={{ color: colors.accentBlue }} />
                  <ShinyText text="AI Progress Analysis" speed={3} className="text-lg font-semibold" />
                </div>
                <button
                  onClick={() => setShowAIAnalysis(false)}
                  className="p-1 rounded-lg transition-all hover:bg-opacity-20"
                  style={{ color: colors.textSecondary }}
                >
                  <X size={20} />
                </button>
              </div>

              {/* One-liner */}
              {aiAnalysisData.one_liner && (
                <div className="mb-4 p-3 rounded-lg" style={{ backgroundColor: 'rgba(10, 132, 255, 0.1)' }}>
                  <p style={{ color: colors.accentBlue }} className="font-semibold">
                    {aiAnalysisData.one_liner}
                  </p>
                </div>
              )}

              {/* Detailed Report (collapsible) */}
              {aiAnalysisData.detailed && (
                <details className="mt-4">
                  <summary
                    className="cursor-pointer font-semibold mb-2"
                    style={{ color: colors.accentBlue }}
                  >
                    View Detailed Analysis
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
                    {aiAnalysisData.detailed}
                  </div>
                </details>
              )}
            </div>
          </GlareHover>
        </div>
      )}
    </div>
  );
}
