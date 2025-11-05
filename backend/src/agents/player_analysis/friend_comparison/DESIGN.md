# PeerComparisonAgent Design Document

## Overview
Compares player performance against same-rank baseline to identify relative strengths and weaknesses.

## Key Features
- **Rank-relative comparison**: vs同段位平均水平
- **Z-score analysis**: 标准化性能指标
- **Advantage/disadvantage domains**: 优势和劣势领域识别
- **Rank matching**: 基于表现预测合理段位

## Note
**Data Requirement**: Requires Gold layer rank baseline data (currently unavailable)
**Fallback**: Can work with estimated baselines or throw clear error

## Input: Player packs + Rank baseline | Output: 2000-2500 word comparison report
