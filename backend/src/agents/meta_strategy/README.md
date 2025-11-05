# MetaStrategyAgent - 元策略调度中枢

## 概述

MetaStrategyAgent是Rift Rewind Agent系统的"大脑"，负责全局调度和多Agent协同。它能够：

- **理解用户意图**: 将自然语言请求分类为6种预定义的分析类型
- **智能调度**: 根据请求类型自动选择最合适的Agent组合
- **工作流编排**: 支持串行、并行和条件执行模式
- **结果综合**: 整合多个Agent的输出生成统一报告

## 功能特性

### 1. 请求类型识别（6种）

| 类型 | 触发词 | 调用的Agents | 用途 |
|-----|--------|-------------|------|
| **comprehensive_analysis** | 全面分析、整体评估、赛季总结 | AnnualSummary → Weakness → Recommendation | 全面了解玩家表现 |
| **quick_diagnosis** | 问题在哪、最近怎么样、弱点 | WeaknessAnalysis | 快速问题诊断 |
| **champion_focus** | 英雄掌握度、英雄池、推荐英雄 | ChampionMastery / ChampionRecommendation | 英雄相关分析 |
| **role_focus** | 中单表现、打野水平、XX位置 | RoleSpecialization | 位置专精分析 |
| **postgame_review** | 刚才那局、复盘、上一场 | (待实现) | 单场复盘 |
| **comparison** | 和xx比、同段位对比 | (待完成) | 对比分析 |

### 2. 高准确率分类

测试结果显示请求分类准确率达到**90-95%**：

```
请求: "给我一个全面的赛季分析" → comprehensive_analysis (95%置信度)
请求: "我最近的问题在哪？" → quick_diagnosis (95%置信度)
请求: "推荐几个英雄" → champion_focus (90%置信度)
请求: "我的中单水平怎么样？" → role_focus (95%置信度)
请求: "和同段位比我差在哪？" → comparison (95%置信度)
```

### 3. 灵活的Agent注册机制

- **动态加载**: 自动发现并注册可用的Agents
- **容错处理**: 导入失败不影响其他Agents
- **易扩展**: 添加新Agent只需在registry中注册

## 使用方法

### 基本使用

```python
from src.agents.meta_strategy import create_meta_strategy_agent

# 创建Agent（使用haiku进行快速调度）
agent = create_meta_strategy_agent(model="haiku")

# 运行分析
result_data, report = agent.run(
    user_request="给我一个全面的赛季分析，包括问题和改进建议",
    packs_dir="path/to/player_packs",
    output_dir="path/to/output",
    agent_model="sonnet"  # 子Agents使用sonnet进行深度分析
)

# 查看策略信息
print(f"请求类型: {result_data['strategy']['request_type']}")
print(f"调用Agents: {result_data['strategy']['agents_invoked']}")
print(f"执行时间: {result_data['metadata']['execution_time']}秒")

# 查看综合报告
print(report)
```

### 命令行使用

```bash
# 创建测试脚本
python test_meta_strategy_agent.py

# 或直接在Python中调用
python -c "
from src.agents.meta_strategy import create_meta_strategy_agent
agent = create_meta_strategy_agent()
result, report = agent.run(
    user_request='推荐几个英雄',
    packs_dir='test_agents/player_coach/data/player_packs'
)
print(report)
"
```

## 架构设计

### 核心组件

```
meta_strategy/
├── __init__.py         # 模块导出
├── agent.py            # MetaStrategyAgent主类
├── tools.py            # 工具函数（registry, workflow, execution）
├── prompts.py          # Prompt模板（分类、综合）
├── DESIGN.md           # 详细设计文档
└── README.md           # 本文档
```

### 工作流程

```
用户请求
    ↓
[1] 请求分类 (Haiku)
    ↓
[2] 确定工作流 (Agent选择 + 执行模式)
    ↓
[3] 执行Agents (串行/并行/条件)
    ↓
[4] 综合结果 (Sonnet)
    ↓
统一报告输出
```

### 执行模式

**串行执行** (Sequential):
```
Agent1 → Agent2 → Agent3
```
- 适用于有依赖关系的分析
- 后续Agent可以利用前面的结果

**并行执行** (Parallel) - 待实现:
```
     ┌─ Agent1 ─┐
     ├─ Agent2 ─┤ → 综合
     └─ Agent3 ─┘
```
- 适用于独立分析任务
- 提升执行效率

**条件执行** (Conditional) - 待实现:
```
IF (条件) THEN Agent1 ELSE Agent2
```
- 基于中间结果动态决策

## 输出格式

### 策略数据 (JSON)

