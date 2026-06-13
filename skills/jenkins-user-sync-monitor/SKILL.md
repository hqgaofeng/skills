---
name: jenkins-user-sync-monitor
description: "Jenkins 用户同步任务通用监控 — 接收 Jenkins PostBuildScript webhook, 分析 consoleText 提取目标公司失败记录, 飞书通知 + 飞书 Sheets 记录。支持任意公司接入, 通用失败关键词 + 公司名走环境变量。"
version: 1.1.0
metadata:
  hermes:
    tags: [jenkins, user-sync, feishu-notification, console-analysis, multi-company]
    related_skills: [jenkins-build-monitor, webhook-subscriptions]
---

# Jenkins 用户同步任务通用监控（v1.1.0 - 通用化版本）

> 📋 **自检卡片**
> - **Skill 版本**: `1.1.0`（2026-06-13, 通用化重写）
> - **零硬编码**: 公司名 / 失败关键词 / Jenkins URL 走 `~/.hermes/.env`
> - **目标公司**: `TARGET_COMPANY` env（用户部署时改）
> - **失败关键词**: `FAILURE_KEYWORDS` env（逗号分隔, 默认常用关键词）
> - **跨平台**: Hermes / OpenClaw 通用
> - **测试**: `python3 scripts/test_analyzer.py`（22 个测试, 5 场景 + 5 边界, 独立可跑）

## 这是什么

监控任意 Jenkins 用户同步任务, 自动:

1. 接收 Jenkins PostBuildScript webhook
2. 拉取 consoleText (完整日志)
3. **通用解析 USER INFO 行** (支持 8/9/10/11/12 token 格式, 通用算法不绑特定 token 数)
4. 提取**目标公司**的失败记录 (公司名走 env 变量)
5. **智能排除 "No changed for"** 状态 (该状态是成功, 不是失败)
6. **智能排除"单用户失败 + 批量救回"** 假阳性 (200 字符内有"创建用户成功"就不算失败)
7. 飞书通知 (>= 5 条汇总, < 5 条逐条列, 0 条静默)
8. 飞书 Sheets 记录 (独立表, 用 `values_append` API)

**适用场景**:
- 任何公司 / 任何用户同步 Jenkins job
- 多公司混合: 只统计目标公司, 不混其他公司
- "No changed for" 是成功状态 (不是失败), LLM 容易误判

## 与 jenkins-build-monitor 的区别

|  | jenkins-build-monitor | jenkins-user-sync-monitor |
|---|---|---|
| 监控目标 | 编译日志 (Android/iOS/...) | 用户同步 consoleText |
| 失败关键词 | `fatal error`, `make: ***`, etc. | `创建用户失败`, `invalid phone number`, etc. (env 注入) |
| Git blame | ✅ 需要 (定位 commit) | ❌ 不需要 |
| SSH | ✅ 需要 | ❌ 不需要 |
| 目标过滤 | 无 (单项目) | ✅ 按公司名过滤 (env 注入) |
| 飞书表 | 构建记录 | 同步记录 (独立表) |

## 关键概念

### "No changed for [用户名]" 不是失败

**LLM 误判陷阱**: "No changed for 张三" 表示该用户**已存在且状态一致**, **无需同步**, 是**成功状态**, 不是失败.

**示例**:
```
USER INFO:  张三 13800138000 zhang@testco.com 10001 2024-01-01 软件部 软件 TestCo 1/15531
No changed for 张三 13800138000 zhang@testco.com 10001 2024-01-01 软件部 软件 TestCo
```

**正确理解**: No changed = 同步成功, 不应发失败通知.

### "单用户失败 + 批量救回" 不是失败

**陷阱**: 出现 `单用户方式创建失败` 时, 不要直接判定为失败. 必须看其后 200 字符内是否有 `创建用户成功`.

**示例**:
```
单用户方式创建失败，用批量方式创建用户
enterpriseMail不符合规范
创建用户成功          ← 批量方式成功了, 不算失败
```

### 通用解析 (不按 token 数硬切)

**实测 USER INFO 行有 4 种 token 数** (按出现频率):
- 9-token (标准): `姓名 手机号 邮箱 工号 入职日期 部门 领域 公司 N/M`
- 10-token (部门名含空格): `NT PDT部 PDT ...` 拆成 2 个 token
- 11-token (姓名/手机号含空格): `Vishal Kumar Sharma 18664041471`
- 8-token (旧格式, 无 email): `15991641654 - 10285752 ...` 手机号和工号间是 dash

**通用规则 (v1.0.6 实测)**:
- 最后一个 `N/M` 格式 token (e.g. `1474/15237`) 之前是公司名
- 公司 = `tokens[-2]`
- **不按 token 数硬切**, 用倒数法

