# 飞书 Sheets API 速查 (v1.2.0 通用化)

> 适用于 OpenAPI 调用飞书 Sheets V2 / V3 接口
> 通用化: 去除所有具体 token/ID, 用 env 变量注入

## 1. 获取 tenant_access_token

**V1 接口**, 通用, 任何飞书应用都用这个:

```bash
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
Content-Type: application/json

{
  "app_id": "<FEISHU_APP_ID>",
  "app_secret": "<FEISHU_APP_SECRET>"
}
```

响应:

```json
{
  "code": 0,
  "msg": "ok",
  "tenant_access_token": "t-xxx",
  "expire": 7200
}
```

**代码示例** (Python, 通用):

```python
import os, urllib.request, json
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

app_id = os.environ["FEISHU_APP_ID"]
app_secret = os.environ["FEISHU_APP_SECRET"]

req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=15) as resp:
    tenant_token = json.loads(resp.read()).get("tenant_access_token", "")
```

**注意**:
- token 有效期 2 小时, 频繁调用要缓存
- app_id 形如 `cli_xxxxx`
- app_secret 在飞书开发者后台查看

## 2. 创建表格 (V3)

```bash
POST https://open.feishu.cn/open-apis/sheets/v3/spreadsheets
Authorization: Bearer <tenant_access_token>
Content-Type: application/json

{
  "title": "构建记录表"
}
```

响应:

```json
{
  "code": 0,
  "data": {
    "spreadsheet": {
      "spreadsheet_token": "shtcnxxxxxx",
      "title": "构建记录表",
      "url": "https://xxx.feishu.cn/sheets/shtcnxxxxxx"
    }
  }
}
```

## 3. 查 sheet_id (V3)

**⚠️ 重要**: `sheet_id` 不是 "Sheet1" 也不是 "0", 而是数字字符串, 必须查 API:

```bash
GET https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/<spreadsheet_token>/sheets/query
Authorization: Bearer <tenant_access_token>
```

响应:

```json
{
  "code": 0,
  "data": {
    "sheets": [
      {
        "sheet_id": "6cabb7",  // ← 这才是真值
        "title": "Sheet1",
        "index": 0
      }
    ]
  }
}
```

## 4. 读数据 (V2)

```bash
GET https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/<spreadsheet_token>/values/<sheet_id>!A1:F1000
Authorization: Bearer <tenant_access_token>
```

**⚠️ 限制 1000 行**, 超出要分页.

### 分页读全表

```python
all_values = []
page_size = 1000
offset = 1
while True:
    end = offset + page_size - 1
    req = urllib.request.Request(
        f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/values/{sheet_id}!A{offset}:F{end}",
        headers={"Authorization": f"Bearer {tenant_token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    page = data.get("data", {}).get("valueRange", {}).get("values", [])
    if not page:
        break
    all_values.extend(page)
    if len(page) < page_size:
        break
    offset += page_size
```

## 5. 写数据 (V2 values_append - 推荐)

**✅ 推荐**: 用 v2 `values_append` API, 飞书服务端自动定位末尾空行, 100% 准确无 1000 行限制.

```bash
POST https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/<spreadsheet_token>/values_append
Authorization: Bearer <tenant_access_token>
Content-Type: application/json

{
  "valueRange": {
    "range": "<sheet_id>!A1:F1",  // 起点不重要, append 会自动找末尾
    "values": [
      ["2026-06-13 19:30:00", "myjob", "#123", "SUCCESS", "zhangsan", "构建成功"]
    ]
  }
}
```

响应:

```json
{
  "code": 0,
  "data": {
    "tableRange": "<sheet_id>!A110:F110",
    "updates": {
      "updatedRange": "<sheet_id>!A110:F110"
    }
  }
}
```

**代码**:

