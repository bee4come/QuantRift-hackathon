# AnnualSummaryAgent 设计文档

## 📋 概述

**目的**: 生成整个赛季（40-50个版本）的年度总结报告

**输入**: 整个赛季的Player-Pack JSON文件
**输出**: 3000-5000字年度总结报告 + JSON数据包

**模型**: Claude Sonnet 4.5 (16000 tokens)

---

## 🎯 核心功能

### 1. 时间分段分析

**月度分析**:
- 按月聚合统计数据
- 每月游戏量、胜率、核心英雄
- 月度表现趋势

**季度分析**:
- Q1/Q2/Q3/Q4 四季度对比
- 季度性能变化
- 季节性模式识别

**三期分析**:
- 早期（赛季前1/3）
- 中期（赛季中1/3）
- 晚期（赛季后1/3）
- 成长轨迹分析

### 2. 年度亮点提取

**统计亮点**:
- 最高胜率英雄-角色组合
- 最多游戏英雄
- 总游戏数、总胜场
- 覆盖的版本数、英雄数

**里程碑**:
- 首次达到某个成就
- 突破性表现（如单版本胜率突破70%）
- 特殊事件（如连胜记录、新英雄掌握）

**年度最佳**:
- 最佳时期（哪个月/季度表现最好）
- 最佳英雄（综合考虑胜率和场次）
- 最佳版本（单版本最高表现）

### 3. 版本适应趋势

**复用MultiVersionAgent逻辑**:
- 使用 `analyze_trends()` 分析整个赛季趋势
- 使用 `identify_key_transitions()` 识别关键转折点

**新增年度特色**:
- 适应速度分析（新版本后多久达到稳定胜率）
- 版本敏感度（大版本vs小版本的影响）
- 长期学习曲线

### 4. 英雄池演进

**广度分析**:
- 每月/季度使用的unique champions数量
- 英雄池扩张 vs 收缩趋势
- 专精 vs 泛用策略

**深度分析**:
- 核心英雄稳定性（长期使用的英雄）
- 实验性英雄（短期尝试后放弃）
- 新英雄学习曲线（首次使用到掌握的过程）

**角色偏好**:
- 主要位置选择变化
- 多位置适应能力
- 位置专精度

---

## 📊 数据处理流程

### Step 1: 加载所有Player-Pack

```python
def load_all_annual_packs(packs_dir: str) -> Dict[str, Any]:
    """
    加载整个赛季的Player-Pack数据

    Returns:
        {
            "15.1": {...},
            "15.2": {...},
            ...
            "15.50": {...}
        }
    """
```

### Step 2: 时间分段聚合

```python
def segment_by_time(all_packs: Dict, segment_type: str) -> Dict:
    """
    按时间分段聚合数据

    Args:
        segment_type: "monthly", "quarterly", "tri-period"

    Returns:
        {
            "2024-01": {...},  # 月度
            "Q1": {...},       # 季度
            "early": {...}     # 三期
        }
    """
```

### Step 3: 提取年度亮点

```python
def extract_annual_highlights(all_packs: Dict) -> Dict:
    """
    提取年度统计亮点

    Returns:
        {
            "total_games": 500,
            "total_wins": 275,
            "overall_winrate": 0.55,
            "unique_champions": 35,
            "unique_roles": 5,
            "patches_covered": 48,
            "best_champion_role": {...},
            "most_played_champion": {...},
            "best_month": {...},
            "best_quarter": {...}
        }
    """
```

### Step 4: 英雄池演进分析

```python
def analyze_champion_pool_evolution(all_packs: Dict) -> Dict:
    """
    分析英雄池演进

    Returns:
        {
            "monthly_breadth": [...],  # 每月unique champions
            "core_champions": [...],   # 长期核心英雄
            "experimental_champions": [...],  # 短期尝试
            "learning_curves": {...},  # 新英雄学习曲线
            "role_preferences": {...}  # 位置偏好变化
        }
    """
```

### Step 5: 生成综合分析数据

```python
def generate_comprehensive_annual_analysis(all_packs: Dict) -> Dict:
    """
    生成完整年度分析数据包

    Returns:
        {
            "time_segments": {...},
            "annual_highlights": {...},
            "version_adaptation": {...},  # 复用MultiVersionAgent
            "champion_pool_evolution": {...},
            "metadata": {...}
        }
    """
```

### Step 6: 趣味化功能（社交分享）✨ 新增

