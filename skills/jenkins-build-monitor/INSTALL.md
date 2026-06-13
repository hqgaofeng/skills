# 安装指南 - jenkins-build-monitor

## 📋 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [环境变量配置](#环境变量配置)
- [Jenkins 配置](#jenkins-配置)
- [飞书配置 (可选)](#飞书配置-可选)
- [企业微信配置 (可选)](#企业微信配置-可选)
- [SSH 编译服务器配置](#ssh-编译服务器配置)
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
| Jenkins | 任意版本 | 编译任务 |
| Jenkins PostBuildScript 插件 | 任意版本 | 触发 webhook |

### Python 依赖

```
requests >= 2.28
paramiko >= 2.10
python-dotenv >= 0.20
```

## 安装步骤

### 1. 部署 skill

```bash
# 从 hqgaofeng/skills 仓库 clone
git clone https://github.com/hqgaofeng/skills.git /tmp/skills-archive
cp -r /tmp/skills-archive/skills/jenkins-build-monitor ~/.hermes/skills/devops/
rm -rf /tmp/skills-archive
```

或直接下载 tarball:

```bash
wget https://github.com/hqgaofeng/skills/releases/download/v1.2.0/jenkins-build-monitor-v1.2.0.tar.gz
tar -xzf jenkins-build-monitor-v1.2.0.tar.gz -C ~/.hermes/skills/devops/
```

### 2. 装 Python 依赖

```bash
# 推荐: 装到 hermes 自带 venv
~/.hermes/venv/bin/pip install requests paramiko python-dotenv

# 或全局装
pip install requests paramiko python-dotenv
```

### 3. 配环境变量

```bash
# 复制示例
cp ~/.hermes/skills/devops/jenkins-build-monitor/.env.example ~/.hermes/.env
# 然后编辑 ~/.hermes/.env 填入真实值
```

**所有变量都在 `.env.example` 列出, 详见下节.**

## 环境变量配置

**所有变量必须在 `~/.hermes/.env` 配置**.

| 变量 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `JENKINS_URL` | ✅ | Jenkins base URL | `http://jenkins:8080` |
| `JENKINS_USER` | ✅ | Jenkins 认证用户 | `jenkins` |
| `JENKINS_PASS` | ✅ | Jenkins 认证密码 | - |
| `BUILD_SERVER_USER` | ✅ | 编译服务器 SSH 用户 | `builder` |
| `BUILD_SERVER_PASS` | ✅ | 编译服务器 SSH 密码 | - |
| `BUILD_SERVER_PASS_ALT` | ❌ | 备用密码 (优先用) | - |
| `MY_SSH_PUB_KEY` | ❌ | 你的 SSH 公钥 (新服务器配置用) | `ssh-rsa AAAAB3...` |
| `LOCAL_TZ_OFFSET_HOURS` | ❌ | 时区偏移, 默认 8 (北京) | `8` / `-5` / `0` |
| `JOB_NAME_PATTERN` | ❌ | 自定义噪音正则 (多选用 \| 分隔) | `^\[MY_\w+\]` |
| `FEISHU_APP_ID` | ❌ | 飞书应用 ID | `cli_xxxx` |
| `FEISHU_APP_SECRET` | ❌ | 飞书应用 Secret | - |
| `FEISHU_SHEETS_TOKEN_BUILD` | ❌ | 飞书表 token (构建记录) | - |
| `FEISHU_SHEET_ID_BUILD` | ❌ | 飞书表 ID | - |
| `FEISHU_CHAT_ID` | ❌ | 飞书 chat_id (通知目标) | `oc_xxxx` |
| `WX_WORK_WEBHOOK_URL_GENERAL` | ❌ | 企业微信通用 webhook | - |
| `WX_WORK_WEBHOOK_URL_<PROJECT>` | ❌ | 项目专用 webhook (动态匹配) | - |
| `TARGET_JOBS` | ❌ | analyze_history.py 用, 逗号分隔 | `myapp-prod,myapp-staging` |
| `ANALYZE_WINDOW_SIZE` | ❌ | analyze_history.py 用, 默认 100 | `100` |
| `WORKSPACE_GIT_RULES` | ❌ | git root 推断规则, 格式 `<prefix>=<git_subdir>;` | - |

**变量命名规范**:
- `FEISHU_SHEETS_TOKEN_<PURPOSE>`: 按用途, 不用项目名
- `WX_WORK_WEBHOOK_URL_<UPPER_PROJECT_WITH_UNDERSCORE>`: 项目专用

**避免**:
- ❌ `JENKINS_SM68B_URL` (项目名)
- ❌ `MY_FEISHU_TOKEN` (公司前缀)
- ❌ 硬编码在 skill 里 (一切走 env)

## Jenkins 配置

### 1. 装 PostBuildScript 插件

**Jenkins → Manage Jenkins → Manage Plugins → Available → 搜 "PostBuildScript" → Install**

### 2. 配置 trigger job

**Jenkins → 你的 trigger job → 配置 → 构建后操作 → Add post-build step → PostBuildScript**

勾选 "Always" (无论成功失败都触发).

在 "Script" 框填:

```bash
#!/bin/bash

# === 配置 ===
HERMES_URL="http://your-hermes-host:8644/webhooks/jenkins-monitor"  # 改: 你 Hermes gateway 地址
HERMES_SECRET="your_shared_secret_with_hermes"  # 改: 你定的 HMAC 密钥 (跟 ~/.hermes/config.yaml 对齐)

# === 参数 ===
# J_Project 和 J_Branch 必须在 Jenkins job 里定义为构建参数
# 例: 在 "参数化构建过程" 里加 "J_Project" (字符串) 和 "J_Branch" (字符串)

PAYLOAD=$(cat <<EOF
{
  "job_name": "${JOB_NAME}",
  "build_number": "${BUILD_NUMBER}",
  "build_result": "${BUILD_RESULT}",
  "build_url": "${BUILD_URL}",
  "build_user": "${BUILD_USER:-unknown}",
  "project": "${J_Project:-}",
  "branch": "${J_Branch:-}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)

# === HMAC 签名 ===
SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$HERMES_SECRET" | sed 's/^.* //')

# === 发 webhook ===
curl -s -X POST "${HERMES_URL}" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD"

echo "Webhook sent to ${HERMES_URL}"
```

### 3. 参数配置 (重要!)

**⚠️ 参数名注意**:
- 项目名用 `J_Project` (大写下划线)
- 分支名用 `J_Branch` (大写下划线)
- 不要用 `J_PROJECT` / `GIT_BRANCH` (大小写敏感)

配置方法:
- Jenkins job → 配置 → "参数化构建过程" → 勾选 → 添加参数 → "String Parameter"
- 名称: `J_Project`, 默认值: (空) 或你的项目名
- 名称: `J_Branch`, 默认值: `main` 或你的分支

## 飞书配置 (可选)

如果**不用飞书**, 跳过这节. skill 会自动跳过飞书相关操作 (写表 / 发通知).

### 1. 创建飞书应用

1. 飞书开放平台: https://open.feishu.cn/app
2. 创建企业自建应用
3. 权限管理 → 开启:
   - `sheets:spreadsheet` (读写表格)
   - `im:message` (发消息)
4. 版本管理 → 创建版本 → 申请发布 (需管理员审核)

### 2. 创建飞书表

1. 飞书 → 新建电子表格
2. 标题: "Jenkins 构建记录" (或你喜欢的)
3. 表头 (第 1 行):
   - A: 触发时间
   - B: Job 名称
   - C: 构建号
   - D: 结果
   - E: 触发者
   - F: 备注
4. URL 里 `shtcnxxxxx` 段是 `spreadsheet_token`
5. 调 API 查 `sheet_id`:
   ```bash
   curl -H "Authorization: Bearer <tenant_token>" \
     "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/shtcnxxxxx/sheets/query"
   ```
   返回的 `sheets[0].sheet_id` (数字字符串) 是真值

### 3. 添加应用到表格

1. 飞书表 → 右上角 "分享" → 添加协作者
2. 搜你的应用名, 添加为 "可编辑"

### 4. 填到 .env

```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
FEISHU_SHEETS_TOKEN_BUILD=shtcnxxxxxxxxxxxxxxx
FEISHU_SHEET_ID_BUILD=6cabb7
FEISHU_CHAT_ID=oc_xxxxxxxxxxxxxxxxxxxxxxxx
```

## 企业微信配置 (可选)

### 1. 创建群机器人

1. 企业微信 → 群 → 群设置 → 群机器人 → 添加
2. 复制 webhook URL (形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx`)

### 2. 填到 .env

```bash
# 通用 (所有项目都发)
WX_WORK_WEBHOOK_URL_GENERAL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx

# 项目专用 (可选, 按 project 字段匹配)
# 项目名 "sm68b-do" → 变量名 "WX_WORK_WEBHOOK_URL_SM68B_DO"
WX_WORK_WEBHOOK_URL_SM68B_DO=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=yyyyy
```

**变量名规则**: `WX_WORK_WEBHOOK_URL_<UPPER_PROJECT_WITH_UNDERSCORE>`, 大写 + 下划线.

## SSH 编译服务器配置

### 1. 生成 SSH key

```bash
# 如果你还没有 SSH key
ssh-keygen -t rsa -b 4096 -C "your.email@company.com"
# 默认存在 ~/.ssh/id_rsa, 密码留空
```

### 2. 把公钥加到编译服务器

**手动方式** (一次性):

```bash
# 把你的公钥加到编译服务器
ssh-copy-id -i ~/.ssh/id_rsa.pub user@build-server
```

**自动方式** (skill 自带脚本):

```bash
# 把公钥填到 .env
MY_SSH_PUB_KEY="$(cat ~/.ssh/id_rsa.pub)"

# 跑 skill 的 setup_ssh_key.py
python3 ~/.hermes/skills/devops/jenkins-build-monitor/scripts/setup_ssh_key.py 192.168.1.10
```

### 3. 把公钥填到 .env

```bash
MY_SSH_PUB_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAA... user@host"
```

## Webhook Route 配置

### 1. 在 Hermes config.yaml 加 route

```yaml
# ~/.hermes/config.yaml
webhook_routes:
  - id: jenkins-monitor
    path: /webhooks/jenkins-monitor
    skill: jenkins-build-monitor
    secret_env: HERMES_JENKINS_SECRET  # env 变量名, 里面是 HMAC 密钥
    platform_toolsets: [terminal, code_execution, messaging, file, skills, memory, web]
```

### 2. 把密钥加到 .env

```bash
# 跟 Jenkins PostBuildScript 里的 HERMES_SECRET 一致
HERMES_JENKINS_SECRET=your_random_long_string
```

### 3. 重启 gateway

```bash
systemctl --user restart hermes-gateway
# 或
supervisorctl restart hermes-gateway
```

## 验证

### 1. 跑 skill 自带测试

```bash
python3 ~/.hermes/skills/devops/jenkins-build-monitor/scripts/test_logic.py
```

**期望**: `Ran 26 tests in 0.006s OK`

### 2. 手动触发 webhook 测试

```bash
HERMES_URL="http://127.0.0.1:8644/webhooks/jenkins-monitor"
HERMES_SECRET="your_secret"  # 跟 ~/.hermes/.env 一致

PAYLOAD='{
  "job_name": "test-job",
  "build_number": "999",
  "build_result": "FAILURE",
  "build_url": "http://jenkins:8080/job/test-job/999/",
  "build_user": "tester",
  "project": "smoke-test",
  "branch": "main",
  "timestamp": "2026-06-13T19:30:00Z"
}'

SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$HERMES_SECRET" | sed 's/^.* //')

curl -i -X POST "$HERMES_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD"

# 期望: HTTP/1.1 200 OK
```

### 3. 验证 session 跑了工具

```bash
# 看 hermes 是否有 session 跑这个 webhook
python3 -c "
import sqlite3
con = sqlite3.connect('/home/ontim/.hermes/state.db')
cur = con.cursor()
res = cur.execute(\"SELECT id, tool_call_count, api_call_count, started_at FROM sessions WHERE source='webhook' ORDER BY started_at DESC LIMIT 3\").fetchall()
for r in res: print(r)
"
# 期望: tool_call_count >= 1 (说明有工具被调用, 不是空跑)
```

## 故障排查

### Q: webhook 200 OK 但没通知

1. **检查 platform_toolsets**:
   ```yaml
   platform_toolsets: [terminal, code_execution, messaging, file, skills, memory, web]
   ```
   `code_execution` 和 `messaging` 必须有.

2. **检查 skill 是否加载**:
   ```bash
   ls ~/.hermes/skills/devops/jenkins-build-monitor/SKILL.md
   ```

3. **看 gateway log**:
   ```bash
   tail -100 ~/.hermes/logs/gateway.log
   # 搜 "jenkins-monitor" 或 "skill"
   ```

### Q: 401 Unauthorized from Jenkins

- `JENKINS_USER` / `JENKINS_PASS` 错
- 用 curl 测:
  ```bash
  curl -u "$JENKINS_USER:$JENKINS_PASS" "$JENKINS_URL/api/json"
  ```

### Q: SSH 登录失败

- `BUILD_SERVER_USER` / `BUILD_SERVER_PASS` 错
- 编译服务器没开 22 端口
- SSH key 没部署

### Q: 飞书报 99991663 (权限不足)

- 应用没被加为表格协作者
- 应用 scope 没包含 `sheets:spreadsheet`

### Q: 测试报错 `ModuleNotFoundError`

```bash
# 装依赖到 hermes venv
~/.hermes/venv/bin/pip install requests paramiko python-dotenv
```

### Q: 误报判定不准确

调整 `JOB_NAME_PATTERN`, 例如:

```bash
# 只把 PostBuildScript 里特定的 trigger 标记为噪音
JOB_NAME_PATTERN=^\[MYPROJECT_\w+_trigger\]
```

## 资源

- [SKILL.md](./SKILL.md) — Skill 描述
- [README.md](./README.md) — 入口
- [CHANGELOG.md](./CHANGELOG.md) — 变更记录
- [根 INSTALL.md](../../INSTALL.md) — 通用安装
- [根 CONTRIBUTING.md](../../CONTRIBUTING.md) — 贡献流程
