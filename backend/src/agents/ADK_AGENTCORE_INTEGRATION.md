# ADK + AgentCore 集成方案 - 生产级 Agent 架构

基于 AWS 官方支持的 Google ADK Python + Bedrock AgentCore 集成模式

## 核心发现

✅ **官方支持确认**：AWS 在 `amazon-bedrock-agentcore-samples/tree/main/03-integrations/agentic-frameworks/adk` 提供完整集成示例

✅ **最佳组合**：
- **Google ADK** = Agent 开发框架（定义逻辑、工具、编排）
- **Bedrock AgentCore** = AWS 托管运行时（部署、扩展、监控）
- **Bedrock Models** = 底层 LLM（Claude Sonnet 4.5, Haiku）

## 集成架构模式

### 官方集成模式
```python
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# 1. ADK Agent 定义（业务逻辑）
root_agent = Agent(
    model="bedrock/anthropic.claude-sonnet-4-5",  # Bedrock 模型
    name="PlayerAnalysisAgent",
    description="Analyzes League of Legends player performance",
    instruction="You analyze player statistics across patches...",
    tools=[build_patch_report, analyze_champions]  # ADK tools
)

# 2. AgentCore 运行时集成（部署层）
app = BedrockAgentCoreApp()

@app.entrypoint
async def agent_invocation(payload, context):
    """AgentCore 入口点 - 连接 ADK agent 和 AWS 运行时"""
    session, runner = await setup_session_and_runner(
        user_id=payload.get("user_id", "default"),
        session_id=context.session_id
    )

    # 调用 ADK agent
    events = runner.run_async(
        user_id=payload.get("user_id"),
        session_id=context.session_id,
        new_message=payload.get("prompt")
    )

    # 返回结果
    async for event in events:
        if event.is_final_response():
            return event.content.parts[0].text

# 3. 启动（本地测试 or 部署到 AWS）
app.run()
```

### 关键组件职责

| 组件 | 职责 | 技术栈 |
|------|-----|--------|
| **ADK Agent** | 业务逻辑、工具定义、prompt 管理 | `google-adk` |
| **AgentCore Runtime** | 会话管理、部署、监控、扩展 | `bedrock-agentcore` |
| **Bedrock Client** | 模型调用（Sonnet 4.5, Haiku） | `boto3` |

## 生产级目录结构

```
src/agents/
├── __init__.py
├── README.md                    # Agent 总览和使用文档
├── requirements.txt             # 依赖管理
│
├── shared/                      # 🔗 共享模块
│   ├── __init__.py
│   ├── bedrock_adapter.py       # Bedrock LLM 适配器（ADK → boto3）
│   ├── config.py                # 环境变量和模型配置
│   ├── prompts.py               # 共享 Prompt 模板
│   └── tools.py                 # 共享 ADK 工具定义
│
└── player_analysis/             # 🎮 玩家分析 Agent 套件
    ├── __init__.py
    │
    ├── multi_version/           # 📊 多版本趋势分析 Agent
    │   ├── __init__.py          # from. import agent
    │   ├── agent.py             # root_agent = Agent(...)
    │   ├── config.py            # Agent 特定配置
    │   ├── tools.py             # ADK tools（数据构建）
    │   └── prompts.py           # Prompt 模板
    │
    ├── detailed_analysis/       # 🔍 详细深度分析 Agent
    │   ├── __init__.py          # from. import agent
    │   ├── agent.py             # root_agent = Agent(model="haiku/sonnet")
    │   ├── config.py            # 模型选择配置
    │   ├── tools.py             # 6 个分析维度工具
    │   └── prompts.py           # 8000-10000 字报告 Prompt
    │
    └── version_comparison/      # ⚔️ 双版本对比 Agent
        ├── __init__.py          # from. import agent
        ├── agent.py             # root_agent = Agent(...)
        ├── config.py            # Agent 配置
        ├── tools.py             # Coach Card 生成工具
        └── prompts.py           # 对比分析 Prompt
```

## Bedrock 模型适配器

ADK 默认优化 Gemini，需要自定义 Bedrock 适配器：

