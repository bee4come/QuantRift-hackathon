import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/player/[gameName]/[tagLine]/progress
 * Get player progress data (time series)
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ gameName: string; tagLine: string }> }
) {
  try {
    const { gameName, tagLine } = await params;
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

    // Call backend API to fetch player progress data
    const response = await fetch(
      `${backendUrl}/api/player/${gameName}/${tagLine}/progress`,
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
        { success: false, error: 'Failed to fetch progress data' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Progress API error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
