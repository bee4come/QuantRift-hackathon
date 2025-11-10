'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import ChatInterface from '../components/ChatInterface';

function ChatContent() {
  const searchParams = useSearchParams();
  const gameName = searchParams.get('gameName') || '';
  const tagLine = searchParams.get('tagLine') || '';

  return (
    <div className="min-h-screen p-4 md:p-8">
      <ChatInterface gameName={gameName} tagLine={tagLine} />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ChatContent />
    </Suspense>
  );
}
