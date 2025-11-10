import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    console.log('[ShareAPI Route] Received request, body keys:', Object.keys(body));
    console.log('[ShareAPI Route] Report content length:', body.report_content?.length || 0);

    const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    console.log('[ShareAPI Route] Backend URL:', BACKEND_URL);

    const response = await fetch(`${BACKEND_URL}/api/share/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    console.log('[ShareAPI Route] Backend response status:', response.status);

    if (!response.ok) {
      const error = await response.json();
      console.error('[ShareAPI Route] Backend error:', error);
      return NextResponse.json(
        { success: false, error: error.detail || 'Failed to create share' },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('[ShareAPI Route] Success, share_id:', data.share_id);
    return NextResponse.json(data);
  } catch (error) {
    console.error('[ShareAPI Route] Exception:', error);
    console.error('[ShareAPI Route] Stack trace:', (error as Error).stack);
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
