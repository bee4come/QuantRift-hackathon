# 时间范围选择器实现 - 2025-11-06

## 功能概述

为 Annual Summary 和 Progress Tracker 两个 AI 分析 Agent 添加了用户可选的时间范围过滤功能。

## 两个时间范围选项

1. **2024 Full Year** (2024全年)
   - 从 2024-01-01 到今天的所有数据
   - 分析整个2024年度的表现

2. **Past 365 Days** (最近365天)
   - 从今天往前推365天的数据
   - 滚动窗口分析最近一年表现

## 实现细节

### 前端修改 (5个文件)

**1. `/frontend/app/components/AICoachAnalysis.tsx`**
- 添加 `TimeRangeOption` 接口定义
- 扩展 `AgentState` 接口，新增 `timeRangeOptions` 和 `selectedTimeRange` 字段
- 为 `annual-summary` agent 配置时间范围选项
- 为 `performance-insights` agent 配置时间范围选项（内部使用 progress_tracker）
- 添加 `handleTimeRangeChange` 函数处理用户选择
- 修改 `handleGenerate` 函数，在 API 调用中传递 `time_range` 参数

**2. `/frontend/app/components/AgentCard.tsx`**
- 添加 `TimeRangeOption` 接口（与父组件保持一致）
- 扩展 `AgentCardProps`，新增 `timeRangeOptions`, `selectedTimeRange`, `onTimeRangeChange` 属性
- 添加时间范围选择器 UI（下拉框 + 描述文本）
- 选择器样式与整体 UI 风格保持一致（玻璃态效果）

### 后端修改 (3个文件)

**3. `/backend/api/server.py`**
- 在 `AgentRequest` 模型中添加 `time_range: Optional[str]` 字段
- 修改 `/v1/agents/annual-summary` 端点：
  - 从 request 中提取 `time_range` 参数
  - 传递给 `load_all_annual_packs()` 函数
  - 添加日志输出显示加载的 patch 数量
- 修改 `/v1/agents/progress-tracker` 端点：
  - 从 request 中提取 `time_range` 参数
  - 传递给 `load_recent_packs()` 函数
  - 添加日志输出显示加载的 patch 数量

**4. `/backend/src/agents/player_analysis/annual_summary/tools.py`**
- 修改 `load_all_annual_packs()` 函数签名，添加 `time_range: str = None` 参数
- 实现时间过滤逻辑：
  - 解析 `time_range` 值计算 `cutoff_timestamp`
  - 读取每个 pack 文件的 `generation_timestamp` 字段
  - 处理 timestamp 字符串转换（ISO 8601 格式）
  - 过滤掉早于 cutoff 的 pack 文件
- 添加 `from datetime import timedelta` 导入

**5. `/backend/src/agents/player_analysis/progress_tracker/tools.py`**
- 修改 `load_recent_packs()` 函数签名，添加 `time_range: str = None` 参数
- 实现时间过滤逻辑：
  - 解析 `time_range` 值计算 `cutoff_timestamp`
  - 先加载所有 pack 文件
  - 根据 `generation_timestamp` 过滤符合条件的文件
  - 对于没有 timestamp 的文件，默认包含
- 添加 `from datetime import timedelta` 导入

## 数据过滤逻辑

### 时间戳计算

```python
# "2024-01-01" → 2024年1月1日 00:00:00 的 Unix timestamp
cutoff_timestamp = datetime(2024, 1, 1).timestamp()

# "past-365" → (今天 - 365天) 的 Unix timestamp
cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()
```

### Player-Pack 时间戳字段

假设 Player-Pack JSON 文件包含 `generation_timestamp` 字段：
```json
{
  "patch": "15.18",
  "generation_timestamp": "2024-09-15T10:30:00Z",
  "by_cr": [...],
  ...
}
```

### 过滤规则

- 如果 pack 有 `generation_timestamp` 字段 AND `time_range` 参数存在：
  - 比较 pack_timestamp >= cutoff_timestamp
  - 符合条件的 pack 被包含
- 如果 pack 没有 `generation_timestamp` 字段：
  - 默认包含（向后兼容旧数据）

## UI 效果

### Agent Card 新增元素

```
┌─────────────────────────────────────┐
│ 🎯 Annual Summary                  │
│ Year-in-review performance          │
│                                     │
│ Time Range                          │
│ ┌─────────────────────────────────┐ │
│ │ 2024 Full Year            ▼    │ │
│ └─────────────────────────────────┘ │
│ From January 1st, 2024 to today    │
│                                     │
│ [Generate Analysis]                 │
└─────────────────────────────────────┘
```

### 选择器交互

1. 用户点击下拉框
2. 显示两个选项：
   - "2024 Full Year"
   - "Past 365 Days"
3. 选择后，下方显示对应描述文本
4. 点击 "Generate Analysis" 时，将选中的 `time_range` 值传递给后端

## 测试建议

### 前端测试

1. 打开 http://localhost:3000/player/s1ne/na1
2. 等待 Data Status Checker 完成
3. 检查 Annual Summary 和 Performance Insights 两个卡片
4. 验证下拉框显示正确
5. 切换时间范围选项，验证描述文本更新
6. 点击 Generate Analysis，检查 Network 面板中的 POST 请求是否包含 `time_range` 参数

### 后端测试

1. 查看后端日志，确认收到 `time_range` 参数
2. 查看日志输出 "📊 Loaded X patches (time_range: ...)"
3. 验证返回的分析报告数据范围正确

### 数据验证

**场景1: 2024 Full Year**
- 应包含所有 2024-01-01 之后的 patch
- 如果当前是 2025-11-06，应包含约 675 天的数据

**场景2: Past 365 Days**
- 应包含最近 365 天的 patch
- 滚动窗口，随时间推移自动更新

### 边界情况

1. **没有符合条件的数据**
   - 时间范围设置为 2024-01-01，但所有 pack 都是 2023 年的
   - 应返回空字典 `{}`，前端显示适当错误信息

2. **Pack 缺少 timestamp 字段**
   - 旧版本 pack 可能没有 `generation_timestamp`
   - 这些 pack 会被默认包含（向后兼容）

3. **时间戳格式问题**
   - 代码支持 ISO 8601 格式字符串（如 "2024-09-15T10:30:00Z"）
   - 自动去除 'Z' 并转换为 UTC timestamp

## 技术栈

- **前端**: React 19, TypeScript, Next.js 15, Tailwind CSS
- **后端**: Python 3.11, FastAPI, Pydantic
- **数据格式**: JSON (Player-Pack format)
- **时间处理**: Python `datetime` module

## Git Commit

```
feat: Add time range selector for Annual Summary and Progress Tracker agents

Author: bee4come <bee4come@gmail.com>
Commit: 0d8601c
Files changed: 5 (187 insertions, 12 deletions)
```

## 后续改进建议

1. **UI 优化**
   - 添加日期范围的可视化提示（如日历图标）
   - 显示所选时间范围实际包含的比赛数量

2. **更多时间范围选项**
   - "Last 30 Days" (最近30天)
   - "Last 90 Days" (最近90天)
   - "Season 2024" (2024赛季，精确到赛季开始/结束日期)

3. **自定义日期范围**
   - 允许用户输入自定义起止日期
   - 日期选择器组件

4. **性能优化**
   - 对时间过滤后的结果进行缓存
   - 避免重复加载相同时间范围的数据

5. **数据完整性检查**
   - 如果选择的时间范围内数据不足，给出警告
   - 建议用户选择更宽的时间范围
