#!/usr/bin/env python3
"""
Three-Tier Generator - Sonnet详细报告 + Haiku总结（已优化：跳过brief以节省token）
流程：
1. Sonnet直接生成完整详细报告（不生成brief）
2. Haiku从detailed开头提取one-liner
3. 返回 {one_liner, brief: "", detailed}（brief已移除以节省token）
"""

import json
import re
from typing import Dict, Any
from .bedrock_adapter import BedrockLLM


class ThreeTierGenerator:
    """三层报告生成器"""

    def __init__(self):
        self.sonnet = BedrockLLM(model="sonnet")
        self.haiku = BedrockLLM(model="haiku")

    def generate(
        self,
        prompt: str,
        agent_name: str = "",
        use_json: bool = False
    ) -> Dict[str, str]:
        """
        生成三层报告（已优化：跳过brief生成以节省token）

        Args:
            prompt: 分析任务的prompt
            agent_name: Agent名称
            use_json: 是否要求JSON格式输出

        Returns:
            {
                "one_liner": "30-40字一句话摘要",
                "brief": "",  # 已移除以节省token
                "detailed": "完整详细报告"
            }
        """
        # Step 1: Sonnet直接生成detailed报告（不生成brief）
        detailed_prompt = self._build_detailed_only_prompt(prompt, agent_name)
        detailed = self.sonnet.generate(detailed_prompt)

        # Step 2: Haiku从detailed开头提取one-liner
        one_liner = self._generate_one_liner_from_detailed(detailed, agent_name)

        return {
            "one_liner": one_liner,
            "brief": "",  # 不再生成brief，节省token
            "detailed": detailed
        }

    def _build_structured_prompt(self, base_prompt: str, agent_name: str, use_json: bool) -> str:
        """构建结构化输出prompt"""
        if use_json:
            structure_instruction = """
请以JSON格式输出，包含两个字段：
{
  "brief": "100-150字的简要分析，包含3-5个核心发现（bullet points）",
  "detailed": "完整的详细分析报告（可以很长）"
}

要求：
1. brief部分：简洁明了，每个发现用 • 开头，控制在150字以内
2. detailed部分：详细展开brief中的每个发现，提供数据支持、案例、建议
3. 内容必须连贯一致（detailed是brief的自然延伸）
"""
        else:
            structure_instruction = """
请按以下结构输出：

# BRIEF
[100-150字的简要分析，包含3-5个核心发现，每个用 • 开头]

# DETAILED
[完整的详细分析报告，详细展开brief中的每个发现]

要求：
1. BRIEF部分：简洁明了，控制在150字以内
2. DETAILED部分：详细展开，提供数据支持、案例、建议
3. 内容必须连贯一致（DETAILED是BRIEF的自然延伸）
"""

        return f"{base_prompt}\n\n{structure_instruction}"

    def _parse_text_output(self, output: str) -> tuple[str, str]:
        """从文本输出解析brief和detailed"""
        # 尝试找到 # BRIEF 和 # DETAILED 标记
        brief_match = re.search(r'#\s*BRIEF\s*\n(.*?)(?=#\s*DETAILED|\Z)', output, re.DOTALL | re.IGNORECASE)
        detailed_match = re.search(r'#\s*DETAILED\s*\n(.*)', output, re.DOTALL | re.IGNORECASE)

        if brief_match and detailed_match:
            brief = brief_match.group(1).strip()
            detailed = detailed_match.group(1).strip()
        else:
            # 如果没有找到标记，尝试分割
            parts = output.split('\n\n', 1)
            if len(parts) == 2:
                brief = parts[0].strip()
                detailed = parts[1].strip()
            else:
                # 回退：前150字作为brief，全文作为detailed
                brief = output[:150].strip()
                detailed = output.strip()

        # 清理brief，确保在150字以内
        if len(brief) > 150:
            # 提取bullet points
            lines = [line.strip() for line in brief.split('\n') if line.strip()]
            brief_points = []
            total_len = 0
            for line in lines:
                if total_len + len(line) <= 150:
                    brief_points.append(line)
                    total_len += len(line)
                else:
                    break
            brief = '\n'.join(brief_points)

        return brief, detailed

    def _build_detailed_only_prompt(self, base_prompt: str, agent_name: str) -> str:
        """构建仅生成详细报告的prompt（跳过brief以节省token）"""
        instruction = """
请直接输出完整的详细分析报告。

要求：
1. 开头用1-2句话总结核心发现（这将被提取为one-liner）
2. 然后展开详细分析，提供数据支持、案例、具体建议
3. 结构清晰，内容完整，可以很长

直接输出报告内容，不需要任何标记或格式说明。
"""
        return f"{base_prompt}\n\n{instruction}"

    def _generate_one_liner_from_detailed(self, detailed: str, agent_name: str) -> str:
        """从detailed报告开头提取one-liner（用Haiku总结）"""
        # 提取detailed的前300字作为上下文
        excerpt = detailed[:300] if len(detailed) > 300 else detailed

        one_liner_prompt = f"""
以下是{agent_name}的详细分析报告开头：

{excerpt}

请用一句话（30-40字以内）总结核心发现。要求：
1. 简洁有力，突出最关键的信息
2. 如果有数字或发现数量，包含进去
3. 30-40字以内，不要超过

只输出一句话摘要，不要其他内容。
"""

        one_liner = self.haiku.generate(one_liner_prompt)

        # 清理输出
        one_liner = one_liner.strip()
        # 移除可能的引号
        one_liner = one_liner.strip('"\'')
        # 限制长度
        if len(one_liner) > 45:
            one_liner = one_liner[:40] + "..."

        return one_liner

    def _generate_one_liner(self, brief: str, agent_name: str) -> str:
        """用Haiku总结brief成one-liner（已废弃，保留以防兼容性需要）"""
        one_liner_prompt = f"""
以下是{agent_name}的简要分析：

{brief}

请用一句话（30-40字以内）总结核心发现。要求：
1. 简洁有力，突出最关键的信息
2. 包含具体数字或发现的数量
3. 30-40字以内，不要超过

只输出一句话摘要，不要其他内容。
"""

        one_liner = self.haiku.generate(one_liner_prompt)

        # 清理输出
        one_liner = one_liner.strip()
        # 移除可能的引号
        one_liner = one_liner.strip('"\'')
        # 限制长度
        if len(one_liner) > 45:
            one_liner = one_liner[:40] + "..."

        return one_liner