```python
def generate_fun_tags(analysis: Dict) -> List[str]:
    """
    生成趣味化标签

    返回标签示例:
    - "🎮 峡谷劳模" (>500场)
    - "👑 大神玩家" (胜率>60%)
    - "❤️ 亚索专精" (某英雄>50场)
    - "📈 进步之星" (胜率提升>5%)
    - "🎯 全能型选手" (>20个英雄)
    """

def generate_share_text(analysis: Dict, style: str) -> str:
    """
    生成社交分享文案

    支持风格:
    - "twitter": 简短、有趣、带emoji和hashtag (#RiftRewind)
    - "casual": 轻松朋友间分享
    - "formal": 详细数据报告
    """

def format_annual_card_data(analysis: Dict) -> Dict:
    """
    格式化年度卡片数据，供前端生成分享图片

    返回数据包括:
    - fun_tags: 趣味标签列表
    - stats: 核心统计数据
    - most_played: 最常玩英雄
    - best_performance: 最佳表现
    - core_champions: 核心英雄池
    - progress: 进步情况（早期→晚期）
    - share_texts: 三种风格的分享文案
    """
```

---

## 🤖 LLM Prompt 设计

### Prompt 结构

**System Prompt**:
```
你是一位资深的英雄联盟数据分析师，专门负责生成年度赛季总结报告。
你需要基于整个赛季的数据，生成一份3000-5000字的综合分析报告。

报告应包括：
1. 赛季总览（统计摘要）
2. 时间演进分析（月度/季度/三期）
3. 版本适应表现（关键转折点、适应模式）
4. 英雄池演进（核心英雄、新英雄学习）
5. 年度亮点与成就
6. 未来展望与建议

要求：
- 数据驱动，引用具体数字
- 叙述流畅，有故事性
- 突出成长轨迹和进步
- 客观评价优势与不足
```

**User Prompt Template**:
```
基于以下赛季数据，生成年度总结报告：

## 赛季统计摘要
- 总游戏数: {total_games}
- 总胜场: {total_wins}
- 整体胜率: {overall_winrate:.1%}
- 覆盖版本: {patches_covered}个版本
- 使用英雄: {unique_champions}个英雄
- 涉及位置: {unique_roles}个位置

## 时间分段数据
{time_segments_summary}

## 版本适应趋势
{version_adaptation_summary}

## 英雄池演进
{champion_pool_evolution_summary}

## 年度亮点
{annual_highlights_summary}

请生成完整的年度总结报告。
```

---

## 📁 文件结构

```
src/agents/player_analysis/annual_summary/
├── __init__.py           # 导出AnnualSummaryAgent
├── DESIGN.md             # 本设计文档
├── tools.py              # 数据处理工具函数
├── prompts.py            # Prompt模板
└── agent.py              # AnnualSummaryAgent主类
```

---

## 🔄 复用策略

### 从MultiVersionAgent复用

**直接复用**:
- `analyze_trends()` - 跨版本趋势分析
- `identify_key_transitions()` - 关键转折点识别
- `load_all_packs()` - Player-Pack加载逻辑

**修改复用**:
- 扩展时间跨度处理（9个版本 → 40-50个版本）
- 增加时间分段维度

### 从DetailedAnalysisAgent借鉴

**借鉴思路**:
- 详细的英雄剖析方法
- 数据驱动的叙述风格

**不直接复用**:
- DetailedAnalysisAgent关注单个版本深度
- AnnualSummaryAgent关注整个赛季广度

---

## 🎨 输出示例

### JSON数据包

```json
{
  "metadata": {
    "analysis_type": "annual_summary",
    "season": "2024",
    "generated_at": "2025-10-10T12:00:00Z",
    "total_patches": 48,
    "date_range": ["2024-01-01", "2024-12-31"]
  },
  "summary": {
    "total_games": 520,
    "total_wins": 286,
    "overall_winrate": 0.55,
    "unique_champions": 38,
    "unique_roles": 5,
    "patches_covered": 48
  },
  "time_segments": {
    "monthly": [...],
    "quarterly": [...],
    "tri_period": [...]
  },
  "annual_highlights": {
    "best_champion_role": {
      "champion_id": 157,
      "role": "MIDDLE",
      "games": 85,
      "winrate": 0.68
    },
    "most_played": {...},
    "best_month": {...},
    "best_quarter": {...}
  },
  "version_adaptation": {
    "trends": {...},
    "key_transitions": [...]
  },
  "champion_pool_evolution": {
    "monthly_breadth": [12, 15, 18, ...],
    "core_champions": [...],
    "experimental_champions": [...]
  }
}
```

### 报告示例

