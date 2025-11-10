"""
Query Parser - Infers GroupFilters from natural language queries

Uses heuristics and LLM to parse user intent into GroupFilter objects
"""

import re
from typing import Tuple, Optional
from .tools import GroupFilter
from src.agents.shared.bedrock_adapter import BedrockLLM


def parse_query_with_llm(user_query: str, llm: BedrockLLM) -> Tuple[GroupFilter, GroupFilter]:
    """
    Use LLM to parse user query into two GroupFilters

    Args:
        user_query: User's natural language query
        llm: BedrockLLM instance

    Returns:
        Tuple of (group1_filter, group2_filter)
    """
    prompt = f"""Parse this League of Legends analysis query into two data group filters.

**Query**: {user_query}

**Task**: Identify two time periods, champion sets, or roles to compare.

**Common patterns**:
- Time: "last 30 days vs previous 30 days", "recent vs old", "this month vs last month"
- Role: "ADC vs Support", "my top lane vs mid lane"
- Champion type: "tanks vs assassins", "AP vs AD champions"
- Data quality: "reliable games vs all games", "games with >10 matches"

**Output JSON** (no additional text):
{{
  "group1": {{
    "name": "Group 1 descriptive name",
    "time_filter": {{"days_ago": 30, "days_until": 0}},
    "role_filter": ["ADC"],
    "champion_filter": null,
    "governance_filter": null,
    "min_games": 5
  }},
  "group2": {{
    "name": "Group 2 descriptive name",
    "time_filter": {{"days_ago": 60, "days_until": 30}},
    "role_filter": null,
    "champion_filter": null,
    "governance_filter": null,
    "min_games": 5
  }}
}}

**Field explanations**:
- time_filter: {{"days_ago": X, "days_until": Y}} filters data from X days ago until Y days ago
- role_filter: ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"] or null
- champion_filter: [champion_ids] or null
- governance_filter: ["CONFIDENT"] for high-quality data, null for all
- min_games: minimum games threshold (default 5)

Generate the JSON now:"""

    try:
        result = llm.generate_sync(prompt=prompt, max_tokens=800, temperature=0.3)
        response_text = result["text"].strip()

        # Extract JSON
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()

        import json
        parsed = json.loads(response_text)

        # Create GroupFilter objects
        group1_data = parsed["group1"]
        group2_data = parsed["group2"]

        group1 = GroupFilter(
            name=group1_data["name"],
            time_filter=group1_data.get("time_filter"),
            role_filter=group1_data.get("role_filter"),
            champion_filter=group1_data.get("champion_filter"),
            governance_filter=group1_data.get("governance_filter"),
            min_games=group1_data.get("min_games", 5)
        )

        group2 = GroupFilter(
            name=group2_data["name"],
            time_filter=group2_data.get("time_filter"),
            role_filter=group2_data.get("role_filter"),
            champion_filter=group2_data.get("champion_filter"),
            governance_filter=group2_data.get("governance_filter"),
            min_games=group2_data.get("min_games", 5)
        )

        return group1, group2

    except Exception as e:
        print(f"⚠️ LLM query parsing failed: {e}")
        # Fallback to heuristic
        return parse_query_heuristic(user_query)


def parse_query_heuristic(user_query: str) -> Tuple[GroupFilter, GroupFilter]:
    """
    Fallback heuristic parser for common query patterns

    Args:
        user_query: User's natural language query

    Returns:
        Tuple of (group1_filter, group2_filter)
    """
    query_lower = user_query.lower()

    # Pattern 1: Last X days vs previous X days
    match = re.search(r'last (\d+) days? vs (?:previous|past) (\d+) days?', query_lower)
    if match:
        days1 = int(match.group(1))
        days2 = int(match.group(2))

        return (
            GroupFilter(
                name=f"Last {days1} days",
                time_filter={"days_ago": days1, "days_until": 0}
            ),
            GroupFilter(
                name=f"Previous {days2} days",
                time_filter={"days_ago": days1 + days2, "days_until": days1}
            )
        )

    # Pattern 2: Role comparison
    role_keywords = {
        'top': 'TOP',
        'jungle': 'JUNGLE',
        'jg': 'JUNGLE',
        'mid': 'MID',
        'adc': 'ADC',
        'bot': 'ADC',
        'support': 'SUPPORT',
        'supp': 'SUPPORT'
    }

    roles_found = []
    for keyword, role in role_keywords.items():
        if keyword in query_lower:
            roles_found.append(role)

    if len(roles_found) >= 2:
        return (
            GroupFilter(
                name=f"{roles_found[0]} games",
                role_filter=[roles_found[0]]
            ),
            GroupFilter(
                name=f"{roles_found[1]} games",
                role_filter=[roles_found[1]]
            )
        )

    # Pattern 3: Time-based (recent vs old)
    if 'recent' in query_lower and ('old' in query_lower or 'previous' in query_lower or 'earlier' in query_lower):
        return (
            GroupFilter(
                name="Recent (Last 30 days)",
                time_filter={"days_ago": 30, "days_until": 0}
            ),
            GroupFilter(
                name="Previous (30-60 days ago)",
                time_filter={"days_ago": 60, "days_until": 30}
            )
        )

    # Default fallback: last 30 vs previous 30
    print(f"⚠️ Query not recognized, using default time comparison: {query_lower}")
    return (
        GroupFilter(
            name="Recent (Last 30 days)",
            time_filter={"days_ago": 30, "days_until": 0}
        ),
        GroupFilter(
            name="Previous (30-60 days ago)",
            time_filter={"days_ago": 60, "days_until": 30}
        )
    )
