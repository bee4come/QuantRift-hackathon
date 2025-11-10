import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Configure route to allow longer execution time for LLM generation
export const maxDuration = 180; // 180 seconds for agent analysis

// Map frontend agent IDs to backend endpoints
const AGENT_ENDPOINTS: Record<string, string> = {
  'annual-summary': '/v1/agents/annual-summary',
  'weakness-analysis': '/v1/agents/weakness-analysis',
  'performance-insights': '/v1/agents/weakness-analysis', // Performance Insights uses weakness-analysis endpoint
  'champion-mastery': '/v1/agents/champion-mastery',
  'progress-tracker': '/v1/agents/progress-tracker',
  'peer-comparison': '/v1/agents/peer-comparison',
  'friend-comparison': '/v1/agents/friend-comparison',
  'comparison-hub': '/v1/agents/comparison-hub', // Unified comparison endpoint
  'role-specialization': '/v1/agents/role-specialization',
  'champion-recommendation': '/v1/agents/champion-recommendation',
  'version-comparison': '/v1/agents/version-comparison',
  'version-trends': '/v1/agents/multi-version', // Version Trends uses multi-version endpoint
  'build-simulator': '/v1/agents/build-simulator',
  'drafting-coach': '/v1/agents/drafting-coach',
  'team-synergy': '/v1/agents/team-synergy',
  'match-analysis': '/v1/agents/match-analysis', // Match Analysis (Timeline Deep Dive + Postgame Review)
  'timeline-deep-dive': '/v1/agents/timeline-deep-dive',
  'postgame-review': '/v1/agents/postgame-review',
  'risk-forecaster': '/v1/agents/risk-forecaster',
  'detailed-analysis': '/v1/agents/detailed-analysis',
  'multi-version': '/v1/agents/multi-version',
};

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ agentId: string }> }
) {
  try {
    const { agentId } = await context.params;

    // Get backend endpoint for this agent
    const endpoint = AGENT_ENDPOINTS[agentId];
    if (!endpoint) {
      return NextResponse.json(
        { success: false, error: `Unknown agent: ${agentId}` },
        { status: 404 }
      );
    }

    // Get request body
    const body = await request.json();

    const url = `${BACKEND_URL}${endpoint}`;
    console.log(`🔄 Proxying agent request: ${agentId} → ${url}`);

    // Different timeout for different agents
    const timeoutMs = (agentId === 'friend-comparison' || agentId === 'comparison-hub') ? 180000 : 120000; // 180s for comparison agents, 120s for others
    console.log(`⏱️  Timeout set to ${timeoutMs / 1000}s for ${agentId}`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        cache: 'no-store',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      console.log(`✅ Agent response: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`❌ Agent error: ${response.status}`, errorText);
        return NextResponse.json(
          {
            success: false,
            error: `Backend returned ${response.status}: ${response.statusText}`,
            details: errorText
          },
          { status: response.status }
        );
      }

      // Check if response is SSE stream (text/event-stream)
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('text/event-stream')) {
        // Pass through the SSE stream
        return new Response(response.body, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        });
      }

      // Otherwise treat as JSON
      const data = await response.json();
      return NextResponse.json(data);
    } catch (fetchError) {
      clearTimeout(timeoutId);

      // Handle abort/timeout
      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        return NextResponse.json(
          {
            success: false,
            error: `Request timed out after ${timeoutMs / 1000} seconds. Agent analysis is taking too long.`,
          },
          { status: 504 }
        );
      }
      throw fetchError;
    }
  } catch (error) {
    console.error('❌ Error in agent API route:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

    // Check if it's a connection error
    if (errorMessage.includes('fetch failed') || errorMessage.includes('ECONNREFUSED')) {
      return NextResponse.json(
        {
          success: false,
          error: 'Cannot connect to backend server. Please make sure backend is running on port 8000.',
          details: errorMessage
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: errorMessage
      },
      { status: 500 }
    );
  }
}
