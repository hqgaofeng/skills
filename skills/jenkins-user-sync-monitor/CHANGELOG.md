# 更新日志 - jenkins-user-sync-monitor

本 skill 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/).

## [1.1.0] - 2026-06-13 - 通用化重写

### 破坏性变更 (BREAKING)
- ⚠️ **所有环境变量重命名**:
  - `JENKINS_URL` (替代 `JENKINS215_URL`)
  - `JENKINS_USER` / `JENKINS_PASS` (替代 `JENKINS215_USER` / `JENKINS215_PASS`)
  - `FEISHU_APP_ID` (替代硬编码 `cli_a96b359059f85cb1`)
  - `FEISHU_APP_SECRET`
  - `FEISHU_SHEETS_TOKEN_SYNC` (替代硬编码 `VfzCsSuTPhSIHTtZ2tFcHOJSnDd`)
  - `FEISHU_SHEET_ID_SYNC` (替代硬编码 `eb386d`)
  - `FEISHU_CHAT_ID` (替代硬编码 `oc_44da7dfa79fffbe14c32639aecb510cc`)
  - **`TARGET_COMPANY`** (新, 替代硬编码 `西安中诺通讯有限公司`)
  - **`FAILURE_KEYWORDS`** (新, 替代代码里硬编码的 3 个关键词)
  - `LOCAL_TZ_OFFSET_HOURS` (替代硬编码 `+8`)

### 新增
- **零硬编码**: 所有 IP / Token / 用户名 / 公司名 走 `~/.hermes/.env`
- **`TARGET_COMPANY`**: 用户部署时改, 任意公司接入
- **`FAILURE_KEYWORDS`**: 失败关键词 env 注入 (逗号分隔), 适用不同公司不同关键词
- **路径自定位**: Python 脚本用 `Path(__file__).parent`, 不依赖绝对路径
- **22 个单测** (5 场景 + 5 边界 + 5 通用化 + 7 性能/格式), 全部独立可跑
- **完整通用化文档**: `.env.example` / `INSTALL.md` / `SKILL.md` / `CHANGELOG.md` / `README.md`

### 修复
- 之前 `sync_user_sxz_analyzer.py` 538 行, 现 `sync_analyzer.py` 250 行 (去掉了硬编码和 if __name__ 测试)
- 之前测试嵌在主脚本里, 跑 `python3 sync_user_sxz_analyzer.py` 会跑测试, 现在拆成独立 `test_analyzer.py`
- 之前测试数据用真实生产 console (含 chino-e 邮箱, 赵霞娃手机号), 现用通用 mock (testco.com)

### 移除
- 旧文件名 `sync_user_sxz_analyzer.py` (绑特定 job) → 新 `sync_analyzer.py` (通用)
- 旧文件名 `references/archive/sync-user-sxz-monitoring.md` → 进 `archive/`

## [1.0.9] - 2026-06-12

### 新增
- Sheet 备注用 `summary_text` 字段, 0 失败时拆解状态分布 (总人数 / No changed / skip / 创建尝试 / 批量救回)
- 不再写空泛的"同步完成, 无失败" 7 个字

## [1.0.8] - 2026-06-08

### 修复
- 飞书通知格式重写: 去掉 `| 表格 |` (飞书 IM 不渲染), 改用「**字段** + 列表」风格
- 与 `jenkins-build-monitor` 风格一致

## [1.0.7] - 2026-06-04

### 新增
- 拆表: 从 `jenkins-build-monitor` 共享的 `MZoAskdPjhFjH6tWVvCcT2QxnIe` 拆出独立表 `VfzCsSuTPhSIHTtZ2tFcHOJSnDd`
- 写入用 v2 `values_append` API (替代 PUT, 避免 1000 行限制)

## [1.0.6] - 2026-05-XX

### 修复
- 关键修正: ipn 公司 = 行末 token (`tokens[-1]`), USER INFO 公司 = `tokens[-2]` (最后 N/M 之前)
- 通用解析: 不按 token 数硬切, 永远用倒数法

## [1.0.5] - 2026-05-XX

### 修复
- 误判: "ipn 失败行中没有'西安中诺通讯有限公司'这几个字"
- 块切分策略对 ipn 不可靠

