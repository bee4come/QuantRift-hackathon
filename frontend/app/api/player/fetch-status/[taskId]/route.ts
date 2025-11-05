import { NextRequest, NextResponse } from 'next/server';

const AGENTS_API_URL = process.env.AGENTS_API_URL || 'http://localhost:8000';

/**
 * GET /api/player/fetch-status/{taskId}
 * Check status of background data fetch task
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await context.params;

    // Forward request to FastAPI backend
    const response = await fetch(`${AGENTS_API_URL}/v1/player/fetch-status/${taskId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.detail || 'Failed to get fetch status' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in fetch-status route:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
