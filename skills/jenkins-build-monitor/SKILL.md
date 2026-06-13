---
name: jenkins-build-monitor
description: "Jenkins 编译任务通用监控 — 接收 Jenkins PostBuildScript webhook,SUCCESS 简单通知,FAILURE 自动定位第一个失败的 sub-job,SSH 到编译服务器 git blame 报错文件定位 commit,发送企业微信 + 飞书 Sheets 结构化报告。支持多项目通用接入。"
version: 1.2.0
metadata:
  hermes:
    tags: [jenkins, ci-cd, build-failure, ssh, git-blame, compilation-error, android-build, build-server, false-positive-detection, postbuildscript]
    related_skills: [jenkins-user-sync-monitor, webhook-subscriptions]
---

# Jenkins 编译任务通用监控（v1.2.0 - 通用化版本）

> 📋 **自检卡片**
> - **Skill 版本**: `1.2.0`（2026-06-13, 通用化重写）
> - **零硬编码**: 所有 IP/Token/用户名/公司名 走 `~/.hermes/.env`
> - **路径自定位**: Python 脚本用 `Path(__file__).parent`, 不依赖绝对路径
> - **跨平台**: Hermes / OpenClaw 通用
> - **测试**: `python3 scripts/test_logic.py`（5 场景 + 5 边界, 独立可跑）
> - **关键文档**: `references/logic.py`（核心逻辑）/ `references/feishu-sheets-api.md`（飞书 API）

## 这是什么

监控任意 Jenkins 编译任务 (Android / iOS / 嵌入式 / 后端 / 前端 等所有类型), 自动:

1. 解析构建结果 (SUCCESS / FAILURE / UNSTABLE)
2. **FAILURE 误报检测** (PostBuildScript 失败 vs 真实编译失败)
3. SUCCESS: 发送简短企业微信通知 + 写入飞书 Sheets
4. FAILURE: **立即发预通知** (< 5s), 告诉用户"正在分析"
5. FAILURE: 定位失败根因 (第一个 FAILURE 的 sub-job)
6. FAILURE: SSH 到编译服务器, git blame 报错文件定位 commit
7. FAILURE: 发送企业微信 + 飞书结构化报告
8. 所有构建结果都写入飞书 Sheets (含子任务 console 关键错误行, 给 AI 训练留料)

**适用场景**:
- 任何公司 / 任何项目 / 任何语言的编译任务
- 多项目通用 (按 `J_Project` 字段路由到不同企业微信 webhook)
- 历史失败可回溯 (飞书表保存 sub-job 错误行, Jenkins 50-build FIFO 覆盖也不丢)

## 触发条件

Jenkins **任意 trigger job** 构建完成后, PostBuildScript 发 webhook → Hermes 自动执行分析.

## 关键概念

### Trigger job vs Sub-job

- **Trigger job**: Jenkins 上的"协调任务", 调用多个 sub-job 并收集结果
- **Sub-job**: 真正的编译任务, 跑在指定编译服务器 (Build Executor) 上

**示例** (Android 编译):
- Trigger: `sm68b_do_smt_trigger`
- Sub-job: `sm6650_bp` (bootloader) / `sm6650_vnd_userdebug` (vendor) / `sm6650_sys_userdebug` (system)
- Sub-job 跑在 3 台不同编译服务器 (BP_SPACE / VND_SPACE / SYS_SPACE)

### 误报 (v1.1.4 数据分析发现, v1.2.0 通用化)

**现象**: trigger 被标 FAILURE, 但所有 sub-job 实际 SUCCESS.

**根因**: PostBuildScript 里的 `curl` 失败 (webhook 投递未回 200), 触发器被设为 FAILURE.

**检测规则** (必须**两个条件同时满足**才判误报):
1. trigger `build_result == "FAILURE"`
2. 包含 `PostBuildScript` 且 `changed build result to FAILURE`
3. **且**所有 sub-job 状态为 SUCCESS

**节省**: 跳过 SSH git blame (5-15 分钟), 仍写入飞书表 (备注标 `⚠️ 误报`).

## 安装

详见 [INSTALL.md](./INSTALL.md).

快速开始:

