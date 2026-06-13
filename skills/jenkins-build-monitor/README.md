# jenkins-build-monitor

> Jenkins 编译任务通用监控 — 自动分析失败, SSH 定位 commit, 飞书/企微通知

## ✨ 简介

监控任意 Jenkins 编译任务 (Android / iOS / 嵌入式 / 后端 / 前端), 自动:

- ✅ SUCCESS 简短通知 + 飞书表记录
- 🚨 FAILURE **误报检测** (PostBuildScript 失败 vs 真实编译失败)
- 📍 FAILURE SSH 到编译服务器, git blame 报错文件定位 commit
- 📊 FAILURE 完整报告 (commit 作者 / 时间 / 修复建议)
- 📝 所有构建结果都写入飞书 Sheets (含子任务 console 关键错误行)

**适用**: 任何公司 / 任何项目 / 任何语言的编译任务.

**版本**: v1.2.0 (2026-06-13, 通用化重写)

## 🚀 快速开始 (5 分钟)

```bash
# 1. 装 skill
cp -r jenkins-build-monitor ~/.hermes/skills/devops/

# 2. 配 .env
cat >> ~/.hermes/.env <<'EOF'
JENKINS_URL=http://jenkins.your-company.com:8080
JENKINS_USER=jenkins
JENKINS_PASS=your_password
BUILD_SERVER_USER=builder
BUILD_SERVER_PASS=your_password
FEISHU_APP_ID=cli_xxxx
FEISHU_APP_SECRET=your_secret
FEISHU_SHEETS_TOKEN_BUILD=***
FEISHU_SHEET_ID_BUILD=***
FEISHU_CHAT_ID=oc_xxxx
WX_WORK_WEBHOOK_URL_GENERAL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...
EOF

# 3. 装依赖
~/.hermes/venv/bin/pip install requests paramiko python-dotenv

# 4. 跑测试 (验证环境)
python3 ~/.hermes/skills/devops/jenkins-build-monitor/scripts/test_logic.py
# 期望: Ran 26 tests in 0.006s OK

# 5. 配 webhook route (在 ~/.hermes/config.yaml)
# 见 INSTALL.md 步骤 5
```

详细安装见 [INSTALL.md](./INSTALL.md).

## 📖 关键文档

- [SKILL.md](./SKILL.md) — Skill 描述 + 完整执行流程
- [INSTALL.md](./INSTALL.md) — 详细安装 (含 Jenkins / 飞书 / 企微 / SSH 配 置)
- [CHANGELOG.md](./CHANGELOG.md) — 变更记录
- [references/logic.py](./references/logic.py) — 核心逻辑 (classify_failure / extract_key_error_lines / build_remark)
- [references/feishu-sheets-api.md](./references/feishu-sheets-api.md) — 飞书 Sheets API 速查
- [references/feishu-sheets-append-api.md](./references/feishu-sheets-append-api.md) — 飞书 v2 append API 详解
- [references/templates/git-root-inference.md](./references/templates/git-root-inference.md) — Git Root 推断方法论

## 🔧 脚本

- [scripts/test_logic.py](./scripts/test_logic.py) — 单测 (26 个测试, 5 场景 + 5 边界)
- [scripts/analyze_history.py](./scripts/analyze_history.py) — 历史构建分析
- [scripts/setup_ssh_key.py](./scripts/setup_ssh_key.py) — 新服务器 SSH key 自动配置

## 📦 目录结构

```
jenkins-build-monitor/
├── SKILL.md                # Skill 描述
├── README.md               # 本文件
├── INSTALL.md              # 详细安装
├── CHANGELOG.md            # 变更记录
├── .env.example            # 环境变量示例
├── references/             # 详细文档 + 核心代码
│   ├── logic.py            # 通用核心逻辑
│   ├── feishu-sheets-api.md
│   ├── feishu-sheets-append-api.md
│   └── templates/          # 通用方法论模板
│       └── git-root-inference.md
├── scripts/                # 可执行脚本
│   ├── test_logic.py
│   ├── analyze_history.py
│   └── setup_ssh_key.py
└── archive/                # 历史快照 (不进主代码)
    └── data-analysis-2026-06-06.md
```

## 🆚 通用化 (v1.1.4 → v1.2.0)

| 变更 | v1.1.4 (旧) | v1.2.0 (新) |
|------|--------------|--------------|
| Jenkins URL | 硬编码 `192.168.100.207` | `JENKINS_URL` env |
| 飞书 app_id | 硬编码 `cli_a96b359059f85cb1` | `FEISHU_APP_ID` env |
| 飞书 chat_id | 硬编码 `oc_44da7dfa79fffbe14c32639aecb510cc` | `FEISHU_CHAT_ID` env |
| 飞书表 token | 硬编码 `MZoAskdPjhFjH6tWVvCcT2QxnIe` | `FEISHU_SHEETS_TOKEN_BUILD` env |
| SSH 公钥 | 硬编码 `ontim@ontim` | `MY_SSH_PUB_KEY` env (用户自填) |
| 编译服务器 IP | 硬编码列表 | 从 sub-job consoleText 动态取 |
| 路径 | `~/.hermes/skills/...` 绝对路径 | `Path(__file__).parent` 自定位 |
| 时区 | 硬编码 `+8` | `LOCAL_TZ_OFFSET_HOURS` env |
| 噪音模式 | 硬编码 `SM68B_*_trigger` | `JOB_NAME_PATTERN` env (可注入) |
| 测试路径 | `/tmp/jenkins-analysis` | `Path(__file__).parent` 自定位 |
| 测试数据 | 外部 JSON fixture | 内嵌常量, 不依赖文件 |

**核心原则**: **零硬编码** — 任何 IP / Token / 用户名 / 公司名 / 项目名 **必须** 走环境变量.

## 🤝 贡献

详见 [根 CONTRIBUTING.md](../../CONTRIBUTING.md).

## 📜 许可证

[MIT](../../LICENSE)
