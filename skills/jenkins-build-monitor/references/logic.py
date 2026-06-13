"""
jenkins-build-monitor v1.2.0 核心逻辑（纯函数式，不依赖网络，零硬编码）

三个核心函数：
1. classify_failure() - 分类 trigger FAILURE：postbuild_falsealarm vs real_subjob_fail
2. extract_key_error_lines() - 从 sub_console 提取关键错误行（限 500 字符）
3. build_remark() - 生成飞书备注列内容

通用化变更 (v1.1.4 → v1.2.0):
- 去除所有硬编码 IP / Token / 用户名 / 项目名
- 噪音模式 SM68B_*_trigger 改为可注入 (JOB_NAME_PATTERN env)
- 错误模式保留通用编译错误, 移除项目专属
- 函数签名不变, 兼容 v1.1.4 调用方

作者: hqgaofeng + Hermes
日期: 2026-06-13
"""
import os
import re
from typing import List, Tuple, Dict, Any, Optional


# ============================================================================
# 噪音模式 (v1.2.0 通用化)
# ============================================================================

# 用户可通过环境变量 JOB_NAME_PATTERN 添加自定义噪音模式
# 例: JOB_NAME_PATTERN=^\[MYPROJECT_\w+_trigger\]
# 这样部署在 MYPROJECT 环境时, 自动识别其 trigger job 噪音

def _get_default_noise_patterns() -> list:
    """默认噪音模式 (通用, 跨项目)"""
    return [
        re.compile(r"^Error calculating quiet time"),
        re.compile(r"^quiet period for \S+ is \d+ seconds"),
        re.compile(r"PostBuildScript.*INFO"),
        re.compile(r"^\+ (HERMES_URL|HERMES_SECRET|PAYLOAD|curl|echo|SIGNATURE|openssl|sed|printf)"),
        re.compile(r"^\[PostBuildScript\]"),
        re.compile(r"^Variable with name 'BUILD_DISPLAY_NAME'"),
        re.compile(r"^New run name is"),
        re.compile(r"^Starting build job"),
        re.compile(r"^Finished Build"),
        re.compile(r"^Build step 'Execute scripts'"),
        re.compile(r"^Build step 'Execute shell'"),
        re.compile(r"^Build step.*changed build result"),
        re.compile(r"^Build step.*did not set build result"),
        re.compile(r"^\{.*\}$"),  # 纯 JSON 行
        re.compile(r"^$"),
    ]


def _get_user_noise_patterns() -> list:
    """从 env 读取用户自定义噪音模式 (支持多个, 用 | 分隔)"""
    patterns_env = os.environ.get("JOB_NAME_PATTERN", "")
    if not patterns_env:
        return []
    # 用户可以传多个 pattern, 用 | 分隔
    return [re.compile(p) for p in patterns_env.split("|") if p]


def get_noise_patterns() -> list:
    """获取所有噪音模式 (默认 + 用户自定义)"""
    return _get_default_noise_patterns() + _get_user_noise_patterns()


# ============================================================================
# 错误模式 (通用编译错误, 跨语言跨项目)
# ============================================================================

ERROR_PATTERNS = [
    # C / C++ / ObjC
    re.compile(r"fatal error:\s*['\"]?([^'\"]+)['\"]?\s*file not found", re.IGNORECASE),
    re.compile(r"undefined reference to\s+[`']([^'`]+)", re.IGNORECASE),
    # Make / Build
    re.compile(r"FAILED:\s*(\S+)", re.IGNORECASE),
    re.compile(r"Failed to build module\s*[:\s]+(\S+)", re.IGNORECASE),
    re.compile(r"make:\s*\*\*\*\s*\[([^\]]+)\]\s*Error\s*(\d+)", re.IGNORECASE),
    re.compile(r"ninja:\s*build stopped", re.IGNORECASE),
    # 通用 error
    re.compile(r"error\s+F\d+:\s*(.+)$", re.IGNORECASE),
    re.compile(r"error\s+\d+:\s*(.+)$", re.IGNORECASE),
    # Python
    re.compile(r"FileNotFoundError:\s*\[Errno\s+\d+\]\s*No such file or directory:\s*['\"]?([^'\"]+)", re.IGNORECASE),
    re.compile(r"ImportError:\s*([^\n]+)", re.IGNORECASE),
    re.compile(r"ModuleNotFoundError:\s*([^\n]+)", re.IGNORECASE),
    # Java / JVM
    re.compile(r"java\.lang\.\w+Exception", re.IGNORECASE),
    re.compile(r"Caused by:", re.IGNORECASE),
    # Go
    re.compile(r"\.go:\d+:\d+:\s*(.+)$", re.IGNORECASE),
    # Rust
    re.compile(r"error\[E\d+\]:", re.IGNORECASE),
    # 系统资源
    re.compile(r"killed by signal\s+(\w+)", re.IGNORECASE),
    re.compile(r"out of memory|OOM", re.IGNORECASE),
    re.compile(r"No space left on device", re.IGNORECASE),
    re.compile(r"Permission denied", re.IGNORECASE),
    # 链接
    re.compile(r"cannot find -l(\S+)", re.IGNORECASE),
]


