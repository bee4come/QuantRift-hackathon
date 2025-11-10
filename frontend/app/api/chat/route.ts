import { NextRequest } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const message = searchParams.get('message') || '';
  const gameName = searchParams.get('gameName') || '';
  const tagLine = searchParams.get('tagLine') || '';

  // Create streaming response
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Call backend SSE endpoint
        const backendUrl = `${BACKEND_URL}/v1/chat?message=${encodeURIComponent(message)}&game_name=${encodeURIComponent(gameName)}&tag_line=${encodeURIComponent(tagLine)}`;

        const response = await fetch(backendUrl, {
          method: 'GET',
          headers: {
            'Accept': 'text/event-stream',
          },
        });

        if (!response.ok) {
          throw new Error(`Backend error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Forward SSE chunks to frontend
          const chunk = decoder.decode(value, { stream: true });
          controller.enqueue(encoder.encode(chunk));
        }

        controller.close();
      } catch (error) {
        console.error('SSE proxy error:', error);
        const errorMessage = `data: ${JSON.stringify({ type: 'error', content: error instanceof Error ? error.message : 'Unknown error' })}\n\n`;
        controller.enqueue(encoder.encode(errorMessage));
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
