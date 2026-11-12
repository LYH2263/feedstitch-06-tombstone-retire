# 01-feedstitch（信汇）

Feedstitch — 多源目录/价目 Feed 归并落库：解析 → 业务键去重/冲突隔离 → 按源水位线增量或全量落库。

## 启动

```bash
docker compose up --build
```

| 入口 | 地址 |
| --- | --- |
| 前端 | http://localhost:5100 |
| API | http://localhost:10100 |

## 主链

配置源与夹具 → 触发 Run → 解析 / 去重 / 冲突隔离 → Canonical + 运行报告对账

## 种子说明

- **Alpha Catalog（clean）**：JSON，三件干净货号，增量可落库。
- **Beta Offers（dirty）**：JSONL，含与 Alpha 同键但价格不同的冲突行，以及迟到低 revision 行（底座增量会因水位线跳过）。
- **Gamma Shelf（xml）**：简易 XML，两件独立货号。
- **Delta Retirements（源级墓碑源）**：JSONL，源被标记 `tombstone_source`，每行都按退役事件处理；对 SKU-1002 软删，另含一条重复墓碑与一条未知键。
- **Epsilon Revive Feed（带内墓碑）**：JSONL，用 `tombstone:true` / `status:"retired"` 标记退役，并演示退役键上的复活（新 revision）与拒绝（旧 revision）。

打开“运行台”选源跑一次增量，再看 Staging / 冲突 / Canonical 三页计数是否与本次 Run 报告一致。

## 墓碑退役链路（tombstone_retire）

退役是 canonical 行上的软删状态（`status=alive|retired` + `retired_at/retired_by_*` 审计列），
不是 Type-2 历史链，也不走冲突死信；行不会被物理删除，刷新/重启后仍在，可按键查询。

- **识别**：带内字段（`tombstone` / `retired` / `is_deleted` / `deleted` 为真，或
  `status` / `event_type` 取值为 tombstone/retired/delete…），或源级 `tombstone_source` 标记。
  墓碑行只需业务键 + event_ts + revision，描述字段可缺省。
- **退役**：存活键收到墓碑 → `tombstone_retire`，从存活视图移除并写入退役元数据；
  已退役键再收墓碑 → `tombstone_duplicate`（不动计数、不改退役元数据、不回退水位线）；
  未知键墓碑 → `tombstone_unknown`，不凭空建行。
- **复活/拒绝策略（可审计）**：退役键收到存活事件时，按 revision 裁决——
  新 revision → `revive_upsert` 复活写回存活视图；同/旧 revision → `reject_stale_revived`
  拒绝写入，退役行保持不变。两类结果在 Staging 与 Run 报告中用不同 disposition 区分。
- **对账**：每次 Run 满足
  `parsed = upserted + retired + revived + conflict + skipped`，
  且 `staging_row_count = parsed`；报告里的存活/退役条数与 Canonical 列表页、总览页
  取自同一组 SQLite 计数查询（报告 `reconciled=true` 即恒等式成立）。

## 技术栈

Python 3.12 + FastAPI + SQLite；Vue 3 + Vite + Nginx。

## 0-1 切口（未实现）

`lookback_backfill` / `schema_drift_guard` / `dead_letter_replay` / `webhook_push_source` /
`source_authority_rank` / `scd2_history` / `watermark_commit_gate` /
`field_map_transform` / `lineage_provenance`