```bash
# 1. 装 skill
cp -r skills/jenkins-build-monitor ~/.hermes/skills/devops/

# 2. 配 .env
cat >> ~/.hermes/.env <<'EOF'
JENKINS_URL=http://jenkins.your-company.com:8080
JENKINS_USER=jenkins
JENKINS_PASS=your_password
BUILD_SERVER_USER=builder
BUILD_SERVER_PASS=your_password
FEISHU_APP_ID=cli_xxxx
FEISHU_APP_SECRET=your_secret
FEISHU_SHEETS_TOKEN_BUILD=your_token
FEISHU_SHEET_ID_BUILD=your_sheet_id
FEISHU_CHAT_ID=oc_xxxx
WX_WORK_WEBHOOK_URL_GENERAL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
EOF

# 3. 装 Python 依赖
~/.hermes/venv/bin/pip install requests paramiko python-dotenv

# 4. 跑测试
python3 ~/.hermes/skills/devops/jenkins-build-monitor/scripts/test_logic.py

# 5. 配 webhook route (在 ~/.hermes/config.yaml)
# 见 INSTALL.md 步骤 5
```

## 环境变量

**所有变量必须在 `~/.hermes/.env` 配置, 详见 `.env.example`.**

| 变量 | 必填 | 用途 | 默认 |
|------|------|------|------|
| `JENKINS_URL` | ✅ | Jenkins base URL | - |
| `JENKINS_USER` | ✅ | Jenkins 认证用户 | - |
| `JENKINS_PASS` | ✅ | Jenkins 认证密码 | - |
| `BUILD_SERVER_USER` | ✅ | 编译服务器 SSH 用户 | - |
| `BUILD_SERVER_PASS` | ✅ | 编译服务器 SSH 密码 | - |
| `FEISHU_APP_ID` | ❌ | 飞书应用 ID | (不配 = 跳过飞书) |
| `FEISHU_APP_SECRET` | ❌ | 飞书应用 Secret | (不配 = 跳过飞书) |
| `FEISHU_SHEETS_TOKEN_BUILD` | ❌ | 飞书表 token (构建记录) | (不配 = 跳过表) |
| `FEISHU_SHEET_ID_BUILD` | ❌ | 飞书表 ID | (不配 = 跳过表) |
| `FEISHU_CHAT_ID` | ❌ | 飞书 chat_id (通知目标) | (不配 = 跳过通知) |
| `WX_WORK_WEBHOOK_URL_GENERAL` | ❌ | 企业微信通用 webhook | (不配 = 跳过) |
| `WX_WORK_WEBHOOK_URL_<PROJECT>` | ❌ | 项目专用 webhook (动态匹配) | (不配 = 跳过) |

> **项目专用 webhook** 用法: `WX_WORK_WEBHOOK_URL_<UPPER_PROJECT_WITH_UNDERSCORE>`, 例如项目名是 `sm68b-do`, 则 env 变量名为 `WX_WORK_WEBHOOK_URL_SM68B_DO`.

## Jenkins 配置

**配置位置**: Jenkins job → 配置 → 构建后操作 → PostBuildScript → 勾选「所有结果（Always）」

**⚠️ 参数命名规范**:
- 项目名用 `J_Project` (大写下划线), 不是 `J_PROJECT`
- 分支名用 `J_Branch`, 不是 `GIT_BRANCH`

**必须带 HMAC 签名**:

```bash
HERMES_URL="http://your-hermes-host:8644/webhooks/jenkins-monitor"
HERMES_SECRET="your-shared-secret"

PAYLOAD="{\"job_name\":\"${JOB_NAME}\",\"build_number\":\"${BUILD_NUMBER}\",\"build_result\":\"${BUILD_RESULT}\",\"build_url\":\"${BUILD_URL}\",\"build_user\":\"${BUILD_USER:-unknown}\",\"project\":\"${J_Project:-}\",\"branch\":\"${J_Branch:-}\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"

SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$HERMES_SECRET" | sed 's/^.* //')

curl -s -X POST "${HERMES_URL}" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD"
```

## Webhook 传入参数

