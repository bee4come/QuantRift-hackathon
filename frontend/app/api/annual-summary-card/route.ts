import { NextRequest, NextResponse } from 'next/server';

/**
 * Annual Summary Card Data API
 * Calls backend GET /v1/annual-summary to get real data and transform to AnnualCardData format
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { gameName, tagLine, region, bestChampions: providedChampions } = body;

    if (!gameName || !tagLine) {
      return NextResponse.json(
        { error: 'Missing required parameters: gameName and tagLine' },
        { status: 400 }
      );
    }

    console.log(`[Annual Summary Card] Processing data for ${gameName}#${tagLine}, region: ${region}`);

    // Use provided champion data (from PlayerProfileClient)
    const bestChampions = providedChampions || [];

    if (bestChampions.length === 0) {
      console.error('[Annual Summary Card] No champion data provided');
      return NextResponse.json(
        { error: 'No champion data available for this player' },
        { status: 400 }
      );
    }

    console.log(`[Annual Summary Card] Using ${bestChampions.length} champions from client`);

    // Construct summoner_id (gameName#tagLine format)
    const summonerId = `${gameName}#${tagLine}`;
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    // Call annual summary agent to get season analysis
    const backendResponse = await fetch(
      `${backendUrl}/v1/annual-summary/${encodeURIComponent(summonerId)}?region=${region || 'na1'}`,
      {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      }
    );

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      console.error(`[Annual Summary Card] Backend error: ${errorText}`);
      throw new Error(`Backend returned ${backendResponse.status}: ${errorText}`);
    }

    const backendData = await backendResponse.json();

    // Backend now returns { analysis: {...}, report: "..." }
    if (!backendData.analysis) {
      console.error('[Annual Summary Card] No analysis data in backend response');
      throw new Error('Invalid backend response: missing analysis data');
    }

    const analysis = backendData.analysis;
    const report = backendData.report || null;  // Extract LLM-generated report
    const metadata = analysis.metadata;
    const summary = analysis.summary;
    const timeSegments = analysis.time_segments;
    const championPool = analysis.champion_pool_evolution;
    const versionAdapt = analysis.version_adaptation;
    const highlights = analysis.annual_highlights;

    if (!summary) {
      console.error('[Annual Summary Card] No summary data in analysis');
      throw new Error('Invalid analysis data: missing summary');
    }

    console.log(`[Annual Summary Card] Received backend data for ${summary.total_games} games`);

    // Transform data format to AnnualCardData
    const coreStats = summary;
    const breadth = {
      unique_champions: summary.unique_champions,
      unique_positions: summary.unique_roles || 0
    };

    // Use player summary's best_champions data (has real games and winrate)
    // bestChampions format: { champ_id, name, games, wins, win_rate, avg_kda }
    const mostPlayed = bestChampions[0] || null;
    // Don't mutate original array - create sorted copy for finding best performance
    const sortedByWinrate = [...bestChampions].sort((a: any, b: any) => b.win_rate - a.win_rate);
    const bestPerformance = sortedByWinrate[0] || null;

    // Calculate progress data (from time_segments.tri_period)
    const triPeriod = timeSegments?.tri_period || {};
    const phases = Object.values(triPeriod) as any[]; // Get all phases
    const earlyPhase = phases[0] || {};
    const latePhase = phases[phases.length - 1] || {};
    const earlyWinrate = (earlyPhase as any)?.winrate ?? coreStats.overall_winrate;
    const lateWinrate = (latePhase as any)?.winrate ?? coreStats.overall_winrate;
    const improvement = lateWinrate - earlyWinrate;

    // Generate fun tags (based on data characteristics)
    const funTags: string[] = [];
    if (coreStats.overall_winrate > 0.55) funTags.push('High Winrate');
    if (coreStats.overall_winrate > 0.50 && coreStats.overall_winrate <= 0.55) funTags.push('Consistent Player');
    if (improvement > 0.05) funTags.push('Fast Improvement');
    if (breadth.unique_champions > 10) funTags.push('Deep Champion Pool');
    if (breadth.unique_champions <= 5) funTags.push('Specialist');
    if (coreStats.total_games > 100) funTags.push('Dedicated Grinder');

    // Get season range
    const patchRange = metadata.patch_range; // [startPatch, endPatch]
    const season = `${patchRange[0]}-${patchRange[1]}`;

    // Construct final data
    const cardData = {
      season: season,
      fun_tags: funTags.slice(0, 3), // Max 3 tags
      stats: {
        total_games: coreStats.total_games,
        win_rate: coreStats.overall_winrate, // Keep as decimal (0.54), frontend will multiply by 100
        unique_champions: breadth.unique_champions,
      },
      most_played: mostPlayed ? {
        champion_name: mostPlayed.name,
        games: mostPlayed.games,
        win_rate: mostPlayed.win_rate / 100, // Convert percentage to decimal (66.1 -> 0.661)
      } : null,
      best_performance: bestPerformance ? {
        champion_name: bestPerformance.name,
        role: 'ADC', // TODO: Get actual role from role_stats
        games: bestPerformance.games,
        win_rate: bestPerformance.win_rate / 100, // Convert percentage to decimal (66.1 -> 0.661)
      } : null,
      core_champions: bestChampions.slice(0, 5).map((champ: any) => ({
        champion_name: champ.name,
        games: champ.games,
        winrate: champ.win_rate / 100, // Convert percentage to decimal (66.1 -> 0.661)
      })),
      progress: {
        early_winrate: earlyWinrate, // Keep as decimal (0.467), frontend will multiply by 100
        late_winrate: lateWinrate, // Keep as decimal (0.583), frontend will multiply by 100
        improvement: improvement, // Keep as decimal (0.117), frontend will multiply by 100
      },
      share_texts: {
        twitter: `🎮 Season ${season} Review\n📊 ${coreStats.total_games} games | ${(coreStats.overall_winrate * 100).toFixed(1)}% WR\n🏆 Best Champion: ${bestPerformance?.name || 'N/A'} (${bestPerformance ? bestPerformance.win_rate.toFixed(1) : 'N/A'}% WR)\n📈 Improvement: +${(improvement * 100).toFixed(1)}% #LeagueOfLegends`,
        casual: `Played ${coreStats.total_games} games this season with ${(coreStats.overall_winrate * 100).toFixed(1)}% winrate! ${bestPerformance?.name || ''} performed especially well with ${bestPerformance ? bestPerformance.win_rate.toFixed(1) : 'N/A'}% WR. Overall improved by ${(improvement * 100).toFixed(1)}%!`,
        formal: `Season ${season}: ${coreStats.total_games} ranked games with ${(coreStats.overall_winrate * 100).toFixed(1)}% overall winrate. Core champion pool includes ${bestChampions.slice(0, 3).map((c: any) => c.name).join(', ')}, with ${bestPerformance?.name || ''} showing best performance at ${bestPerformance ? bestPerformance.win_rate.toFixed(1) : 'N/A'}% winrate. Notable improvement in late season, winrate increased by ${(improvement * 100).toFixed(1)}%.`,
      },
      // Pass full analysis data for detailed view
      detailed_analysis: {
        time_segments: timeSegments,
        annual_highlights: highlights,
        version_adaptation: versionAdapt,
        champion_pool_evolution: championPool,
        growth_metrics: analysis.growth_metrics || null,
        consistency_profile: analysis.consistency_profile || null,
        narrative_report: report  // LLM-generated comprehensive report
      }
    };

    console.log(`[Annual Summary Card] ✅ Data transformation complete`);
    return NextResponse.json(cardData);

  } catch (error) {
    console.error('[Annual Summary Card] Error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch annual summary data' },
      { status: 500 }
    );
  }
}
