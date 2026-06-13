# 通用安装指南

本指南说明如何把 hqgaofeng/skills 仓库中的 skill 部署到 Hermes / OpenClaw / 其他兼容 runtime.

## 📋 目录

- [环境要求](#环境要求)
- [部署架构](#部署架构)
- [单 Skill 部署](#单-skill-部署)
- [批量部署](#批量部署)
- [环境变量约定](#环境变量约定)
- [运行时兼容性](#运行时兼容性)
- [升级](#升级)
- [卸载](#卸载)
- [常见问题](#常见问题)

## 环境要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.8 | 跑 skill 自带脚本 |
| pip / pipx | latest | 安装 Python 依赖 |
| Bash | ≥ 4.0 | 跑 PostBuildScript / 测试 |
| curl | ≥ 7.0 | 触发 webhook 测试 |
| openssl | ≥ 1.0 | HMAC 签名 |
| git | ≥ 2.0 | git blame 定位 commit |

### Python 依赖 (skill 自带)

各 skill 所需的 Python 包通常为:

```
requests >= 2.28
paramiko >= 2.10
python-dotenv >= 0.20
```

推荐用 `pipx` 装到 hermes 自己的 venv, 避免污染系统 Python:

```bash
# hermes 自带 venv (推荐)
~/.hermes/venv/bin/pip install requests paramiko python-dotenv

# 或用 pipx
pipx install paramiko  # 全局
```

## 部署架构

### 单机部署 (最常见)

```
~/.hermes/
├── config.yaml
├── .env                       # ← 敏感凭据, 强烈建议 gitignore
├── skills/
│   └── devops/                # ← 你的 skill 装到哪个类别
│       ├── jenkins-build-monitor/    # ← 从 hqgaofeng/skills 拷过来
│       └── jenkins-user-sync-monitor/
└── ...
```

### 多机部署

每台机器单独装. 环境变量可以走:
- 机器本地 `~/.hermes/.env`
- HashiCorp Vault / 1Password CLI (推荐)
- K8s Secret (如果用 K8s)

## 单 Skill 部署

### 1. 下载

```bash
# 方式 A: git clone
git clone https://github.com/hqgaofeng/skills.git
cp -r skills/jenkins-build-monitor ~/.hermes/skills/devops/

# 方式 B: sparse checkout
git clone --depth 1 --filter=blob:none --sparse https://github.com/hqgaofeng/skills.git
cd skills
git sparse-checkout set skills/jenkins-build-monitor
cp -r skills/jenkins-build-monitor ~/.hermes/skills/devops/

# 方式 C: GitHub Release tarball
wget https://github.com/hqgaofeng/skills/releases/download/v1.2.0/jenkins-build-monitor-v1.2.0.tar.gz
tar -xzf jenkins-build-monitor-v1.2.0.tar.gz -C ~/.hermes/skills/devops/
```

### 2. 装 Python 依赖

```bash
~/.hermes/venv/bin/pip install requests paramiko python-dotenv
```

### 3. 配置环境变量

```bash
# 编辑 ~/.hermes/.env
cat >> ~/.hermes/.env <<'EOF'

# === jenkins-build-monitor ===
JENKINS_URL=http://jenkins.your-company.com:8080
JENKINS_USER=jenkins
JENKINS_PASS=your_password
BUILD_SERVER_USER=builder
BUILD_SERVER_PASS=your_password
WX_WORK_WEBHOOK_URL_GENERAL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_SHEETS_TOKEN_BUILD=your_sheets_token
FEISHU_SHEET_ID_BUILD=your_sheet_id
EOF
```

**具体变量名见每个 skill 的 INSTALL.md**.

### 4. 跑测试

```bash
# skill 自带测试, 跑通就 OK
python3 ~/.hermes/skills/devops/jenkins-build-monitor/scripts/test_v114.py
```

### 5. 配置 webhook route (在 Hermes Gateway)

```yaml
# ~/.hermes/config.yaml
webhook_routes:
  - id: jenkins-monitor
    path: /webhooks/jenkins-monitor
    skill: jenkins-build-monitor
    secret_env: HERMES_JENKINS_SECRET
    platform_toolsets: [terminal, code_execution, messaging, file, skills, memory, web]
```

```bash
# 重启 gateway
systemctl --user restart hermes-gateway
```

### 6. 测试 webhook

```bash
HERMES_URL="http://127.0.0.1:8644/webhooks/jenkins-monitor"
HERMES_SECRET="your_secret"

PAYLOAD='{"job_name":"test","build_number":"1","build_result":"SUCCESS","build_url":"http://x","build_user":"test","timestamp":"2026-01-01T00:00:00Z"}'
SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$HERMES_SECRET" | sed 's/^.* //')

curl -s -X POST "$HERMES_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD"
# 期望: HTTP 200
```

## 批量部署

### 一次装所有 skill

```bash
git clone https://github.com/hqgaofeng/skills.git /tmp/skills-archive
for skill_dir in /tmp/skills-archive/skills/*/; do
  skill_name=$(basename "$skill_dir")
  cp -r "$skill_dir" ~/.hermes/skills/devops/
  echo "✅ Installed: $skill_name"
done
rm -rf /tmp/skills-archive
```

### 同步所有 skill (后续更新)

```bash
cd /tmp/skills-archive 2>/dev/null || git clone https://github.com/hqgaofeng/skills.git /tmp/skills-archive
cd /tmp/skills-archive
git pull
for skill_dir in skills/*/; do
  skill_name=$(basename "$skill_dir")
  rsync -av --delete "$skill_dir" ~/.hermes/skills/devops/
  echo "🔄 Updated: $skill_name"
done
```

## 环境变量约定

为避免冲突, **所有 skill 共用的变量**用统一前缀, 避免污染.

| 前缀 | 含义 | 示例 |
|------|------|------|
| `JENKINS_URL` | Jenkins base URL (通用) | `http://jenkins:8080` |
| `JENKINS_USER` / `JENKINS_PASS` | Jenkins 认证 (通用) | - |
| `JENKINS_<NAME>_URL` | 多 Jenkins 实例时按名 | `JENKINS_PROD_URL`, `JENKINS_STAGING_URL` |
| `BUILD_SERVER_*` | 编译服务器 SSH 凭据 | - |
| `WX_WORK_WEBHOOK_URL_*` | 企业微信 webhook | `WX_WORK_WEBHOOK_URL_GENERAL`, `WX_WORK_WEBHOOK_URL_<PROJECT>` |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书应用凭据 (通用) | - |
| `FEISHU_SHEETS_TOKEN_<NAME>` | 飞书表 token (按用途) | `FEISHU_SHEETS_TOKEN_BUILD`, `FEISHU_SHEETS_TOKEN_SYNC` |
| `FEISHU_SHEET_ID_<NAME>` | 飞书表 ID | 同上 |
| `FEISHU_CHAT_ID` | 飞书 chat_id | `oc_xxxxxxxxxxxx` |

> **避免**: 任何公司专属的变量名 (如 `JENKINS_SM68B_URL`, `西安中诺通讯有限公司`)

## 运行时兼容性

| Runtime | 兼容性 | 备注 |
|---------|--------|------|
| Hermes Agent | ✅ 完全支持 | 原生 |
| OpenClaw | ✅ 完全支持 | 同 Hermes 协议 |
| Claude Code (with skill loader) | ✅ | 需手动注册 skill path |
| Codex CLI (with skill loader) | ✅ | 同上 |

所有 skill 都假定:
- `python3` 在 PATH
- `~/.hermes/.env` 存在 (或显式 `load_dotenv(path)`)
- Webhook payload 格式为标准 JSON

## 升级

```bash
cd /tmp
git clone https://github.com/hqgaofeng/skills.git skills-new
diff -ruN ~/.hermes/skills/devops/jenkins-build-monitor skills-new/skills/jenkins-build-monitor
# 看 diff 决定怎么合
rsync -av skills-new/skills/jenkins-build-monitor/ ~/.hermes/skills/devops/jenkins-build-monitor/
```

或者用 git 维护每个 skill:

```bash
cd ~/.hermes/skills/devops/jenkins-build-monitor
git init
git remote add origin https://github.com/hqgaofeng/skills.git
git fetch
git checkout main -- .  # 用仓库版本覆盖本地
```

## 卸载

```bash
rm -rf ~/.hermes/skills/devops/<skill-name>
# 然后从 ~/.hermes/.env 删对应变量
# 然后从 ~/.hermes/config.yaml 删对应 webhook route
```

## 常见问题

### Q: skill 装在哪个目录?

`~/.hermes/skills/<category>/<skill-name>/`. `category` 可以是 `devops`, `monitoring`, `notification` 等任意名字, 反映 skill 用途.

### Q: 多个 skill 用同一份环境变量怎么办?

`~/.hermes/.env` 是**全局**的, 多个 skill 自动共享. 例如 `JENKINS_USER` 给两个 skill 用都可以.

### Q: 想用别的 `.env` 文件?

每个 skill 启动时用 `load_dotenv(os.path.expanduser("~/.hermes/.env"))`. 要换路径, 改 skill 的 `load_dotenv()` 调用 (提 PR).

### Q: 部署到 K8s / Docker?

把环境变量从 `.env` 移到 K8s Secret / env 注入. Skill 本身不需改.

### Q: 没飞书, 只用企业微信?

可以, 大多数 skill 的飞书通知是**可选**的. 不配 `FEISHU_APP_*` 就跳过飞书通知.

### Q: 装好后 skill 不工作?

1. 跑 skill 自带测试 (每个 skill 的 `scripts/test_*.py`)
2. 看 `~/.hermes/state.db` 里 session 状态
3. 看 `~/.hermes/logs/gateway.log`

## 资源

- [Hermes Agent 文档](https://hermes-agent.nousresearch.com/docs)
- [每个 skill 的 INSTALL.md](./skills/jenkins-build-monitor/INSTALL.md)
- [故障排查通用指南](./docs/troubleshooting.md) (待补)