| 参数 | 说明 | 来源 |
|------|------|------|
| `job_name` | Jenkins job 名称 | `${JOB_NAME}` |
| `build_number` | 构建号 | `${BUILD_NUMBER}` |
| `build_result` | FAILURE / SUCCESS / UNSTABLE | `${BUILD_RESULT}` |
| `build_url` | 构建 URL | `${BUILD_URL}` |
| `build_user` | 触发者 | `${BUILD_USER:-unknown}` |
| `project` | 项目名 (可选) | `${J_Project:-}` |
| `branch` | Git 分支 (可选) | `${J_Branch:-}` |
| `timestamp` | ISO 时间戳 | `$(date -u +%Y-%m-%dT%H:%M:%SZ)` |

## 完整分析流程

### 第 0 步: 取真实 trigger_time

**⚠️ webhook payload 的 `timestamp` 是 PostBuildScript 执行时间 (=构建完成时间), 不是触发时间. 必须从 Jenkins API 取真正的触发时间.**

```python
import os, urllib.request, base64, json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

auth = f"{os.environ['JENKINS_USER']}:{os.environ['JENKINS_PASS']}"
api_url = f"{os.environ['JENKINS_URL']}/job/{job_name}/{build_number}/api/json?tree=timestamp"
req = urllib.request.Request(api_url)
req.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
with urllib.request.urlopen(req, timeout=30) as resp:
    api_data = json.loads(resp.read())

ts_ms = api_data["timestamp"]
dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
# 时区: 改成你公司的时区 (示例: 北京 +8, 纽约 -5, 伦敦 0)
LOCAL_TZ_OFFSET = int(os.environ.get("LOCAL_TZ_OFFSET_HOURS", "8"))
dt_local = dt_utc + timedelta(hours=LOCAL_TZ_OFFSET)
trigger_time = dt_local.strftime("%Y-%m-%d %H:%M:%S")
```

### 第 1 步: 获取 trigger consoleText

```python
url = f"{os.environ['JENKINS_URL']}/job/{job_name}/{build_number}/consoleText"
req = urllib.request.Request(url)
req.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
with urllib.request.urlopen(req, timeout=30) as resp:
    trigger_console = resp.read().decode('utf-8', errors='replace')
```

**关键提取** (从 consoleText 直接拿, 不猜测):
- **sub-job FAILURE**: `Finished Build.*FAILURE` (取**第一个**)
- 分支名: `remotes/origin/`

**关键规则**: **第一个 FAILURE 的 sub-job 是根因**, 后续 ABORTED 是被牵连的.

### 第 1.5 步: 误报检测

```python
import sys
from pathlib import Path
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "references"))
from logic import classify_failure

classification = classify_failure(build_result, trigger_console)
# category: success | postbuild_falsealarm | real_subjob_fail | unknown
# is_falsealarm: bool
# sub_results: [(name, status), ...]
# failing_sub_jobs / successful_sub_jobs
# reason: str (给飞书备注用)
```

### 第 2 步: 获取根因 sub-job consoleText

```python
url = f"{os.environ['JENKINS_URL']}/job/{sub_job_name}/{sub_build_number}/consoleText"
req = urllib.request.Request(url)
req.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
with urllib.request.urlopen(req, timeout=30) as resp:
    sub_console = resp.read().decode('utf-8', errors='replace')
```

**从 sub_console 第一行直接提取** (不要猜 IP):
```
Building remotely on <IP> (...) in workspace <WORKSPACE_PATH>
   ^^^^^^^^^^^^^^^^ 直接用这个 IP
                   ^^^^^^^^^^^^^^^^^^^^^^^ 直接用这个 workspace 路径
```

### 第 2.5 步: 提取关键错误行 (给飞书表留料)

**背景**: Jenkins 默认 keep last 50 builds FIFO 覆盖. **必须在失败时立即把关键错误行提取出来**塞到飞书表备注列, 给未来 AI 训练/回溯留料.

```python
from logic import extract_key_error_lines

sub_console_key = extract_key_error_lines(sub_console, max_chars=500)
# 透传到第 6 步, 用 build_remark() 拼入飞书备注列
```

### 第 3 步: 从 sub-job consoleText 尾部提取编译错误

