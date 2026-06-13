# Archive: 数据分析 - 2026-06-06 误报分析

> **⚠️ 此文档是历史快照, 不进通用归档的主代码.**
>
> 通用化重写时 (v1.2.0) 把这份特定日期的分析放到 `archive/`, 仅作历史参考.
> 通用方法论在 SKILL.md "关键概念 - 误报" 段.

## 背景

**日期**: 2026-06-06
**数据源**: 某 Android 编译触发器 (SM68B 系列) 105 个 build 记录
**触发者**: Allen (高峰)
**分析师**: hqgaofeng + Hermes

## 数据

| 指标 | 数值 |
|------|------|
| 总 build 数 | 105 |
| SUCCESS | 79 (75%) |
| FAILURE | 17 (16%) |
| ABORTED | 9 (9%) |
| **真实失败** | **13 (12%)** |
| **PostBuildScript 误报** | **4 (24% 失败中)** |

## 关键发现

### 1. 24% 失败是 PostBuildScript 误报

**现象**: trigger 被标 FAILURE, 但所有 sub-job 实际 SUCCESS.

**根因**: PostBuildScript 里的 `curl` 失败 (webhook 投递未回 200), 触发器被设为 FAILURE.

**节省**: 跳过 SSH git blame (每个 5-15 分钟), 4 个误报节省 ~20-60 分钟/季度.

### 2. 50-build FIFO 覆盖, 历史失败不可回溯

**现象**: Jenkins 默认 keep last 50 builds FIFO 覆盖. 想分析 30 天前失败的错误模式时, sub-job console 已不可访问.

**解决**: 失败时立即把关键错误行提取出来塞到飞书表备注列, 给未来 AI 训练留料. (v1.1.4 实现, `extract_key_error_lines()`)

### 3. 错误类型分布

| 错误类型 | 次数 | 占比 |
|----------|------|------|
| 头文件缺失 (fatal error) | 5 | 38% |
| make 编译错误 | 4 | 31% |
| 模块构建失败 | 2 | 15% |
| FileNotFoundError (构建产物) | 1 | 8% |
| OOM | 1 | 8% |

## v1.1.4 实施的修复

1. `classify_failure()` — 误报检测
2. `extract_key_error_lines()` — 关键错误行提取
3. `build_remark()` — 统一飞书备注格式

## v1.2.0 通用化

误报检测逻辑保留 (v1.2.0), 适用任何项目. 噪音模式从硬编码 `SM68B_*` 改为 env 注入 (`JOB_NAME_PATTERN`).
