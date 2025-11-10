#!/usr/bin/env python3
"""
Batch add caching to all remaining agent endpoints
"""

import re
from pathlib import Path

# Read server.py
server_file = Path(__file__).parent.parent / "api" / "server.py"
with open(server_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all agent endpoints that don't have caching yet
pattern = r'@app\.post\("/v1/agents/([^"]+)"\)'
matches = re.findall(pattern, content)

# Agents already cached
cached_agents = ['weakness-analysis', 'performance-insights', 'champion-mastery']

# Agents to cache
agents_to_cache = [agent for agent in matches if agent not in cached_agents]

print("Agents already cached:")
for agent in cached_agents:
    print(f"  ✓ {agent}")

print(f"\nRemaining agents to cache ({len(agents_to_cache)}):")
for agent in agents_to_cache:
    print(f"  - {agent}")

# Generate modifications
modifications = []

for agent in agents_to_cache:
    modifications.append({
        'agent_id': agent,
        'status': 'pending'
    })

print(f"\nTotal modifications to make: {len(modifications)}")
print("\nThis script prepared the list. Use the manual edit approach for safety.")
