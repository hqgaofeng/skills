"""
jenkins-build-monitor v1.2.0 核心逻辑单测

5 个场景 + 5 个边界 case, 全部应该通过。

通用化变更:
- 路径自定位 (Path(__file__).parent), 不依赖 /tmp/jenkins-analysis
- fixtures 内嵌 (在 tests/ 子目录), 不依赖外部数据
- 可独立跑: python3 scripts/test_logic.py
"""
import sys
import unittest
from pathlib import Path

# 路径自定位: 不依赖绝对路径
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "references"))

from logic import (  # noqa: E402
    classify_failure,
    parse_sub_results,
    extract_key_error_lines,
    build_remark,
    get_noise_patterns,
    _get_user_noise_patterns,
)


# ============================================================================
# Fixtures (内嵌, 不依赖外部文件)
# ============================================================================

CONSOLE_REAL_FAILURE = """
[2026-04-29 15:27:00] Starting build job
[2026-04-29 15:27:01] Quiet period for sm68b_bp is 5 seconds
+ HERMES_URL=http://hermes:8644/webhooks/jenkins-monitor
+ curl -s -X POST $HERMES_URL ...
New run name is '#283'
Finished Build : [... Job: sm6650_bp] of Job : sm6650_bp with status : FAILURE at 15:35:31
Finished Build : [... Job: sm6650_sys_userdebug] of Job : sm6650_sys_userdebug with status : ABORTED at 15:35:33
Finished Build : [... Job: sm6650_vnd_userdebug] of Job : sm6650_vnd_userdebug with status : ABORTED at 15:35:33
Build step 'Execute shell' marked build as failure
"""

CONSOLE_FALSE_ALARM = """
[2026-06-06 10:00:00] Starting build job
+ HERMES_URL=http://hermes:8644/webhooks/jenkins-monitor
+ curl -s -X POST $HERMES_URL ...
+ echo done
[PostBuildScript] - Execution has begun for HTTP request
[PostBuildScript] - The HTTP status code is not 200
[PostBuildScript] - Script has previously been approved by a Jenkins administrator
[PostBuildScript] - The build result was forced to FAILURE
Build step 'Build step' changed build result to FAILURE
Finished Build : [... Job: myproject_sub1] of Job : myproject_sub1 with status : SUCCESS at 10:05:00
Finished Build : [... Job: myproject_sub2] of Job : myproject_sub2 with status : SUCCESS at 10:06:00
"""

CONSOLE_SUCCESS = """
[2026-04-29 15:27:00] Starting build job
+ curl -s -X POST $HERMES_URL ...
Finished Build : [... Job: myproject_sub1] of Job : myproject_sub1 with status : SUCCESS at 10:05:00
Finished Build : [... Job: myproject_sub2] of Job : myproject_sub2 with status : SUCCESS at 10:06:00
"""

CONSOLE_UNKNOWN = """
Some random log content
No sub-job results
Just a weird failure
"""

CONSOLE_EMPTY = ""

# 模拟 sub-job console (带编译错误)
SUB_CONSOLE_WITH_ERRORS = """
make: Entering directory '/build'
Building file: ChargerLibCommon.c
Invoking: GCC C Compiler
gcc -c -o ChargerLibCommon.o ChargerLibCommon.c
In file included from ChargerLibCommon.c:88:0:
fatal error: 'Uefixx.h' file not found
#include <Uefixx.h>
         ^~~~~~~~~~
compilation terminated.
make: *** [ChargerLibCommon.o] Error 1
make: Leaving directory '/build'
"""

SUB_CONSOLE_NO_ERRORS = """
All tasks completed successfully
No errors found
Build finished
"""

SUB_CONSOLE_NOISE_ONLY = """
+ HERMES_URL=http://hermes:8644/webhooks/jenkins-monitor
+ curl -s -X POST $HERMES_URL ...
[PostBuildScript] - Execution has begun for HTTP request
[PostBuildScript] - HTTP status is 200
Finished Build
"""

# 大 console (性能测试, 100K 行)
SUB_CONSOLE_LARGE = "\n".join(["line content " + str(i) for i in range(100000)])


# ============================================================================
# 测试类
# ============================================================================

