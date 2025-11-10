'use client';

import { Share2, Copy, Check, X, Twitter, Linkedin, MessageCircle } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ShareButtonProps {
  agentType: string;
  agentName: string;
  reportContent: string;
  playerInfo: {
    gameName: string;
    tagLine: string;
    region?: string;
  };
  metadata?: {
    total_games?: number;
    time_range?: string;
    model?: string;
  };
}

export default function ShareButton({
  agentType,
  agentName,
  reportContent,
  playerInfo,
  metadata
}: ShareButtonProps) {
  const [isSharing, setIsSharing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCreateShare = async () => {
    if (shareUrl) {
      setShowModal(true);
      return;
    }

    setIsSharing(true);
    setError(null);

    try {
      const response = await fetch('/api/share/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_type: agentType,
          gameName: playerInfo.gameName,
          tagLine: playerInfo.tagLine,
          region: playerInfo.region || 'na1',
          report_content: reportContent,
          total_games: metadata?.total_games,
          time_range: metadata?.time_range,
          model: metadata?.model
        })
      });

      const data = await response.json();

      if (data.success) {
        const url = `${window.location.origin}/share/${data.share_id}`;
        setShareUrl(url);
        setShowModal(true);

        // Track share creation
        if (typeof window !== 'undefined' && (window as any).gtag) {
          (window as any).gtag('event', 'share_created', {
            agent_type: agentType,
            player: `${playerInfo.gameName}#${playerInfo.tagLine}`
          });
        }
      } else {
        setError(data.error || 'Failed to create share');
      }
    } catch (err) {
      console.error('Failed to create share:', err);
      setError('Failed to create share. Please try again.');
    } finally {
      setIsSharing(false);
    }
  };

  const handleCopyLink = async () => {
    if (!shareUrl) return;

    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);

      // Track copy event
      if (typeof window !== 'undefined' && (window as any).gtag) {
        (window as any).gtag('event', 'share_link_copied', {
          agent_type: agentType
        });
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleSocialShare = (platform: string) => {
    if (!shareUrl) return;

    const utmUrl = `${shareUrl}?utm_source=${platform}&utm_medium=social&utm_campaign=agent_share`;
    const shareText = `Check out my ${agentName} for ${playerInfo.gameName}#${playerInfo.tagLine}!`;

    let socialUrl = '';

    switch (platform) {
      case 'twitter':
        socialUrl = `https://twitter.com/intent/tweet?url=${encodeURIComponent(utmUrl)}&text=${encodeURIComponent(shareText)}`;
        break;
      case 'facebook':
        socialUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(utmUrl)}`;
        break;
      case 'linkedin':
        socialUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(utmUrl)}`;
        break;
      case 'reddit':
        socialUrl = `https://reddit.com/submit?url=${encodeURIComponent(utmUrl)}&title=${encodeURIComponent(shareText)}`;
        break;
      default:
        return;
    }

    window.open(socialUrl, '_blank', 'width=600,height=400');

    // Track social share
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'share_social', {
        platform,
        agent_type: agentType
      });
    }

    setShowModal(false);
  };

  const handleNativeShare = async () => {
    if (!shareUrl) return;

    if (navigator.share) {
      try {
        await navigator.share({
          title: `${playerInfo.gameName}'s ${agentName}`,
          text: `Check out my ${agentName} report!`,
          url: shareUrl
        });

        // Track native share
        if (typeof window !== 'undefined' && (window as any).gtag) {
          (window as any).gtag('event', 'share_native', {
            agent_type: agentType
          });
        }
      } catch (err) {
        // User cancelled share
        console.log('Share cancelled');
      }
    }
  };

  return (
    <>
      <button
        onClick={handleCreateShare}
        disabled={isSharing}
        className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all"
        style={{
          backgroundColor: isSharing ? 'rgba(59, 130, 246, 0.5)' : 'rgba(59, 130, 246, 0.8)',
          color: '#FFFFFF',
          cursor: isSharing ? 'not-allowed' : 'pointer'
        }}
      >
        <Share2 className="w-4 h-4" />
        <span>{isSharing ? 'Creating...' : 'Share Report'}</span>
      </button>

      {error && (
        <p className="text-xs text-red-400 mt-1">{error}</p>
      )}

      {/* Share Modal */}
      <AnimatePresence>
        {showModal && shareUrl && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.7)' }}
            onClick={() => setShowModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative rounded-2xl p-6 max-w-md w-full"
              style={{
                backgroundColor: '#1C1C1E',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close Button */}
              <button
                onClick={() => setShowModal(false)}
                className="absolute top-4 right-4 p-1 rounded-lg transition-colors"
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  color: '#8E8E93'
                }}
              >
                <X className="w-5 h-5" />
              </button>

              {/* Header */}
              <h3 className="text-xl font-bold mb-4" style={{ color: '#F5F5F7' }}>
                Share Your Report
              </h3>

              {/* Link Preview */}
              <div
                className="mb-4 p-3 rounded-lg flex items-center gap-2"
                style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)' }}
              >
                <input
                  type="text"
                  value={shareUrl}
                  readOnly
                  className="flex-1 bg-transparent outline-none text-sm"
                  style={{ color: '#8E8E93' }}
                />
                <button
                  onClick={handleCopyLink}
                  className="px-3 py-1 rounded flex items-center gap-1 transition-colors"
                  style={{
                    backgroundColor: copied ? 'rgba(52, 199, 89, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                    color: copied ? '#34C759' : '#3B82F6'
                  }}
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4" />
                      <span className="text-xs">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span className="text-xs">Copy</span>
                    </>
                  )}
                </button>
              </div>

              {/* Social Share Buttons */}
              <div className="space-y-2">
                <p className="text-sm mb-3" style={{ color: '#8E8E93' }}>
                  Share to social media:
                </p>

                <button
                  onClick={() => handleSocialShare('twitter')}
                  className="w-full flex items-center gap-3 p-3 rounded-lg transition-all hover:scale-[1.02]"
                  style={{
                    backgroundColor: 'rgba(29, 155, 240, 0.1)',
                    border: '1px solid rgba(29, 155, 240, 0.3)'
                  }}
                >
                  <Twitter className="w-5 h-5" style={{ color: '#1D9BF0' }} />
                  <span style={{ color: '#F5F5F7' }}>Share on X (Twitter)</span>
                </button>

                <button
                  onClick={() => handleSocialShare('linkedin')}
                  className="w-full flex items-center gap-3 p-3 rounded-lg transition-all hover:scale-[1.02]"
                  style={{
                    backgroundColor: 'rgba(10, 102, 194, 0.1)',
                    border: '1px solid rgba(10, 102, 194, 0.3)'
                  }}
                >
                  <Linkedin className="w-5 h-5" style={{ color: '#0A66C2' }} />
                  <span style={{ color: '#F5F5F7' }}>Share on LinkedIn</span>
                </button>

                <button
                  onClick={() => handleSocialShare('reddit')}
                  className="w-full flex items-center gap-3 p-3 rounded-lg transition-all hover:scale-[1.02]"
                  style={{
                    backgroundColor: 'rgba(255, 69, 0, 0.1)',
                    border: '1px solid rgba(255, 69, 0, 0.3)'
                  }}
                >
                  <MessageCircle className="w-5 h-5" style={{ color: '#FF4500' }} />
                  <span style={{ color: '#F5F5F7' }}>Share on Reddit</span>
                </button>

                {/* Native Share (Mobile) */}
                {navigator.share && (
                  <button
                    onClick={handleNativeShare}
                    className="w-full flex items-center gap-3 p-3 rounded-lg transition-all hover:scale-[1.02]"
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.1)'
                    }}
                  >
                    <Share2 className="w-5 h-5" style={{ color: '#8E8E93' }} />
                    <span style={{ color: '#F5F5F7' }}>More sharing options...</span>
                  </button>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
