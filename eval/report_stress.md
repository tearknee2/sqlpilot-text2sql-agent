# SQLPilot 压力集报告

> 生成时间：2026-11-22 21:04:11
> 模式：压力集（--stress）／ 重复轮数：1／ group：`G2`

## 一、纠错触发率与挽回率

| 指标 | 值 |
|---|---|
| 触发纠错题数 / 总题数 | 11/30 |
| 触发率 | 36.7% |
| 挽回题数 / 触发题数 | 5/11 |
| 挽回率 | 45.5% |

> 触发 = 该题在本轮 `retry_count > 0`（模型首次生成 SQL 被判失败并重试）。
> 挽回率 = 触发纠错且最终 status==success 的比例（纠错把错 SQL 救回来的比例）。

## 二、逐题触发矩阵

| Run | ID | 触发纠错 | retry_count | final_status |
|---|---|---|---|---|
| 1 | S01 | ❌ | 0 | refused |
| 1 | S02 | ✅ | 1 | success |
| 1 | S03 | ❌ | 0 | refused |
| 1 | S04 | ❌ | 0 | refused |
| 1 | S05 | ❌ | 0 | refused |
| 1 | S06 | ❌ | 0 | refused |
| 1 | S07 | ✅ | 2 | failed |
| 1 | S08 | ✅ | 2 | failed |
| 1 | S09 | ✅ | 1 | success |
| 1 | S10 | ✅ | 1 | success |
| 1 | S11 | ✅ | 2 | failed |
| 1 | S12 | ❌ | 0 | success |
| 1 | S13 | ❌ | 0 | success |
| 1 | S14 | ❌ | 0 | success |
| 1 | S15 | ❌ | 0 | success |
| 1 | S16 | ❌ | 0 | success |
| 1 | S17 | ❌ | 0 | success |
| 1 | S18 | ✅ | 2 | failed |
| 1 | S19 | ❌ | 0 | success |
| 1 | S20 | ❌ | 0 | success |
| 1 | S21 | ❌ | 0 | success |
| 1 | S22 | ✅ | 1 | success |
| 1 | S23 | ✅ | 2 | failed |
| 1 | S24 | ❌ | 0 | success |
| 1 | S25 | ❌ | 0 | success |
| 1 | S26 | ✅ | 2 | failed |
| 1 | S27 | ❌ | 0 | refused |
| 1 | S28 | ❌ | 0 | success |
| 1 | S29 | ✅ | 1 | success |
| 1 | S30 | ❌ | 0 | success |

## 三、说明

压力集不含 gt_sql，不判对错，只验证"能否触发自纠错"。
