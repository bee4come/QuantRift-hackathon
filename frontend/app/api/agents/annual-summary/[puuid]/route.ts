import { NextRequest, NextResponse } from 'next/server';

const AGENTS_API_URL = process.env.AGENTS_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ puuid: string }> }
) {
  try {
    const { puuid } = await context.params;
    const searchParams = request.nextUrl.searchParams;
    const region = searchParams.get('region') || 'na1';
    const start_patch = searchParams.get('start_patch');
    const end_patch = searchParams.get('end_patch');

    const queryParams = new URLSearchParams();
    queryParams.append('region', region);
    if (start_patch) queryParams.append('start_patch', start_patch);
    if (end_patch) queryParams.append('end_patch', end_patch);

    const url = `${AGENTS_API_URL}/v1/annual-summary/${encodeURIComponent(puuid)}?${queryParams.toString()}`;
    
    console.log('Fetching annual summary from:', url);

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    console.log('Agents API response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Agents API error:', response.status, errorText);
      return NextResponse.json(
        { 
          success: false, 
          error: `Agents API returned ${response.status}: ${response.statusText}`,
          details: errorText,
          agentsUrl: url
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching annual summary:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    if (errorMessage.includes('fetch failed') || errorMessage.includes('ECONNREFUSED')) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Cannot connect to Agents API. Please make sure the agents server is running (cd agents && uvicorn api.server:app --reload)',
          details: errorMessage,
          agentsUrl: AGENTS_API_URL
        },
        { status: 503 }
      );
    }
    
    return NextResponse.json(
      { 
        success: false, 
        error: errorMessage,
        agentsUrl: AGENTS_API_URL
      },
      { status: 500 }
    );
  }
}

