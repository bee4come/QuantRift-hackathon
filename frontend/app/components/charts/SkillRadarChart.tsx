'use client';

import React, { useState } from 'react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Brain, Sparkles, X } from 'lucide-react';
import { useAdaptiveColors } from '../../hooks/useAdaptiveColors';
import ShinyText from '../ui/ShinyText';
import ClickSpark from '../ui/ClickSpark';
import GlareHover from '../ui/GlareHover';

interface SkillData {
  subject: string;
  value: number;
  fullMark: 100;
}

interface ChampionSkillData {
  champion: string;
  champion_id?: number;
  role?: string;
  skills: SkillData[];
}

interface SkillRadarChartProps {
  data: ChampionSkillData[];
  title?: string;
  maxChampions?: number;
  puuid?: string;
  region?: string;
}

export default function SkillRadarChart({
  data,
  title = "🎯 Skill Analysis",
  maxChampions = 3,
  puuid,
  region
}: SkillRadarChartProps) {
  const colors = useAdaptiveColors();

  // Color scheme for multi-champion comparison
  const championColors = [
    '#5AC8FA', // Blue
    '#FFD60A', // Yellow
    '#30D158', // Green
    '#FF9F0A', // Orange
    '#BF5AF2', // Purple
  ];

  // Toggleable champion display
  const [activeChampions, setActiveChampions] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    data.slice(0, maxChampions).forEach((champ) => {
      initial[champ.champion] = true;
    });
    return initial;
  });

  // AI Analysis states
  const [selectedChampionForAI, setSelectedChampionForAI] = useState<ChampionSkillData | null>(null);
  const [showAIAnalysis, setShowAIAnalysis] = useState(false);
  const [aiAnalysisLoading, setAIAnalysisLoading] = useState(false);
  const [aiAnalysisData, setAIAnalysisData] = useState<any>(null);

  const fetchAIAnalysis = async (champData: ChampionSkillData) => {
    if (!puuid || !region) {
      console.error('PUUID and region are required for AI analysis');
      return;
    }

    if (!champData.champion_id) {
      console.error('Champion ID is required for AI analysis');
      return;
    }

    try {
      setAIAnalysisLoading(true);
      setSelectedChampionForAI(champData);

      const response = await fetch('/api/agents/champion-mastery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          puuid,
          region,
          champion_id: champData.champion_id,
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

  const toggleChampion = (champion: string) => {
    setActiveChampions(prev => ({ ...prev, [champion]: !prev[champion] }));
  };

  // Merge all champion skill data into a unified data structure
  // Format: [{ subject: "Offense", Champion1: 85, Champion2: 72, ... }]
  const mergedData: any[] = [];

  if (data.length > 0 && data[0].skills.length > 0) {
    // Get all skill dimensions
    const subjects = data[0].skills.map(s => s.subject);

    subjects.forEach(subject => {
      const dataPoint: any = { subject };
      data.forEach(champData => {
        const skill = champData.skills.find(s => s.subject === subject);
        if (skill) {
          dataPoint[champData.champion] = skill.value;
        }
      });
      mergedData.push(dataPoint);
    });
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div
          className="fluid-glass-dark p-4 rounded-lg border"
          style={{ borderColor: 'rgba(255, 255, 255, 0.2)' }}
        >
          <p className="font-semibold mb-2" style={{ color: colors.accentBlue }}>
            {payload[0].payload.subject}
          </p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Calculate average score for each champion
  const getAverageScore = (champData: ChampionSkillData) => {
    const sum = champData.skills.reduce((acc, skill) => acc + skill.value, 0);
    return (sum / champData.skills.length).toFixed(1);
  };

  // Find the strongest skill for each champion
  const getStrongestSkill = (champData: ChampionSkillData) => {
    let max = champData.skills[0];
    champData.skills.forEach(skill => {
      if (skill.value > max.value) {
        max = skill;
      }
    });
    return max;
  };

  return (
    <div className="fluid-glass rounded-2xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <ShinyText text={title} speed={3} className="text-2xl font-bold" />
      </div>

      {/* Champion Toggles */}
      {data.length > 1 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {data.map((champData, index) => {
            const isActive = activeChampions[champData.champion];
            const color = championColors[index % championColors.length];
            const uniqueKey = `toggle-${champData.champion_id || champData.champion}-${index}`;
            return (
              <button
                key={uniqueKey}
                onClick={() => toggleChampion(champData.champion)}
                className="px-4 py-2 rounded-lg border font-medium text-sm transition-all"
                style={{
                  backgroundColor: isActive ? `${color}20` : 'rgba(28, 28, 30, 0.5)',
                  borderColor: isActive ? color : 'rgba(142, 142, 147, 0.3)',
                  color: isActive ? color : '#8E8E93'
                }}
              >
                {champData.champion}
                {champData.role && <span className="ml-1 text-xs">({champData.role})</span>}
              </button>
            );
          })}
        </div>
      )}

      {/* Radar Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <RadarChart data={mergedData}>
          <PolarGrid stroke="rgba(255, 255, 255, 0.1)" />
          <PolarAngleAxis
            dataKey="subject"
            stroke="#8E8E93"
            style={{ fontSize: '12px' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            stroke="#8E8E93"
            style={{ fontSize: '10px' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ color: '#EBEBF5' }}
            iconType="circle"
          />

          {/* Radar for each champion */}
          {data.map((champData, index) => {
            if (!activeChampions[champData.champion]) return null;
            const color = championColors[index % championColors.length];
            const uniqueKey = `radar-${champData.champion_id || champData.champion}-${index}`;
            return (
              <Radar
                key={uniqueKey}
                name={champData.champion}
                dataKey={champData.champion}
                stroke={color}
                fill={color}
                fillOpacity={0.25}
                strokeWidth={2}
              />
            );
          })}
        </RadarChart>
      </ResponsiveContainer>

      {/* Champion Analysis Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        {data.map((champData, index) => {
          if (!activeChampions[champData.champion]) return null;
          const color = championColors[index % championColors.length];
          const avgScore = getAverageScore(champData);
          const strongestSkill = getStrongestSkill(champData);
          const uniqueKey = `card-${champData.champion_id || champData.champion}-${index}`;

          return (
            <div
              key={uniqueKey}
              className="fluid-glass-dark p-4 rounded-lg border"
              style={{ borderColor: `${color}40` }}
            >
              <div className="flex items-center justify-between mb-3">
                <ShinyText
                  text={champData.champion}
                  speed={3}
                  className="text-lg font-bold"
                />
                {champData.role && (
                  <span
                    className="text-xs px-2 py-1 rounded"
                    style={{
                      backgroundColor: `${color}20`,
                      color: color
                    }}
                  >
                    {champData.role}
                  </span>
                )}
              </div>

              <div className="space-y-2">
                <div>
                  <p className="text-xs mb-1" style={{ color: '#8E8E93' }}>
                    Average Score
                  </p>
                  <p className="text-2xl font-bold" style={{ color }}>
                    {avgScore}
                  </p>
                </div>

                <div>
                  <p className="text-xs mb-1" style={{ color: '#8E8E93' }}>
                    Strongest Skill
                  </p>
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium" style={{ color: colors.textPrimary }}>
                      {strongestSkill.subject}
                    </p>
                    <p className="text-sm font-bold" style={{ color }}>
                      {strongestSkill.value}
                    </p>
                  </div>
                </div>

                {/* Skill Bars */}
                <div className="mt-3 space-y-1">
                  {champData.skills.map((skill) => (
                    <div key={skill.subject}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span style={{ color: '#8E8E93' }}>{skill.subject}</span>
                        <span style={{ color }}>{skill.value}</span>
                      </div>
                      <div
                        className="h-1.5 rounded-full"
                        style={{ backgroundColor: 'rgba(142, 142, 147, 0.2)' }}
                      >
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${skill.value}%`,
                            backgroundColor: color
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {/* AI Analysis Button */}
                {puuid && region && champData.champion_id && (
                  <div className="mt-4">
                    <ClickSpark inline={true}>
                      <button
                        onClick={() => fetchAIAnalysis(champData)}
                        disabled={aiAnalysisLoading}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm transition-all"
                        style={{
                          backgroundColor: `${color}20`,
                          borderWidth: '1px',
                          borderStyle: 'solid',
                          borderColor: `${color}40`,
                          color: color,
                          opacity: aiAnalysisLoading ? 0.6 : 1
                        }}
                      >
                        <Brain size={16} />
                        {aiAnalysisLoading && selectedChampionForAI?.champion === champData.champion
                          ? 'Analyzing...'
                          : 'Deep Analysis'}
                      </button>
                    </ClickSpark>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Skill Dimension Explanations */}
      <div className="mt-6 p-4 rounded-lg" style={{ backgroundColor: 'rgba(28, 28, 30, 0.5)' }}>
        <p className="text-sm font-semibold mb-2" style={{ color: colors.textPrimary }}>
          📊 Skill Dimensions
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs" style={{ color: colors.textSecondary }}>
          <div>
            <span className="font-medium" style={{ color: championColors[0] }}>Offense</span>: Damage output, kills, combat power
          </div>
          <div>
            <span className="font-medium" style={{ color: championColors[1] }}>Defense</span>: Damage taken, deaths, survival
          </div>
          <div>
            <span className="font-medium" style={{ color: championColors[2] }}>Teamwork</span>: Assists, objective participation
          </div>
          <div>
            <span className="font-medium" style={{ color: championColors[3] }}>Economy</span>: Gold per min, CS efficiency
          </div>
          <div>
            <span className="font-medium" style={{ color: championColors[4] }}>Vision</span>: Vision score, ward placement
          </div>
        </div>
      </div>

      {/* AI Analysis Section */}
      {showAIAnalysis && aiAnalysisData && selectedChampionForAI && (
        <div className="mt-6">
          <GlareHover width="100%" height="auto" background="transparent" borderRadius="12px">
            <div className="fluid-glass-dark p-6 rounded-xl border" style={{ borderColor: 'rgba(10, 132, 255, 0.3)' }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Sparkles size={20} style={{ color: colors.accentBlue }} />
                  <ShinyText
                    text={`${selectedChampionForAI.champion} Mastery Analysis`}
                    speed={3}
                    className="text-lg font-semibold"
                  />
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