```markdown
# 2024赛季年度总结报告

## 一、赛季总览

在2024赛季中，你共进行了520场排位赛，取得了286场胜利，
整体胜率达到55%。横跨48个版本，使用了38个不同英雄，
涉及全部5个位置，展现了出色的英雄池广度和位置灵活性。

## 二、时间演进分析

### 月度表现
- 1月：起步阶段，胜率48%...
- 2月：稳步提升，胜率52%...
...

### 季度对比
- Q1：赛季初期适应，平均胜率50%
- Q2：技术提升，平均胜率54%
- Q3：高峰期，平均胜率58%
- Q4：稳定维持，平均胜率56%

## 三、版本适应表现

你展现了出色的版本适应能力...
关键转折点：
1. 15.15 → 15.16: 游戏量激增，标志着掌握亚索...
...

## 四、英雄池演进

### 核心英雄池
- 亚索 (MIDDLE): 全赛季最稳定carry点...
- 剑姬 (TOP): 第二核心...

### 新英雄学习
- 刀妹: 从40%胜率进步到60%，展现快速学习能力...

## 五、年度亮点与成就

🏆 最佳表现：Q3季度，胜率58%
🎮 最多场次：亚索，85场
⭐ 最高胜率：亚索 MIDDLE，68%（85场）
...

## 六、未来展望与建议

基于本赛季表现，建议2025赛季...
```

---

## 🧪 测试计划

### 测试数据

使用模拟数据：
- 40个版本的Player-Pack文件
- 每个版本包含3-5个champion-role组合
- 总游戏量500场左右

### 测试场景

1. **完整赛季分析**: 40个版本 → 生成报告
2. **短赛季分析**: 20个版本 → 验证适应性
3. **数据质量处理**: 部分版本缺失 → 健壮性测试

### 成功标准

- ✅ 报告长度 3000-5000字
- ✅ 包含所有必需章节
- ✅ 数据引用准确
- ✅ JSON数据包完整
- ✅ 运行时间 < 2分钟

---

## 📝 实现优先级

### P0 (必须实现) ✅ 已完成
- [x] 设计架构
- [x] tools.py: 基础数据加载和处理
  - [x] load_all_annual_packs()
  - [x] segment_by_time() (monthly/quarterly/tri-period)
  - [x] extract_annual_highlights()
  - [x] analyze_champion_pool_evolution()
  - [x] generate_comprehensive_annual_analysis()
  - [x] format_analysis_for_prompt()
- [x] prompts.py: Prompt模板
  - [x] SYSTEM_PROMPT (3000-5000字要求)
  - [x] USER_PROMPT_TEMPLATE
  - [x] build_narrative_prompt()
- [x] agent.py: Agent主类
  - [x] AnnualSummaryAgent 类
  - [x] run() 方法完整实现
  - [x] DataAutoFetcher 集成
  - [x] API endpoint: /v1/agents/annual-summary
- [ ] 基本测试

### P1 (应该实现) ✅ 已完成
- [x] 时间分段分析（月度/季度/三期）
- [x] 年度亮点提取
- [x] 英雄池演进分析
- [ ] 完整测试

### P2 (可选实现) ✅ 部分完成
- [x] 高级可视化数据准备
  - [x] format_annual_card_data() - 卡片数据格式化
- [ ] 多赛季对比功能
- [ ] 自定义时间段分析

### 🎉 P3 (社交分享功能) ✅ 新增完成 (2025-10-30)
- [x] 趣味化标签生成
  - [x] generate_fun_tags() - 根据数据生成个性化标签
  - 支持标签：峡谷劳模、大神玩家、英雄专精、进步之星、全能型选手等
- [x] 社交分享文案生成
  - [x] generate_share_text() - 三种风格文案
  - Twitter风格：简短、有趣、带emoji和#RiftRewind
  - Casual风格：朋友间轻松分享
  - Formal风格：详细数据报告
- [x] 年度卡片数据格式化
  - [x] format_annual_card_data() - 供前端生成分享图片
  - 包含：fun_tags, stats, most_played, best_performance, core_champions, progress, share_texts

---

**设计完成时间**: 2025-10-10
**实际完成时间**: 2025-10-30
**复杂度**: 中等
**状态**: ✅ Backend 100% 完成，待前端集成

### 🚀 下一步工作

**Backend** ✅ 完成:
- Annual Summary Agent 功能完整
- 趣味标签和分享文案已集成到 tools.py

**Frontend** ⏳ 待实现:
1. Annual Summary 前端 API route
2. Annual Summary Card 组件（展示趣味标签和年度数据）
3. 社交分享按钮（下载图片/复制文案/Twitter分享）
4. 集成到 PlayerProfileClient