# ============================================================================
# 函数 1: classify_failure (v1.1.4 引入, v1.2.0 保留)
# ============================================================================

def parse_sub_results(trigger_console: str) -> List[Tuple[str, str]]:
    """
    从 trigger consoleText 解析所有 sub-job 结果。
    输出: [(sub_job_name, status), ...] 按 console 中出现顺序

    例子:
    "Finished Build : ... of Job : sm6650_bp with status : FAILURE at 15:35:31"
    → ("sm6650_bp", "FAILURE")
    """
    if not trigger_console:
        return []
    pattern = r'Job\s*:\s*(\S+)\s*with status\s*:\s*(\w+)'
    return [(m.group(1), m.group(2)) for m in re.finditer(pattern, trigger_console)]


def classify_failure(build_result: str, trigger_console: str) -> Dict[str, Any]:
    """
    分类 trigger 构建结果

    返回 dict:
    {
        "category": "success" | "postbuild_falsealarm" | "real_subjob_fail" | "unknown",
        "is_falsealarm": bool,
        "sub_results": [(sub_job, status), ...],
        "failing_sub_jobs": [sub_job, ...],   # 真的失败的 sub
        "successful_sub_jobs": [sub_job, ...], # 成功的 sub
        "postbuild_marker_found": bool,
        "reason": str  # 给飞书备注列用
    }

    分类规则:
    - SUCCESS → "success"
    - FAILURE + 所有 sub 都 SUCCESS + 有 PostBuildScript 标记 → "postbuild_falsealarm"
    - FAILURE + 有 sub FAILURE → "real_subjob_fail"
    - FAILURE + 其他 (没 sub 记录, 没 PostBuildScript 标记) → "unknown"
    """
    result = {
        "category": "unknown",
        "is_falsealarm": False,
        "sub_results": [],
        "failing_sub_jobs": [],
        "successful_sub_jobs": [],
        "postbuild_marker_found": False,
        "reason": ""
    }

    if not trigger_console:
        result["reason"] = "trigger_console 为空"
        if build_result == "SUCCESS":
            result["category"] = "success"
        return result

    # 解析 sub-job 结果
    sub_results = parse_sub_results(trigger_console)
    result["sub_results"] = sub_results
    result["failing_sub_jobs"] = [s for s, r in sub_results if r == "FAILURE"]
    result["successful_sub_jobs"] = [s for s, r in sub_results if r == "SUCCESS"]

    # 检测 PostBuildScript 失败标记
    has_postbuild_marker = (
        "PostBuildScript" in trigger_console
        and "changed build result to FAILURE" in trigger_console
    )
    result["postbuild_marker_found"] = has_postbuild_marker

    if build_result == "SUCCESS":
        result["category"] = "success"
        result["reason"] = "trigger SUCCESS"
    elif build_result == "FAILURE":
        all_sub_success = (
            len(sub_results) > 0
            and all(r == "SUCCESS" for _, r in sub_results)
        )
        if all_sub_success and has_postbuild_marker:
            result["category"] = "postbuild_falsealarm"
            result["is_falsealarm"] = True
            result["reason"] = (
                f"⚠️ 误报:PostBuildScript 失败但 {len(sub_results)} 个 sub-job 全 SUCCESS"
            )
        elif len(result["failing_sub_jobs"]) > 0:
            result["category"] = "real_subjob_fail"
            fail_str = ", ".join(result["failing_sub_jobs"])
            result["reason"] = f"真失败:sub-job 编译失败 ({fail_str})"
        else:
            result["category"] = "unknown"
            result["reason"] = (
                f"无法分类:sub_results={len(sub_results)}, "
                f"postbuild_marker={has_postbuild_marker}"
            )
    else:
        result["category"] = "unknown"
        result["reason"] = f"未知 build_result: {build_result}"

    return result


