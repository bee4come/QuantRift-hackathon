import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ gameName: string; tagLine: string }> }
) {
  try {
    const { gameName, tagLine } = await params;

    const url = `${BACKEND_URL}/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/data-status`;

    console.log('[API Route] Fetching data status from:', url);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      console.log('[API Route] Backend response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[API Route] Backend error:', response.status, errorText);
        return NextResponse.json(
          {
            success: false,
            error: `Backend returned ${response.status}: ${response.statusText}`,
            details: errorText
          },
          { status: response.status }
        );
      }

      const data = await response.json();
      console.log('[API Route] Data status retrieved successfully');
      return NextResponse.json(data);
    } catch (fetchError) {
      clearTimeout(timeoutId);

      // Handle abort/timeout
      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        return NextResponse.json(
          {
            success: false,
            error: 'Request timed out. Backend took too long to respond.'
          },
          { status: 504 }
        );
      }
      throw fetchError;
    }
  } catch (error) {
    console.error('[API Route] Error fetching data status:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

    // Check if it's a connection error
    if (errorMessage.includes('fetch failed') || errorMessage.includes('ECONNREFUSED')) {
      return NextResponse.json(
        {
          success: false,
          error: 'Cannot connect to backend server. Please ensure backend is running on port 8000.',
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
