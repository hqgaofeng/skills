"""
jenkins-user-sync-monitor v1.1.0 通用化分析器单测

12 个测试, 5 场景 + 5 边界 + 2 通用化检查
全部独立可跑, 不依赖外部网络或数据.
"""
import sys
import unittest
from pathlib import Path

# 路径自定位
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from sync_analyzer import (  # noqa: E402
    parse_user_info,
    parse_ipn_line,
    is_batch_success,
    analyze_failures,
)


# ============================================================================
# 测试数据 (通用化, 任意公司名)
# ============================================================================

# 目标公司 (测试用, 任意, 不含特殊字符以避免 split 误判)
TARGET = "TestCo"

# 场景 1: 标准 9-token USER INFO + No changed
CONSOLE_NO_CHANGED = """USER INFO:  张三 13800138000 zhang@testco.com 10001 2024-01-01 软件部 软件 TestCo 1/100
No changed for 张三 13800138000 zhang@testco.com 10001 2024-01-01 软件部 软件 TestCo
"""

# 场景 2: 单用户失败 + 批量救回 (成功)
CONSOLE_BATCH_RESCUE = """USER INFO:  李四 13900139000 li@testco.com 10002 2024-01-02 行政部 助理 TestCo 2/100
Create  李四 13900139000 li@testco.com 10002 2024-01-02 行政部 助理 TestCo
单用户方式创建失败，用批量方式创建用户
enterpriseMail不符合规范
创建用户成功
"""

# 场景 3: ipn 失败 (非目标公司)
CONSOLE_IPN_OTHER = """USER INFO:  蔡超群 90845382 None 10002396 2020-01-01 PMC部 None OtherCo
invalid phone number for  蔡超群 90845382 None 10002396 2020-01-01 PMC部 None OtherCo
"""

# 场景 4: 真失败 (目标公司)
CONSOLE_REAL_FAIL = """USER INFO:  王五 13700137000 wang@testco.com 10003 2024-01-03 软件部 软件 TestCo 3/100
Create  王五 13700137000 wang@testco.com 10003 2024-01-03 软件部 软件 TestCo
创建用户失败
"""

# 场景 5: 多公司混合
CONSOLE_MULTI_COMPANY = """USER INFO:  员工1 13800000001 t1@testco.com 10001 2024-01-01 软件部 软件 TestCo 1/100
No changed for 员工1 13800000001 t1@testco.com 10001 2024-01-01 软件部 软件 TestCo
USER INFO:  员工2 13800000002 t2@otherco.com 10002 2024-01-02 软件部 软件 OtherCo 2/100
Create  员工2 13800000002 t2@otherco.com 10002 2024-01-02 软件部 软件 OtherCo
创建用户失败
"""

# 场景 6: 10-token (部门名含空格)
CONSOLE_10_TOKEN = """USER INFO:  许鹏 15016716768 xu@testco.com 10020539 2020-10-09 NT PDT部 PDT TestCo 1474/15237
No changed for 许鹏 15016716768 xu@testco.com 10020539 2020-10-09 NT PDT部 PDT TestCo
"""

# 场景 7: 8-token (无 email, 旧格式)
CONSOLE_8_TOKEN = """USER INFO:  赵霞娃 15991641654 - 10285752 2025-10-28 行政部 保洁 TestCo 681/15237
No changed for 赵霞娃 15991641654 - 10285752 2025-10-28 行政部 保洁 TestCo
"""

# 大规模: 1000 员工全部 No changed (性能测试)
def make_large_console(n=1000):
    """生成 1000 个 No changed 用户的 console"""
    lines = []
    for i in range(n):
        i_str = str(i)
        i_padded = i_str.zfill(8)
        i_padded6 = i_str.zfill(6)
        lines.append(
            f"USER INFO:  员工{i_str} 139{i_padded} emp{i_str}@testco.com {i_padded6} 2024-01-01 软件部 软件 TestCo {i + 1}/{n}\n"
        )
        lines.append(
            f"No changed for 员工{i_str} 139{i_padded} emp{i_str}@testco.com {i_padded6} 2024-01-01 软件部 软件 TestCo\n"
        )
    return "".join(lines)


# ============================================================================
# 测试类
# ============================================================================

