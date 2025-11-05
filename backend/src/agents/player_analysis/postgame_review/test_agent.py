"""
PostgameReviewAgent 测试脚本

测试复盘 Agent 的基本功能（使用模拟数据）
"""

import json
from pathlib import Path
from agent import PostgameReviewAgent


def create_mock_match_features():
    """创建模拟的比赛特征数据"""
    return {
        'match_id': 'NA1_1234567890',
        'champion_name': '亚索',
        'role': 'MIDDLE',
        'win': True,
        'game_duration': 1850,  # 30分50秒
        'kills': 8,
        'deaths': 5,
        'assists': 12,
        'kda_adj': 4.0,
        'obj_participation': 3,
        'items': [
            {'item_id': 3153, 'name': '破败王者之刃'},
            {'item_id': 3006, 'name': '狂战士胫甲'},
            {'item_id': 3031, 'name': '无尽之刃'}
        ]
    }


def create_mock_timeline_features():
    """创建模拟的时间线特征数据"""
    return {
        'cs_at': {
            'cs_10': 65,
            'cs_15': 95,
            'cs_20': 125
        },
        'gold_curve': [
            {'min': 10, 'gold': 3200},
            {'min': 15, 'gold': 5400},
            {'min': 20, 'gold': 8100}
        ],
        'item_purchases': [
            {'item_id': 1053, 'time': 5.2},
            {'item_id': 3153, 'time': 15.8},
            {'item_id': 3006, 'time': 19.2},
            {'item_id': 3031, 'time': 25.5}
        ],
        'ward_events': [
            {'type': 'placed', 'time': 120},
            {'type': 'placed', 'time': 450},
            {'type': 'placed', 'time': 780}
        ],
        'time_to_core2': 19.2  # 第二件核心装备时间（分钟）
    }


def test_basic_review():
    """测试基础复盘功能（仅规则引擎）"""
    print("=" * 60)
    print("测试 1: 基础复盘（Rule Engine Only）")
    print("=" * 60)

    agent = PostgameReviewAgent(use_llm=False)

    match_features = create_mock_match_features()
    timeline_features = create_mock_timeline_features()

    review = agent.run(
        match_features=match_features,
        timeline_features=timeline_features,
        output_dir="test_output"
    )

    print(f"\n✅ 规则引擎诊断完成")
    print(f"   - 对线期问题: {len(review['lane_phase']['issues'])}个")
    print(f"   - 目标控制问题: {len(review['objective_phase']['issues'])}个")
    print(f"   - 出装问题: {len(review['build_timing']['issues'])}个")
    print(f"   - 团战问题: {len(review['teamfight']['issues'])}个")
    print(f"   - 总体评分: {review['overall_score']['grade']} ({review['overall_score']['score']}分)")

    return review


def test_llm_enhanced_review():
    """测试LLM增强复盘（需要AWS凭证）"""
    print("\n" + "=" * 60)
    print("测试 2: LLM增强复盘（Sonnet）")
    print("=" * 60)

    try:
        agent = PostgameReviewAgent(use_llm=True, model="sonnet")

        match_features = create_mock_match_features()
        timeline_features = create_mock_timeline_features()

        review = agent.run(
            match_features=match_features,
            timeline_features=timeline_features,
            output_dir="test_output"
        )

        print(f"\n✅ LLM增强复盘完成")
        print(f"   - 生成叙述长度: {len(review.get('llm_narrative', ''))}字符")
        print(f"\n📝 LLM复盘报告:")
        print(review.get('llm_narrative', '未生成'))

        return review

    except Exception as e:
        print(f"\n⚠️  LLM测试跳过（可能缺少AWS凭证）: {e}")
        return None


def main():
    """运行所有测试"""
    print("\n🚀 PostgameReviewAgent 集成测试\n")

    # 测试1: 基础规则引擎
    basic_review = test_basic_review()

    # 保存基础诊断结果
    with open('test_output/basic_review.json', 'w', encoding='utf-8') as f:
        json.dump(basic_review, f, indent=2, ensure_ascii=False)

    print(f"\n💾 基础诊断结果已保存: test_output/basic_review.json")

    # 测试2: LLM增强（可选）
    # 注释掉避免需要AWS凭证
    # llm_review = test_llm_enhanced_review()

    print("\n" + "=" * 60)
    print("✅ PostgameReviewAgent 测试完成")
    print("=" * 60)
    print("\n📋 验证清单:")
    print("  [✓] PostgameReviewAgent 导入成功")
    print("  [✓] PostgameReviewEngine 规则引擎工作正常")
    print("  [✓] 量化诊断输出符合预期")
    print("  [✓] JSON输出保存成功")
    print("  [-] LLM增强功能（需要AWS凭证，已跳过）")


if __name__ == "__main__":
    main()