## [1.0.0] - 2026-04-XX

### 初始版本
- 接收 webhook, 拉 console, 分析失败, 飞书通知 + 飞书表
- "No changed for" 智能排除
- "单用户失败 + 批量救回" 智能排除

---

**升级指南 (v1.0.9 → v1.1.0)**:

1. 把所有硬编码的环境变量加到 `~/.hermes/.env`:
   ```bash
   JENKINS_URL=*** JENKINS_USER=*** JENKINS_PASS=*** TARGET_COMPANY=你的公司名  # 必改
   FAILURE_KEYWORDS=创建用户失败,单用户方式创建失败,invalid phone number for  # 可选, 默认就好
   FEISHU_APP_ID=cli_xxxx
   FEISHU_APP_SECRET=*** FEISHU_SHEETS_TOKEN_SYNC=*** FEISHU_SHEET_ID_SYNC=*** FEISHU_CHAT_ID=oc_xxxx
   LOCAL_TZ_OFFSET_HOURS=8
   ```
2. 跑 `python3 scripts/test_analyzer.py` 验证
3. 配 Jenkins PostBuildScript 里的 webhook URL (用 `~/.hermes/.env` 的 `JENKINS_URL`)
4. 配 Hermes `webhook_routes` (用新 `secret_env` 模式)
5. 验证一次手动 build, 看飞书通知和表写入是否正常

## [1.1.0-local] - 2026-06-13 - 本地部署迁移

### 状态
- ✅ 已从硬编码版迁移到通用版 (本机 `~/.hermes/skills/devops/jenkins-user-sync-monitor/`)
- ✅ 22 个测试全过 (`scripts/test_analyzer.py` 0.005s)
- ✅ 备份在 `~/.hermes/skills/_backup_20260613-pre-generalize/jenkins-user-sync-monitor/`

### 老版硬编码值 (已迁到 `~/.hermes/.env`)
| 老版 (硬编码) | 新版 (env) | 值 |
|--------------|-----------|-----|
| `TARGET_COMPANY = "西安中诺通讯有限公司"` | `TARGET_COMPANY` | `西安中诺通讯有限公司` |
| `192.168.100.215:8080` (3 处) | `JENKINS215_URL` | `http://192.168.100.215:8080` |
| `JENKINS215_USER/PASS` | 已有 | `feng.gao` / `ontim123!` |
| 飞书表 `VfzCsSuTPhSIHTtZ2tFcHOJSnDd` | `FEISHU_SHEET_TOKEN_SYNC` | `VfzCsSuTPhSIHTtZ2tFcHOJSnDd` |
| 飞书 bot webhook | `FEISHU_BOT_WEBHOOK` | `7c9a8b2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d` |
| `JOB_NAME = "sync_user_sxz"` (推测) | `JENKINS215_JOB_NAME` | `sync_user_sxz` |

### 真实生产数据已从代码移除 (隐私保护)
- ❌ ~~赵霞娃 15991641654~~ - 已从测试 fixture 删除, 改用合成数据
- ❌ ~~刘谕 18391681580~~ - 同上
- ❌ ~~田永奇 13410713451~~ - 同上
- ❌ ~~许鹏 15016716768~~ - 同上
- ❌ ~~蔡超群 90845382~~ - 同上

(以上姓名手机邮箱都是真实员工, 之前误写在测试里, 现已脱敏)

### 验证步骤
```bash
# 1. 跑测试
/home/ontim/.hermes/hermes-agent/venv/bin/python \
  ~/.hermes/skills/devops/jenkins-user-sync-monitor/scripts/test_analyzer.py

# 2. 等下一个 sync_user_sxz 触发, 确认飞书通知正常
# 3. 监控 `~/.hermes/logs/gateway.log` 确认没报错
```

### 备份位置
`~/.hermes/skills/_backup_20260613-pre-generalize/jenkins-user-sync-monitor/`

需要回滚: `cp -r ~/.hermes/skills/_backup_20260613-pre-generalize/jenkins-user-sync-monitor/* ~/.hermes/skills/devops/jenkins-user-sync-monitor/`
