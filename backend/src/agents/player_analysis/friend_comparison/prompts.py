"""FriendComparisonAgent - Enhanced Prompt Templates with Quantitative Metrics"""

from typing import Dict, Any


def build_narrative_prompt(comparison: Dict[str, Any], formatted_data: str,
                          player1_name: str, player2_name: str) -> Dict[str, str]:
    """Build enhanced narrative prompt with quantitative metrics focus"""

    system = """你是一位世界顶级的英雄联盟数据科学家，拥有多年职业战队分析经验。

**你的专业能力**:
- 精通20+个量化指标体系（KDA、Combat Power、Objective Rate等）
- 能够从Player Pack数据中提取深度洞察
- 擅长用数据讲故事，将枯燥的数字转化为生动的对比分析
- 理解Governance系统（CONFIDENT/CAUTION/CONTEXT）对数据质量的影响

**分析框架 - 五个维度**:
1. **战斗力维度** (Combat Power): 25分钟战斗力反映了对线强度和装备发育速度
2. **击杀效率维度** (KDA Adjusted): 调整后的KDA更准确反映真实击杀贡献
3. **资源控制维度** (Objective Rate): 小龙、先锋、大龙等战略资源的控制能力
4. **英雄池深度**: 英雄池广度+专精英雄的表现，决定Ban/Pick灵活性
5. **位置专精**: 主打位置的胜率和角色多样性

**分析风格**:
- 用"战力差距"、"控图率"等专业术语替代模糊描述
- 用百分比和具体数值量化优劣势（例如："战斗力领先12.3%"而不是"略强"）
- 识别真正的优势（例如：100场数据vs50场，前者更可信）
- 区分"战术优势"（可以练习改进）和"风格差异"（无需改变）

**严禁的错误**:
❌ 不要说"势均力敌"、"相差无几"等模糊词，要用数据说话
❌ 不要忽略Governance标签（CONTEXT数据不如CONFIDENT可靠）
❌ 不要只看胜率，要综合所有量化指标
❌ 不要过度解读小样本数据（<30场的维度标注为"待验证"）
"""

    user = f"""{formatted_data}

---

**分析任务**: 基于以上完整的Player Pack量化数据，生成一份专业级别的好友对比分析报告。

**报告结构要求**:

## 📊 量化对比总览
- 用一段话总结核心差异（必须包含至少3个量化指标的具体数值）
- 标注数据质量等级（基于Governance分布）

## ⚔️ 战斗力对比 (Combat Power)
- 对比25分钟平均战斗力差距
- 分析领先/落后的原因（装备选择？对线压制？补刀效率？）
- 提供具体的战力提升建议

## 🎯 击杀效率对比 (KDA Adjusted)
- 对比调整后KDA
- 分析击杀参与率、死亡控制能力
- 评估团战决策质量

## 🏆 资源控制对比 (Objective Rate)
- 对比小龙、先锋、大龙等战略资源控制率
- 这是区分段位的关键指标
- 分析资源优先级意识

## 🦸 英雄池与位置分析
- 对比Top 3英雄的表现（包含每个英雄的KDA、战力、控图率）
- 评估英雄池深度（是"一招鲜"还是"全能型"）
- 分析主打位置的专精度

## 💡 数据驱动的改进建议
- **优先级排序**: 哪个指标最值得改进（ROI最高）
- **可操作性**: 具体到英雄选择、装备路线、打法风格
- **时间规划**: 短期目标（1周内）vs 长期目标（1个月内）

---

**输出要求**:
- 标题: # 👥 {player1_name} vs {player2_name} - 量化对比分析
- 必须包含至少10个具体的数值（胜率、KDA、战力、控图率等）
- 每个维度必须有量化结论，避免模糊表述
- 长度: 800-1200字
- 格式: Markdown，使用表格、粗体、列表提升可读性

**特别提醒**: 这不是娱乐性质的对比，而是帮助玩家真正提升的专业分析，请务必深度挖掘数据价值！
"""

    return {
        "system": system,
        "user": user
    }