```python
import os, urllib.request, json
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

# 1. 取 token
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({
        "app_id": os.environ["FEISHU_APP_ID"],
        "app_secret": os.environ["FEISHU_APP_SECRET"],
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=15) as resp:
    tenant_token = json.loads(resp.read()).get("tenant_access_token", "")

# 2. 写数据
spreadsheet_token = os.environ["FEISHU_SHEETS_TOKEN_BUILD"]
sheet_id = os.environ["FEISHU_SHEET_ID_BUILD"]

row_values = [[
    "2026-06-13 19:30:00",  # 触发时间
    "myjob",                  # Job 名称
    "#123",                   # 构建号
    "SUCCESS",                # 结果
    "zhangsan",               # 触发者
    "构建成功",                # 备注
]]

payload = {
    "valueRange": {
        "range": f"{sheet_id}!A1:F1",
        "values": row_values,
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
    result = json.loads(resp.read())
print(f"code={result.get('code')}, range={result.get('data', {}).get('tableRange', '')}")
```

## 6. 覆盖写 (V2 PUT)

**⚠️ 不推荐**: PUT 会清空再写, 容易丢数据.

```bash
PUT https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/<spreadsheet_token>/values
Authorization: Bearer <tenant_access_token>
Content-Type: application/json

{
  "valueRange": {
    "range": "<sheet_id>!A1:F1",
    "values": [["...", "..."]]
  }
}
```

## 7. 删行策略

**V2 飞书没有原生"删行"API**. 常用方法:
1. 读出全部数据 → 过滤掉要删的 → PUT 回去 (适用于小表)
2. 物理上"重置": 建新表 + 把非删数据 append 过去 + 删旧表
3. 用 V3 高级 API: 待 V3 接口稳定

## 8. 错误码

| code | 含义 | 解决 |
|------|------|------|
| 0 | 成功 | - |
| 99991663 | 权限不足 | 检查 app 是否被授权访问该表 |
| 99991668 | app secret 错误 | 检查 `FEISHU_APP_SECRET` |
| 99991672 | tenant_access_token 无效 | 重新获取 |
| 1254045 | sheet_id 不存在 | 用 `/sheets/query` 查真值 |
| 1254000 | range 格式错 | 检查 `A1:F1` 格式 |
| 99991400 | rate limit | 限流, 降速 |

## 9. 通用化 ENV 变量

**强烈建议所有 skill 用统一 env 变量名**:

```bash
# ~/.hermes/.env 追加
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=xxxxxxxx

# 通用表 (按用途命名, 不带项目名)
FEISHU_SHEETS_TOKEN_BUILD=shtcnxxxx  # 构建记录
FEISHU_SHEET_ID_BUILD=xxxxx

FEISHU_SHEETS_TOKEN_SYNC=shtcnyyyy   # 用户同步
FEISHU_SHEET_ID_SYNC=yyyyy

FEISHU_SHEETS_TOKEN_KNOWN_CAUSES=shtcnzzzz  # 已知根因
FEISHU_SHEET_ID_KNOWN_CAUSES=zzzzz

# 飞书 chat_id
FEISHU_CHAT_ID=oc_xxxx
```

**避免**:
- ❌ `FEISHU_SHEETS_TOKEN_MZoA...` (用具体 token)
- ❌ `FEISHU_SHEETS_TOKEN_SM68B` (用项目名)
- ❌ `MY_FEISHU_TOKEN` (用自己公司前缀)

## 10. 常见陷阱

### Q: 报 99991663 (权限不足)

- 检查应用是否被加为表格的"协作者"
- 检查应用 scope 是否包含 `sheets:spreadsheet` 等

### Q: values_append 不工作

- 确认用 V2 endpoint: `/sheets/v2/`
- V3 没有 `values_append`, 报 404
- 不要用 `/open-apis/sheets/v3/spreadsheets/{token}/values_append`

### Q: sheet_id 找不到

- 用 `/sheets/v3/spreadsheets/{token}/sheets/query` 查真值
- 不要用 "Sheet1" 或 "0" 猜

### Q: rate limit

- 飞书默认 QPS 限制, 写太快会 99991400
- 建议加 200ms 间隔 (`time.sleep(0.2)`)

## 资源

- [飞书开放平台](https://open.feishu.cn/document/server-docs/docs/sheets-v3/overview)
- [V2 values_append](https://open.feishu.cn/document/server-docs/docs/sheets-v2/operation/append-data)
- [tenant_access_token](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal)