**错误模式** (内置在 `logic.py` `ERROR_PATTERNS`):
- `fatal error: 'xxx.h' file not found`
- `make: *** [...path.../File.obj] Error 1`
- `error 7000: Failed to execute command`
- `error F002: Failed to build module`
- `FileNotFoundError: ... /path/to/GeneratedFile.txt`
- `killed by signal X` / `OOM` / `No space left on device` / `Permission denied`
- `undefined reference to xxx`

**提取三个关键信息**:
1. **报错文件完整路径** (从编译日志里找 `<用户主目录>/...` 开头的路径, 或 `%WORKSPACE%` 变量展开)
2. **错误类型** (如 `fatal error: 'Uefixx.h' file not found`)
3. **行号**

**从报错文件路径反推 git root** (项目结构可能不同, 根据你的项目调整):

```python
# 示例: SM68B Android 项目, boot_images 是 .git 所在目录
# /home/ontim/BP_SPACE/SM6650_do/BP/BOOT.MXF.2.1/boot_images/boot/QcomPkg/Library/ChargerLib/ChargerLibCommon.c
# git_root = '/home/ontim/BP_SPACE/SM6650_do/BP/BOOT.MXF.2.1/boot_images'
# file_path = 'boot/QcomPkg/Library/ChargerLib/ChargerLibCommon.c'
```

**⚠️ 先判断错误类型, 再决定是否需要 git blame**:

| 错误类型 | 是否需要 git blame | 说明 |
|---|---|---|
| `fatal error: 'xxx.h' file not found` | ✅ 需要 | 头文件 typo 或缺失 |
| `make: *** Error 1` | ✅ 需要 | 编译/链接错误 |
| `error CODE: Unknown fatal error` | ✅ 需要 | 代码问题 |
| `FileNotFoundError: ... .txt/.Fv.txt` | ❌ 不需要 | 构建中间文件丢失, 是环境问题 |
| `error: failed to create ...` | ❌ 不需要 | 文件系统/权限问题 |
| `Permission denied` | ❌ 不需要 | 权限问题 |

### 第 3.5 步: 查已知根因 (内部原因库)

**在分析前先查表格, 看这个 error_type 是否已有用户预定义的内部根因.**

**通用化方法**:
- 表格 / Sheet token + ID 走 `FEISHU_SHEETS_TOKEN_KNOWN_CAUSES` / `FEISHU_SHEET_ID_KNOWN_CAUSES`
- 查 F 列 (备注), 找包含 `【内部根因】` 标记的行
- 匹配 `error_type` 字符串 (简单子串匹配)

```python
# 详见 references/feishu-sheets-api.md
```

**判断结果**:
- `use_known_cause=True`: 跳过 Step 4 (SSH git blame), 直接用已知根因
- `use_known_cause=False`: 继续 Step 4 正常分析

### 第 4 步: SSH 到编译服务器, git blame 定位 commit

**⚠️ 当 `use_known_cause=True` (第 3.5 步已找到已知根因) 时, 跳过本步.**

**⚠️ 当 `classification["is_falsealarm"] == True` (第 1.5 步判误报) 时, 也跳过本步.**

**SSH 参数**:
- 使用 Python `paramiko`, 支持密码认证
- 服务器 IP = sub-job consoleText 第一行 `Building remotely on` 后的 IP
- workspace = sub-job consoleText 第一行 `in workspace` 后的路径
- **不要猜 IP/workspace, 必须从 consoleText 取**

```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    ip,
    username=os.environ["BUILD_SERVER_USER"],
    password=os.environ["BUILD_SERVER_PASS"],
    timeout=15,
    look_for_keys=False,
)
```

**Step 4a: 验证 git root 正确性**:
```python
stdin, stdout, stderr = client.exec_command(
    f'test -d "{git_root}/.git" && echo "GIT_OK" || echo "NOT_A_REPO"'
)
```

**Step 4b: git blame 直接用报错文件路径**:
```python
stdin, stdout, stderr = client.exec_command(
    f"cd {git_root} && git blame -L {line_num},{line_num} {file_path}"
)
blame_output = stdout.read().decode().strip()
# 输出: "02422ac5e5 (wanliang.zhang 2026-02-10 09:52:44 +0800 88) #include <Uefixx.h>"
# 提取 commit hash 前 8 位: 02422ac5e5
```