# ============================================================================
# 函数 2: extract_key_error_lines (v1.1.4 引入, v1.2.0 通用化)
# ============================================================================

def extract_key_error_lines(sub_console: str, max_chars: int = 500) -> str:
    """
    从 sub-job console 提取关键错误行, 限 max_chars 字符

    流程:
    1. 取 console 后 8KB (错误通常在尾部)
    2. 过滤噪音行 (PostBuildScript / curl / Quiet period 等)
    3. 优先匹配 ERROR_PATTERNS 中的行
    4. 拼接到 max_chars 字符

    返回: 单行字符串 (用 ` | ` 分隔), 适合飞书备注列
    """
    if not sub_console:
        return ""

    # 1. 取尾部 8KB
    tail = sub_console[-8000:] if len(sub_console) > 8000 else sub_console

    # 2. 分行
    lines = [l.strip() for l in tail.split("\n") if l.strip()]

    # 3. 过滤噪音 (使用动态获取的噪音模式)
    noise_patterns = get_noise_patterns()
    filtered = []
    for line in lines:
        if any(np.match(line) for np in noise_patterns):
            continue
        filtered.append(line)

    # 4. 优先匹配错误模式
    error_lines = []
    seen = set()  # 去重
    for line in filtered:
        for pat in ERROR_PATTERNS:
            if pat.search(line):
                if line not in seen:
                    error_lines.append(line)
                    seen.add(line)
                break

    # 5. 如果没匹配到错误模式, 返回空 (不要塞 INFO 噪音)
    if not error_lines:
        return ""

    # 6. 拼接, 限 max_chars
    result_parts = []
    total = 0
    for line in error_lines:
        sep_len = 3 if result_parts else 0  # " | " = 3 chars
        if total + sep_len + len(line) > max_chars:
            # 截断
            remaining = max_chars - total - sep_len
            if remaining > 20:  # 至少留 20 字符
                result_parts.append(line[:remaining] + "...")
                total += sep_len + remaining + 3
            break
        result_parts.append(line)
        total += sep_len + len(line)

    return " | ".join(result_parts)


# ============================================================================
# 函数 3: build_remark (v1.1.4 引入, v1.2.0 保留)
# ============================================================================

def build_remark(
    classification: Dict[str, Any],
    error_file: str = "",
    error_type: str = "",
    commit_hash: str = "",
    known_root_cause: str = "",
    sub_console_key: str = "",
) -> str:
    """
    根据分类生成飞书表备注列内容

    返回示例:
    - 成功: "构建成功"
    - 误报: "⚠️ 误报（PostBuildScript）| trigger 失败但 3 个 sub-job 全 SUCCESS | [监控: webhook 投递失败]"
    - 已知根因: "失败：fatal error: 'xxx.h' file not found | ChargerLibCommon.c | 【内部根因】xxx | sub_console_key"
    - 未知根因: "失败：fatal error: 'xxx.h' file not found | ChargerLibCommon.c | commit 9bf7c5c25 | sub_console_key"
    """
    cat = classification.get("category", "unknown")

    if cat == "success":
        return "构建成功"

    if cat == "postbuild_falsealarm":
        n_sub = len(classification.get("successful_sub_jobs", []))
        return f"⚠️ 误报（PostBuildScript）| trigger 失败但 {n_sub} 个 sub-job 全 SUCCESS | [监控: webhook 投递失败]"

    # 真失败或 unknown
    parts = []
    if error_type:
        parts.append(f"失败:{error_type}")
    else:
        parts.append("失败")
    if error_file:
        parts.append(error_file)

    if known_root_cause:
        parts.append(f"【内部根因】{known_root_cause}")
    elif commit_hash:
        parts.append(f"commit {commit_hash[:8]}")
    else:
        # 既无内部根因也无 commit hash 时, 标记待分析
        parts.append("[待 git blame]")

    if sub_console_key:
        parts.append(f"sub_errs: {sub_console_key}")

    return " | ".join(parts)
