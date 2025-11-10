'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import { ArrowRight, AlertCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface ShareData {
  share_id: string;
  agent_type: string;
  player: {
    gameName: string;
    tagLine: string;
    region: string;
  };
  created_at: string;
  report_content: string;
  metadata: {
    total_games?: number;
    time_range?: string;
    model?: string;
  };
}

export default function ShareReportView({ shareId }: { shareId: string }) {
  const [shareData, setShareData] = useState<ShareData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchShare = async () => {
      try {
        const response = await fetch(`/api/share/${shareId}`);

        if (!response.ok) {
          if (response.status === 404) {
            setError('Report not found');
          } else {
            setError('Failed to load report');
          }
          setLoading(false);
          return;
        }

        const data = await response.json();
        setShareData(data);
        setLoading(false);

        // Track view event
        if (typeof window !== 'undefined' && (window as any).gtag) {
          (window as any).gtag('event', 'share_view', {
            share_id: shareId,
            agent_type: data.agent_type,
            player: `${data.player.gameName}#${data.player.tagLine}`
          });
        }
      } catch (err) {
        console.error('Failed to fetch share:', err);
        setError('Failed to load report');
        setLoading(false);
      }
    };

    fetchShare();
  }, [shareId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#000000' }}>
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4" style={{ color: '#3B82F6' }} />
          <p style={{ color: '#8E8E93' }}>Loading report...</p>
        </div>
      </div>
    );
  }

  if (error || !shareData) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: '#000000' }}>
        <div className="max-w-md w-full text-center">
          <AlertCircle className="w-16 h-16 mx-auto mb-4" style={{ color: '#EF4444' }} />
          <h1 className="text-2xl font-bold mb-2" style={{ color: '#F5F5F7' }}>
            {error || 'Report Not Found'}
          </h1>
          <p className="mb-6" style={{ color: '#8E8E93' }}>
            This report may have been removed or the link is invalid.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg transition-all"
            style={{
              backgroundColor: 'rgba(59, 130, 246, 0.8)',
              color: '#FFFFFF'
            }}
          >
            Go to Homepage
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  const agentTypeNames: Record<string, string> = {
    'weakness-analysis': 'Weakness Analysis',
    'annual-summary': 'Annual Summary',
    'champion-mastery': 'Champion Mastery',
    'champion-recommendation': 'Champion Recommendation',
    'role-specialization': 'Role Specialization',
    'peer-comparison': 'Peer Comparison',
    'progress-tracker': 'Progress Tracker',
    'timeline-deep-dive': 'Timeline Deep Dive',
    'friend-comparison': 'Friend Comparison',
    'performance-insights': 'Performance Insights',
    'comparison-hub': 'Comparison Hub',
    'match-analysis': 'Match Analysis',
    'version-trends': 'Version Trends',
    'build-simulator': 'Build Simulator'
  };

  const agentName = agentTypeNames[shareData.agent_type] || shareData.agent_type;

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#000000', color: '#F5F5F7' }}>
      {/* Header */}
      <div className="border-b" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }}>
        <div className="max-w-4xl mx-auto px-6 py-6">
          <Link href="/" className="inline-block mb-4">
            <h1 className="text-2xl font-bold" style={{ color: '#3B82F6' }}>
              QuantRift
            </h1>
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold mb-2">
                {shareData.player.gameName}
                <span style={{ color: '#8E8E93' }}>#{shareData.player.tagLine}</span>
              </h2>
              <p style={{ color: '#8E8E93' }}>
                {agentName} • {new Date(shareData.created_at).toLocaleDateString()}
              </p>
              {shareData.metadata.total_games && (
                <p className="text-sm mt-1" style={{ color: '#8E8E93' }}>
                  Based on {shareData.metadata.total_games} games
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Report Content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto px-6 py-8"
      >
        <div
          className="prose prose-invert max-w-none"
          style={{
            color: '#F5F5F7'
          }}
        >
          <ReactMarkdown
            components={{
              h1: ({ children }) => (
                <h1 className="text-3xl font-bold mb-4 mt-8" style={{ color: '#F5F5F7' }}>
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-2xl font-bold mb-3 mt-6" style={{ color: '#F5F5F7' }}>
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-xl font-semibold mb-2 mt-4" style={{ color: '#F5F5F7' }}>
                  {children}
                </h3>
              ),
              p: ({ children }) => (
                <p className="mb-4 leading-relaxed" style={{ color: '#E5E5E7' }}>
                  {children}
                </p>
              ),
              ul: ({ children }) => (
                <ul className="list-disc list-inside mb-4 space-y-2" style={{ color: '#E5E5E7' }}>
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside mb-4 space-y-2" style={{ color: '#E5E5E7' }}>
                  {children}
                </ol>
              ),
              code: ({ children }) => (
                <code
                  className="px-2 py-1 rounded text-sm"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    color: '#3B82F6'
                  }}
                >
                  {children}
                </code>
              ),
              blockquote: ({ children }) => (
                <blockquote
                  className="border-l-4 pl-4 py-2 my-4"
                  style={{
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    color: '#E5E5E7'
                  }}
                >
                  {children}
                </blockquote>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto my-4">
                  <table className="w-full border-collapse">
                    {children}
                  </table>
                </div>
              ),
              th: ({ children }) => (
                <th
                  className="border px-4 py-2 text-left"
                  style={{
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    color: '#F5F5F7'
                  }}
                >
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td
                  className="border px-4 py-2"
                  style={{
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    color: '#E5E5E7'
                  }}
                >
                  {children}
                </td>
              )
            }}
          >
            {shareData.report_content}
          </ReactMarkdown>
        </div>
      </motion.div>

      {/* CTA Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="max-w-4xl mx-auto px-6 py-8 mb-12"
      >
        <div
          className="rounded-2xl p-8 text-center"
          style={{
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%)',
            border: '1px solid rgba(59, 130, 246, 0.3)'
          }}
        >
          <h3 className="text-2xl font-bold mb-3" style={{ color: '#F5F5F7' }}>
            Want Your Own AI Analysis?
          </h3>
          <p className="mb-6" style={{ color: '#8E8E93' }}>
            Get detailed insights into your League of Legends performance with AI-powered analysis
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-lg font-semibold transition-all hover:scale-105"
            style={{
              backgroundColor: '#3B82F6',
              color: '#FFFFFF'
            }}
          >
            Analyze Your Performance
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </motion.div>

      {/* Footer */}
      <div className="border-t" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }}>
        <div className="max-w-4xl mx-auto px-6 py-6 text-center" style={{ color: '#8E8E93' }}>
          <p className="text-sm">
            Powered by <span style={{ color: '#3B82F6' }}>QuantRift</span> • League of Legends AI Analysis
          </p>
        </div>
      </div>
    </div>
  );
}
