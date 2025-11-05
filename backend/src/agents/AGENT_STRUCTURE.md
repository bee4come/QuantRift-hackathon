# Rift Rewind Agents - Production Structure

基于AWS Bedrock AgentCore最佳实践的生产级Agent组织方案

## 目录结构

```
src/agents/
├── __init__.py
├── README.md                  # Agent总览文档
├── requirements.txt           # Agent依赖
│
├── shared/                    # 🔗 共享模块
│   ├── __init__.py
│   ├── bedrock_client.py      # 统一Bedrock客户端管理
│   ├── config.py              # 全局配置（从.env加载）
│   ├── prompts.py             # 共享Prompt模板
│   └── utils.py               # 工具函数
│
└── player_analysis/           # 🎮 玩家分析Agent套件
    ├── __init__.py
    ├── README.md              # 套件文档
    │
    ├── multi_version/         # 📊 多版本趋势分析Agent
    │   ├── __init__.py
    │   ├── agent.py           # MultiVersionAnalysisAgent类
    │   ├── config.py          # Agent配置
    │   ├── data_builder.py    # 数据包构建逻辑
    │   └── prompts.py         # Prompt模板
    │
    ├── detailed_analysis/     # 🔍 详细深度分析Agent
    │   ├── __init__.py
    │   ├── agent.py           # DetailedAnalysisAgent类
    │   ├── config.py          # Agent配置（支持Haiku/Sonnet选择）
    │   ├── data_builder.py    # 6个分析维度构建
    │   └── prompts.py         # 8000-10000字报告Prompt
    │
    └── version_comparison/    # ⚔️ 双版本对比Agent
        ├── __init__.py
        ├── agent.py           # VersionComparisonAgent类
        ├── config.py          # Agent配置
        ├── coach_card.py      # Coach Card生成逻辑
        └── prompts.py         # 对比分析Prompt
```

## 设计原则

### 1. Bedrock AgentCore模式
- **Agent类封装**: 每个Agent都是独立的类，继承共享基类
- **配置分离**: 配置文件独立于业务逻辑
- **Prompt模块化**: Prompt单独文件，便于调优
- **服务分层**: 数据构建(data_builder) + Agent核心(agent) + 工具(utils)

### 2. 生产级特性
- **统一Bedrock客户端**: 共享boto3配置，超时设置，重试逻辑
- **环境变量管理**: 从/home/zty/rift_rewind/.env统一加载AWS凭证
- **错误处理**: 完善的异常处理和日志记录
- **类型注解**: 完整的类型提示，便于IDE支持

### 3. 可扩展性
- **新Agent添加**: 在player_analysis/下新建目录即可
- **共享逻辑复用**: shared/模块被所有Agent使用
- **版本控制**: 每个Agent独立版本，互不影响

## Agent命名规范

| 原文件名 | 新Agent名称 | 位置 |
|---------|-----------|------|
| multi_version_analyzer.py | MultiVersionAnalysisAgent | player_analysis/multi_version/ |
| detailed_analyzer.py | DetailedAnalysisAgent | player_analysis/detailed_analysis/ |
| coach_card_generator.py | VersionComparisonAgent | player_analysis/version_comparison/ |

## 使用示例

```python
from src.agents.player_analysis.detailed_analysis import DetailedAnalysisAgent

# 初始化Agent（自动加载配置）
agent = DetailedAnalysisAgent(model_name="sonnet")  # 或 "haiku"

# 运行分析
data_package, report = agent.run(
    packs_dir="/path/to/packs",
    meta_dir="/path/to/meta",
    output_dir="/path/to/output"
)

# 结果
# - report: 16000 token详细报告
# - data_package: 140KB JSON分析数据
# - 文件: output_dir/detailed_report_sonnet.md
```

## 迁移计划

1. ✅ 分析Bedrock AgentCore最佳实践
2. ⏳ 创建目录结构和共享模块
3. ⏳ 迁移multi_version_analyzer → MultiVersionAnalysisAgent
4. ⏳ 迁移detailed_analyzer → DetailedAnalysisAgent
5. ⏳ 迁移coach_card_generator → VersionComparisonAgent
6. ⏳ 编写README和使用文档
7. ⏳ 添加单元测试

## 与现有系统集成

这些Agent可以被以下模块调用：
- `src/battle_manual/` - 战役手册处理器
- `src/export/` - 导出系统
- 用户自定义脚本

不影响现有的：
- `src/core/` - 核心数据聚合
- `src/metrics/` - 指标计算
- `src/transforms/` - 数据转换
