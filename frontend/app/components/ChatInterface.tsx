'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Loader2, ArrowLeft, Bot, Sparkles } from 'lucide-react';
import ClickSpark from './ui/ClickSpark';
import ReactMarkdown from 'react-markdown';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ChatInterfaceProps {
  gameName: string;
  tagLine: string;
}

export default function ChatInterface({ gameName, tagLine }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setStreamingMessage('');

    try {
      // Close previous EventSource if exists
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Create SSE connection
      const url = `/api/chat?message=${encodeURIComponent(userMessage.content)}&gameName=${encodeURIComponent(gameName)}&tagLine=${encodeURIComponent(tagLine)}`;
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      let fullResponse = '';

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            // Status messages
            case 'thinking':
            case 'routing':
            case 'planning':
            case 'executing':
              setStreamingMessage(`_${data.content}_`);
              break;

            // Routing system messages
            case 'routing_start':
              setStreamingMessage(`_Analyzing: ${data.query}_`);
              break;

            case 'routing_method':
              const method = data.method === 'rule' ? 'Rule-based' : 'AI-powered';
              setStreamingMessage(`_${method} routing (confidence: ${Math.round(data.confidence * 100)}%)_`);
              break;

            case 'routing_decision':
              if (data.subagent) {
                setStreamingMessage(`_Calling ${data.subagent} agent..._`);
              }
              break;

            case 'agent_start':
              setStreamingMessage(`_Starting ${data.agent} analysis..._`);
              break;

            // Thinking process
            case 'thinking_start':
              setStreamingMessage('_Thinking..._');
              break;

            case 'thinking':
              setStreamingMessage(`_Thinking: ${data.content.substring(0, 100)}..._`);
              break;

            case 'thinking_end':
              setStreamingMessage('_Generating response..._');
              break;

            // Progress updates
            case 'progress':
              setStreamingMessage(prev => prev + '\n' + data.content);
              break;

            // Content chunks
            case 'report':
            case 'chunk':
              fullResponse += data.content;
              setStreamingMessage(fullResponse);
              break;

            // Completion
            case 'complete':
              if (data.detailed) {
                fullResponse = data.detailed;
                setStreamingMessage(fullResponse);
              }
              break;

            case 'done':
              // Finalize message
              const assistantMessage: Message = {
                id: Date.now().toString(),
                role: 'assistant',
                content: fullResponse || streamingMessage,
                timestamp: Date.now()
              };
              setMessages(prev => [...prev, assistantMessage]);
              setStreamingMessage('');
              setIsLoading(false);
              eventSource.close();
              break;

            // Errors
            case 'error':
              setStreamingMessage(`Error: ${data.content || data.error}`);
              setIsLoading(false);
              eventSource.close();
              break;
          }
        } catch (err) {
          console.error('Error parsing SSE data:', err);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        setStreamingMessage('Connection error. Please try again.');
        setIsLoading(false);
        eventSource.close();
      };

    } catch (error) {
      console.error('Error sending message:', error);
      setStreamingMessage('Failed to send message. Please try again.');
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickPrompts = [
    "Analyze my recent performance",
    "What are my main weaknesses?",
    "Recommend champions for me",
    "Show my season overview"
  ];

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor: '#1C1C1E' }}>
      {/* Minimal Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: '#2C2C2E' }}>
        <ClickSpark>
          <a
            href={`/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`}
            className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" style={{ color: '#8E8E93' }} />
          </a>
        </ClickSpark>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4" style={{ color: '#5AC8FA' }} />
            <span className="font-semibold" style={{ color: '#FFFFFF' }}>AI Analysis</span>
          </div>
          <p className="text-xs" style={{ color: '#8E8E93' }}>
            {gameName}#{tagLine}
          </p>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6">
          {/* Empty State */}
          {messages.length === 0 && !isLoading && (
            <div className="h-full flex flex-col items-center justify-center py-12">
              <div className="w-12 h-12 rounded-full flex items-center justify-center mb-4" style={{
                backgroundColor: 'rgba(10, 132, 255, 0.15)',
                border: '1px solid rgba(10, 132, 255, 0.3)'
              }}>
                <Bot className="w-6 h-6" style={{ color: '#5AC8FA' }} />
              </div>
              <h3 className="text-lg font-medium mb-2" style={{ color: '#FFFFFF' }}>
                How can I help you today?
              </h3>
              <p className="text-sm text-center mb-8" style={{ color: '#8E8E93' }}>
                Ask me anything about your League of Legends performance
              </p>

              {/* Quick Prompts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-lg">
                {quickPrompts.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(prompt)}
                    className="text-left px-4 py-3 rounded-lg text-sm transition-colors border"
                    style={{
                      backgroundColor: '#2C2C2E',
                      borderColor: '#3A3A3C',
                      color: '#FFFFFF'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#3A3A3C';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#2C2C2E';
                    }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message List */}
          <div className="space-y-6">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex gap-3"
                >
                  {message.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0" style={{
                      backgroundColor: 'rgba(10, 132, 255, 0.15)',
                      border: '1px solid rgba(10, 132, 255, 0.3)'
                    }}>
                      <Bot className="w-4 h-4" style={{ color: '#5AC8FA' }} />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    {message.role === 'user' && (
                      <div className="text-xs mb-1" style={{ color: '#8E8E93' }}>You</div>
                    )}
                    <div
                      style={{
                        color: message.role === 'user' ? '#FFFFFF' : '#E5E5E7',
                        fontSize: '14px',
                        lineHeight: '1.6'
                      }}
                    >
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Streaming Message */}
            {streamingMessage && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3"
              >
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0" style={{
                  backgroundColor: 'rgba(10, 132, 255, 0.15)',
                  border: '1px solid rgba(10, 132, 255, 0.3)'
                }}>
                  <Bot className="w-4 h-4" style={{ color: '#5AC8FA' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div
                    style={{
                      color: '#E5E5E7',
                      fontSize: '14px',
                      lineHeight: '1.6'
                    }}
                  >
                    <ReactMarkdown>{streamingMessage}</ReactMarkdown>
                  </div>
                  {isLoading && (
                    <div className="flex items-center gap-1 mt-2">
                      <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: '#5AC8FA' }} />
                      <div className="w-2 h-2 rounded-full animate-pulse delay-75" style={{ backgroundColor: '#5AC8FA' }} />
                      <div className="w-2 h-2 rounded-full animate-pulse delay-150" style={{ backgroundColor: '#5AC8FA' }} />
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </div>

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Fixed Input Area */}
      <div className="border-t" style={{ borderColor: '#2C2C2E', backgroundColor: '#1C1C1E' }}>
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="relative flex items-end gap-2 p-2 rounded-2xl" style={{
            backgroundColor: '#2C2C2E',
            border: '1px solid #3A3A3C'
          }}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message AI Analysis..."
              disabled={isLoading}
              rows={1}
              className="flex-1 bg-transparent border-0 resize-none focus:outline-none disabled:opacity-50 px-2 py-2"
              style={{
                color: '#FFFFFF',
                maxHeight: '200px',
                minHeight: '24px'
              }}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="p-2 rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
              style={{
                backgroundColor: input.trim() && !isLoading ? '#5AC8FA' : 'transparent',
                color: input.trim() && !isLoading ? '#000000' : '#8E8E93'
              }}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-center mt-2" style={{ color: '#636366' }}>
            AI can make mistakes. Check important info.
          </p>
        </div>
      </div>
    </div>
  );
}
