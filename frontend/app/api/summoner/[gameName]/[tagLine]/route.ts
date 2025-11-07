import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ gameName: string; tagLine: string }> }
) {
  try {
    const { gameName, tagLine } = await params;
    const searchParams = request.nextUrl.searchParams;
    const days = searchParams.get('days');
    const count = searchParams.get('count');
    const timeRange = searchParams.get('time_range') || '2024-01-01'; // Default to 2024 full year

    // Build query string
    const queryParams = new URLSearchParams();
    if (count) {
      queryParams.append('count', count);
    } else if (timeRange) {
      queryParams.append('time_range', timeRange);
    } else if (days) {
      queryParams.append('days', days);
    } else {
      // Fallback: use time_range=2024-01-01 as default
      queryParams.append('time_range', '2024-01-01');
    }

    // Debug: log the actual parameter values
    console.log('[DEBUG] Raw params - gameName:', JSON.stringify(gameName), 'tagLine:', JSON.stringify(tagLine));

    const url = `${BACKEND_URL}/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/summary?${queryParams.toString()}`;

    console.log('Fetching summoner data from:', url);
    console.log('Backend URL:', BACKEND_URL);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout for year data
    
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
            error: 'Request timed out after 120 seconds. Backend may be processing large dataset. Please try again.',
            backendUrl: url
          },
          { status: 504 }
        );
      }
      
      // Handle network/fetch errors
      const errorMessage = fetchError instanceof Error ? fetchError.message : String(fetchError);
      console.error('Fetch error details:', errorMessage, fetchError);
      
      return NextResponse.json(
        {
          success: false,
          error: `Failed to connect to backend: ${errorMessage}`,
          details: 'Please ensure the backend server is running on port 8000',
          backendUrl: url
        },
        { status: 503 }
      );
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

