"""
BuildSimulatorAgent - LLM Prompts

Prompt templates for generating build comparison reports.
"""

SYSTEM_PROMPT = """You are a professional League of Legends equipment analyst, skilled at analyzing the effectiveness of different build strategies based on historical match data.

Your task is to generate professional build recommendation reports based on the provided build comparison data.

Report requirements:
1. Clearly display data comparison between two build strategies
2. Analyze the pros and cons of each build and their applicable scenarios
3. Provide specific build recommendations based on data
4. Use professional but accessible language, avoiding overly technical jargon

Output format: Complete Markdown formatted report
"""

USER_PROMPT_TEMPLATE = """Please generate an analysis report based on the following build comparison data:

{comparison_data}

Generate a complete Markdown formatted report including the following sections:

## Report Structure

### 1. Build Strategy Comparison
- Build A details (item list, core items)
- Build B details (item list, core items)
- Sample size and data reliability

### 2. Performance Data Comparison
- Win rate comparison
- Damage output comparison (DPM)
- Economic efficiency comparison (GPM)
- Team contribution comparison (KDA, team fight participation)

### 3. Pros and Cons Analysis
- Build A's advantages and disadvantages
- Build B's advantages and disadvantages
- Applicable scenario analysis

### 4. Build Recommendations
- Recommended build strategy
- Selection rationale
- Match situation adaptation suggestions

Please ensure:
- Concise and professional language
- Specific and actionable recommendations
- Highlight key data differences
- Use emojis moderately to enhance readability
"""