class TestClassifyFailure(unittest.TestCase):
    """classify_failure 函数测试"""

    def test_real_subjob_failure(self):
        """场景 1: 真失败 (1 个 sub FAILURE, 2 个 ABORTED)"""
        cls = classify_failure("FAILURE", CONSOLE_REAL_FAILURE)
        self.assertEqual(cls["category"], "real_subjob_fail")
        self.assertFalse(cls["is_falsealarm"])
        self.assertIn("sm6650_bp", cls["failing_sub_jobs"])
        self.assertEqual(len(cls["failing_sub_jobs"]), 1)

    def test_postbuild_false_alarm(self):
        """场景 2: 误报 (PostBuildScript 失败 + sub 全 SUCCESS)"""
        cls = classify_failure("FAILURE", CONSOLE_FALSE_ALARM)
        self.assertEqual(cls["category"], "postbuild_falsealarm")
        self.assertTrue(cls["is_falsealarm"])
        self.assertEqual(len(cls["successful_sub_jobs"]), 2)
        self.assertTrue(cls["postbuild_marker_found"])

    def test_success(self):
        """场景 3: 成功"""
        cls = classify_failure("SUCCESS", CONSOLE_SUCCESS)
        self.assertEqual(cls["category"], "success")
        self.assertFalse(cls["is_falsealarm"])

    def test_unknown_no_sub_results(self):
        """场景 4: 未知 (FAILURE 但没 sub 记录也没 PostBuildScript)"""
        cls = classify_failure("FAILURE", CONSOLE_UNKNOWN)
        self.assertEqual(cls["category"], "unknown")
        self.assertFalse(cls["is_falsealarm"])

    def test_empty_console(self):
        """边界 1: 空 console"""
        cls = classify_failure("FAILURE", CONSOLE_EMPTY)
        self.assertEqual(cls["category"], "unknown")
        self.assertEqual(len(cls["sub_results"]), 0)

    def test_unknown_build_result(self):
        """边界 2: 未知 build_result 值"""
        cls = classify_failure("WEIRD_STATUS", CONSOLE_SUCCESS)
        self.assertEqual(cls["category"], "unknown")


class TestExtractKeyErrorLines(unittest.TestCase):
    """extract_key_error_lines 函数测试"""

    def test_extract_compilation_error(self):
        """场景 1: 提取 fatal error"""
        result = extract_key_error_lines(SUB_CONSOLE_WITH_ERRORS)
        self.assertIn("fatal error", result.lower())
        self.assertIn("Uefixx.h", result)
        self.assertIn("make: ***", result)

    def test_no_errors(self):
        """场景 2: 无错误返回空"""
        result = extract_key_error_lines(SUB_CONSOLE_NO_ERRORS)
        self.assertEqual(result, "")

    def test_noise_only(self):
        """场景 3: 只有噪音返回空"""
        result = extract_key_error_lines(SUB_CONSOLE_NOISE_ONLY)
        self.assertEqual(result, "")

    def test_empty_console(self):
        """边界 1: 空 console"""
        result = extract_key_error_lines("")
        self.assertEqual(result, "")

    def test_max_chars_limit(self):
        """边界 2: max_chars 限制"""
        result = extract_key_error_lines(SUB_CONSOLE_WITH_ERRORS, max_chars=50)
        self.assertLessEqual(len(result), 60)  # 允许 3 字符截断符

    def test_large_console_performance(self):
        """边界 3: 10 万行性能测试"""
        import time
        start = time.time()
        result = extract_key_error_lines(SUB_CONSOLE_LARGE)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0)  # 2 秒内完成
        # 大 console 无错误, 应返回空
        self.assertEqual(result, "")


