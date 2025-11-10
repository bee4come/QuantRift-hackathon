"""
Script to add caching to all agent endpoints
"""

# Agent endpoints that need caching (excluding already done ones)
AGENTS_TO_CACHE = [
    'annual-summary',
    'champion-mastery',
    'progress-tracker',
    'detailed-analysis',
    'peer-comparison',
    'friend-comparison',
    'role-specialization',
    'champion-recommendation',
    'multi-version',
    'build-simulator',
    'drafting-coach',
    'team-synergy',
    'postgame-review',
    'risk-forecaster',
    'timeline-deep-dive',
    'version-comparison',
    'comparison-hub',
    'match-analysis',
    'version-trends'
]

# Parameters to extract for each agent (for cache key)
AGENT_PARAMS = {
    'annual-summary': ['time_range', 'queue_id'],
    'champion-mastery': ['time_range', 'champion_id'],
    'progress-tracker': ['time_range', 'queue_id'],
    'detailed-analysis': ['time_range', 'queue_id', 'recent_count'],
    'peer-comparison': ['time_range', 'queue_id', 'rank'],
    'friend-comparison': ['friend_name', 'friend_tag', 'time_range', 'queue_id'],
    'role-specialization': ['role', 'time_range', 'queue_id'],
    'champion-recommendation': ['time_range', 'queue_id'],
    'multi-version': ['time_range', 'queue_id'],
    'build-simulator': ['champion_id', 'time_range'],
    'drafting-coach': ['time_range', 'queue_id'],
    'team-synergy': ['time_range', 'queue_id'],
    'postgame-review': ['match_id'],
    'risk-forecaster': ['time_range', 'queue_id', 'recent_count'],
    'timeline-deep-dive': ['match_id'],
    'version-comparison': ['time_range', 'queue_id'],
    'comparison-hub': ['time_range', 'queue_id'],
    'match-analysis': ['match_id'],
    'version-trends': ['time_range', 'queue_id']
}

print("Agent caching configuration:")
print(f"Total agents to cache: {len(AGENTS_TO_CACHE)}")
print("\nAgent parameters:")
for agent, params in AGENT_PARAMS.items():
    print(f"  {agent}: {', '.join(params)}")
