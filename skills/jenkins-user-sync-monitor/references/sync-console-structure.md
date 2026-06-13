# 用户同步 console 结构通用方法论

> **v1.1.0 通用化重写**: 之前 `sync-user-sxz-console-structure.md` 绑了 sync_user_sxz + 西安中诺 + 赵霞娃 等特定数据. 现改为通用方法论, 任何公司的用户同步 console 都适用.

## 1. 典型 console 结构

```
[2026-04-29 10:00:00] Starting build job
USER INFO:  张三 13800138000 zhang@yourco.com 10001 2024-01-01 软件部 软件 YourCo 1/100
Create  张三 13800138000 zhang@yourco.com 10001 2024-01-01 软件部 软件 YourCo
No changed for 张三 13800138000 zhang@yourco.com 10001 2024-01-01 软件部 软件 YourCo
USER INFO:  李四 13900139000 li@yourco.com 10002 2024-01-02 行政部 助理 YourCo 2/100
Create  李四 13900139000 li@yourco.com 10002 2024-01-02 行政部 助理 YourCo
单用户方式创建失败，用批量方式创建用户
enterpriseMail不符合规范
创建用户成功
USER INFO:  王五 13700137000 wang@yourco.com 10003 2024-01-03 软件部 软件 YourCo 3/100
Create  王五 13700137000 wang@yourco.com 10003 2024-01-03 软件部 软件 YourCo
创建用户失败
USER INFO:  赵六 13600136000 zhao@yourco.com 10004 2024-01-04 软件部 软件 YourCo 4/100
invalid phone number for  赵六 13600136000 zhao@yourco.com 10004 2024-01-04 软件部 软件 YourCo
```

## 2. 关键结构元素

### 2.1 USER INFO 行

**通用格式**:
```
USER INFO:  <姓名> <手机号> [<邮箱>] <工号> <入职日期> <部门> [<领域>] <公司> <N/M>
```

**4 种 token 数** (实测):
- **9-token** (标准, 90%+): 姓名 手机号 邮箱 工号 入职日期 部门 领域 公司 N/M
- **10-token** (部门名含空格, ~2%): `NT PDT部 PDT ...` 拆成 2 个 token
- **11-token** (姓名/手机号含空格, 罕见): `Vishal Kumar Sharma 18664041471`
- **8-token** (旧格式, 无 email, 罕见): `15991641654 - 10285752 ...` 用 dash 分隔

**通用解析规则**:
- 最后一个 `N/M` 格式 token (e.g. `1474/15237`) 之前是公司名
- 公司 = `tokens[-2]`
- **永远用倒数法, 不要按 9-token 索引硬切**

### 2.2 Create 行

```
Create  <姓名> <手机号> [<邮箱>] <工号> <入职日期> <部门> [<领域>] <公司>
```

**作用**: 标识"开始创建"动作. 紧跟 USER INFO 行.

### 2.3 No changed for 行

```
No changed for <姓名> <手机号> [<邮箱>] <工号> <入职日期> <部门> [<领域>] <公司>
```

**作用**: 标识"无需同步" (用户已存在且状态一致). **这是成功状态, 不是失败.**

### 2.4 失败关键词

| 关键词 | 含义 | 后续行 | 计入失败? |
|--------|------|--------|----------|
| `创建用户失败` | 用户创建失败 | 通常紧跟 | ✅ 是 |
| `单用户方式创建失败` | 单用户方式失败 | 后面 200 字符内有 `创建用户成功` 则不算 | 需判断 |
| `invalid phone number for` | 手机号格式不规范 | 紧跟 | ✅ 是 |
| `email 不符合规范` | 邮箱格式不规范 | 紧跟 | (可选, 看 FAILURE_KEYWORDS) |
| `enterpriseMail不符合规范` | 企业邮箱不规范 | 紧跟 | (可选) |

**判断单用户失败是否真失败**:
```python
def is_batch_success(pos, console, window=200):
    """检查 failure line 后 window 字符内是否有 创建用户成功"""
    chunk = console[pos:min(len(console), pos + window)]
    return "创建用户成功" in chunk
```

### 2.5 ipn 行 (invalid phone number)

```
invalid phone number for  <姓名> <手机号> None <工号> <入职日期> <部门> None <公司>
```

**v1.0.6 关键发现**: ipn 行**行末最后一个 token 就是公司名**, 直接 `tokens[-1]`.

