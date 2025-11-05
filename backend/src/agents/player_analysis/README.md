## Player Analysis Agent Suite

三个玩家分析 Agents：

### 1. MultiVersionAgent - 多版本趋势分析
- 模型: Haiku (快速)
- 用途: 跨版本适应能力评估
- 命令: `python -m src.agents.player_analysis.multi_version.agent --packs-dir ... --output-dir ...`

### 2. DetailedAnalysisAgent - 详细深度分析
- 模型: Haiku/Sonnet (可选)
- 用途: 超详细逐版本、逐英雄分析
- 命令: `python -m src.agents.player_analysis.detailed_analysis.agent --model sonnet --packs-dir ... --meta-dir ... --output-dir ...`

### 3. VersionComparisonAgent - 双版本对比
- 模型: Sonnet 4.5
- 用途: Coach Card 生成
- 命令: `python -m src.agents.player_analysis.version_comparison.agent --packs-dir ... --meta-dir ... --output-dir ...`
