# SQLPilot 压力集报告

> 生成时间：2026-11-22 19:00:53
> 模式：压力集（--stress）／ 重复轮数：1／ group：`G2`

## 一、纠错触发率

| 指标 | 值 |
|---|---|
| 触发纠错题数 / 总题数 | 11/30 |
| 触发率 | 36.7% |

> 触发 = 该题在本轮 `retry_count > 0`（模型首次生成 SQL 被判失败并重试）。

## 二、逐题触发矩阵

| ID | 触发纠错 | retry_count | final_status |
|---|---|---|---|
| S01 | ❌ | 0 | refused |
| S02 | ✅ | 1 | success |
| S03 | ❌ | 0 | refused |
| S04 | ❌ | 0 | refused |
| S05 | ❌ | 0 | refused |
| S06 | ❌ | 0 | refused |
| S07 | ✅ | 2 | failed |
| S08 | ✅ | 2 | failed |
| S09 | ✅ | 1 | success |
| S10 | ✅ | 1 | success |
| S11 | ✅ | 2 | failed |
| S12 | ❌ | 0 | success |
| S13 | ❌ | 0 | success |
| S14 | ❌ | 0 | success |
| S15 | ❌ | 0 | success |
| S16 | ❌ | 0 | success |
| S17 | ❌ | 0 | success |
| S18 | ✅ | 2 | failed |
| S19 | ❌ | 0 | success |
| S20 | ❌ | 0 | success |
| S21 | ❌ | 0 | success |
| S22 | ✅ | 1 | success |
| S23 | ✅ | 2 | failed |
| S24 | ❌ | 0 | success |
| S25 | ❌ | 0 | success |
| S26 | ✅ | 2 | failed |
| S27 | ❌ | 0 | refused |
| S28 | ❌ | 0 | success |
| S29 | ✅ | 1 | success |
| S30 | ❌ | 0 | success |

## 三、说明

压力集不含 gt_sql，不判对错，只验证"能否触发自纠错"。
