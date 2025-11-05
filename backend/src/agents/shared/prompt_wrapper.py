#!/usr/bin/env python3
"""
Prompt Wrapper - 将现有agent prompt包装成三层结构化输出
不需要修改每个agent的prompts.py，在API层面统一处理
"""


def wrap_for_three_tier_output(system_prompt: str, user_prompt: str) -> dict:
    """
    将现有prompt包装成三层结构化输出格式

    Args:
        system_prompt: 原始system prompt
        user_prompt: 原始user prompt

    Returns:
        {
            "system": 修改后的system prompt,
            "user": 修改后的user prompt
        }
    """
    # 在system prompt末尾添加结构化输出要求
    structured_system = system_prompt.strip() + """

IMPORTANT: Output in the following structured format:

# BRIEF
[100-150 words concise analysis with 3-5 key findings, each starting with •]

# DETAILED
[Complete detailed analysis report following the original requirements above]

Requirements:
1. BRIEF: Concise summary with bullet points (• ), max 150 words
2. DETAILED: Full analysis expanding on each brief point with data, examples, recommendations
3. Content must be coherent - DETAILED naturally extends BRIEF
"""

    return {
        "system": structured_system,
        "user": user_prompt
    }


def extract_brief_and_detailed(full_output: str) -> tuple:
    """
    从Sonnet的结构化输出中提取brief和detailed

    Args:
        full_output: Sonnet的完整输出

    Returns:
        (brief_text, detailed_text)
    """
    import re

    # 查找 # BRIEF 和 # DETAILED 标记
    brief_pattern = r'#\s*BRIEF\s*\n(.*?)(?=\n#\s*DETAILED|\Z)'
    detailed_pattern = r'#\s*DETAILED\s*\n(.*)'

    brief_match = re.search(brief_pattern, full_output, re.DOTALL | re.IGNORECASE)
    detailed_match = re.search(detailed_pattern, full_output, re.DOTALL | re.IGNORECASE)

    if brief_match and detailed_match:
        brief = brief_match.group(1).strip()
        detailed = detailed_match.group(1).strip()
    else:
        # 回退策略：如果没有找到标记
        lines = full_output.split('\n\n', 1)
        if len(lines) == 2:
            brief = lines[0].strip()
            detailed = lines[1].strip()
        else:
            # 最后的回退：前150字作为brief，全文作为detailed
            brief = full_output[:150].strip() + "..."
            detailed = full_output.strip()

    # 清理brief，确保不超过150字
    if len(brief) > 150:
        # 提取bullet points
        brief_lines = [line.strip() for line in brief.split('\n') if line.strip()]
        brief_points = []
        total_len = 0
        for line in brief_lines:
            if total_len + len(line) <= 150:
                brief_points.append(line)
                total_len += len(line)
            else:
                break
        brief = '\n'.join(brief_points)

    return brief, detailed


def test_prompt_wrapper():
    """测试prompt包装器"""
    # 示例：原始的WeaknessAnalysis prompt
    original_system = """You are a League of Legends weakness diagnosis expert.

Generate a 1500-2000 word diagnostic report including:
1. Weakness Overview (300 words): Main issues identified
2. Champion Pool Weaknesses (400 words): Low winrate champions and cause analysis
3. Position Weaknesses (400 words): Specific issues with weak positions
4. Skill-Level Weaknesses (300 words): Laning/teamfighting/macro-level issues
5. Improvement Recommendations (300-400 words): Priority-ranked specific action plans (Top 3-5)

Objective diagnosis, specific and actionable, with clear priorities."""

    original_user = """Please generate a weakness diagnosis report.

Player Data:
- Average CS: 6.2 CS/min (Rank avg: 7.0)
- Vision Score: 0.8 wards/min (Rank avg: 1.2)
- Teamfight Deaths: 35% aggressive positioning

Requirements: 1500-2000 words, specific and actionable."""

    # 包装成三层结构化输出
    wrapped = wrap_for_three_tier_output(original_system, original_user)

    print("=" * 60)
    print("🔧 Prompt Wrapper Test")
    print("=" * 60)
    print("\n📝 ORIGINAL SYSTEM PROMPT:")
    print(original_system)
    print("\n" + "-" * 60)
    print("\n✨ WRAPPED SYSTEM PROMPT:")
    print(wrapped["system"])
    print("\n" + "=" * 60)

    # 测试提取功能
    sample_output = """
# BRIEF
• Found 3 main improvement areas with 8% potential WR increase
• CS efficiency 12% below rank average (6.2 vs 7.0 CS/min)
• Vision control insufficient: 0.8 wards/min vs recommended 1.2+
• Teamfight positioning 35% too aggressive, need safer output distance

# DETAILED
## Weakness Overview
The player shows consistent performance gaps across three key dimensions...
(更多详细内容)
"""

    brief, detailed = extract_brief_and_detailed(sample_output)
    print("\n📊 EXTRACTION TEST:")
    print(f"\nBRIEF ({len(brief)} chars):")
    print(brief)
    print(f"\nDETAILED ({len(detailed)} chars):")
    print(detailed[:100] + "...")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_prompt_wrapper()
