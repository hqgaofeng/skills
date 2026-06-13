# Archive: sync-user-sxz 历史快照

> **⚠️ 此目录是历史快照, 不进通用归档的主代码.**
>
> 通用化重写时 (v1.1.0) 把原 sync_user_sxz 相关历史放到这里, 仅作参考.
> 当前 skill 通用化版见 SKILL.md / README.md / INSTALL.md.

## 历史文件 (已迁移 / 已通用化)

| 原文件 (v1.0.x) | 现状 |
|------------------|------|
| `scripts/sync_user_sxz_analyzer.py` (538 行, 绑西安中诺) | 拆为通用 `sync_analyzer.py` (250 行) + `test_analyzer.py` (独立) |
| `references/sync-user-sxz-console-structure.md` (绑 sync_user_sxz) | 改为通用 `sync-console-structure.md` (任意公司) |
| `references/archive/sync-user-sxz-monitoring.md` | 保留在此目录, 仅作历史 |

## 历史里程碑

- **v1.0.0** (2026-04-XX): 初始, sync_user_sxz job 监控, 西安中诺过滤
- **v1.0.5**: 发现 ipn 误判, 块切分策略有 bug
- **v1.0.6**: 关键修正, ipn 公司 = `tokens[-1]`, USER INFO = `tokens[-2]`
- **v1.0.7** (2026-06-04): 拆表, 从构建表拆出独立 sync_user_sxz 表
- **v1.0.8** (2026-06-08): 飞书通知格式重写, 去掉 markdown 表格
- **v1.0.9** (2026-06-12): summary_text 字段, 0 失败时拆解状态分布
- **v1.1.0** (2026-06-13): 通用化重写, 零硬编码, 任意公司接入

## 经验教训 (v1.0.x → v1.1.0)

1. **多公司过滤必要**: 一个 Jenkins job 同步多公司时, 必须能按公司名过滤
2. **失败关键词 env 化**: 不同公司失败关键词可能不同, 不要硬编码
3. **路径自定位**: 测试不应依赖 `/tmp/jenkins-analysis` 这种绝对路径
4. **方法论与数据分离**: 真实生产 console (含 chino-e 邮箱, 赵霞娃手机号) 不应进通用归档
5. **测试独立可跑**: 内嵌测试 + 真实数据 = 难维护, 拆为独立 test_*.py + 通用 mock