```python
# src/agents/shared/bedrock_adapter.py
import boto3
from botocore.config import Config
from google.adk.llms import BaseLLM  # 假设 ADK 有 LLM 基类

class BedrockLLM(BaseLLM):
    """ADK 兼容的 Bedrock LLM 适配器"""

    def __init__(self, model_id: str, region: str = "us-west-2"):
        config = Config(
            read_timeout=600,
            connect_timeout=60,
            retries={'max_attempts': 3}
        )
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region,
            config=config
        )
        self.model_id = model_id

    async def generate(self, prompt: str, **kwargs) -> str:
        """ADK 调用接口 → Bedrock API"""
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 10000),
                "temperature": kwargs.get("temperature", 0.7)
            })
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']

# 使用示例
bedrock_sonnet = BedrockLLM("us.anthropic.claude-sonnet-4-5-20250929-v1:0")
bedrock_haiku = BedrockLLM("us.anthropic.claude-3-5-haiku-20241022-v1:0")
```

## ADK Agent 实现示例

### 详细分析 Agent（支持 Haiku/Sonnet 双模型）

```python
# src/agents/player_analysis/detailed_analysis/agent.py
from google.adk.agents import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from ..shared.bedrock_adapter import BedrockLLM
from .tools import (
    build_patch_analysis,
    build_champion_deep_dive,
    build_build_evolution,
    build_rune_analysis,
    build_meta_alignment,
    build_playstyle_analysis
)
from .prompts import DETAILED_ANALYSIS_PROMPT

# 模型选择（通过环境变量配置）
import os
model_choice = os.getenv("DETAILED_AGENT_MODEL", "sonnet")
model_id = {
    "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "haiku": "us.anthropic.claude-3-5-haiku-20241022-v1:0"
}[model_choice]

# ADK Agent 定义
root_agent = Agent(
    model=BedrockLLM(model_id),
    name="DetailedAnalysisAgent",
    description="深度分析玩家在多个版本间的表现（6 个分析维度）",
    instruction=DETAILED_ANALYSIS_PROMPT,
    tools=[
        build_patch_analysis,
        build_champion_deep_dive,
        build_build_evolution,
        build_rune_analysis,
        build_meta_alignment,
        build_playstyle_analysis
    ]
)

# AgentCore 集成
app = BedrockAgentCoreApp()

@app.entrypoint
async def agent_invocation(payload, context):
    """处理来自 AgentCore Runtime 的调用"""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    # 设置会话
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="rift-rewind-agents",
        user_id=payload.get("user_id", "default"),
        session_id=context.session_id
    )

    # 创建 runner
    runner = Runner(
        agent=root_agent,
        app_name="rift-rewind-agents",
        session_service=session_service
    )

    # 构建用户消息
    user_prompt = payload.get("prompt", "")
    content = types.Content(
        role='user',
        parts=[types.Part(text=user_prompt)]
    )

    # 运行 agent
    events = runner.run_async(
        user_id=payload.get("user_id", "default"),
        session_id=context.session_id,
        new_message=content
    )

    # 提取最终响应
    final_response = ""
    async for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text

    return {"report": final_response, "model_used": model_choice}

if __name__ == "__main__":
    app.run()
```

### ADK Tools 定义示例

```python
# src/agents/player_analysis/detailed_analysis/tools.py
from google.adk import tool
import json

@tool
def build_patch_analysis(packs_dir: str) -> dict:
    """
    逐版本分析 - 解析 player-pack 构建每个 patch 的统计数据

    Args:
        packs_dir: player-pack 目录路径

    Returns:
        dict: 每个版本的详细统计（胜率、KDA、场均经济等）
    """
    # 实现逻辑（与原 detailed_analyzer.py 中 _build_patch_analysis 一致）
    patches_data = {}

    for pack_file in glob.glob(f"{packs_dir}/*.json"):
        with open(pack_file) as f:
            pack = json.load(f)

        patch = pack['metadata']['patch']
        # ... 计算逻辑
        patches_data[patch] = {
            'games': len(pack['matches']),
            'wins': sum(1 for m in pack['matches'] if m['win']),
            'avg_kda': ...,
            'avg_gold': ...
        }

    return patches_data

@tool
def build_champion_deep_dive(packs_dir: str) -> dict:
    """
    核心英雄深度剖析 - 分析每个英雄在不同版本间的表现

    Returns:
        dict: 英雄跨版本表现数据
    """
    # 实现逻辑...
    pass

# 其他 4 个工具类似定义...
```

## 部署工作流

