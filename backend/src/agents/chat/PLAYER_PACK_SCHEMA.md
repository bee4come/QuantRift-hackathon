# Player Pack Data Schema

## Overview
Player Pack 是经过预处理的玩家数据包，按 patch + queue_id 组织，包含该时期内玩家的完整表现数据。

## File Structure

每个玩家有一个目录：`data/player_packs/{puuid}/`

```
player_packs/{puuid}/
├── pack_14.10_420.json    # 14.10 版本排位数据
├── pack_14.11_420.json    # 14.11 版本排位数据
├── matches_data.json      # 原始比赛数据
└── match_ids.json         # 比赛ID列表
```

## Pack File Schema

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `puuid` | string | 玩家唯一ID |
| `patch` | string | 游戏版本 (如 "14.10") |
| `queue_id` | int | 队列类型 (420=排位, 400=匹配) |
| `total_games` | int | 该版本总游戏数 |
| `earliest_match_date` | string | 最早比赛日期 |
| `latest_match_date` | string | 最新比赛日期 |
| `past_season_games` | int | 本赛季总游戏数 |
| `past_365_days_games` | int | 过去一年总游戏数 |
| `generation_timestamp` | string | 数据生成时间 |
| `by_cr` | array | **核心数据**: 按英雄+位置分组的统计 |

### by_cr Array Structure

`by_cr` 是一个数组，每个元素代表一个 **Champion + Role** 组合的完整统计：

```json
{
  "champ_id": 42,           // 英雄ID (42=Corki)
  "role": "BOTTOM",         // 位置 (TOP/JUNGLE/MID/BOTTOM/UTILITY)
  "games": 4,               // 游戏场次
  "wins": 2,                // 胜场
  "losses": 2,              // 负场

  // 胜率相关 (Wilson Confidence Interval)
  "p_hat": 0.5,             // 原始胜率 (wins/games)
  "p_hat_ci": [0.15, 0.85], // 95%置信区间 [下界, 上界]
  "effective_n": 3.2,       // 有效样本量 (考虑数据质量)
  "governance_tag": "CAUTION", // 数据质量标签: CONFIDENT/CAUTION/CONTEXT

  // 核心表现指标
  "kda_adj": 3.1,           // 调整后 KDA [(K+A)/max(D,1)]
  "obj_rate": 0.68,         // 目标控制率 [0-1]
  "cp_25": 285.4,           // 25分钟战斗力 (综合伤害/承伤/经济效率)

  // 出装数据
  "build_core": [3078, 3031, 3087], // 核心装备ID列表
  "avg_time_to_core": 18.5, // 平均成装时间 (分钟)
  "rune_keystone": 8008,    // 主符文ID

  // 详细数据 (部分英雄可能有)
  "avg_damage_dealt": 18500,    // 平均输出伤害
  "avg_damage_taken": 12000,    // 平均承受伤害
  "avg_gold_earned": 11500,     // 平均金币
  "avg_cs": 185,                // 平均补刀
  "avg_vision_score": 28,       // 平均视野分
  "first_blood_rate": 0.25,     // 一血率
  "avg_kill_participation": 0.58 // 平均击杀参与率
}
```

## Key Metrics Explained

### 1. Governance Tags (数据质量)
- **CONFIDENT**: 样本量充足 (≥10场)，数据可信
- **CAUTION**: 样本量一般 (5-9场)，需谨慎解读
- **CONTEXT**: 样本量不足 (<5场)，仅供参考

### 2. Combat Power (cp_25)
综合战斗力评分，基于：
- 输出伤害 / 承受伤害比
- 金币效率 (gold/min)
- 击杀参与率
- 视野控制

计算公式：`cp_25 = (damage_dealt * 0.4 + gold_earned * 0.3 + kp * 0.2 + vision * 0.1) / game_length_25min`

### 3. Objective Rate (obj_rate)
目标控制参与率：
```
obj_rate = (baron_kills + dragon_kills + tower_kills) / total_objectives_in_game
```

### 4. KDA Adjusted (kda_adj)
调整后 KDA，避免除零问题：
```
kda_adj = (kills + assists) / max(deaths, 1)
```

## Data Access Patterns

### Pattern 1: 找到特定英雄+位置的数据
```python
# 找 Corki ADC 的数据
for entry in pack_data['by_cr']:
    if entry['champ_id'] == 42 and entry['role'] == 'BOTTOM':
        print(f"Corki ADC: {entry['games']}场, 胜率{entry['p_hat']:.1%}")
```

### Pattern 2: 跨版本对比
```python
# 对比 14.10 vs 14.11
pack_14_10 = load_pack('pack_14.10_420.json')
pack_14_11 = load_pack('pack_14.11_420.json')

# 找同一英雄在两个版本的数据
for entry_old in pack_14_10['by_cr']:
    for entry_new in pack_14_11['by_cr']:
        if entry_old['champ_id'] == entry_new['champ_id']:
            wr_diff = entry_new['p_hat'] - entry_old['p_hat']
            print(f"胜率变化: {wr_diff:+.1%}")
```

### Pattern 3: 筛选高质量数据
```python
# 只看 CONFIDENT 数据
confident_data = [
    entry for entry in pack_data['by_cr']
    if entry['governance_tag'] == 'CONFIDENT'
]
```

### Pattern 4: 找最强/最弱英雄
```python
# 按胜率排序 (只看样本量≥5的)
sorted_champs = sorted(
    [e for e in pack_data['by_cr'] if e['games'] >= 5],
    key=lambda x: x['p_hat'],
    reverse=True
)
```

## Common Analysis Use Cases

### 1. 时间对比
"对比我最近30天 vs 之前30天"
- 按 `latest_match_date` 筛选 packs
- 聚合两个时间段的 `by_cr` 数据
- 对比胜率、KDA、战斗力变化

### 2. 英雄对比
"我玩坦克 vs 刺客哪个更好"
- 定义英雄分类 (tank: [1,3,78...], assassin: [7,11,55...])
- 筛选对应 `champ_id` 的数据
- 对比平均胜率和表现

### 3. 位置分析
"我 TOP vs ADC 哪个位置强"
- 按 `role` 字段分组
- 聚合每个位置的游戏数、胜率、平均 KDA

### 4. 版本趋势
"我在不同版本的表现趋势"
- 加载所有 pack_*.json
- 按 `patch` 排序
- 绘制胜率/战斗力时间序列

## Data Limitations

1. **样本量不足**: 小于5场的数据标记为 CONTEXT
2. **版本缺失**: 某些版本可能没有数据 (玩家未游玩)
3. **位置混淆**: Riot API 位置识别可能有误
4. **时间范围**: 只包含可用的比赛数据，不保证完整赛季

## Notes for LLM Analysis

当分析用户查询时：
1. **优先使用 CONFIDENT 数据** - 样本量充足
2. **说明数据限制** - 如果样本量不足，明确告知
3. **使用置信区间** - `p_hat_ci` 比 `p_hat` 更可靠
4. **跨版本谨慎** - 版本改动可能影响英雄强度
5. **建议后续分析** - 推荐用户使用专业 agent 深入分析
