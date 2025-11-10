"""
Postgame Review Agent
赛后复盘 Agent - 单场比赛量化诊断
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

# 导入共享模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.shared import BedrockLLM, get_config
from .engine import PostgameReviewEngine
from .prompts import build_narrative_prompt


class PostgameReviewAgent:
    """
    赛后复盘 Agent

    基于规则引擎的量化诊断系统，可选LLM增强叙述

    Args:
        use_llm: 是否使用LLM生成增强报告（默认False，仅规则引擎）
        model: LLM模型选择（"sonnet" 或 "haiku"）
    """

    def __init__(self, use_llm: bool = False, model: str = "haiku"):
        self.config = get_config()
        self.engine = PostgameReviewEngine()
        self.use_llm = use_llm

        if use_llm:
            self.llm = BedrockLLM(model=model)

    def run(
        self,
        match_features: Dict[str, Any],
        timeline_features: Dict[str, Any],
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        运行赛后复盘分析

        Args:
            match_features: 比赛基础特征（match_id, champion, role, win, kda等）
            timeline_features: 时间线特征（cs_at, gold_curve, item_purchases等）
            output_dir: 输出目录（可选，如果提供则保存JSON文件）

        Returns:
            包含诊断结果的字典
        """
        # 使用规则引擎生成量化诊断
        review = self.engine.generate_postgame_review(
            match_features=match_features,
            timeline_features=timeline_features
        )

        # 可选：使用LLM生成增强叙述
        if self.use_llm:
            llm_narrative = self._generate_llm_narrative(review)
            review['llm_narrative'] = llm_narrative

        # 保存结果
        if output_dir:
            self._save_review(review, output_dir)

        return review

    def _generate_llm_narrative(self, review: Dict[str, Any]) -> str:
        """使用LLM生成人性化的复盘报告"""
        prompt = build_narrative_prompt(review)
        result = self.llm.generate_sync(prompt=prompt, max_tokens=2000)
        return result["text"]

    def _save_review(self, review: Dict[str, Any], output_dir: str):
        """保存复盘结果为JSON文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        match_id = review['match_id']
        filename = f"postgame_review_{match_id}.json"
        file_path = output_path / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(review, f, indent=2, ensure_ascii=False)

        print(f"✅ 复盘报告已保存: {file_path}")


def main():
    """命令行入口（示例用法）"""
    import argparse

    parser = argparse.ArgumentParser(description="赛后复盘 Agent")
    parser.add_argument("--match-features", required=True, help="比赛特征JSON文件路径")
    parser.add_argument("--timeline-features", required=True, help="时间线特征JSON文件路径")
    parser.add_argument("--output-dir", default="output/postgame_review", help="输出目录")
    parser.add_argument("--use-llm", action="store_true", help="使用LLM生成增强报告")
    parser.add_argument("--model", default="sonnet", choices=["sonnet", "haiku"], help="LLM模型")

    args = parser.parse_args()

    # 加载输入数据
    with open(args.match_features, 'r', encoding='utf-8') as f:
        match_features = json.load(f)

    with open(args.timeline_features, 'r', encoding='utf-8') as f:
        timeline_features = json.load(f)

    # 运行复盘
    agent = PostgameReviewAgent(use_llm=args.use_llm, model=args.model)
    review = agent.run(
        match_features=match_features,
        timeline_features=timeline_features,
        output_dir=args.output_dir
    )

    # 打印摘要
    print("\n" + "="*60)
    print(f"📊 赛后复盘完成")
    print("="*60)
    print(f"   英雄: {review['champion']} ({review['role']})")
    print(f"   结果: {review['result']}")
    print(f"   评分: {review['overall_score']['grade']} ({review['overall_score']['score']}分)")
    print(f"   问题数: {review['overall_score']['total_issues']}个")

    if args.use_llm and 'llm_narrative' in review:
        print("\n📝 LLM 复盘报告:")
        print(review['llm_narrative'])


if __name__ == "__main__":
    main()
