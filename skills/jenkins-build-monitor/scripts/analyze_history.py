#!/usr/bin/env python3
"""
Jenkins 构建历史通用分析脚本（v1.2.0 - 通用化重写）

用途: 拉指定 Jenkins job 的构建历史, 分析失败率 / 误报率 / 错误类型分布, 输出报告。
调用: python3 scripts/analyze_history.py
季度或半年跑一次, 发现异常趋势时跑。

通用化变更 (v1.0 → v1.2.0):
- 去除所有硬编码 IP/项目名/用户名
- 配置走 ~/.hermes/.env (JENKINS_URL, JENKINS_USER, JENKINS_PASS, TARGET_JOBS)
- 路径自定位 (Path(__file__).parent)
- 通用化输出 (不绑 SM68B / boot_images 等特定项目)
- 错误类型统计跨语言 (不只 Android 编译)

依赖: python3 标准库 + python-dotenv
"""
import os
import json
import urllib.request
import base64
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# 路径自定位
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "references"))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.hermes/.env"))

# 必需配置
JENKINS_URL = os.environ.get("JENKINS_URL")
if not JENKINS_URL:
    print("❌ JENKINS_URL 未配置, 请在 ~/.hermes/.env 设置")
    sys.exit(1)

JENKINS_USER = os.environ["JENKINS_USER"]
JENKINS_PASS = os.environ["JENKINS_PASS"]

# TARGET_JOBS: 逗号分隔, 例如 TARGET_JOBS=myapp-prod,myapp-staging
target_jobs_env = os.environ.get("TARGET_JOBS", "")
if not target_jobs_env:
    print("❌ TARGET_JOBS 未配置, 请在 ~/.hermes/.env 设置 (逗号分隔多个)")
    sys.exit(1)
TARGET_JOBS = [j.strip() for j in target_jobs_env.split(",") if j.strip()]

# 分析窗口: 最近 N 个 build
WINDOW_SIZE = int(os.environ.get("ANALYZE_WINDOW_SIZE", "100"))

auth = f"{JENKINS_USER}:{JENKINS_PASS}"
b64 = base64.b64encode(auth.encode()).decode()
HEADERS = {"Authorization": f"Basic {b64}"}


def jenkins_get(path: str) -> dict:
    """调 Jenkins API"""
    req = urllib.request.Request(f"{JENKINS_URL}{path}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_console(job: str, build_no: int, tail_kb: int = 8) -> str:
    """拉 sub-job console 尾部"""
    try:
        req = urllib.request.Request(
            f"{JENKINS_URL}/job/{job}/{build_no}/consoleText",
            headers=HEADERS,
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        return text[-tail_kb * 1024:]
    except Exception as e:
        return f"(拉取失败: {e})"


def analyze_job(job_name: str) -> dict:
    """分析单个 job 的最近 N 个 build"""
    print(f"\n📊 分析: {job_name} (最近 {WINDOW_SIZE} 个 build)")

    try:
        data = jenkins_get(f"/job/{job_name}/api/json?tree=builds[number,result,timestamp]")
    except Exception as e:
        print(f"  ❌ 拉取失败: {e}")
        return {"job": job_name, "error": str(e)}

    builds = data.get("builds", [])[:WINDOW_SIZE]
    if not builds:
        print(f"  ⚠️  无构建记录")
        return {"job": job_name, "total": 0}

    total = len(builds)
    success = sum(1 for b in builds if b.get("result") == "SUCCESS")
    failure = sum(1 for b in builds if b.get("result") == "FAILURE")
    unstable = sum(1 for b in builds if b.get("result") == "UNSTABLE")

    print(f"  总数: {total} | SUCCESS: {success} | FAILURE: {failure} | UNSTABLE: {unstable}")

    # 抽样: 失败 build 的 console 分析误报
    false_alarms = 0
    real_failures = 0
    error_types = Counter()

    for b in builds[:20]:  # 只抽最近 20 个分析 console, 节省时间
        if b.get("result") != "FAILURE":
            continue

        console = get_console(job_name, b["number"], tail_kb=4)
        is_falsealarm = (
            "PostBuildScript" in console
            and "changed build result to FAILURE" in console
            and "Finished Build" in console
            and "FAILURE" not in re.findall(
                r"Finished Build.*with status\s*:\s*(\w+)", console
            )
        )

        if is_falsealarm:
            false_alarms += 1
        else:
            real_failures += 1
            # 错误类型统计
            for pattern_name, pattern in [
                ("fatal error", r"fatal error"),
                ("make error", r"make:\s*\*\*\*"),
                ("module failed", r"Failed to build module"),
                ("undefined ref", r"undefined reference"),
                ("FileNotFound", r"FileNotFoundError"),
                ("OOM", r"out of memory|OOM"),
                ("permission", r"Permission denied"),
                ("disk full", r"No space left on device"),
            ]:
                if re.search(pattern, console, re.IGNORECASE):
                    error_types[pattern_name] += 1

    if false_alarms + real_failures > 0:
        print(f"  抽样分析 (最近 20 失败):")
        print(f"    误报 (PostBuildScript): {false_alarms}")
        print(f"    真失败: {real_failures}")
        if error_types:
            print(f"  错误类型分布:")
            for et, count in error_types.most_common():
                print(f"    {et}: {count}")

    return {
        "job": job_name,
        "total": total,
        "success": success,
        "failure": failure,
        "unstable": unstable,
        "sample_size": min(20, failure),
        "false_alarms": false_alarms,
        "real_failures": real_failures,
        "error_types": dict(error_types),
    }


def main():
    print(f"🚀 Jenkins 构建历史分析")
    print(f"   URL: {JENKINS_URL}")
    print(f"   Jobs: {', '.join(TARGET_JOBS)}")
    print(f"   窗口: 最近 {WINDOW_SIZE} 个 build")
    print(f"   抽样分析: 最近 20 个失败 build 的 console")

    results = []
    for job in TARGET_JOBS:
        result = analyze_job(job)
        results.append(result)

    # 输出汇总
    print(f"\n\n{'=' * 60}")
    print(f"汇总报告")
    print(f"{'=' * 60}")
    print(f"{'Job':<30} {'总数':<6} {'成功':<6} {'失败':<6} {'误报率':<8}")
    print(f"{'-' * 60}")
    for r in results:
        if "error" in r:
            print(f"{r['job']:<30} ❌ 拉取失败")
            continue
        total = r["total"]
        success = r["success"]
        failure = r["failure"]
        false_alarm_rate = (
            f"{r['false_alarms'] * 100 // r['sample_size']}%"
            if r.get("sample_size", 0) > 0
            else "N/A"
        )
        print(f"{r['job']:<30} {total:<6} {success:<6} {failure:<6} {false_alarm_rate:<8}")

    # 输出 JSON
    out_file = SKILL_DIR / "reports" / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n📄 详细报告: {out_file}")


if __name__ == "__main__":
    main()
