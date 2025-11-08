import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ gameName: string; tagLine: string }> }
) {
  try {
    const { gameName, tagLine } = await params;
    const { searchParams } = new URL(request.url);
    const timeRange = searchParams.get('time_range');
    const queueId = searchParams.get('queue_id');

    const queryParams = new URLSearchParams();
    if (timeRange) {
      queryParams.append('time_range', timeRange);
    }
    if (queueId) {
      queryParams.append('queue_id', queueId);
    }

    const url = `${BACKEND_URL}/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/role-stats?${queryParams.toString()}`;

    console.log('[API Route] Fetching role stats from:', url);

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[API Route] Backend error:', response.status, errorText);
      
      // If 404 or no data, return empty array instead of error
      if (response.status === 404) {
        return NextResponse.json({
          success: true,
          role_stats: []
        });
      }
      
      return NextResponse.json(
        {
          success: false,
          error: `Backend returned ${response.status}: ${response.statusText}`,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Role stats API error:', error);
    // Return empty array on error instead of failing
    return NextResponse.json({
      success: true,
      role_stats: []
    });
  }
}

