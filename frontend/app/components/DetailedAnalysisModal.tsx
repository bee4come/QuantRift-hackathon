'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ShinyText from './ui/ShinyText';
import ClickSpark from './ui/ClickSpark';
import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

interface DetailedAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentName: string;
  agentDescription: string;
  detailedReport: string;
}

export default function DetailedAnalysisModal({
  isOpen,
  onClose,
  agentName,
  agentDescription,
  detailedReport
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
