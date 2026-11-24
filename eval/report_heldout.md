# SQLPilot 评测报告

> 生成时间：2026-11-24 12:11:40
> split：`heldout`
> model：`deepseek-chat` ／ PROMPT_VERSION：`v2.0-final` ／ dataset_sha256：`ab9c1143c3d45c06...`
> **小样本声明**：当前 8 道可评分题（目标 24，D8 补齐）；1 题 ≈ 12.5pp；不做显著性检验，结论以逐题矩阵为准。

## 一、执行准确率

| 指标 | 值 |
|---|---|
| passed / total | 8/8 |
| accuracy | 100.0% |

## 二、逐题矩阵（heldout）

| ID | layer | difficulty | passed | reason |
|---|---|---|---|---|
| E04 | 时间条件 | medium | ✅ | multiset_compare_ok |
| E08 | 脏数据 | medium | ✅ | multiset_compare_ok |
| E23 | 时间条件 | medium | ✅ | multiset_compare_ok |
| E24 | 聚合分组 | hard | ✅ | ordered_compare_ok |
| E25 | 多表JOIN | hard | ✅ | multiset_compare_ok |
| E26 | 子查询 | hard | ✅ | multiset_compare_ok |
| E27 | 脏数据 | easy | ✅ | multiset_compare_ok |
| E28 | 排序TopN | medium | ✅ | ordered_compare_ok |

## 三、G0/G1 消融（D11 填充）

| 组 | 执行准确率 | 说明 |
|---|---|---|
| G0 Full-Schema | ⬜ 待填 | D11（全量表，无检索） |
| G1 +SchemaLink | ⬜ 待填 | D11（top-k，无纠错） |
| **G2 Full** | **8/8** | **当前**（top-k + 纠错） |

## 四、翻转清单（D11 填）

⬜ 待填（需要 G0/G1/G2 三组数据对比）

## 五、压力集（D8 建 + D11 跑）

⬜ 待填（12 道压力题）

## 六、拒答 / 安全指标

⬜ 待填（当前 dev/heldout 无 refuse/blocked 题；D8 补完 24 道后统计）

## 七、badcase 汇总

（见逐题矩阵中 ❌ 的行；D11 做详细归因）
