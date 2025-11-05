#!/usr/bin/env python3
"""
Brief Extractor - 从完整报告提取三层信息
Three-tier information extraction:
1. One-liner (30-40字): 卡片内1行摘要
2. Brief (100-150字): 浮动窗口3-5个要点
3. Detailed (完整): 已有的详细报告
"""

import re
from typing import Dict, Any


class BriefExtractor:
    """从完整报告提取简短摘要"""

    @staticmethod
    def extract_three_tier(full_report: str, agent_name: str = "") -> Dict[str, str]:
        """
        从完整报告提取三层信息

        Args:
            full_report: 完整的分析报告
            agent_name: Agent名称（用于生成通用摘要）

        Returns:
            {
                "one_liner": "30-40字的1行摘要",
                "brief": "100-150字的简要分析（3-5个要点）",
                "detailed": "完整报告"
            }
        """
        # 清理报告
        report = full_report.strip()

        # 提取one-liner (第一个实质性句子，限制30-40字)
        one_liner = BriefExtractor._extract_one_liner(report, agent_name)

        # 提取brief (前3-5个要点，限制100-150字)
        brief = BriefExtractor._extract_brief(report, agent_name)

        return {
            "one_liner": one_liner,
            "brief": brief,
            "detailed": report
        }

    @staticmethod
    def _extract_one_liner(report: str, agent_name: str = "") -> str:
        """
        提取1行摘要（30-40字）
        策略：
        1. 查找第一个包含数字或关键词的句子
        2. 如果是markdown，跳过标题行
        3. 限制在40字以内
        """
        lines = report.split('\n')

        # 关键词列表
        keywords = [
            '发现', '建议', '分析', '显示', '表现', '改进', '优势', '劣势',
            'found', 'suggest', 'recommend', 'analysis', 'shows', 'improve'
        ]

        for line in lines:
            line = line.strip()

            # 跳过空行、标题、分割线
            if not line or line.startswith('#') or line.startswith('---') or line.startswith('==='):
                continue

            # 移除markdown标记
            clean_line = re.sub(r'\*\*|\*|`|^[-•]\s*', '', line)

            # 检查是否包含关键词或数字
            has_keyword = any(kw in clean_line.lower() for kw in keywords)
            has_number = bool(re.search(r'\d+', clean_line))

            if has_keyword or has_number:
                # 限制长度
                if len(clean_line) > 45:
                    # 截取到第一个句号或逗号
                    truncated = re.split(r'[。，,.]', clean_line)[0]
                    return truncated[:40] + ('...' if len(truncated) > 40 else '')
                return clean_line

        # 如果没有找到合适的，返回前40字
        clean_report = re.sub(r'[#\*`-]', '', report).strip()
        first_sentence = clean_report.split('\n')[0]
        return first_sentence[:40] + ('...' if len(first_sentence) > 40 else '')

    @staticmethod
    def _extract_brief(report: str, agent_name: str = "") -> str:
        """
        提取Brief摘要（100-150字，3-5个要点）
        策略：
        1. 提取markdown列表项
        2. 提取带数字的句子
        3. 提取段落首句
        4. 限制在150字以内
        """
        lines = report.split('\n')
        points = []
        current_point = ""

        for line in lines:
            line = line.strip()

            # 跳过空行和分割线
            if not line or line.startswith('---') or line.startswith('==='):
                continue

            # 跳过一级二级标题，保留三级标题作为要点
            if line.startswith('# ') or line.startswith('## '):
                continue

            # 提取列表项（markdown格式）
            if line.startswith('- ') or line.startswith('* ') or line.startswith('• '):
                point = re.sub(r'^[-\*•]\s*', '', line)
                point = re.sub(r'\*\*|\*|`', '', point)  # 移除markdown标记
                if len(point) > 10:  # 避免太短的项
                    points.append(point)
                    if len(points) >= 5:  # 最多5个要点
                        break

            # 提取三级标题作为要点
            elif line.startswith('### '):
                point = line.replace('### ', '').strip()
                # 读取下一行作为详细说明
                continue

            # 提取包含数字的句子
            elif re.search(r'\d+', line) and len(line) > 15:
                clean_line = re.sub(r'\*\*|\*|`|^#+\s*', '', line)
                if len(clean_line) > 10 and len(points) < 5:
                    points.append(clean_line)

        # 如果提取的要点不够，使用前几个段落
        if len(points) < 3:
            paragraphs = [p.strip() for p in report.split('\n\n') if p.strip()]
            for para in paragraphs[:5]:
                # 跳过标题段落
                if para.startswith('#'):
                    continue
                clean_para = re.sub(r'\*\*|\*|`|^#+\s*', '', para)
                # 取段落首句
                first_sentence = clean_para.split('.')[0].strip()
                if len(first_sentence) > 10 and len(points) < 5:
                    points.append(first_sentence)

        # 组合要点，限制总长度
        brief_text = ""
        for i, point in enumerate(points[:5], 1):
            bullet_point = f"• {point}\n"
            if len(brief_text) + len(bullet_point) <= 150:
                brief_text += bullet_point
            else:
                break

        # 如果还是太短，返回报告前150字
        if len(brief_text) < 50:
            clean_report = re.sub(r'[#\*`-]', '', report).strip()
            brief_text = clean_report[:150]
            if len(clean_report) > 150:
                brief_text += "..."

        return brief_text.strip()


def test_brief_extractor():
    """测试Brief提取器"""
    sample_report = """
# Weakness Analysis

## 核心发现

发现3个主要改进领域，预计可提升8% Win Rate。

### 1. 补刀效率偏低
- 当前平均6.2 CS/min，低于同段位平均水平12%
- 对线期错过补刀较多，建议加强基础练习
- 建议目标：提升至7.0+ CS/min

### 2. 视野控制不足
- 平均每分钟0.8个视野，建议提升至1.2+
- 河道视野覆盖率仅45%，容易被gank
- 需要养成定期插眼习惯

### 3. 团战站位偏后
- 死亡位置分析显示35%过于激进
- 建议保持更安全的输出距离
- 观察敌方关键技能CD再进场

## 改进建议
...（更多详细内容）
"""

    result = BriefExtractor.extract_three_tier(sample_report, "Weakness Analysis")

    print("=" * 60)
    print("📊 Three-Tier Information Extraction Test")
    print("=" * 60)
    print(f"\n✨ ONE-LINER ({len(result['one_liner'])} chars):")
    print(f"   {result['one_liner']}")
    print(f"\n💡 BRIEF ({len(result['brief'])} chars):")
    print(f"   {result['brief']}")
    print(f"\n📖 DETAILED ({len(result['detailed'])} chars):")
    print(f"   (Full report preserved)")
    print("=" * 60)


if __name__ == "__main__":
    test_brief_extractor()
