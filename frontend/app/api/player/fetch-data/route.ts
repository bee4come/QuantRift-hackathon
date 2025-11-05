import { NextRequest, NextResponse } from 'next/server';

const AGENTS_API_URL = process.env.AGENTS_API_URL || 'http://localhost:8000';

/**
 * POST /api/player/fetch-data
 * Trigger background data fetch for a player
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { gameName, tagLine, region = 'na1', days = 365, includeTimeline = true } = body;

    if (!gameName || !tagLine) {
      return NextResponse.json(
        { error: 'gameName and tagLine are required' },
        { status: 400 }
      );
    }

    // Forward request to FastAPI backend
    const response = await fetch(`${AGENTS_API_URL}/v1/player/fetch-data`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        game_name: gameName,
        tag_line: tagLine,
        region,
        days,
        include_timeline: includeTimeline,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.detail || 'Failed to start data fetch' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in fetch-data route:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
