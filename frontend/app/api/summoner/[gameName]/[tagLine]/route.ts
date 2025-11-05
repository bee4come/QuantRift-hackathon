import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ gameName: string; tagLine: string }> }
) {
  try {
    const { gameName, tagLine } = await params;
    const searchParams = request.nextUrl.searchParams;
    const days = searchParams.get('days') || '365';
    const count = searchParams.get('count');

    // Build query string
    const queryParams = new URLSearchParams();
    if (count) {
      queryParams.append('count', count);
    } else {
      queryParams.append('days', days);
    }

    const url = `${BACKEND_URL}/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/summary?${queryParams.toString()}`;
    
    console.log('Fetching summoner data from:', url);
    console.log('Backend URL:', BACKEND_URL);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
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

      console.log('Backend response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Backend error:', response.status, errorText);
        return NextResponse.json(
          { 
            success: false, 
            error: `Backend returned ${response.status}: ${response.statusText}`,
            details: errorText,
            backendUrl: url
          },
          { status: response.status }
        );
      }

      const data = await response.json();
      console.log('Backend response success:', data.success);
      return NextResponse.json(data);
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // Handle abort/timeout
      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        return NextResponse.json(
          { 
            success: false, 
            error: 'Request timed out after 30 seconds. The backend is taking too long to respond.',
            backendUrl: url
          },
          { status: 504 }
        );
      }
      throw fetchError;
    }
  } catch (error) {
    console.error('Error fetching summoner data:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    console.error('Error details:', errorMessage);
    
    // Check if it's a connection error
    if (errorMessage.includes('fetch failed') || errorMessage.includes('ECONNREFUSED')) {
      return NextResponse.json(
        {
          success: false,
          error: 'Cannot connect to backend server. Please make sure backend is running on port 8000.',
          details: errorMessage,
          backendUrl: BACKEND_URL
        },
        { status: 503 }
      );
    }
    
    return NextResponse.json(
      { 
        success: false, 
        error: errorMessage,
        backendUrl: BACKEND_URL
      },
      { status: 500 }
    );
  }
}

