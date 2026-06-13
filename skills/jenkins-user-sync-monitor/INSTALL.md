# 安装指南 - jenkins-user-sync-monitor

## 📋 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [环境变量配置](#环境变量配置)
- [Jenkins 配置](#jenkins-配置)
- [飞书配置 (可选)](#飞书配置-可选)
- [Webhook Route 配置](#webhook-route-配置)
- [验证](#验证)
- [故障排查](#故障排查)

## 环境要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.8 | 跑 skill 自带脚本 |
| pip | latest | 装 Python 依赖 |
| curl | ≥ 7.0 | 触发 webhook 测试 |
| openssl | ≥ 1.0 | HMAC 签名 |
| Jenkins | 任意版本 | 用户同步任务 |
| Jenkins PostBuildScript 插件 | 任意版本 | 触发 webhook |

### Python 依赖

```
python-dotenv >= 0.20
```

(本 skill 比 jenkins-build-monitor 简单, 不需要 paramiko / requests)

## 安装步骤

### 1. 部署 skill

```bash
git clone https://github.com/hqgaofeng/skills.git /tmp/skills-archive
cp -r /tmp/skills-archive/skills/jenkins-user-sync-monitor ~/.hermes/skills/devops/
rm -rf /tmp/skills-archive
```

或直接下载 tarball:

```bash
wget https://github.com/hqgaofeng/skills/releases/download/v1.1.0/jenkins-user-sync-monitor-v1.1.0.tar.gz
tar -xzf jenkins-user-sync-monitor-v1.1.0.tar.gz -C ~/.hermes/skills/devops/
```

### 2. 装 Python 依赖

```bash
~/.hermes/venv/bin/pip install python-dotenv
# 或 pip install python-dotenv
```

### 3. 配环境变量

```bash
# 复制示例
cp ~/.hermes/skills/devops/jenkins-user-sync-monitor/.env.example ~/.hermes/.env
# 然后编辑 ~/.hermes/.env 填入真实值
```

## 环境变量配置

| 变量 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `JENKINS_URL` | ✅ | Jenkins base URL | `http://jenkins:8080` |
| `JENKINS_USER` | ✅ | Jenkins 认证用户 | `jenkins` |
| `JENKINS_PASS` | ✅ | Jenkins 认证密码 | - |
| `TARGET_COMPANY` | ✅ | **目标公司名** (要监控哪个公司) | `Your Company Ltd` |
| `FAILURE_KEYWORDS` | ❌ | 失败关键词, 逗号分隔 | `创建用户失败,单用户方式创建失败,invalid phone number for` |
| `LOCAL_TZ_OFFSET_HOURS` | ❌ | 时区偏移, 默认 8 (北京) | `8` / `-5` / `0` |
| `FEISHU_APP_ID` | ❌ | 飞书应用 ID | `cli_xxxx` |
| `FEISHU_APP_SECRET` | ❌ | 飞书应用 Secret | - |
| `FEISHU_SHEETS_TOKEN_SYNC` | ❌ | 飞书表 token (同步记录, 独立表) | - |
| `FEISHU_SHEET_ID_SYNC` | ❌ | 飞书表 ID | - |
| `FEISHU_CHAT_ID` | ❌ | 飞书 chat_id (通知目标) | `oc_xxxx` |

**关键变量**:
- `TARGET_COMPANY`: 决定只监控哪家公司. 多公司同步时, 其他公司的失败不计入.
- `FAILURE_KEYWORDS`: 决定哪些文本被算作"失败". 默认 3 个常见关键词, 你公司有特殊的可以追加.

**避免**:
- ❌ `JENKINS215_URL` (用通用名 `JENKINS_URL`, 不要带具体 Jenkins 实例名)
- ❌ `TARGET_COMPANY_DEFAULT` (用通用名 `TARGET_COMPANY`)
- ❌ 硬编码在 skill 里

## Jenkins 配置

### 1. 装 PostBuildScript 插件

**Jenkins → Manage Jenkins → Manage Plugins → Available → 搜 "PostBuildScript" → Install**

### 2. 配置用户同步 job

**Jenkins → 你的用户同步 job → 配置 → 构建后操作 → Add post-build step → PostBuildScript**

勾选 "Always".

在 "Script" 框填:

```bash
#!/bin/bash

# === 配置 ===
HERMES_URL="http://your-hermes-host:8644/webhooks/sync-user-monitor"  # 改
HERMES_SECRET=*** # 改 (跟 ~/.hermes/config.yaml 对齐)

# === Payload ===
PAYLOAD=$(cat <<EOF
{
  "job_name": "${JOB_NAME}",
  "build_number": "${BUILD_NUMBER}",
  "build_result": "${BUILD_RESULT}",
  "build_url": "${BUILD_URL}",
  "build_user": "${BUILD_USER:-unknown}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)

# === HMAC ===
SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$HERMES_SECRET" | sed 's/^.* //')

# === 发 webhook ===
curl -s -X POST "${HERMES_URL}" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD"

echo "Webhook sent to ${HERMES_URL}"
```

## 飞书配置 (可选)

如果**不用飞书**, 跳过这节. skill 会自动跳过.

### 1. 创建飞书应用 + 表格

详见 [jenkins-build-monitor INSTALL.md#飞书配置](../jenkins-build-monitor/INSTALL.md#飞书配置-可选).

**注意**: 本 skill 用**独立表** (跟构建记录分开), 推荐用 `FEISHU_SHEETS_TOKEN_SYNC` / `FEISHU_SHEET_ID_SYNC` 标识.

### 2. 表头 (第 1 行)

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| 触发时间 | Job 名称 | 构建号 | 结果 | 触发者 | 备注 |

备注列由 `summary_text` 自动生成, 0 失败时显示 "✅ 同步完成 (公司: 0 失败) | 总人数 N | No changed M | 批量救回 K".

## Webhook Route 配置

### 1. 在 Hermes config.yaml 加 route

```yaml
# ~/.hermes/config.yaml
webhook_routes:
  - id: sync-user-monitor
    path: /webhooks/sync-user-monitor
    skill: jenkins-user-sync-monitor
    secret_env: HERMES_SYNC_USER_SECRET  # env 变量名, 里面是 HMAC 密钥
    platform_toolsets: [terminal, code_execution, messaging, file, skills, memory, web]
```

### 2. 把密钥加到 .env

```bash
# 跟 Jenkins PostBuildScript 里的 HERMES_SECRET 一致
HERMES_SYNC_USER_SECRET=your_r...n### 3. 重启 gateway

```bash
systemctl --user restart hermes-gateway
```

## 验证

### 1. 跑 skill 自带测试

```bash
python3 ~/.hermes/skills/devops/jenkins-user-sync-monitor/scripts/test_analyzer.py
```

**期望**: `Ran 22 tests in 0.005s OK`

### 2. 直接跑分析器 (单 build 测试)

```bash
# 需要先在 .env 配 JENKINS_URL 等
python3 ~/.hermes/skills/devops/jenkins-user-sync-monitor/scripts/sync_analyzer.py <job_name> <build_number>
# 例
python3 ~/.hermes/skills/devops/jenkins-user-sync-monitor/scripts/sync_analyzer.py sync_user_xxx 1752
```

**期望**: 输出 JSON 包含:
- `matched_failures`: 目标公司失败数
- `by_keyword`: 按失败关键词统计
- `summary_text`: 给飞书备注用的摘要

### 3. 手动触发 webhook 测试

```bash
HERMES_URL="http://127.0.0.1:8644/webhooks/sync-user-monitor"
HERMES_SECRET=*** # 跟 .env 一致

PAYLOAD='{
  "job_name": "test-sync",
  "build_number": "999",
  "build_result": "FAILURE",
  "build_url": "http://jenkins:8080/job/test-sync/999/",
  "build_user": "tester",
  "timestamp": "2026-06-13T19:30:00Z"
}'

SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$HERMES_SECRET" | sed 's/^.* //')

curl -i -X POST "$HERMES_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD"

# 期望: HTTP 200
```

## 故障排查

### Q: 误报 (No changed for 被算成失败)

检查 `analyze_failures` 逻辑: `No changed for` 不应在 `FAILURE_KEYWORDS` 里 (默认也没有).

### Q: 漏报 (真失败没算)

- 检查 `TARGET_COMPANY` 是否跟 console 里的公司名完全一致 (含空格/标点)
- 用 `python3 scripts/sync_analyzer.py <job> <build>` 直接跑, 看 JSON 输出

### Q: 飞书 99991663 (权限不足)

应用没被加为表格协作者, 或 scope 没包含 `sheets:spreadsheet`.

### Q: 多公司混合时, 只想监控一家

确保 `TARGET_COMPANY` 跟目标公司名**完全一致** (含空格/标点).

`analyze_failures` 自动过滤其他公司, 但 console 里公司名格式要稳定.

### Q: 飞书 IM 收到 `| 表格 |` 原样渲染

**飞书 IM 不支持 markdown 表格**. skill 已经规避: 用 `**加粗**` + 有序列表.

如果自己扩展, 不要用表格, 用列表 + 加粗.

## 资源

- [SKILL.md](./SKILL.md) — Skill 描述
- [README.md](./README.md) — 入口
- [CHANGELOG.md](./CHANGELOG.md) — 变更记录
- [根 INSTALL.md](../../INSTALL.md) — 通用安装
- [根 CONTRIBUTING.md](../../CONTRIBUTING.md) — 贡献流程
- [jenkins-build-monitor INSTALL.md](../jenkins-build-monitor/INSTALL.md) — 兄弟 skill, 飞书配置可参考
