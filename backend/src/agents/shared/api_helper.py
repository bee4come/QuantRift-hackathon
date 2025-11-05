#!/usr/bin/env python3
"""
API Helper - 三层报告生成的API层辅助函数
用于server.py中的agent endpoints
"""

from typing import Dict, Any, Tuple
from .prompt_wrapper import wrap_for_three_tier_output, extract_brief_and_detailed
from .bedrock_adapter import BedrockLLM


def generate_three_tier_report(
    agent_class,
    agent_init_kwargs: Dict[str, Any],
    agent_run_kwargs: Dict[str, Any],
    agent_name: str = ""
) -> Dict[str, Any]:
    """
    生成三层报告（Sonnet结构化输出 + Haiku总结）

    Args:
        agent_class: Agent类（例如WeaknessAnalysisAgent）
        agent_init_kwargs: Agent初始化参数
        agent_run_kwargs: Agent.run()的参数
        agent_name: Agent名称（用于总结）

    Returns:
        {
            "one_liner": "30-40字一句话摘要",
            "brief": "100-150字简要分析（3-5个要点）",
            "detailed": "完整详细报告",
            "raw_output": "原始输出（用于调试）"
        }
    """
    print(f"\n🎯 Generating three-tier report for {agent_name}...")

    # Step 1: 初始化agent（使用Sonnet）
    print("📝 Step 1: Initializing agent with Sonnet...")
    agent = agent_class(model="sonnet", **agent_init_kwargs)

    # Step 2: 包装agent的prompt（如果agent支持）
    # 注意：这里假设agent使用BedrockLLM.generate_sync()
    # 我们需要修改agent的prompt building过程
    # 暂时先直接调用，看看输出格式

    print("🚀 Step 2: Running agent analysis (Sonnet)...")
    result, report_text = agent.run(**agent_run_kwargs)

    # Step 3: 从输出提取brief和detailed
    print("📊 Step 3: Extracting brief and detailed from Sonnet output...")
    brief, detailed = extract_brief_and_detailed(report_text)

    print(f"   Brief: {len(brief)} chars")
    print(f"   Detailed: {len(detailed)} chars")

    # Step 4: 用Haiku总结brief成one-liner
    print("✨ Step 4: Generating one-liner with Haiku...")
    haiku = BedrockLLM(model="haiku")

    one_liner_prompt = f"""
以下是{agent_name}的简要分析：

{brief}

请用一句话（30-40字以内）总结核心发现。要求：
1. 简洁有力，突出最关键的信息
2. 包含具体数字或发现的数量（如果有）
3. 30-40字以内，不要超过

只输出一句话摘要，不要其他内容。
"""

    one_liner_result = haiku.generate_sync(
        prompt=one_liner_prompt,
        max_tokens=100
    )
    one_liner = one_liner_result["text"].strip().strip('"\'')

    # 限制长度
    if len(one_liner) > 45:
        one_liner = one_liner[:40] + "..."

    print(f"   One-liner: {one_liner}")
    print("✅ Three-tier report generation complete!")

    return {
        "one_liner": one_liner,
        "brief": brief,
        "detailed": detailed,
        "raw_output": report_text,  # 保留原始输出用于调试
        "result_data": result  # 保留agent的结构化数据
    }


def wrap_agent_for_three_tier(agent_instance):
    """
    包装agent实例，使其生成三层结构化输出

    这个函数修改agent的LLM调用，在生成前包装prompt

    Args:
        agent_instance: Agent实例

    Returns:
        修改后的agent实例（原地修改）
    """
    # 保存原始的generate_sync方法
    original_generate = agent_instance.llm.generate_sync

    def wrapped_generate(prompt, system=None, **kwargs):
        """包装的generate方法，自动添加三层结构化输出格式"""
        # 如果有system prompt，包装它
        if system:
            wrapped_prompts = wrap_for_three_tier_output(system, prompt)
            return original_generate(
                prompt=wrapped_prompts["user"],
                system=wrapped_prompts["system"],
                **kwargs
            )
        else:
            # 没有system prompt，直接在user prompt中添加结构化要求
            structured_prompt = prompt + """

IMPORTANT: Output in the following structured format:

# BRIEF
[100-150 words concise analysis with 3-5 key findings, each starting with •]

# DETAILED
[Complete detailed analysis]
"""
            return original_generate(prompt=structured_prompt, **kwargs)

    # 替换方法
    agent_instance.llm.generate_sync = wrapped_generate

    return agent_instance