**Step 4c: git show 获取 commit 详情**:
```python
cmd = f"cd {git_root} && git show {commit_hash} --format='%H%n%an%n%ae%n%ad%n%s%n%B' -s"
stdin, stdout, stderr = client.exec_command(cmd)
output = stdout.read().decode().strip()
```

### 第 5 步: 发送企业微信 Webhook 通知

```python
import requests

if build_result == "SUCCESS":
    content = f"""✅ **构建成功**

**基本信息**
- Trigger: {job_name}
- 项目: {project}
- 构建号: #{build_number}
- 结果: ✅ SUCCESS
- 触发者: {build_user}
- 时间: {trigger_time}
- Build URL: {os.environ['JENKINS_URL']}/job/{job_name}/{build_number}/"""
elif classification["is_falsealarm"]:
    n_sub = len(classification["successful_sub_jobs"])
    content = f"""⚠️ **构建误报 (PostBuildScript 失败)**

**基本信息**
- Trigger: {job_name}
- 项目: {project}
- 构建号: #{build_number}
- 触发者: {build_user}
- 触发时间: {trigger_time}
- Build URL: {os.environ['JENKINS_URL']}/job/{job_name}/{build_number}/

**说明**
trigger 被标 FAILURE 是因为 PostBuildScript 里的 curl 失败, 但实际编译已通过.
- {n_sub} 个 sub-job 全部 SUCCESS: {', '.join(classification['successful_sub_jobs'])}
- 已跳过 SSH git blame (节省 5-15 分钟)
- 仍写入飞书表, 备注标 `⚠️ 误报 (PostBuildScript)`

**如 webhook 投递持续失败**
- 检查 gateway 是否在线
- 检查 curl 调用是否在 5s 内返回"""
else:
    if use_known_cause:
        content = f"""🚨 **构建失败分析**

**基本信息**
- Trigger: {job_name}
- 项目: {project}
- 构建号: #{build_number}
- 触发者: {build_user}
- 触发时间: {trigger_time}
- Build URL: {os.environ['JENKINS_URL']}/job/{job_name}/{build_number}/

**失败范围**
{failed_list}

**编译错误**
- 报错文件: {error_file}
- 错误类型: {error_type}

**修复建议**
{fix_suggestion}"""
    else:
        content = f"""🚨 **构建失败分析**

**基本信息**
- Trigger: {job_name}
- 项目: {project}
- 构建号: #{build_number}
- 触发者: {build_user}
- 触发时间: {trigger_time}
- Build URL: {os.environ['JENKINS_URL']}/job/{job_name}/{build_number}/

**失败范围**
{failed_list}

**编译错误**
- 报错文件: {error_file}
- 错误类型: {error_type}

**根因定位**
- Commit: {commit_hash}
- 作者: {author_name} ({author_email})
- 提交时间: {commit_time}
- Commit Message: {commit_msg}

**修复建议**
{fix_suggestion}"""

payload = {"msgtype": "markdown", "markdown": {"content": content}}

# 通用 URL
general_url = os.environ.get("WX_WORK_WEBHOOK_URL_GENERAL", "")
if general_url:
    r = requests.post(general_url, json=payload, timeout=15)
    print(f"[通用] -> {r.json()}")

# 项目专用 URL
project_key = project.upper().replace("-", "_")
specific_key = f"WX_WORK_WEBHOOK_URL_{project_key}"
specific_url = os.environ.get(specific_key, "")
if specific_url:
    r = requests.post(specific_url, json=payload, timeout=15)
    print(f"[{project}] -> {r.json()}")
```

### 第 6 步: 写入飞书 Sheets

所有构建结果都写入飞书 Sheets, 用于长期记录.

**⚠️ 写入用 v2 `values_append` API** (飞书服务端自动定位末尾).

完整 API 说明见 `references/feishu-sheets-append-api.md`.

