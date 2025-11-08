'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, Brain, Loader2 } from 'lucide-react';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

interface StreamingAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentName: string;
  agentDescription: string;
  agentId: string;
  puuid: string;
  region: string;
  additionalParams?: Record<string, any>;
}

export default function StreamingAnalysisModal({
  isOpen,
  onClose,
  agentName,
  agentDescription,
  agentId,
  puuid,
  region,
  additionalParams = {}
}: StreamingAnalysisModalProps) {
  const colors = useAdaptiveColors();

  // Stream states
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingContent, setThinkingContent] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const [finalContent, setFinalContent] = useState('');
  const [oneLiner, setOneLiner] = useState('');
  const [error, setError] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (isOpen && !isComplete && !error) {
      // Create new AbortController for this stream
      abortControllerRef.current = new AbortController();
      startStreaming();
    }

    // Cleanup: abort stream on unmount or when modal closes
    return () => {
      if (abortControllerRef.current) {
        console.log('[StreamingAnalysisModal] Aborting stream on cleanup');
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [isOpen]);

  // Handle page refresh/unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (abortControllerRef.current) {
        console.log('[StreamingAnalysisModal] Aborting stream on page unload');
        abortControllerRef.current.abort();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  const startStreaming = async () => {
    try {
      setIsThinking(false);
      setThinkingContent('');
      setStreamingContent('');
      setFinalContent('');
      setError('');
      setIsComplete(false);

      // Import stream utility
      const { handleSSEStream } = await import('@/app/lib/streamUtils');

      const url = `/api/agents/${agentId}`;
      const body = {
        puuid,
        region,
        recent_count: 5,
        model: 'haiku',
        ...additionalParams
      };

      await handleSSEStream(url, body, {
        onThinkingStart: () => {
          setIsThinking(true);
          setThinkingContent('');
        },
        onThinking: (content) => {
          setThinkingContent((prev) => prev + content);
        },
        onThinkingEnd: () => {
          setIsThinking(false);
        },
        onChunk: (content) => {
          setStreamingContent((prev) => prev + content);
        },
        onComplete: (liner, detailed) => {
          setOneLiner(liner);
          setFinalContent(detailed || streamingContent);
          setIsComplete(true);
        },
        onError: (err) => {
          // Don't set error if aborted
          if (abortControllerRef.current?.signal.aborted) {
            console.log('[StreamingAnalysisModal] Stream aborted');
            return;
          }
          setError(err);
          setIsComplete(true);
        }
      }, abortControllerRef.current || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stream failed');
      setIsComplete(true);
    }
  };

  const handleDownload = () => {
    const content = finalContent || streamingContent;
    if (!content) return;

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${agentName.replace(/\s+/g, '_')}_Analysis.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatMarkdown = (text: string) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^### (.*$)/gim, '<h3 class="text-xl font-bold mt-6 mb-3" style="color: #5AC8FA;">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-2xl font-bold mt-8 mb-4" style="color: #5AC8FA;">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold mt-8 mb-4" style="color: #5AC8FA;">$1</h1>')
      .replace(/^- (.*$)/gim, '<li class="ml-4">$1</li>')
      .replace(/\n\n/g, '<br/><br/>');
  };

  const displayContent = finalContent || streamingContent;

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
                <div className="flex-1">
                  <ShinyText
                    text={agentName}
                    speed={3}
                    className="text-2xl font-bold"
                  />
                  <p className="text-sm mt-1" style={{ color: '#8E8E93' }}>
                    {agentDescription}
                  </p>

                  {/* One-liner summary when available */}
                  {oneLiner && (
                    <p className="text-sm mt-2 font-medium" style={{ color: '#5AC8FA' }}>
                      {oneLiner}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {/* Download Button */}
                  {displayContent && (
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
                        title="Download Analysis"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    </ClickSpark>
                  )}

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
                {/* Error State */}
                {error && (
                  <div className="text-center py-8">
                    <p className="text-red-400 mb-4">{error}</p>
                    <button
                      onClick={startStreaming}
                      className="px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                )}

                {/* Thinking State */}
                {isThinking && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-4 p-4 rounded-lg"
                    style={{
                      backgroundColor: 'rgba(94, 92, 230, 0.1)',
                      borderLeft: '3px solid #5E5CE6'
                    }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Brain className="w-4 h-4 animate-pulse" style={{ color: '#5E5CE6' }} />
                      <span className="text-sm font-medium" style={{ color: '#5E5CE6' }}>
                        AI Thinking...
                      </span>
                    </div>
                    {thinkingContent && (
                      <p className="text-sm opacity-70 whitespace-pre-wrap" style={{ color: '#F5F5F7' }}>
                        {thinkingContent}
                      </p>
                    )}
                  </motion.div>
                )}

                {/* Loading State (no content yet) */}
                {!error && !displayContent && !isThinking && (
                  <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin mb-4" style={{ color: '#5AC8FA' }} />
                    <p className="text-sm" style={{ color: '#8E8E93' }}>
                      Connecting to AI agent...
                    </p>
                  </div>
                )}

                {/* Streaming/Final Content */}
                {displayContent && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="prose prose-invert max-w-none"
                    style={{
                      color: '#F5F5F7',
                      fontSize: '0.95rem',
                      lineHeight: '1.7'
                    }}
                  >
                    <div
                      className="whitespace-pre-wrap"
                      dangerouslySetInnerHTML={{
                        __html: formatMarkdown(displayContent)
                      }}
                    />

                    {/* Streaming indicator */}
                    {!isComplete && (
                      <motion.span
                        animate={{ opacity: [1, 0.3, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                        className="inline-block ml-1"
                        style={{ color: '#5AC8FA' }}
                      >
                        ▊
                      </motion.span>
                    )}
                  </motion.div>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between p-6 border-t border-white/10">
                <div className="text-xs" style={{ color: '#8E8E93' }}>
                  {isComplete ? (
                    '✓ Analysis complete'
                  ) : !error && displayContent ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                      Streaming...
                    </>
                  ) : null}
                </div>

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