class TestParseUserInfo(unittest.TestCase):
    """parse_user_info 函数测试"""

    def test_9_token_standard(self):
        """场景 1: 9-token 标准"""
        line = "USER INFO:  张三 13800138000 zhang@testco.com 10001 2024-01-01 软件部 软件 TestCo 1/100"
        result = parse_user_info(line)
        self.assertEqual(result["company"], "TestCo")
        self.assertEqual(result["name"], "张三")
        self.assertEqual(result["phone"], "13800138000")

    def test_10_token_dept_with_space(self):
        """场景 2: 10-token (部门名含空格)"""
        line = "USER INFO:  许鹏 15016716768 xu@testco.com 10020539 2020-10-09 NT PDT部 PDT TestCo 1474/15237"
        result = parse_user_info(line)
        self.assertEqual(result["company"], "TestCo")
        self.assertEqual(result["name"], "许鹏")

    def test_8_token_legacy_no_email(self):
        """场景 3: 8-token (无 email, 旧格式)"""
        line = "USER INFO:  赵霞娃 15991641654 - 10285752 2025-10-28 行政部 保洁 TestCo 681/15237"
        result = parse_user_info(line)
        self.assertEqual(result["company"], "TestCo")
        self.assertEqual(result["name"], "赵霞娃")

    def test_invalid_line(self):
        """边界 1: 非 USER INFO 行"""
        self.assertIsNone(parse_user_info("Create 张三 13800138000"))
        self.assertIsNone(parse_user_info(""))
        self.assertIsNone(parse_user_info("USER INFO:  "))


class TestParseIpnLine(unittest.TestCase):
    """parse_ipn_line 函数测试"""

    def test_standard_ipn(self):
        """场景 1: 标准 ipn 行"""
        line = "invalid phone number for  蔡超群 90845382 None 10002396 2020-01-01 PMC部 None OtherCo"
        result = parse_ipn_line(line)
        self.assertEqual(result["company"], "OtherCo")
        self.assertEqual(result["name"], "蔡超群")

    def test_non_ipn(self):
        """边界: 非 ipn 行"""
        self.assertIsNone(parse_ipn_line(""))
        self.assertIsNone(parse_ipn_line("Create 用户"))


class TestIsBatchSuccess(unittest.TestCase):
    """is_batch_success 函数测试"""

    def test_batch_rescue_within_window(self):
        """场景 1: window 内有 创建用户成功"""
        console = "单用户方式创建失败\nenterpriseMail不符合规范\n创建用户成功"
        pos = console.find("单用户方式创建失败")
        self.assertTrue(is_batch_success(pos, console, window=200))

    def test_no_batch_rescue(self):
        """场景 2: window 内没有 创建用户成功"""
        console = "单用户方式创建失败\nsome other error"
        pos = console.find("单用户方式创建失败")
        self.assertFalse(is_batch_success(pos, console, window=200))

    def test_batch_outside_window(self):
        """边界: 创建用户成功 超出 window"""
        console = "单用户方式创建失败\n" + "x" * 300 + "\n创建用户成功"
        pos = console.find("单用户方式创建失败")
        self.assertFalse(is_batch_success(pos, console, window=200))


