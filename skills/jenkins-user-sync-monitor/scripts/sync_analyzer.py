"""
jenkins-user-sync-monitor v1.1.0 通用化分析器

原 v1.0.9 (sync_user_sxz_analyzer.py) 绑了西安中诺通讯有限公司 + 192.168.100.215 等特定环境.
v1.1.0 重写为通用版本:
- 目标公司走 TARGET_COMPANY env
- 失败关键词走 FAILURE_KEYWORDS env (逗号分隔)
- Jenkins URL/认证 走 JENKINS_URL/JENKINS_USER/JENKINS_PASS env
- 路径自定位 (Path(__file__).parent)
- 测试独立可跑 (内嵌 console fixture)

用法:
  python3 scripts/sync_analyzer.py <job_name> <build_number>
  # 输出 JSON: 触发时间, 目标公司失败数, 分类统计, summary_text
"""
import os
import re
import sys
import json
import urllib.request
import base64
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter
from dotenv import load_dotenv

# 路径自定位
SKILL_DIR = Path(__file__).parent.parent

# 加载 env
load_dotenv(os.path.expanduser("~/.hermes/.env"))


# ============================================================================
# 配置 (从 env 读, 缺省值给合理默认)
# ============================================================================

def _get_env_or_default(key, default):
    val = os.environ.get(key, "").strip()
    return val if val else default


JENKINS_URL = _get_env_or_default("JENKINS_URL", _get_env_or_default("JENKINS215_URL", ""))
JENKINS_USER = _get_env_or_default("JENKINS_USER", _get_env_or_default("JENKINS215_USER", ""))
JENKINS_PASS = _get_env_or_default("JENKINS_PASS", _get_env_or_default("JENKINS215_PASS", ""))

# 目标公司 (用户部署时改)
TARGET_COMPANY = _get_env_or_default("TARGET_COMPANY", "目标公司")

# 失败关键词 (逗号分隔, 默认常见用户同步失败关键词)
_default_keywords = "创建用户失败,单用户方式创建失败,invalid phone number for"
FAILURE_KEYWORDS = [
    k.strip() for k in _get_env_or_default("FAILURE_KEYWORDS", _default_keywords).split(",")
    if k.strip()
]

# 时区偏移
LOCAL_TZ_OFFSET_HOURS = int(_get_env_or_default("LOCAL_TZ_OFFSET_HOURS", "8"))


# ============================================================================
# Jenkins API 工具
# ============================================================================

def _auth_header():
    auth = f"{JENKINS_USER}:{JENKINS_PASS}"
    return {"Authorization": "Basic " + base64.b64encode(auth.encode()).decode()}


def fetch_trigger_time(job_name: str, build_number: str) -> str:
    """从 Jenkins API 取真实触发时间"""
    api_url = f"{JENKINS_URL}/job/{job_name}/{build_number}/api/json?tree=timestamp"
    req = urllib.request.Request(api_url, headers=_auth_header())
    with urllib.request.urlopen(req, timeout=30) as resp:
        api_data = json.loads(resp.read())
    ts_ms = api_data["timestamp"]
    dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    dt_local = dt_utc + timedelta(hours=LOCAL_TZ_OFFSET_HOURS)
    return dt_local.strftime("%Y-%m-%d %H:%M:%S")


def fetch_console(job_name: str, build_number: str) -> str:
    """从 Jenkins API 取 consoleText"""
    url = f"{JENKINS_URL}/job/{job_name}/{build_number}/consoleText"
    req = urllib.request.Request(url, headers=_auth_header())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ============================================================================
# Console 解析 (纯函数, 可独立测试)
# ============================================================================

def parse_user_info(line: str) -> dict:
    """
    通用解析 USER INFO 行, 返回 {name, phone, company, dept} 或 None

    通用规则 (v1.0.6 实测):
    - 最后一个 N/M 格式 token (e.g. "1474/15237") 之前是公司名
    - 公司 = tokens[-2]
    - 不按 token 数硬切 (8/9/10/11/12 token 都可能)
    """
    m = re.match(r'USER INFO:\s+(.+)$', line)
    if not m:
        return None
    tokens = m.group(1).strip().split()
    if not tokens:
        return None
    last = tokens[-1]
    if "/" in last and re.match(r'^\d+/\d+$', last):
        if len(tokens) >= 2:
            return {
                "name": tokens[0],
                "phone": tokens[1] if len(tokens) > 1 else None,
                "company": tokens[-2],
                "dept": tokens[5] if len(tokens) > 5 else None,
            }
    return None


def is_batch_success(pos: int, console: str, window: int = 200) -> bool:
    """检查 failure line 后 window 字符内是否有 创建用户成功 (批量救回)"""
    chunk = console[pos:min(len(console), pos + window)]
    return "创建用户成功" in chunk


def parse_ipn_line(line: str) -> dict:
    """
    解析 invalid phone number for 行, 返回 {name, company} 或 None
    通用规则: company = tokens[-1] (行末最后一个 token)
    """
    m = re.match(r'invalid phone number for\s+(.+)$', line)
    if not m:
        return None
    tokens = m.group(1).strip().split()
    if not tokens:
        return None
    return {
        "name": tokens[0],
        "company": tokens[-1] if tokens else None,
    }


