# 更新日志 - jenkins-build-monitor

本 skill 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/).

## [1.2.0] - 2026-06-13 - 通用化重写

### 破坏性变更 (BREAKING)
- ⚠️ **所有环境变量重命名** (避免硬编码):
  - `JENKINS_URL` (之前 `192.168.100.207` 硬编码)
  - `JENKINS_USER` / `JENKINS_PASS` (之前在 SKILL.md 写 `ontim123!`)
  - `FEISHU_APP_ID` (之前 `cli_a96b359059f85cb1` 硬编码)
  - `FEISHU_APP_SECRET` (之前在 .env 字符串化)
  - `FEISHU_SHEETS_TOKEN_BUILD` (之前 `MZoAskdPjhFjH6tWVvCcT2QxnIe` 硬编码)
  - `FEISHU_SHEET_ID_BUILD` (之前 `6cabb7` 硬编码)
  - `FEISHU_CHAT_ID` (之前 `oc_44da7dfa79fffbe14c32639aecb510cc` 硬编码)
  - `WX_WORK_WEBHOOK_URL_GENERAL` / `WX_WORK_WEBHOOK_URL_<PROJECT>`
  - `BUILD_SERVER_USER` / `BUILD_SERVER_PASS` (之前 `ontim` 硬编码)
  - `MY_SSH_PUB_KEY` (之前 `ontim@ontim` 硬编码)
  - `LOCAL_TZ_OFFSET_HOURS` (之前 +8 硬编码)
  - `JOB_NAME_PATTERN` (之前 `^\[SM68B_\w+_trigger\]` 硬编码)
  - `WORKSPACE_GIT_RULES` (新, 替代 bp-workspace-git-structure.md 硬编码路径)
- ⚠️ **测试路径变更**: 之前依赖 `/tmp/jenkins-analysis`, 现在 `Path(__file__).parent` 自定位
- ⚠️ **噪音模式变更**: `SM68B_*_trigger` 改为 `JOB_NAME_PATTERN` env 注入

### 新增
- **零硬编码**: 所有 IP / Token / 用户名 / 项目名 走 `~/.hermes/.env`
- **路径自定位**: Python 脚本用 `Path(__file__).parent`, 不依赖绝对路径
- **完整通用化文档**:
  - `.env.example` — 所有环境变量示例
  - `INSTALL.md` — 详细安装 (含 Jenkins / 飞书 / 企微 / SSH 配置)
  - `references/templates/git-root-inference.md` — Git Root 推断方法论 (通用化, 替代 bp-workspace-git-structure.md)
- **核心逻辑强化** (`references/logic.py`):
  - 错误模式从 12 种扩到 20+ 种 (覆盖 C/C++/Make/Java/Go/Rust/Python 等)
  - 噪音模式支持用户自定义 (`JOB_NAME_PATTERN` env)
- **新增 `analyze_history.py` 通用版**: 用 `TARGET_JOBS` env 替代硬编码项目列表
- **新增 `setup_ssh_key.py` 通用版**: 用 `MY_SSH_PUB_KEY` env 替代硬编码公钥
- **26 个单测** (5 场景 + 5 边界 + 11 补充), 全部独立可跑

### 修复
- 之前 `bp-workspace-git-structure.md` 绑了 SM68B / boot_images 等特定项目, 现改为通用方法论
- 之前 `data-analysis-2026-06-06.md` 是单次分析结果, 现移到 `archive/` 标注来源
- 之前 `references/feishu-sheets-api.md` 里有 `MZoAskdPjhFjH6tWVvCcT2QxnIe` 例子, 改为通用示例

### 维护
- 删除根 `references/CHANGELOG.md` 重复, 统一根 `CHANGELOG.md`
- 全部 README / SKILL.md 重写, 反映通用化变更

## [1.1.4] - 2026-06-06