### 公司识别 (v1.0.6 关键修正)

**USER INFO 行**: 公司 = `tokens[-2]` (最后 N/M 之前)

**ipn (invalid phone number) 行**: 公司 = `tokens[-1]` (行末最后一个 token)

**两种行格式不同, 用不同方法解析**.

## 触发条件

Jenkins **任意用户同步 job** 构建完成后, PostBuildScript 发 webhook → Hermes 自动执行分析.

## 环境变量

**所有变量在 `~/.hermes/.env` 配置, 详见 `.env.example`.**

| 变量 | 必填 | 用途 | 默认 |
|------|------|------|------|
| `JENKINS_URL` | ✅ | Jenkins base URL | - |
| `JENKINS_USER` | ✅ | Jenkins 认证用户 | - |
| `JENKINS_PASS` | ✅ | Jenkins 认证密码 | - |
| `TARGET_COMPANY` | ✅ | 目标公司名 (要监控哪个公司) | `目标公司` |
| `FAILURE_KEYWORDS` | ❌ | 失败关键词 (逗号分隔) | `创建用户失败,单用户方式创建失败,invalid phone number for` |
| `LOCAL_TZ_OFFSET_HOURS` | ❌ | 时区偏移, 默认 8 (北京) | `8` |
| `FEISHU_APP_ID` | ❌ | 飞书应用 ID | (不配 = 跳过飞书) |
| `FEISHU_APP_SECRET` | ❌ | 飞书应用 Secret | (不配 = 跳过飞书) |
| `FEISHU_SHEETS_TOKEN_SYNC` | ❌ | 飞书表 token (同步记录) | (不配 = 跳过表) |
| `FEISHU_SHEET_ID_SYNC` | ❌ | 飞书表 ID | (不配 = 跳过表) |
| `FEISHU_CHAT_ID` | ❌ | 飞书 chat_id (通知目标) | (不配 = 跳过通知) |

## Jenkins 配置

**配置位置**: Jenkins job → 配置 → 构建后操作 → PostBuildScript → 勾选「所有结果（Always）」

**必须带 HMAC 签名**:

```bash
HERMES_URL="http://your-hermes-host:8644/webhooks/sync-user-monitor"
HERMES_SECRET="*** -u +%Y-%m-%dT%H:%M:%SZ)\"}"

SIGNATURE=$(printf '%s' "$PAYLOAD" | openssl dgst -sha256 -hmac "$HERMES_SECRET" | sed 's/^.* //')

curl -s -X POST "${HERMES_URL}" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=${SIGNATURE}" \
  -d "$PAYLOAD"
```

## 执行流程

### 第 0 步: 取真实 trigger_time

**⚠️ webhook payload 的 `timestamp` 是 PostBuildScript 执行时间 (=构建完成时间), 不是触发时间.**

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
LOCAL_TZ_OFFSET_HOURS = int(os.environ.get("LOCAL_TZ_OFFSET_HOURS", "8"))
dt_local = dt_utc + timedelta(hours=LOCAL_TZ_OFFSET_HOURS)
trigger_time = dt_local.strftime("%Y-%m-%d %H:%M:%S")
```

### 第 1 步: 获取 consoleText

```python
url = f"{os.environ['JENKINS_URL']}/job/{job_name}/{build_number}/consoleText"
req = urllib.request.Request(url)
req.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
with urllib.request.urlopen(req, timeout=60) as resp:
    console = resp.read().decode('utf-8', errors='replace')
```

### 第 2 步: 分析失败记录

**通用化分析器**: `scripts/sync_analyzer.py` 内置, 可独立调用.

```python
import sys
from pathlib import Path
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
from sync_analyzer import analyze_failures, fetch_trigger_time, fetch_console

trigger_time = fetch_trigger_time(job_name, build_number)
console = fetch_console(job_name, build_number)

result = analyze_failures(
    console,
    target_company=os.environ["TARGET_COMPANY"],
)
# result 包含: matched_failures, total_failures, by_keyword, samples, summary_text
```

**分析规则**:
1. 按 `FAILURE_KEYWORDS` (env 注入) 找所有失败行
2. 每个失败行找最近的 USER INFO 提取公司
3. 排除: 公司不匹配目标
4. 排除: 批量救回 (200 字符内有"创建用户成功")
5. 按关键词统计, 生成 `summary_text`

**判断规则表**:

| 关键词 | 含义 | 是否计入失败 |
|--------|------|---------------|
| `创建用户失败` | 用户创建失败 | ✅ 失败 |
| `单用户方式创建失败` | 单用户失败 (需确认后续无"创建用户成功") | ✅ 失败 (需排除批量救回) |
| `invalid phone number for` | 手机号格式不规范 | ✅ 失败 |
| `No changed for [用户名]` | 该用户已存在且状态一致 | ❌ 成功, 不计失败 |

### 第 3 步: 发送飞书通知

**阈值规则** (v1.0.8):
- 失败 >= 5 条: 汇总格式
- 失败 < 5 条: 逐条列出
- 失败 0 条: **静默不通知** (Sheet 仍写入)

**汇总格式 (>= 5 条)**:

```
🔴 **<job_name> 用户同步异常**

