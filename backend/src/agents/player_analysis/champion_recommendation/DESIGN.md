# ChampionRecommendationAgent Design Document

## Overview
Recommends new champions based on player style, existing champion pool, and current meta.

## Key Features
- **Style identification**: 玩家擅长的英雄类型（刺客/坦克/法师等）
- **Playstyle pattern**: 激进型/稳健型/支援型
- **Meta gap analysis**: 当前meta强势但未掌握的英雄
- **Style matching**: 推荐与已掌握英雄相似的新英雄
- **Learning difficulty estimate**: 基于学习曲线预测上手速度

## Note
**Data Requirement**: Requires champion similarity matrix and meta tier list
**Fallback**: Can work with simplified heuristics or throw clear error

## Input: Player packs + Meta data | Output: 1500-2000 word report + Top 5 recommendations