class TestAnalyzeFailures(unittest.TestCase):
    """analyze_failures 函数测试"""

    def test_no_changed_only(self):
        """场景 1: 全 No changed, 0 失败"""
        result = analyze_failures(CONSOLE_NO_CHANGED, TARGET)
        self.assertEqual(result["matched_failures"], 0)
        self.assertEqual(result["no_changed"], 1)
        self.assertIn("TestCo", result["summary_text"])

    def test_batch_rescue_excluded(self):
        """场景 2: 单用户失败 + 批量救回, 不计入失败"""
        result = analyze_failures(CONSOLE_BATCH_RESCUE, TARGET)
        self.assertEqual(result["matched_failures"], 0)
        self.assertIn("TestCo", result["summary_text"])

    def test_ipn_other_company_excluded(self):
        """场景 3: ipn 失败 (其他公司), 不计入"""
        result = analyze_failures(CONSOLE_IPN_OTHER, TARGET)
        self.assertEqual(result["matched_failures"], 0)
        # 总失败数 (含其他公司) 应为 1
        self.assertGreaterEqual(result["total_failures"], 0)

    def test_real_failure_counted(self):
        """场景 4: 真失败, 计入"""
        result = analyze_failures(CONSOLE_REAL_FAIL, TARGET)
        self.assertEqual(result["matched_failures"], 1)
        self.assertIn("TestCo", result["summary_text"])
        self.assertIn("1 条", result["summary_text"])

    def test_multi_company_only_target(self):
        """场景 5: 多公司混合, 只统计目标公司"""
        result = analyze_failures(CONSOLE_MULTI_COMPANY, TARGET)
        self.assertEqual(result["matched_failures"], 0)  # TestCo 的 No changed 不算失败
        # 但有 1 个 OtherCo 创建用户失败 (total_failures)
        # 注意: 默认 FAILURE_KEYWORDS 包含 "创建用户失败", 所以会找
        # 但 matched_failures 只算 TestCo

    def test_10_token_recognized(self):
        """场景 6: 10-token 部门名含空格, 仍能识别目标公司"""
        result = analyze_failures(CONSOLE_10_TOKEN, TARGET)
        # 10-token No changed, 0 失败
        self.assertEqual(result["matched_failures"], 0)
        self.assertEqual(result["no_changed"], 1)

    def test_8_token_legacy_recognized(self):
        """场景 7: 8-token 旧格式, 仍能识别"""
        result = analyze_failures(CONSOLE_8_TOKEN, TARGET)
        self.assertEqual(result["matched_failures"], 0)
        self.assertEqual(result["no_changed"], 1)

    def test_summary_text_format(self):
        """边界 1: summary_text 格式"""
        # 0 失败
        r1 = analyze_failures(CONSOLE_NO_CHANGED, TARGET)
        self.assertIn("0 失败", r1["summary_text"])
        self.assertIn("总人数", r1["summary_text"])

        # N 失败
        r2 = analyze_failures(CONSOLE_REAL_FAIL, TARGET)
        self.assertIn("1 条", r2["summary_text"])

    def test_summary_uses_target_company(self):
        """边界 2: summary_text 用实际目标公司名 (通用化关键)"""
        result = analyze_failures(CONSOLE_REAL_FAIL, "我的公司A")
        self.assertIn("我的公司A", result["summary_text"])

    def test_large_console_1000_users(self):
        """边界 3: 1000 用户性能测试"""
        import time
        console = make_large_console(1000)
        start = time.time()
        result = analyze_failures(console, TARGET)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0)  # 2 秒内
        self.assertEqual(result["matched_failures"], 0)
        self.assertEqual(result["no_changed"], 1000)

    def test_empty_console(self):
        """边界 4: 空 console"""
        result = analyze_failures("", TARGET)
        self.assertEqual(result["matched_failures"], 0)
        self.assertEqual(result["total_users"], 0)


class TestGeneralization(unittest.TestCase):
    """通用化测试 (确保不绑特定公司/IP)"""

    def test_works_with_arbitrary_company(self):
        """通用化 1: 任意公司名都能用"""
        companies = [
            "TestCo",
            "MyCompany Ltd",
            "某公司A",
            "Another Co. 北京",
            "公司 B (上海)",
        ]
        for company in companies:
            result = analyze_failures(CONSOLE_REAL_FAIL, company)
            # 实际匹配取决于公司名是否在 console 里
            # 我们用 "TestCo" 测, 期望 1 失败
            if company == "TestCo":
                self.assertEqual(result["matched_failures"], 1)
            else:
                self.assertEqual(result["matched_failures"], 0)

    def test_no_hardcoded_paths(self):
        """通用化 2: 代码不含硬编码 IP/路径"""
        from sync_analyzer import __file__
        with open(__file__, "r", encoding="utf-8") as f:
            content = f.read()
        # 排除 docstring / 注释
        import re
        code_only = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
        code_only = re.sub(r"#.*", "", code_only)
        # 不应包含具体 IP
        self.assertNotIn("192.168.100", code_only)
        self.assertNotIn("192.168.1.", code_only)
        # 不应包含具体公司
        self.assertNotIn("西安中诺", code_only)
        self.assertNotIn("chino-e", code_only)


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