**不要**用 lookback 找 USER INFO 来推断公司 (会产生 61550 字符距离误判).

## 3. 多公司混合策略

**场景**: 一个 Jenkins job 同步多个公司 (e.g. 西安中诺 + 深圳福日 + 广东以诺 + ...)

**策略**: 只统计目标公司, 其他公司失败不计入.

```python
# 提取每行公司
def get_company_from_user_info(line):
    m = re.match(r'USER INFO:\s+(.+)$', line)
    if not m: return None
    tokens = m.group(1).strip().split()
    if not tokens: return None
    last = tokens[-1]
    if '/' in last and re.match(r'^\d+/\d+$', last):
        return tokens[-2] if len(tokens) >= 2 else None
    return None

def get_company_from_ipn(line):
    tokens = line.strip().split()
    return tokens[-1] if tokens else None

# 过滤
matched_failures = [f for f in all_failures if f["company"] == target_company]
```

## 4. 真实案例分析 (脱敏后通用)

### 案例 1: 100 用户, 0 失败 (理想状态)

```
100 × USER INFO + 100 × No changed
```

**summary_text**: `✅ 同步完成 (YourCo: 0 失败) | 总人数 100 | No changed 100 | 批量救回 0`

### 案例 2: 100 用户, 5 失败 (典型失败)

```
95 × No changed + 5 × 创建用户失败 / invalid phone / 单用户失败
```

**summary_text**: `🚨 失败 5 条 (YourCo): 创建用户失败 3 + invalid phone number for 2`

### 案例 3: 单用户失败 + 批量救回 (假阳性)

```
1 × 单用户方式创建失败 + 1 × enterpriseMail不符合规范 + 1 × 创建用户成功
```

**判定**: 200 字符内有 `创建用户成功` → **不算失败**.

### 案例 4: 多公司混合 (1000 用户, 多公司)

```
700 × No changed (YourCo)
200 × No changed (OtherCo)        # 不计入 YourCo
100 × 创建用户失败 (OtherCo)        # 不计入 YourCo
```

**判定**: 只统计 0 个 YourCo 失败 → **不发通知**.

## 5. 通用化 ENV 变量

```bash
# ~/.hermes/.env
TARGET_COMPANY=YourCo  # 改成你的公司名
FAILURE_KEYWORDS=创建用户失败,单用户方式创建失败,invalid phone number for  # 按需调整
```

**公司名完全匹配**: `analyze_failures` 用 `company == target_company` 严格匹配, console 里公司名要稳定.

## 6. 调试技巧

### 跑分析器单 build

```bash
python3 scripts/sync_analyzer.py <job_name> <build_number>
```

输出 JSON 包含:
- `matched_failures`: 目标公司失败数
- `by_keyword`: 各关键词计数
- `samples`: 前 10 条失败样本
- `summary_text`: 给飞书备注用

### 加 debug 日志

在 `analyze_failures` 里加:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# 会输出每行解析过程
```

### 验证 console 公司名

```bash
# 找所有 USER INFO 行的最后 token
grep "USER INFO:" console.txt | awk '{print $NF}' | sort -u
```

确认你的 `TARGET_COMPANY` 在列表里, 且拼写完全一致.

## 7. 跨公司自适配

如果**一个新公司想用这个 skill**, 只需改 2 个 env 变量:

```bash
TARGET_COMPANY=NewCompanyName
FAILURE_KEYWORDS=创建用户失败,单用户方式创建失败,invalid phone number for  # 大概率不用改
```

不需要改任何代码.

## 8. 与 jenkins-build-monitor 区别

| 维度 | jenkins-build-monitor | jenkins-user-sync-monitor |
|------|----------------------|---------------------------|
| 失败关键词来源 | 代码内置 (编译错误) | env 注入 (用户同步错误) |
| 目标过滤 | 无 (单项目) | 按公司名 |
| "假阳性"陷阱 | PostBuildScript 失败 | 单用户失败 + 批量救回 |
| "成功"陷阱 | 无 | "No changed for" |

**核心区别**: 用户同步有"多公司过滤"和"假阳性"两层陷阱, 编译监控只有"假阳性"一层.

## 资源

- [SKILL.md](../SKILL.md) — Skill 描述
- [scripts/sync_analyzer.py](../scripts/sync_analyzer.py) — 通用化分析器
- [scripts/test_analyzer.py](../scripts/test_analyzer.py) — 单测