### 本地开发和测试
```bash
# 1. 安装依赖
pip install google-adk bedrock-agentcore boto3

# 2. 配置环境变量
export AWS_REGION=us-west-2
export DETAILED_AGENT_MODEL=sonnet  # or haiku

# 3. 本地测试
agentcore launch -l --env AWS_REGION=us-west-2

# 4. 调用测试
agentcore invoke -l '{
    "prompt": "分析玩家在 15.12-15.20 的表现",
    "user_id": "player123",
    "packs_dir": "data/packs/"
}'
```

### 部署到 AWS AgentCore Runtime
```bash
# 1. 配置 agent
cd src/agents/player_analysis/detailed_analysis
agentcore configure -e agent.py

# 2. 部署到 AWS
agentcore launch --env AWS_REGION=us-west-2 --env DETAILED_AGENT_MODEL=sonnet

# 3. 获取 Agent 端点
# AgentCore 返回 HTTP 端点 URL
```

### 在 Python 代码中调用（已部署的 Agent）
```python
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime')

response = bedrock_agent.invoke_agent(
    agentId='your-agent-id',
    agentAliasId='your-alias-id',
    sessionId='session-123',
    inputText='分析玩家在 15.12-15.20 的表现'
)

# 处理流式响应
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode())
```

## 迁移路线图

### 阶段 1: 共享基础设施（Week 1）
- [ ] 创建 `src/agents/shared/` 模块
- [ ] 实现 `bedrock_adapter.py`（ADK → Bedrock LLM 适配器）
- [ ] 迁移 `config.py` 和 `prompts.py`
- [ ] 编写单元测试

### 阶段 2: 迁移第一个 Agent（Week 2）
- [ ] 迁移 `multi_version_analyzer.py` → ADK agent
- [ ] 转换数据构建逻辑为 ADK tools
- [ ] 集成 AgentCore runtime
- [ ] 本地测试 + 部署测试

### 阶段 3: 迁移剩余 Agents（Week 3-4）
- [ ] 迁移 `detailed_analyzer.py`（双模型支持）
- [ ] 迁移 `coach_card_generator.py`
- [ ] 端到端测试（3 个 agents）
- [ ] 性能优化

### 阶段 4: 生产准备（Week 5）
- [ ] 编写完整文档（README, API 文档）
- [ ] CI/CD 集成（GitHub Actions + AgentCore）
- [ ] 监控和日志配置
- [ ] 安全审查（IAM roles, VPC 配置）

## 优势总结

### 对比纯 Bedrock boto3（当前方案）
✅ **标准化框架**：ADK 提供 agent、tools、sessions 标准抽象
✅ **可扩展性**：轻松添加新 tools，多 agent 编排
✅ **状态管理**：ADK 内置 session 管理（vs 手动管理）
✅ **工具生态**：可集成 ADK 预构建工具（搜索、数据库等）

### 对比纯 ADK（无 AgentCore）
✅ **AWS 托管**：AgentCore 自动处理扩展、监控、日志
✅ **一键部署**：`agentcore launch` vs 自建 FastAPI + Lambda
✅ **Bedrock 集成**：原生 IAM、VPC、KMS 集成
✅ **企业级特性**：Multi-region、高可用、灾备

### 对比简单模块化
✅ **未来扩展**：当需要交互式 agent 时，架构已就绪
✅ **标准化**：遵循行业标准 agent 框架
⚠️ **学习曲线**：需要学习 ADK 和 AgentCore（但有官方文档）
⚠️ **依赖增加**：`google-adk` + `bedrock-agentcore`（但换来标准化）

## 依赖清单

```txt
# requirements.txt
boto3>=1.39.15
google-adk>=0.1.0
bedrock-agentcore>=1.0.0
python-dotenv>=1.0.0
```

## 下一步行动

1. **创建共享模块**：`src/agents/shared/bedrock_adapter.py`
2. **迁移第一个 agent**：`multi_version_analyzer.py` → ADK agent
3. **本地测试**：使用 `agentcore launch -l` 验证
4. **部署测试**：部署到 AWS AgentCore Runtime
5. **文档编写**：README + API 文档

---

**参考资源**：
- AWS AgentCore 官方文档: https://docs.aws.amazon.com/bedrock-agentcore/
- ADK 集成示例: https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/03-integrations/agentic-frameworks/adk
- Google ADK Python: https://github.com/google/adk-python