```python
import os, urllib.request, json
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

# 获取 tenant_access_token
app_id = os.environ["FEISHU_APP_ID"]
app_secret = os.environ["FEISHU_APP_SECRET"]
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=15) as resp:
    tenant_token = json.loads(resp.read()).get("tenant_access_token", "")

spreadsheet_token = os.environ["FEISHU_SHEETS_TOKEN_BUILD"]
sheet_id = os.environ["FEISHU_SHEET_ID_BUILD"]

# 构造写入数据
from logic import build_remark

remark = build_remark(
    classification,
    error_file=error_file,
    error_type=error_type,
    commit_hash=commit_hash,
    known_root_cause=known_root_cause,
    sub_console_key=sub_console_key,
)

row_values = [[
    trigger_time,
    job_name,
    f"#{build_number}",
    build_result,
    build_user,
    remark,
]]

# 用 v2 values_append 追加到末尾
payload = {
    "valueRange": {
        "range": f"{sheet_id}!A1:F1",
        "values": row_values
    }
}
req = urllib.request.Request(
    f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_append",
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tenant_token}",
    },
    method="POST"
)
with urllib.request.urlopen(req, timeout=15) as resp:
    result = json.loads(resp.read())
```

**Sheet 格式**: 触发时间 | Job 名称 | 构建号 | 结果 | 触发者 | 备注

### 第 7 步: 输出结构化分析报告 (FAILURE)

通过 `send_message` 工具发到飞书:

```python
send_message(
    target=f"feishu:{os.environ['FEISHU_CHAT_ID']}",
    message=report_content,
)
```

## 编译服务器 SSH 登录

### 已配置 SSH Key 的服务器 (免密登录)

每个用户环境不同, 请自行维护 `KNOWN_BUILD_SERVERS` 列表:

```python
# .env 追加
KNOWN_BUILD_SERVERS=192.168.1.10,192.168.1.11,192.168.1.12
```

### 新服务器接入 (SSH Key 自动配置)

```python
# 参考 scripts/setup_ssh_key.py
import os, paramiko
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

# 用户应自己生成 SSH key, 然后把这个公钥部署到新服务器
# ⚠️ 不要把 ontim@ontim 这种用户专属的公钥写进通用 skill!
# 用户运行前, 把自己机器的 ~/.ssh/id_rsa.pub 内容填到 MY_SSH_PUB_KEY 变量
def setup_ssh_key(ip, user, password, pub_key):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password, timeout=15, look_for_keys=False)
    client.exec_command("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
    client.exec_command(f"echo '{pub_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys")
    client.close()
```

## 飞书发送机制

通过 `send_message` 工具发到飞书:

```python
send_message(
    target=f"feishu:{os.environ['FEISHU_CHAT_ID']}",
    message="...",
)
```

> **⚠️ 飞书 IM 不支持 markdown 表格!** 第 5 步通知和第 7 步报告都**不用** `| 表格 |`, 改用 `**加粗**` + 有序列表. 详见 `webhook-subscriptions` skill.

## 注意事项

### Skill 维护规范

修改本 skill 后, 必须:
1. 更新 `CHANGELOG.md` 顶部
2. 更新根 `CHANGELOG.md` (仓库级)
3. 跑 `python3 scripts/test_logic.py` 确保通过
4. 提 PR / commit

### Skill 命名与拆分规范

- **必须用类级别名称**, 不能带具体项目标识
  - ✅ `jenkins-build-monitor` (通用)
  - ❌ `jenkins-sm68b-build-monitor` (绑定具体项目)
- **一个 Jenkins job (或同类 job) = 一个独立 skill**, 不能把多个不同任务混在一个 skill 里
  - ✅ `jenkins-build-monitor` (编译失败分析) + `jenkins-user-sync-monitor` (用户同步) 分立
  - ❌ `jenkins-build-failure-analysis` (合并了两个不相关任务)
- **Skill 目录名 = skill name**, 直接用 `name` 字段值 (小写、中划线分隔)

### 通用化原则 (本 skill v1.2.0 实施)

1. **零硬编码** — 所有 IP/Token/用户名/项目名 走 `~/.hermes/.env`
2. **路径自定位** — Python 脚本用 `Path(__file__).parent`, 不依赖绝对路径
3. **方法论与数据分离** — 特定项目分析结果进 `archive/`, 不进主代码
4. **跨平台兼容** — Hermes / OpenClaw 通用
5. **可独立测试** — `python3 scripts/test_logic.py` 独立跑通