class TestBuildRemark(unittest.TestCase):
    """build_remark 函数测试"""

    def test_success_remark(self):
        """场景 1: 成功"""
        cls = {"category": "success"}
        remark = build_remark(cls)
        self.assertEqual(remark, "构建成功")

    def test_false_alarm_remark(self):
        """场景 2: 误报"""
        cls = {
            "category": "postbuild_falsealarm",
            "successful_sub_jobs": ["sub1", "sub2", "sub3"],
        }
        remark = build_remark(cls)
        self.assertIn("误报", remark)
        self.assertIn("3 个 sub-job", remark)

    def test_real_failure_with_commit(self):
        """场景 3: 真失败 + commit hash"""
        cls = {"category": "real_subjob_fail"}
        remark = build_remark(
            cls,
            error_file="ChargerLibCommon.c",
            error_type="fatal error: 'Uefixx.h' file not found",
            commit_hash="9bf7c5c25abc",
        )
        self.assertIn("失败", remark)
        self.assertIn("Uefixx.h", remark)
        self.assertIn("ChargerLibCommon.c", remark)
        self.assertIn("9bf7c5c2", remark)  # 前 8 位

    def test_real_failure_with_known_cause(self):
        """场景 4: 真失败 + 已知根因"""
        cls = {"category": "real_subjob_fail"}
        remark = build_remark(
            cls,
            error_type="fatal error: 'xxx.h' file not found",
            known_root_cause="header typo, fix in PR #123",
        )
        self.assertIn("内部根因", remark)
        self.assertIn("PR #123", remark)

    def test_real_failure_no_commit_no_cause(self):
        """场景 5: 真失败, 没 commit 也没已知根因"""
        cls = {"category": "real_subjob_fail"}
        remark = build_remark(cls, error_type="some error")
        self.assertIn("待 git blame", remark)

    def test_remark_with_sub_console_key(self):
        """场景 6: 含 sub_console_key"""
        cls = {"category": "real_subjob_fail"}
        remark = build_remark(
            cls,
            error_type="some error",
            sub_console_key="fatal error: xxx | make: *** Error 1",
        )
        self.assertIn("sub_errs:", remark)
        self.assertIn("fatal error: xxx", remark)


class TestNoisePatterns(unittest.TestCase):
    """噪音模式通用化测试"""

    def test_default_patterns_exist(self):
        """场景 1: 默认噪音模式存在"""
        patterns = get_noise_patterns()
        self.assertGreater(len(patterns), 10)

    def test_user_patterns_from_env(self):
        """场景 2: 从 env 读取用户自定义模式"""
        import os
        os.environ["JOB_NAME_PATTERN"] = r"^\[MYPROJECT_\w+_trigger\]"
        patterns = _get_user_noise_patterns()
        self.assertEqual(len(patterns), 1)
        self.assertTrue(patterns[0].match("[MYPROJECT_xxx_trigger]"))
        del os.environ["JOB_NAME_PATTERN"]

    def test_multiple_user_patterns(self):
        """场景 3: 多个用户模式 (用 | 分隔)"""
        import os
        os.environ["JOB_NAME_PATTERN"] = r"^\[A_\w+\]|^X_b$"
        patterns = _get_user_noise_patterns()
        self.assertEqual(len(patterns), 2)
        del os.environ["JOB_NAME_PATTERN"]

    def test_no_user_patterns(self):
        """场景 4: 无 env 变量时返回空列表"""
        import os
        os.environ.pop("JOB_NAME_PATTERN", None)
        patterns = _get_user_noise_patterns()
        self.assertEqual(patterns, [])

    def test_combined_patterns(self):
        """场景 5: 默认 + 用户组合"""
        import os
        os.environ["JOB_NAME_PATTERN"] = r"^\[MY_\w+\]"
        patterns = get_noise_patterns()
        self.assertGreater(len(patterns), 10)  # 默认 + 用户
        del os.environ["JOB_NAME_PATTERN"]


class TestParseSubResults(unittest.TestCase):
    """parse_sub_results 函数测试"""

    def test_parse_multiple(self):
        """场景 1: 多个 sub"""
        results = parse_sub_results(CONSOLE_REAL_FAILURE)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], ("sm6650_bp", "FAILURE"))
        self.assertEqual(results[1][1], "ABORTED")

    def test_empty_console(self):
        """场景 2: 空 console"""
        self.assertEqual(parse_sub_results(""), [])

    def test_no_sub_results(self):
        """场景 3: 无 sub 结果"""
        self.assertEqual(parse_sub_results(CONSOLE_UNKNOWN), [])


# ============================================================================
# 测试运行
# ============================================================================

if __name__ == "__main__":
    # 详细输出
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 退出码
    sys.exit(0 if result.wasSuccessful() else 1)