def test_three_tier_generator():
    """测试三层生成器"""
    print("=" * 60)
    print("🧪 Testing Three-Tier Generator")
    print("=" * 60)

    generator = ThreeTierGenerator()

    # 测试prompt
    test_prompt = """
分析以下玩家数据，找出需要改进的弱点：

玩家统计：
- 平均补刀：6.2 CS/min（段位平均：7.0）
- 视野得分：0.8 wards/min（段位平均：1.2）
- 团战死亡率：35%偏激进
- Win Rate: 48%

请分析主要弱点并提供改进建议。
"""

    # 生成三层报告
    print("\n⏳ Generating three-tier analysis...")
    result = generator.generate(
        prompt=test_prompt,
        agent_name="Weakness Analysis",
        use_json=False  # 使用文本格式更稳定
    )

    print("\n" + "=" * 60)
    print("📊 Results")
    print("=" * 60)

    print(f"\n✨ ONE-LINER ({len(result['one_liner'])} chars):")
    print(f"   {result['one_liner']}")

    print(f"\n💡 BRIEF ({len(result['brief'])} chars):")
    print(f"   {result['brief']}")

    print(f"\n📖 DETAILED ({len(result['detailed'])} chars):")
    print(f"   {result['detailed'][:200]}...")
    print(f"   (truncated, full length: {len(result['detailed'])} chars)")

    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_three_tier_generator()