### 错误处理经验

| 问题 | 解决方案 |
|------|----------|
| `git fetch` 报 `Couldn't find remote ref HEAD` | 直接用具体分支名, 如 `b/sm6650/do_25131` |
| `git log` 只有 1-2 条 | 执行 `git fetch --depth=500 origin <branch>` |
| git 命令报 `not a git repository` | git root 路径不对, 需从报错文件路径反推 `.git` 所在目录 |
| 构建失败但报错是 `FileNotFoundError` | **不是代码 commit 问题**, 无需 git blame |
| `terminal` 工具 curl/wget 超时 | 改用 `execute_code` (Python urllib) 执行 Jenkins API 调用 |
| 企业微信 webhook 在 webhook session 中超时 | 必须用 `execute_code` + Python `requests.post` |
| SSH 报 `File is not open for reading` | 确保每条命令执行后调用 `channel.recv_exit_status()` 等待完成 |
| Commit Message 是 "build error test" | **测试性质误提交**, 通知中应明确标注 |
| 写入 Sheets 后表格里出现空行错位 | 用 v2 `values_append` API, 飞书服务端定位末尾, 100% 准确 |
| 飞书表里所有构建都标 FAILURE, 但实际编过了 | 用 `classify_failure()` 检测 PostBuildScript 误报, 跳过 SSH git blame |
| 想回溯分析历史失败的错误模式, 发现 sub-job console 已不可访问 | 真失败时立即用 `extract_key_error_lines()` 提取 sub-job console 关键错误行 |

## 资源

- [references/logic.py](./references/logic.py) — 核心逻辑 (classify_failure / extract_key_error_lines / build_remark)
- [references/feishu-sheets-api.md](./references/feishu-sheets-api.md) — 飞书 Sheets API 速查
- [references/feishu-sheets-append-api.md](./references/feishu-sheets-append-api.md) — 飞书 v2 append API
- [scripts/test_logic.py](./scripts/test_logic.py) — 单测 (5 场景 + 5 边界)
- [scripts/setup_ssh_key.py](./scripts/setup_ssh_key.py) — SSH key 自动配置
- [scripts/analyze_history.py](./scripts/analyze_history.py) — 历史构建分析
- [archive/](./archive/) — 历史快照 (特定项目的一次性分析)
- [CHANGELOG.md](./CHANGELOG.md) — 变更记录
- [INSTALL.md](./INSTALL.md) — 详细安装

## 关联 Skill

- **jenkins-user-sync-monitor**: 监控用户同步任务 (本仓库另一个 skill)
- **webhook-subscriptions**: Hermes webhook 接收机制

## v1.1.4 → v1.2.0 通用化变更

| 变更 | 之前 (v1.1.4) | 现在 (v1.2.0) |
|------|----------------|----------------|
| Jenkins URL | 硬编码 `192.168.100.207` | `os.environ["JENKINS_URL"]` |
| 飞书 app_id | 硬编码 `cli_a96b359059f85cb1` | `os.environ["FEISHU_APP_ID"]` |
| 飞书 chat_id | 硬编码 `oc_44da7dfa79fffbe14c32639aecb510cc` | `os.environ["FEISHU_CHAT_ID"]` |
| 飞书表 token | 硬编码 `MZoAskdPjhFjH6tWVvCcT2QxnIe` | `os.environ["FEISHU_SHEETS_TOKEN_BUILD"]` |
| SSH 公钥 | 硬编码 `ontim@ontim` | 用户自己提供 (`.env` 注入) |
| 编译服务器 IP | 硬编码列表 | 从 sub-job consoleText 动态取 |
| 路径 | `~/.hermes/skills/devops/...` | `Path(__file__).parent` |
| 时区 | 硬编码 `+8` | `os.environ["LOCAL_TZ_OFFSET_HOURS"]` |
| 噪音模式 `SM68B_*_trigger` | 硬编码项目名 | 通用正则 `^\[<JOB_NAME_PATTERN>\]` (env 注入) |
| 测试路径 | `/tmp/jenkins-analysis` | `Path(__file__).parent / "fixtures"` |
