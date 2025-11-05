import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Configure route to allow longer execution time for Annual Summary
export const maxDuration = 180; // 180 seconds for detailed analysis

/**
 * POST /api/agents/annual-summary
 * Call Annual Summary Agent to generate annual summary
 *
 * Request Body:
 * {
 *   puuid: string;
 *   region?: string;
 *   model?: "sonnet" | "haiku";
 * }
 *
 * Response:
 * {
 *   success: boolean;
 *   agent: "annual_summary";
 *   one_liner: string;
 *   brief: string;
 *   detailed: string;
 *   data: {
 *     analysis: object;  // Complete annual analysis data
 *     card_data: object; // Frontend card data (including fun tags and share copy)
 *   };
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { puuid, region = 'na1', model = 'sonnet' } = body;

    if (!puuid) {
      return NextResponse.json(
        { success: false, error: 'Missing required parameter: puuid' },
        { status: 400 }
      );
    }

    const url = `${BACKEND_URL}/v1/agents/annual-summary`;
    console.log(`🔄 Annual Summary request: puuid=${puuid}, region=${region}, model=${model}`);

    // Annual Summary may take longer (generating 3000-5000 word report)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 minutes timeout

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          puuid,
          region,
          model,
        }),
        cache: 'no-store',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      console.log(`✅ Annual Summary response: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`❌ Annual Summary error: ${response.status}`, errorText);
        return NextResponse.json(
          {
            success: false,
            error: `Backend returned ${response.status}: ${response.statusText}`,
            details: errorText
          },
          { status: response.status }
        );
      }

      // Check if response is SSE stream (text/event-stream)
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('text/event-stream')) {
        console.log(`🌊 Passing through SSE stream for annual-summary`);
        // Pass through the SSE stream
        return new Response(response.body, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        });
      }

      // Fallback to JSON (backward compatible)
      const data = await response.json();
      return NextResponse.json(data);
    } catch (fetchError) {
      clearTimeout(timeoutId);

      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        return NextResponse.json(
          {
            success: false,
            error: 'Annual Summary generation timed out after 3 minutes. The report is very detailed and may take longer.',
          },
          { status: 504 }
        );
      }
      throw fetchError;
    }
  } catch (error) {
    console.error('❌ Error in Annual Summary API route:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

    if (errorMessage.includes('fetch failed') || errorMessage.includes('ECONNREFUSED')) {
      return NextResponse.json(
        {
          success: false,
          error: 'Cannot connect to backend server. Please make sure backend is running on port 8000.',
          details: errorMessage
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: errorMessage
      },
      { status: 500 }
    );
  }
}
