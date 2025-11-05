# MetaStrategyAgent 设计文档

## 功能定位

**元策略Agent** - 全局调度中枢和智能编排器

作为整个Agent生态的"大脑"，负责：
1. 解析用户复杂请求
2. 制定最优分析策略
3. 协调多个专项Agent执行
4. 综合多源分析结果
5. 生成统一输出报告

## 核心价值

### 1. 智能决策
- 根据用户需求自动选择最合适的Agent组合
- 避免用户手动调用多个Agent
- 提供一站式分析服务

### 2. 多Agent协同
- 实现Agent间的工作流编排
- 支持串行、并行、条件执行
- 统一管理Agent间的数据流

### 3. 自适应策略
- 根据数据可用性调整分析路径
- 基于中间结果动态优化后续步骤
- 支持策略优先级和降级方案

## 设计架构

### 输入
- `user_request`: 用户自然语言请求
- `player_data_dir`: 玩家数据目录
- `context`: 额外上下文信息（可选）

### 输出
```python
{
    "strategy": {
        "request_type": "comprehensive_analysis",
        "agents_invoked": ["AnnualSummary", "Weakness", "Recommendation"],
        "execution_order": ["sequential", "parallel", ...]
    },
    "results": {
        "annual_summary": {...},
        "weakness_analysis": {...},
        "recommendations": {...}
    },
    "synthesis": "综合报告文本",
    "metadata": {
        "execution_time": 45.2,
        "tokens_used": 12500,
        ...
    }
}
```

## 请求类型识别

### 1. 综合分析 (comprehensive_analysis)
**触发词**: "全面分析"、"整体评估"、"赛季总结"
**调用链**: AnnualSummary → Weakness → Progress → Recommendation

### 2. 快速诊断 (quick_diagnosis)
**触发词**: "问题在哪"、"最近怎么样"、"弱点"
**调用链**: ProgressTracker → WeaknessAnalysis

### 3. 英雄相关 (champion_focus)
**触发词**: "某英雄掌握度"、"英雄池"、"推荐英雄"
**调用链**: ChampionMastery / RoleSpecialization → ChampionRecommendation

### 4. 位置分析 (role_focus)
**触发词**: "中单表现"、"打野水平"
**调用链**: RoleSpecialization → ChampionMastery (该位置核心英雄)

### 5. 赛后复盘 (postgame_review)
**触发词**: "刚才那局"、"复盘"、"上一场"
**调用链**: PostgameReview

### 6. 对比分析 (comparison)
**触发词**: "和xx比"、"同段位对比"
**调用链**: PeerComparison

## 执行策略

### 串行执行 (Sequential)
```
AnnualSummary → (根据结果) → WeaknessAnalysis → (根据弱点) → Recommendation
```

### 并行执行 (Parallel)
```
┌─ ChampionMastery (英雄A) ─┐
├─ ChampionMastery (英雄B) ─┤→ 综合报告
└─ ChampionMastery (英雄C) ─┘
```

### 条件执行 (Conditional)
```
IF (近期胜率 < 45%) THEN
    调用 WeaknessAnalysis
ELSE
    调用 ProgressTracker
```

## 实现要点

### 1. 请求解析
使用LLM理解用户意图：
```python
def parse_request(self, user_request: str) -> Dict:
    prompt = f"分析用户请求并分类：{user_request}"
    result = self.llm.generate_sync(prompt=prompt)
    return {
        "type": "comprehensive_analysis",
        "focus_areas": ["overall", "weakness", "improvement"],
        "priority": "high"
    }
```

### 2. Agent注册表
```python
AGENT_REGISTRY = {
    "annual_summary": AnnualSummaryAgent,
    "weakness": WeaknessAnalysisAgent,
    "recommendation": ChampionRecommendationAgent,
    # ...
}
```

### 3. 工作流编排
```python
def execute_workflow(self, strategy: Dict) -> Dict:
    results = {}
    for step in strategy["steps"]:
        if step["mode"] == "parallel":
            results.update(self._parallel_execute(step["agents"]))
        else:
            results.update(self._sequential_execute(step["agents"]))
    return results
```

### 4. 结果综合
使用LLM整合多个Agent输出：
```python
def synthesize_results(self, results: Dict) -> str:
    prompt = f"综合以下分析结果生成统一报告：\n{results}"
    return self.llm.generate_sync(prompt=prompt)["text"]
```

## 扩展方向

### 短期 (1-2周)
- [x] 基本请求识别和Agent调度
- [ ] 3-5种常见请求类型支持
- [ ] 串行执行模式

### 中期 (1个月)
- [ ] 并行执行优化
- [ ] 条件执行逻辑
- [ ] 策略学习和优化

### 长期 (3个月)
- [ ] 强化学习优化调度策略
- [ ] 用户偏好学习
- [ ] 自适应Prompt生成

## 测试用例

### 用例1: 综合分析
```python
request = "给我一个全面的赛季分析，包括问题和改进建议"
# 预期: AnnualSummary + Weakness + Recommendation
```

### 用例2: 快速诊断
```python
request = "最近10场我的问题在哪？"
# 预期: ProgressTracker + WeaknessAnalysis
```

### 用例3: 英雄推荐
```python
request = "推荐我几个适合我风格的英雄"
# 预期: ChampionRecommendation (基于英雄池分析)
```

## 性能指标

- **请求识别准确率**: > 90%
- **Agent选择合理性**: > 85%
- **综合报告质量**: 用户满意度 > 4/5
- **平均执行时间**: < 60秒（串行）、< 30秒（并行）