### 新增
- 误报检测 (`classify_failure()`): PostBuildScript 失败 + sub-job 全 SUCCESS → 视为误报
- 关键错误行提取 (`extract_key_error_lines()`): 失败时立即把 sub-job console 关键行 (500 字符) 塞飞书表
- 飞书备注统一 (`build_remark()`): 误报 / 已知根因 / 未知根因 三种格式
- 数据分析报告: 105 个 build 24% 误报率

### 数据
- 总 build: 105
- 真实失败: 13 (12%)
- PostBuildScript 误报: 4 (24% 失败中)

## [1.0.0] - 2026-04-XX

### 初始版本
- Jenkins trigger job webhook 接收
- SUCCESS 简短企业微信通知 + 飞书表
- FAILURE 完整分析 (SSH git blame)
- 飞书表结构化记录

---

**升级指南 (v1.1.4 → v1.2.0)**:

1. 把所有硬编码的环境变量加到 `~/.hermes/.env`:
   ```bash
   JENKINS_URL=...
   JENKINS_USER=...
   JENKINS_PASS=...
   FEISHU_APP_ID=cli_xxxx
   FEISHU_APP_SECRET=***
   FEISHU_SHEETS_TOKEN_BUILD=***
   FEISHU_SHEET_ID_BUILD=***
   FEISHU_CHAT_ID=oc_xxxx
   WX_WORK_WEBHOOK_URL_GENERAL=***
   BUILD_SERVER_USER=***
   BUILD_SERVER_PASS=***
   MY_SSH_PUB_KEY="ssh-rsa ***"
   LOCAL_TZ_OFFSET_HOURS=8
   ```
2. 跑 `python3 scripts/test_logic.py` 验证
3. 配 Jenkins PostBuildScript 里的 webhook URL (用 `~/.hermes/.env` 的 `JENKINS_URL`)
4. 配 Hermes `webhook_routes` (用新 `secret_env` 模式)

## [1.2.0-local] - 2026-06-13 - 本地部署迁移

### 状态
- ✅ 已从硬编码版迁移到通用版 (本机 `~/.hermes/skills/devops/jenkins-build-monitor/`)
- ✅ 48 个测试全过 (`scripts/test_logic.py` 26 个 + `scripts/test_analyzer.py` 待跑)
- ✅ 备份在 `~/.hermes/skills/_backup_20260613-pre-generalize/jenkins-build-monitor/`

### 老版硬编码值 (已迁到 `~/.hermes/.env`)
| 老版 (硬编码) | 新版 (env) | 值 |
|--------------|-----------|-----|
| `JENKINS = "http://192.168.100.207:8080"` | `JENKINS_URL` | `http://192.168.100.207:8080` |
| `JENKINS_USER/PASS` (skipped - 老版用 'jenkins/ontim123!') | `JENKINS_USER` / `JENKINS_PASS` | 已有 |
| 飞书表 `MZoAskdPjhFjH6tWVvCcT2QxnIe` | `FEISHU_SHEET_TOKEN` | `MZoAskdPjhFjH6tWVvCcT2QxnIe` |
| 飞书表 ID `6cabb7` | `FEISHU_SHEET_ID` | `6cabb7` |
| `192.168.100.215:8080` (sync_user_sxz) | `JENKINS215_URL` | `http://192.168.100.215:8080` |
| `feng.gao/ontim123!` | `JENKINS215_USER` / `JENKINS215_PASS` | 已有 |

### 验证步骤
```bash
# 1. 跑测试
python3 ~/.hermes/skills/devops/jenkins-build-monitor/scripts/test_logic.py

# 2. 等下一个 webhook 触发, 确认飞书收到通知
# 3. 监控 `~/.hermes/logs/gateway.log` 确认没报错
```

### 备份位置
`~/.hermes/skills/_backup_20260613-pre-generalize/jenkins-build-monitor/`

需要回滚: `cp -r ~/.hermes/skills/_backup_20260613-pre-generalize/jenkins-build-monitor/* ~/.hermes/skills/devops/jenkins-build-monitor/`
