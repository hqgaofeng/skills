# jenkins-user-sync-monitor

> Jenkins 用户同步任务通用监控 — 自动分析 console, 飞书/企微通知

## ✨ 简介

监控任意 Jenkins 用户同步任务, 自动:

- ✅ 解析 USER INFO 行 (支持 8/9/10/11/12 token 格式, 通用算法)
- 🎯 提取**目标公司**的失败记录 (公司名走 env, 任意公司接入)
- 🚫 智能排除 "No changed for" 状态 (成功, 不是失败)
- 🚫 智能排除"单用户失败 + 批量救回"假阳性
- 📊 按失败类型汇总, 飞书 Sheets 记录
- 📱 飞书通知 (>= 5 条汇总, < 5 条逐条, 0 条静默)

**适用**: 任何公司 / 任何用户同步 Jenkins job.

**版本**: v1.1.0 (2026-06-13, 通用化重写)

## 🚀 快速开始 (5 分钟)

```bash
# 1. 装 skill
cp -r jenkins-user-sync-monitor ~/.hermes/skills/devops/

# 2. 配 .env
cat >> ~/.hermes/.env <<'EOF'
JENKINS_URL=http://jenkins.your-company.com:8080
JENKINS_USER=jenkins
JENKINS_PASS=your_password
TARGET_COMPANY=Your Company Ltd
# FAILURE_KEYWORDS=创建用户失败,单用户方式创建失败,invalid phone number for  (可选)
# FEISHU_APP_ID=cli_xxxx
# FEISHU_APP_SECRET=your_s...n
# FEISHU_SHEETS_TOKEN_SYNC=***
# FEISHU_SHEET_ID_SYNC=***

# 3. 装依赖
~/.hermes/venv/bin/pip install python-dotenv

# 4. 跑测试
python3 ~/.hermes/skills/devops/jenkins-user-sync-monitor/scripts/test_analyzer.py
# 期望: Ran 22 tests in 0.005s OK

# 5. 配 webhook route (在 ~/.hermes/config.yaml)
# 见 INSTALL.md 步骤 5
```

详细安装见 [INSTALL.md](./INSTALL.md).

## 📖 关键文档

- [SKILL.md](./SKILL.md) — Skill 描述 + 完整执行流程
- [INSTALL.md](./INSTALL.md) — 详细安装
- [CHANGELOG.md](./CHANGELOG.md) — 变更记录
- [scripts/sync_analyzer.py](./scripts/sync_analyzer.py) — 通用化分析器
- [scripts/test_analyzer.py](./scripts/test_analyzer.py) — 单测 (22 个测试)

## 🔧 脚本

- [scripts/sync_analyzer.py](./scripts/sync_analyzer.py) — 通用化分析器 (CLI + 库)
- [scripts/test_analyzer.py](./scripts/test_analyzer.py) — 单测

## 🆚 通用化 (v1.0.9 → v1.1.0)

| 变更 | v1.0.9 (旧) | v1.1.0 (新) |
|------|--------------|--------------|
| Jenkins URL | 硬编码 `192.168.100.215` | `JENKINS_URL` env |
| Jenkins 认证 | 硬编码 `JENKINS215_USER` 变量 | 通用 `JENKINS_USER`/`JENKINS_PASS` env |
| 飞书 app_id | 硬编码 `cli_a96b359059f85cb1` | `FEISHU_APP_ID` env |
| 飞书 chat_id | 硬编码 `oc_44da7dfa79fffbe14c32639aecb510cc` | `FEISHU_CHAT_ID` env |
| 飞书表 token | 硬编码 `VfzCsSuTPhSIHTtZ2tFcHOJSnDd` | `FEISHU_SHEETS_TOKEN_SYNC` env |
| 飞书表 ID | 硬编码 `eb386d` | `FEISHU_SHEET_ID_SYNC` env |
| **目标公司** | **硬编码 `西安中诺通讯有限公司`** | **`TARGET_COMPANY` env** |
| 失败关键词 | 代码里硬编码 3 个 | `FAILURE_KEYWORDS` env (逗号分隔) |
| 时区 | 硬编码 `+8` | `LOCAL_TZ_OFFSET_HOURS` env |
| 测试数据 | 真实生产 console | 通用 mock |
| 测试路径 | 内嵌在 sync_user_sxz_analyzer.py | 独立 test_analyzer.py |

**核心原则**: **零硬编码** — 任何公司名 / IP / Token / 用户名 **必须** 走环境变量.

## 🤝 贡献

详见 [根 CONTRIBUTING.md](../../CONTRIBUTING.md).

## 📜 许可证

[MIT](../../LICENSE)
