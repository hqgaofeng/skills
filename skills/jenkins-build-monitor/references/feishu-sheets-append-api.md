# 飞书 Sheets v2 values_append API 详解

> 通用版本 — 适用任意 skill 写飞书表, 不绑特定项目.

## 1. 为什么用 values_append 而不是 PUT

| 特性 | values_append (✅ 推荐) | PUT (❌ 不推荐) |
|------|------------------------|-----------------|
| 定位末尾 | 飞书服务端定位, 100% 准确 | 客户端算 next_row, 易错 |
| 1000 行限制 | 无 | 受 1000 行 API 限制 |
| 并发安全 | 飞书服务端处理 | 客户端有竞态 |
| 速度 | 略慢 (服务端处理) | 略快 |
| 适用场景 | 持续追加 (监控/日志) | 全量覆盖 (一次性导入) |

**结论**: 监控 / 日志类场景**永远用 values_append**.

## 2. 完整代码 (Python, 通用)

```python
import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))


def get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token"""
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read()).get("tenant_access_token", "")


def append_row(
    spreadsheet_token: str,
    sheet_id: str,
    values: list,
) -> dict:
    """追加一行到飞书表末尾

    Args:
        spreadsheet_token: 表 token (env 注入)
        sheet_id: 表 ID (从 /sheets/query 查)
        values: [[col1, col2, col3, ...], ...] 二维数组

    Returns:
        飞书响应 dict, 含 code / msg / data.tableRange
    """
    app_id = os.environ["FEISHU_APP_ID"]
    app_secret = os.environ["FEISHU_APP_SECRET"]
    tenant_token = get_tenant_token(app_id, app_secret)

    payload = {
        "valueRange": {
            "range": f"{sheet_id}!A1:A1",  # 起点不重要
            "values": values,
        }
    }
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_append",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tenant_token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


# 使用示例
if __name__ == "__main__":
    result = append_row(
        spreadsheet_token=os.environ["FEISHU_SHEETS_TOKEN_BUILD"],
        sheet_id=os.environ["FEISHU_SHEET_ID_BUILD"],
        values=[[
            "2026-06-13 19:30:00",
            "myjob",
            "#123",
            "SUCCESS",
            "zhangsan",
            "构建成功",
        ]],
    )
    if result.get("code") == 0:
        print(f"✅ 写入成功: {result['data']['tableRange']}")
    else:
        print(f"❌ 写入失败: code={result.get('code')}, msg={result.get('msg')}")
```

## 3. 写入策略

### 场景 1: 持续追加 (监控/日志) — ✅ values_append

```python
# 每个 build 完成后追加一行
append_row(token, sheet_id, [[
    trigger_time, job_name, f"#{build_number}",
    build_result, build_user, remark,
]])
```

### 场景 2: 批量导入 (一次性) — 用 PUT 覆盖

```python
# 一次性导入历史数据, 覆盖整个表
# ⚠️ 危险: 会清空现有数据
put_values(token, sheet_id, "A1:F1000", all_rows)
```

### 场景 3: 删行 — V2 飞书没有原生 API

详见 `feishu-sheets-api.md` 第 7 节.

## 4. 性能优化

### 批量追加

一次 append 多行比多次 append 一行快 5-10 倍:

```python
# ❌ 慢
for row in rows:
    append_row(token, sheet_id, [row])

# ✅ 快
append_row(token, sheet_id, rows)  # rows = [[r1], [r2], ...]
```

**限制**: 单次最多 5000 行 (飞书服务端限制).

### 异步写入 (高级)

用 `concurrent.futures.ThreadPoolExecutor` 并发写:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(append_row, token, sheet_id, [row])
        for row in rows
    ]
    # 注意: 飞书默认限速, 太快会 99991400
```

**注意**: 飞书默认限速, 并发太高会被 ban. 建议每请求间隔 100ms+.

## 5. 错误处理

### 完整错误码表

| code | 含义 | 解决 |
|------|------|------|
| 0 | 成功 | - |
| 99991663 | 权限不足 | 检查 app 权限 |
| 99991668 | app secret 错 | 检查 env |
| 99991672 | tenant token 失效 | 重新获取 |
| 1254045 | sheet_id 不存在 | 用 query API 查真值 |
| 1254000 | range 格式错 | 检查 `A1:F1` |
| 99991400 | 限流 | 加 sleep 降速 |
| 99991429 | 频率超限 | 同上 |

### 重试逻辑

```python
import time

def append_with_retry(token, sheet_id, values, max_retries=3):
    for i in range(max_retries):
        result = append_row(token, sheet_id, values)
        code = result.get("code", -1)
        if code == 0:
            return result
        elif code == 99991400 or code == 99991429:
            # 限流, 等 1s 重试
            time.sleep(1)
        else:
            # 其他错误, 不重试
            return result
    return result
```

## 6. 真实使用案例 (跨 skill)

**jenkins-build-monitor**: 写构建记录 (6 列: 时间/Job/号/结果/触发者/备注)
**jenkins-user-sync-monitor**: 写用户同步记录 (6 列: 时间/Job/号/结果/触发者/备注)
**feishu-sheets-writer** (未来): 通用任意表写入

**共性**: 6 列日志格式, 都用 `FEISHU_SHEETS_TOKEN_<用途>` + `FEISHU_SHEET_ID_<用途>` 区分表.

## 7. 调试技巧

### 临时打印请求详情

```python
# 加 debug, 看实际请求
import http.client
http.client.HTTPConnection.debuglevel = 1
```

### 用 curl 测试

```bash
TOKEN="t-xxx"  # tenant_access_token
SPREADSHEET="shtcnxxxxx"
SHEET_ID="6cabb7"

curl -X POST "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/$SPREADSHEET/values_append" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "valueRange": {
      "range": "'$SHEET_ID'!A1:F1",
      "values": [["test", "row", "from", "curl", "test", "ok"]]
    }
  }'
```

### 看写入后 range

```json
{
  "code": 0,
  "data": {
    "tableRange": "6cabb7!A110:F110",  // ← 写到了第 110 行
    "updates": {
      "spreadsheetToken": "shtcnxxxxx",
      "updatedRange": "6cabb7!A110:F110",
      "updatedRows": 1,
      "updatedColumns": 6,
      "updatedCells": 6
    }
  }
}
```

## 8. 通用化 ENV 变量约定

```bash
# ~/.hermes/.env 追加

# === 飞书应用 (共用一份) ===
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=***
# === 任意 skill 用的表 (按用途, 不用项目名) ===
FEISHU_SHEETS_TOKEN_<PURPOSE>=<spreadsheet_token>
FEISHU_SHEET_ID_<PURPOSE>=<sheet_id>

# 例:
FEISHU_SHEETS_TOKEN_BUILD=***
FEISHU_SHEET_ID_BUILD=***
FEISHU_SHEETS_TOKEN_SYNC=***
FEISHU_SHEET_ID_SYNC=***
```

## 资源

- [飞书 v2 values_append 官方文档](https://open.feishu.cn/document/server-docs/docs/sheets-v2/operation/append-data)
- [feishu-sheets-api.md](./feishu-sheets-api.md) — 完整 Sheets API 速查