def analyze_failures(console: str, target_company: str, failure_keywords: list = None) -> dict:
    """
    分析 console, 提取目标公司的失败记录

    Args:
        console: Jenkins consoleText 全文
        target_company: 目标公司名 (e.g. "西安中诺通讯有限公司")
        failure_keywords: 失败关键词列表, 默认 FAILURE_KEYWORDS

    Returns:
        {
            "total_users": int,           # USER INFO 行数
            "no_changed": int,            # "No changed for" 数
            "matched_failures": int,      # 目标公司失败数
            "total_failures": int,        # 所有失败数
            "by_keyword": {kw: count},    # 按关键词统计
            "samples": [...],             # 失败样本 (前 10)
            "summary_text": str,          # 给飞书备注用
        }
    """
    if failure_keywords is None:
        failure_keywords = FAILURE_KEYWORDS

    # 1. 统计 USER INFO / No changed
    user_info_pattern = re.compile(r'USER INFO:\s+', re.MULTILINE)
    no_changed_pattern = re.compile(r'No changed for\s+', re.MULTILINE)
    total_users = len(user_info_pattern.findall(console))
    no_changed = len(no_changed_pattern.findall(console))

    # 2. 找失败 (按关键词)
    all_failures = []
    by_keyword = Counter()
    for keyword in failure_keywords:
        for m in re.finditer(re.escape(keyword), console):
            line_start = console.rfind("\n", 0, m.start()) + 1
            line_end = console.find("\n", m.start())
            if line_end == -1:
                line_end = len(console)
            line = console[line_start:line_end].strip()

            # 排除批量救回 (单用户失败 + 后续 创建用户成功)
            if keyword in ("单用户方式创建失败", "单用户方式创建失败，用批量方式创建用户"):
                if is_batch_success(m.start(), console):
                    continue

            # 判断公司
            company = None
            if "invalid phone number" in keyword:
                ipn = parse_ipn_line(line)
                company = ipn["company"] if ipn else None
            else:
                # USER INFO 行的下一行 (Create ... 失败)
                # 找上一行的 USER INFO
                prev_user_info = console.rfind("USER INFO:", 0, m.start())
                if prev_user_info != -1:
                    line_end_prev = console.find("\n", prev_user_info)
                    if line_end_prev == -1:
                        line_end_prev = len(console)
                    user_line = console[prev_user_info:line_end_prev]
                    ui = parse_user_info(user_line)
                    company = ui["company"] if ui else None

            all_failures.append({
                "keyword": keyword,
                "line": line,
                "company": company,
                "is_target": company == target_company,
            })
            by_keyword[keyword] += 1

    # 3. 过滤目标公司
    matched = [f for f in all_failures if f["is_target"]]
    matched_failures = len(matched)
    total_failures = len(all_failures)

    # 4. 失败样本 (前 10 条)
    samples = []
    for f in matched[:10]:
        # 提取姓名 / 手机号 / 部门
        ui = parse_user_info(f["line"]) if "USER INFO" not in f["line"] else None
        if not ui:
            # 找最近的 USER INFO
            line_pos = console.find(f["line"])
            if line_pos != -1:
                prev_user_info = console.rfind("USER INFO:", 0, line_pos)
                if prev_user_info != -1:
                    line_end_prev = console.find("\n", prev_user_info)
                    user_line = console[prev_user_info:line_end_prev] if line_end_prev != -1 else console[prev_user_info:]
                    ui = parse_user_info(user_line)
        if ui:
            samples.append({
                "name": ui.get("name", "?"),
                "phone": ui.get("phone", "?"),
                "dept": ui.get("dept", "?"),
                "keyword": f["keyword"],
            })
        else:
            samples.append({"line": f["line"][:100], "keyword": f["keyword"]})

    # 5. 生成 summary_text
    summary_text = _build_summary_text(
        matched_failures=matched_failures,
        total_users=total_users,
        no_changed=no_changed,
        by_keyword=by_keyword,
        target_company=target_company,
    )

    return {
        "total_users": total_users,
        "no_changed": no_changed,
        "matched_failures": matched_failures,
        "total_failures": total_failures,
        "by_keyword": dict(by_keyword),
        "samples": samples,
        "summary_text": summary_text,
    }


def _build_summary_text(matched_failures, total_users, no_changed, by_keyword, target_company) -> str:
    """
    v1.0.9: 失败 0 时拆解状态分布, 失败 N 时按类型汇总.
    通用化: 用 target_company 参数, 不绑特定公司.
    """
    if matched_failures == 0:
        # 拆解状态分布
        other_no_changed = by_keyword.get("创建用户成功", 0)  # 批量救回数
        return (
            f"✅ 同步完成 ({target_company}: 0 失败) | "
            f"总人数 {total_users} | No changed {no_changed} | "
            f"批量救回 {other_no_changed}"
        )
    else:
        # 失败类型分布
        breakdown = " + ".join(
            f"{kw} {n}" for kw, n in by_keyword.items() if n > 0
        )
        return f"🚨 失败 {matched_failures} 条 ({target_company}): {breakdown}"


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    if len(sys.argv) < 3:
        print(f"用法: python3 {sys.argv[0]} <job_name> <build_number>")
        print(f"  例: python3 {sys.argv[0]} sync_user_sxz 1752")
        sys.exit(1)

    job_name = sys.argv[1]
    build_number = sys.argv[2]

    print(f"🔍 分析 {job_name} #{build_number}...")
    print(f"   Jenkins: {JENKINS_URL}")
    print(f"   目标公司: {TARGET_COMPANY}")

    # 1. 触发时间
    trigger_time = fetch_trigger_time(job_name, build_number)
    print(f"   触发时间: {trigger_time}")

    # 2. console
    console = fetch_console(job_name, build_number)
    print(f"   console 长度: {len(console):,} 字符")

    # 3. 分析
    result = analyze_failures(console, TARGET_COMPANY)
    result["job_name"] = job_name
    result["build_number"] = build_number
    result["trigger_time"] = trigger_time

    # 4. 输出 JSON
    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
