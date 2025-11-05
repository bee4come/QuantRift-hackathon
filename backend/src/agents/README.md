# Rift Rewind Agents

基于 **Google ADK** + **AWS Bedrock AgentCore** 的生产级玩家分析 Agent 系统。

## 架构概述

```
src/agents/
├── shared/                    # 共享模块
│   ├── bedrock_adapter.py      # ADK → Bedrock LLM 适配器
│   ├── config.py               # 环境变量和配置管理
│   └── prompts.py              # Prompt 模板基类
│
└── player_analysis/           # 玩家分析 Agent 套件
    ├── multi_version/          # 多版本趋势分析 Agent
    ├── detailed_analysis/      # 详细深度分析 Agent
    └── version_comparison/     # 双版本对比 Agent
```

## 核心技术栈

- **Google ADK**: Agent 开发框架（定义逻辑、工具、编排）
- **AWS Bedrock AgentCore**: 托管运行时（部署、扩展、监控）
- **Bedrock Models**: Claude Sonnet 4.5, Claude 3.5 Haiku

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 编辑 /home/zty/rift_rewind/.env
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Agent 配置（可选）
AGENT_DEFAULT_MODEL=sonnet  # or haiku
AGENT_MAX_TOKENS=16000
AGENT_TEMPERATURE=0.7
```

### 3. 使用共享模块

```python
from src.agents.shared import BedrockLLM, get_config

# 获取配置
config = get_config()
print(f"AWS Region: {config.aws_region}")

# 创建 Bedrock LLM
llm = BedrockLLM(model="sonnet")

# 同步调用
result = llm.generate_sync(
    prompt="分析玩家在 15.12-15.20 的表现",
    max_tokens=16000
)
print(result["text"])
print(f"Token usage: {result['usage']}")
```

## 开发指南

### Bedrock 适配器

`bedrock_adapter.py` 提供了 ADK 兼容的 Bedrock LLM 接口：

```python
from src.agents.shared import BedrockLLM

# 创建 Sonnet 4.5 LLM
llm = BedrockLLM(model="sonnet")

# 创建 Haiku 3.5 LLM
llm = BedrockLLM(model="haiku")

# 使用完整模型 ID
llm = BedrockLLM(model="us.anthropic.claude-sonnet-4-5-20250929-v1:0")

# 异步调用（用于 ADK Agent）
response = await llm.generate(prompt="...", max_tokens=10000)

# 同步调用（用于非 async 场景）
result = llm.generate_sync(prompt="...", temperature=0.8)
```

### 配置管理

`config.py` 提供全局配置管理：

```python
from src.agents.shared import AgentConfig, get_config

# 获取单例配置
config = get_config()

# 访问配置
print(config.aws_region)          # us-west-2
print(config.default_model)       # sonnet
print(config.max_tokens)          # 16000

# 重新加载配置
from src.agents.shared.config import reload_config
config = reload_config()
```

### Prompt 模板

`prompts.py` 提供可重用的 Prompt 模板：

```python
from src.agents.shared import PromptTemplate
from src.agents.shared.prompts import PlayerAnalysisPromptTemplate

# 创建玩家分析 Prompt
template = PlayerAnalysisPromptTemplate()
prompt = template.build(
    data_package=data,
    word_count="10000字"
)
```

## 迁移计划

### ✅ Week 1: 共享基础设施（已完成）

- [x] 创建 `src/agents/shared/` 模块
- [x] 实现 `bedrock_adapter.py`（ADK → Bedrock 适配器）
- [x] 实现 `config.py`（环境变量管理）
- [x] 实现 `prompts.py`（Prompt 模板）
- [x] 创建 `requirements.txt`

### ⏳ Week 2: 迁移第一个 Agent

- [ ] 迁移 `multi_version_analyzer.py` → ADK agent
- [ ] 转换数据构建逻辑为 ADK tools
- [ ] 集成 AgentCore runtime
- [ ] 本地测试 + 部署测试

### ⏳ Week 3-4: 迁移剩余 Agents

- [ ] 迁移 `detailed_analyzer.py`（双模型支持）
- [ ] 迁移 `coach_card_generator.py`
- [ ] 端到端测试
- [ ] 性能优化

### ⏳ Week 5: 生产准备

- [ ] 编写完整文档
- [ ] CI/CD 集成
- [ ] 监控和日志配置
- [ ] 安全审查

## 参考文档

- [ADK + AgentCore 集成方案](./ADK_AGENTCORE_INTEGRATION.md)
- [方案对比分析](./SOLUTION_COMPARISON.md)
- [AWS AgentCore 官方文档](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Google ADK Python](https://github.com/google/adk-python)
- [AWS AgentCore 集成示例](https://github.com/awslabs/amazon-bedrock-agentcore-samples)

## 许可证

与 Rift Rewind 主项目一致