**基本信息**
- 构建结果: <build_result>
- 构建号: #<build_number>
- 触发时间: <trigger_time>
- 失败条数: N 条 (仅 <TARGET_COMPANY>)
- Build URL: <build_url>

**失败类型分布**
- <keyword1>: N 条
- <keyword2>: M 条

**代表性示例 (前 5 条)**
1. 姓名 (手机号, 部门) - 失败类型
2. ...

**全部失败用户 (共 N 条)**
1. 姓名 (手机号, 部门) - 失败类型
2. ...
```

**逐条列出 (< 5 条)**: 类似但只有"失败详情"段, 无汇总段.

**静默 (0 条)**: 不发通知, 但 Sheet 仍写.

> **⚠️ 飞书 IM 不支持 markdown 表格!** 用 `**加粗**` + 有序列表 (`1.` / `2.`).

### 第 4 步: 写入飞书 Sheets

**用 v2 `values_append` API** (飞书服务端自动定位末尾):

```python
# 详见 references/feishu-sheets-append-api.md (从 jenkins-build-monitor 复用)
# 区别: 表用 FEISHU_SHEETS_TOKEN_SYNC / FEISHU_SHEET_ID_SYNC
```

**Sheet 格式**: 触发时间 | Job 名称 | 构建号 | 结果 | 触发者 | 备注 (summary_text)

## 注意事项

### "No changed for" 不是失败

详见 [关键概念](#关键概念).

### 手机号格式不规范

`invalid phone number for` 常见情况:
- 末尾有多余标点: `19209366542.` / `15235506929,` / `18209549476 |`
- 中间有横杠: `1370-0276-159`
- 手机号长度不对

### console 日志格式导致漏检 (v1.0.6 修正)

**v1.0.5 之前**: 误判 ipn 行没有公司名
**v1.0.6 修正**: ipn 行**行末最后一个 token 就是公司名**, 直接 `tokens[-1]`.

**通用解析策略**: 永远用 `tokens[-2]` (USER INFO) 或 `tokens[-1]` (ipn), **不要按 9-token 索引硬切**.

## 支持文件

- **分析脚本**: `scripts/sync_analyzer.py` — 通用化分析器
- **测试**: `scripts/test_analyzer.py` — 22 个测试, 5 场景 + 5 边界
- **Console 结构参考**: `references/sync-console-structure.md` — 通用方法论
- **监控配置参考**: `references/sync-monitor.md` — webhook / PostBuildScript

## 关联 Skill

- **jenkins-build-monitor**: 编译任务监控 (本仓库另一个 skill)
- **webhook-subscriptions**: Hermes webhook 接收机制

## v1.0.x → v1.1.0 通用化变更

| 变更 | v1.0.9 (旧) | v1.1.0 (新) |
|------|--------------|--------------|
| Jenkins URL | 硬编码 `192.168.100.215` | `JENKINS_URL` env |
| Jenkins 认证 | `JENKINS215_USER=feng.gao` 硬编码密码 | 通用 `JENKINS_USER`/`JENKINS_PASS` env |
| 飞书 app_id | 硬编码 `cli_a96b359059f85cb1` | `FEISHU_APP_ID` env |
| 飞书 chat_id | 硬编码 `oc_44da7dfa79fffbe14c32639aecb510cc` | `FEISHU_CHAT_ID` env |
| 飞书表 token | 硬编码 `VfzCsSuTPhSIHTtZ2tFcHOJSnDd` | `FEISHU_SHEETS_TOKEN_SYNC` env |
| 飞书表 ID | 硬编码 `eb386d` | `FEISHU_SHEET_ID_SYNC` env |
| 目标公司 | 硬编码 `西安中诺通讯有限公司` | `TARGET_COMPANY` env |
| 失败关键词 | 代码里硬编码 3 个 | `FAILURE_KEYWORDS` env (逗号分隔) |
| 时区 | 硬编码 `+8` | `LOCAL_TZ_OFFSET_HOURS` env |
| 测试数据 | 真实生产 console (含 chino-e 邮箱) | 通用 mock 数据 (testco.com) |
| 测试路径 | 内嵌在 sync_user_sxz_analyzer.py | 独立 test_analyzer.py |

**核心原则**: **零硬编码** — 任何公司名 / IP / Token / 用户名 **必须** 走环境变量.
