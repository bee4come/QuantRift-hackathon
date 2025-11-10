import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ shareId: string }> }
) {
  try {
    const { shareId } = await params;

    const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${BACKEND_URL}/api/share/${shareId}`, {
      cache: 'no-store' // Always fetch fresh data
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: 'Share not found' },
          { status: 404 }
        );
      }
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Share retrieval error:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve share' },
      { status: 500 }
    );
  }
}
