import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/player/[gameName]/[tagLine]/skills
 * Get player skill analysis data (5-dimensional radar chart)
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ gameName: string; tagLine: string }> }
) {
  try {
    const { gameName, tagLine } = await params;
    const { searchParams } = new URL(request.url);
    const topN = searchParams.get('top_n') || '3';

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

    // Call backend API to fetch player skill data
    const response = await fetch(
      `${backendUrl}/api/player/${gameName}/${tagLine}/skills?top_n=${topN}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store' // No cache, always fetch latest data
      }
    );

    if (!response.ok) {
      console.error(`Backend error: ${response.status}`);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch skills data' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Skills API error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
