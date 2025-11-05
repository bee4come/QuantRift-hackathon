# RiskForecasterAgent Design

## Overview
对局风险预警Agent - 基于双方阵容预测游戏不同阶段的战力对比和关键时间节点

## Input
```json
{
  "our_composition": [
    {"champion_id": 92, "role": "TOP"},
    {"champion_id": 64, "role": "JUNGLE"},
    ...
  ],
  "enemy_composition": [
    {"champion_id": 122, "role": "TOP"},
    ...
  ]
}
```

## Output
```json
{
  "power_curves": {
    "our_team": {0: 45, 5: 48, 10: 55, ...},
    "enemy_team": {0: 52, 5: 54, 10: 51, ...}
  },
  "key_moments": [
    {
      "time": 12,
      "type": "power_spike",
      "message": "12分钟我方迎来战力高峰"
    }
  ],
  "recommendations": {
    "early_game": "前7分钟避免激进...",
    "mid_game": "15-22分钟主动找团...",
    "late_game": "25分钟后时间对敌方有利..."
  }
}
```

## Data Sources
- power_curves.json (from PowerCurveGenerator)
- Gold layer for validation

## Key Functions
1. `calculate_team_power_curve()` - 计算团队战力曲线
2. `identify_key_moments()` - 识别关键时间点
3. `generate_tactical_recommendations()` - 生成战术建议