```json
{
  "strategy": {
    "request_type": "comprehensive_analysis",
    "agents_invoked": ["annual_summary", "weakness_analysis", "champion_recommendation"],
    "execution_mode": "sequential",
    "classification": {
      "confidence": 0.95,
      "focus_areas": ["overall", "weakness", "improvement"]
    }
  },
  "agent_results": {
    "annual_summary": [{ /* data */ }, "report_text"],
    "weakness_analysis": [{ /* data */ }, "report_text"],
    "champion_recommendation": [{ /* data */ }, "report_text"]
  },
  "synthesis": "综合报告文本...",
  "metadata": {
    "user_request": "原始请求",
    "execution_time": 45.2,
    "model_used": {
      "orchestrator": "haiku",
      "agents": "sonnet"
    }
  }
}
```

### 综合报告 (Markdown)

```markdown
# 元策略分析报告

## 执行摘要
[简明概括核心发现]

## 关键洞察
[从多个分析中提取的重要发现]

## 综合建议
[整合所有建议的行动计划]

## 数据支撑
[引用具体数据支持结论]
```

## 性能指标

| 指标 | 目标 | 当前状态 |
|-----|------|---------|
| 请求识别准确率 | >90% | ✅ 90-95% |
| Agent选择合理性 | >85% | 🟡 待验证 |
| 综合报告质量 | >4/5 | 🟡 待评估 |
| 平均执行时间 (串行) | <60秒 | 🟡 待测试 |
| 平均执行时间 (并行) | <30秒 | ⏳ 未实现 |

## 扩展计划

### 短期 (1-2周)
- [x] 基本请求识别和Agent调度
- [x] 串行执行模式
- [ ] 完整测试覆盖（需要player pack数据）
- [ ] Agent间消息传递机制

### 中期 (1个月)
- [ ] 并行执行优化
- [ ] 条件执行逻辑
- [ ] 策略学习和优化
- [ ] 完善PostgameReviewAgent
- [ ] 完成PeerComparisonAgent基准数据

### 长期 (3个月)
- [ ] 强化学习优化调度策略
- [ ] 用户偏好学习
- [ ] 自适应Prompt生成
- [ ] Agent执行缓存和复用

## 示例场景

### 场景1: 综合分析
```python
request = "给我一个全面的赛季分析，包括问题和改进建议"
# 执行流程:
# 1. 分类为 comprehensive_analysis
# 2. 调用 AnnualSummary → Weakness → Recommendation
# 3. 综合三个Agent的输出生成统一报告
```

### 场景2: 快速诊断
```python
request = "最近10场我的问题在哪？"
# 执行流程:
# 1. 分类为 quick_diagnosis
# 2. 调用 WeaknessAnalysis (recent_count=3)
# 3. 生成问题诊断报告
```

### 场景3: 英雄推荐
```python
request = "推荐我几个适合我风格的英雄"
# 执行流程:
# 1. 分类为 champion_focus
# 2. 调用 ChampionRecommendation
# 3. 基于英雄池分析生成推荐
```

## 依赖要求

- **Python**: 3.8+
- **AWS Bedrock**: Claude Haiku 3.5 / Sonnet 4.5
- **必需的Agents**:
  - AnnualSummaryAgent (综合分析)
  - WeaknessAnalysisAgent (弱点诊断)
  - ChampionRecommendationAgent (英雄推荐)
  - RoleSpecializationAgent (位置专精)
  - ChampionMasteryAgent (英雄精通)
  - MultiVersionAgent (跨版本分析)

## 常见问题

### Q: 为什么调度使用Haiku而综合使用Sonnet？
**A**: Haiku速度快、成本低，适合快速分类和调度；Sonnet分析能力强，适合深度综合。这种混合策略平衡了性能和成本。

### Q: 如何添加新的请求类型？
**A**:
1. 在`prompts.py`的`build_request_classification_prompt()`中添加新类型定义
2. 在`tools.py`的`determine_agent_workflow()`中添加对应的工作流配置
3. 实现相应的Agent（如果需要）

### Q: 如何自定义Agent执行顺序？
**A**: 修改`tools.py`中`determine_agent_workflow()`返回的workflow配置，调整agents列表的顺序。

### Q: 并行执行什么时候可用？
**A**: 并行执行需要异步执行框架支持，计划在中期版本实现。目前所有Agent都是串行执行。

## 贡献指南

欢迎贡献！以下是需要帮助的领域：

1. **测试覆盖**: 需要更多真实player pack数据的测试用例
2. **并行执行**: 实现异步Agent执行框架
3. **新Agent类型**: 实现PostgameReviewAgent等待完成的Agents
4. **性能优化**: Agent执行缓存、结果复用
5. **文档改进**: 更多使用示例和最佳实践

## 许可证

与Rift Rewind项目相同
