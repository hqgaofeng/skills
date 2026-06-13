# 贡献指南

欢迎为 **hqgaofeng/skills** 贡献新 skill 或改进现有 skill.

## 📋 目录

- [通用化原则](#通用化原则)
- [Skill 结构规范](#skill-结构规范)
- [添加新 Skill](#添加新-skill)
- [代码风格](#代码风格)
- [测试要求](#测试要求)
- [文档要求](#文档要求)
- [Commit & PR 流程](#commit--pr-流程)
- [归档新版本](#归档新版本)

## 通用化原则

**这是最重要的部分. 通用化没做好的 skill 不能进库.**

### ✅ 必须做到 (Skill 入库 7 大原则)

1. **零硬编码** — 任何 IP / Token / 用户名 / 公司名 / 项目名 **必须** 走环境变量
2. **路径自定位** — Python 脚本用 `Path(__file__).parent` 替代 `~/.hermes/skills/...`
3. **方法论与数据分离** — 一次性数据分析结果进 `archive/`, 不进主代码
4. **跨平台兼容** — Hermes / OpenClaw / 其他 runtime 都能跑
5. **可独立测试** — `python3 scripts/test_*.py` 必须独立跑通, 不依赖外部服务
6. **完整文档** — SKILL.md + README.md + INSTALL.md + CHANGELOG.md
7. **真实可跑** — 用真 Jenkins / 飞书 / SSH 测过, 不是"理论上能跑"

### ❌ 禁止出现的

- 硬编码 IP (例: `192.168.100.207`)
- 硬编码 token (例: `MZoAskdPjhFjH6tWVvCcT2QxnIe`)
- 硬编码 chat_id (例: `oc_44da7dfa79fffbe14c32639aecb510cc`)
- 硬编码用户名 (例: `ontim`, `feng.gao`)
- 硬编码密码 (例: `ontim123!`)
- 硬编码公司名 (例: `西安中诺通讯有限公司`)
- 硬编码项目名 (例: `SM68B`, `boot_images`)
- 硬编码 Git SSH 公钥

### ✅ 通用化方法

| 硬编码 | 通用化方案 |
|--------|------------|
| IP / URL | 环境变量 `JENKINS_URL`, `BUILD_SERVER_URL` |
| Token / Key | 环境变量 `FEISHU_APP_ID`, `WX_WORK_WEBHOOK_URL_GENERAL` |
| chat_id | 环境变量 `FEISHU_CHAT_ID` |
| 用户名 | 环境变量 `JENKINS_USER`, `BUILD_SERVER_USER` |
| 密码 | 环境变量 `JENKINS_PASS`, `BUILD_SERVER_PASS` (`.env` 加载) |
| 公司名 | 环境变量 `TARGET_COMPANY` (用户部署时改成自己的) |
| 项目名 | 从 Jenkins API 取, 不硬编码 |
| SSH key | 部署时由用户自己加, 不预置 |
| 文件路径 | `Path(__file__).parent / "references"` |

### 示例: 通用化前 vs 后

#### ❌ 通用化前 (硬编码, 禁止入库)

```python
# ~/.hermes/skills/devops/jenkins-build-monitor/scripts/analyze.py
JENKINS_URL = "http://192.168.100.207:8080"
JENKINS_USER = "jenkins"
JENKINS_PASS = "ontim123!"
SHEETS_TOKEN = "MZoAskdPjhFjH6tWVvCcT2QxnIe"
CHAT_ID = "oc_44da7dfa79fffbe14c32639aecb510cc"
```

#### ✅ 通用化后 (零硬编码, 可入库)

```python
# ~/.hermes/skills/devops/jenkins-build-monitor/scripts/analyze.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.hermes/.env"))

JENKINS_URL = os.environ["JENKINS_URL"]
JENKINS_USER = os.environ["JENKINS_USER"]
JENKINS_PASS = os.environ["JENKINS_PASS"]
SHEETS_TOKEN = os.environ.get("FEISHU_SHEETS_TOKEN_BUILD", "")
CHAT_ID = os.environ.get("FEISHU_CHAT_ID", "")

# 路径自定位
SKILL_DIR = Path(__file__).parent.parent
REFERENCES_DIR = SKILL_DIR / "references"
```

## Skill 结构规范

每个 skill 必须长这样:

```
skills/<skill-name>/
├── SKILL.md             # skill 描述 (给 agent 读) — 必填
├── README.md            # 给开发者/部署者读的入口 — 必填
├── INSTALL.md           # 安装 / 配置 / 验证 — 必填
├── CHANGELOG.md         # 变更记录 — 必填
├── references/          # 详细文档 / 模板 — 可选但推荐
│   ├── *.md
│   └── *.py
├── scripts/             # 可执行脚本 — 必填
│   ├── *.py
│   └── test_*.py        # 单测
├── archive/             # 历史快照 / 一次性分析 — 可选
│   └── *.md
└── .env.example         # 环境变量示例 — 必填
```

### 文件要求

| 文件 | 行数目标 | 必填项 |
|------|----------|--------|
| SKILL.md | 300-800 | name, description, version, frontmatter, 触发条件, 执行流程, 注意事项 |
| README.md | 100-300 | 简介, 快速开始, 关键文件索引, 链接到 INSTALL.md / SKILL.md |
| INSTALL.md | 200-500 | 环境要求, 必需变量, 验证步骤, 故障排查 |
| CHANGELOG.md | 30+ | 每版本一条, 格式 `[日期] [版本] - 变更内容` |
| references/*.md | 不限 | 详细 API 说明 / 数据结构 / 错误码 / FAQ |
| scripts/*.py | 不限 | 必须带 if __name__ == "__main__" 入口 |
| scripts/test_*.py | 200+ | 至少 5 场景 + 5 边界 case |

## 添加新 Skill

### 1. 准备

```bash
cd ~/projects/hqgaofeng-skills-archive
mkdir -p skills/<skill-name>/{references,scripts}
```

### 2. SKILL.md frontmatter

```yaml
---
name: <skill-name>           # kebab-case, 类级别, 不带具体项目标识
description: "..."           # 一句话清晰说明做什么, 适合什么场景
version: 1.0.0
metadata:
  hermes:
    tags: [tag1, tag2]
    related_skills: [other-skill]
---
```

**命名**:
- ✅ `jenkins-build-monitor` (通用)
- ✅ `feishu-sheets-writer` (通用)
- ❌ `jenkins-sm68b-monitor` (绑定具体项目)
- ❌ `xianzhongnuo-user-sync` (绑定具体公司)

### 3. 实现

参考现有 skill (`skills/jenkins-build-monitor/`) 作为模板. 重点:
- 路径用 `Path(__file__).parent`
- 配置用 `os.environ.get(...)` + `load_dotenv`
- 关键逻辑拆成 pure function, 便于单测

### 4. 写测试

```python
# scripts/test_<feature>.py
import unittest
import sys
from pathlib import Path

# 让脚本能 import 同一目录的模块
sys.path.insert(0, str(Path(__file__).parent))

from your_module import core_function

class TestCoreFunction(unittest.TestCase):
    def test_normal_case(self):
        ...
    def test_empty_input(self):
        ...
    def test_invalid_input(self):
        ...
    def test_large_input(self):
        ...
    def test_concurrent(self):
        ...

if __name__ == "__main__":
    unittest.main()
```

要求: **至少 5 场景 + 5 边界 case, 全部通过**.

### 5. 文档

**SKILL.md** 必须包含:
- 一句话 description (frontmatter)
- 触发条件
- 完整执行流程 (含代码示例)
- 环境变量清单
- 错误码 / 边界处理
- 注意事项

**README.md** 必须包含:
- 一句话简介
- 适用场景
- 快速开始 (3 步内)
- 关键文件索引
- 链接到 SKILL.md / INSTALL.md / CHANGELOG.md

**INSTALL.md** 必须包含:
- 环境要求
- 必需的环境变量
- Jenkins / 飞书 等第三方配置
- 验证步骤 (含具体命令)
- 故障排查

**CHANGELOG.md** 格式:

```markdown
# 更新日志

## [1.0.0] - 2026-XX-XX

### 新增
- ...

### 修复
- ...

### 破坏性变更 (如有)
- ...
```

### 6. .env.example

每个 skill 都提供 `.env.example` 列出所有用到的环境变量:

```bash
# ~/.hermes/.env 追加

# === <skill-name> ===
JENKINS_URL=
JENKINS_USER=
JENKINS_PASS=
FEISHU_APP_ID=
FEISHU_APP_SECRET=
```

### 7. 提交 PR

```bash
git add skills/<skill-name>/
git commit -m "feat(<skill-name>): 通用化 v1.0.0

- 零硬编码: 所有 IP/Token 走环境变量
- 路径自定位: Path(__file__).parent
- 自带单测: scripts/test_*.py
- 完整文档: SKILL.md + README.md + INSTALL.md + CHANGELOG.md
- 跨平台兼容: Hermes + OpenClaw

测试: python3 skills/<skill-name>/scripts/test_*.py → X/X 通过"
git push -u origin main
```

## 代码风格

### Python

- **PEP 8** + **black** (line-length 100)
- **类型提示** (Python 3.8+ 兼容)
- **Docstring** (Google 风格)
- **避免全局变量**, 用 `main()` 函数 + 参数
- **异常处理**: 不吞 `except Exception: pass`, 显式 raise 或 log

### Markdown

- 中文标点 (句号, 逗号, 括号等)
- 标题层级不超过 3 (h3 后用 `**加粗**` 代替)
- 代码块标语言 (` ```python `, ` ```bash `)
- **不用 markdown 表格** 给 IM 消息 (飞书 IM 不渲染), 用 `**字段** + 列表`

## 测试要求

每个 skill 必须自带测试, 不依赖外部服务:

| 要求 | 说明 |
|------|------|
| **单测** | `scripts/test_*.py`, 至少 5 场景 + 5 边界 |
| **独立可跑** | `python3 scripts/test_*.py` 直接通过 |
| **零外部依赖** | 不调真实 Jenkins / 飞书 / SSH |
| **覆盖率** | 核心 pure function 100%, 总覆盖率 ≥ 60% |
| **CI 必跑** | PR 触发 CI, 测试挂掉不能 merge |

### 推荐的测试结构

```python
# scripts/test_analyzer.py
import unittest
from unittest.mock import patch, MagicMock
from analyzer import parse_console, classify_failure, summarize_failures

class TestParseConsole(unittest.TestCase):
    def setUp(self):
        self.sample_console = """
        Finished Build : sm68b_bp with status : FAILURE
        USER INFO:  张三 13800138000 user@x.com 10001 2024-01-01 行政部 保洁 西安中诺通讯有限公司 1/100
        """
    
    def test_extract_failure_keyword(self):
        result = parse_console(self.sample_console)
        self.assertEqual(len(result["failures"]), 1)
    
    def test_filter_by_company(self):
        result = parse_console(self.sample_console, target_company="西安中诺通讯有限公司")
        self.assertEqual(result["matched"], 1)
    
    def test_empty_console(self):
        result = parse_console("")
        self.assertEqual(result["failures"], [])
    
    def test_no_target_company(self):
        result = parse_console(self.sample_console, target_company="其他公司")
        self.assertEqual(result["matched"], 0)
    
    def test_malformed_user_info(self):
        bad = "USER INFO:  malformed"
        result = parse_console(bad)
        self.assertEqual(result["failures"], [])
    
    # 性能
    def test_large_console_10mb(self):
        huge = self.sample_console * 100000
        result = parse_console(huge)
        self.assertIsNotNone(result)

if __name__ == "__main__":
    unittest.main()
```

## 文档要求

文档是 skill 的**第一公民**. 提交前自查:

```markdown
- [ ] SKILL.md 完整 (frontmatter + 触发条件 + 流程 + 变量 + 注意事项)
- [ ] README.md 入口清晰 (简介 + 快速开始 + 文件索引)
- [ ] INSTALL.md 步骤具体 (含命令, 不只是"配置环境变量")
- [ ] CHANGELOG.md 格式正确 ([日期] [版本] - 变更)
- [ ] .env.example 列出所有变量
- [ ] 引用了真实数据 / 真实测试结果
- [ ] 没有硬编码 (IP/Token/用户名/公司名/项目名)
- [ ] 飞书 IM 警告已加 (如果用飞书通知)
- [ ] 链接到根 INSTALL.md 和相关 skill
```

## Commit & PR 流程

### Commit 规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**: `feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `ci`

**Scope**: skill 名 (`jenkins-build-monitor`)

**Subject**: 中文, 祈使句, < 72 字符

**示例**:

```
feat(jenkins-build-monitor): 通用化 v1.2.0

- 去除所有硬编码 (IP, Token, 用户名, 公司名)
- 路径自定位 (Path(__file__).parent)
- 拆分 test_*.py 独立可跑
- 补 README + INSTALL + CHANGELOG + .env.example

测试: scripts/test_v114.py → 11/11 通过
```

### PR 流程

1. Fork 仓库
2. 建分支 `feat/<skill-name>-generalize`
3. 改 + 测 + commit
4. 跑 `python3 scripts/test_*.py` 确保通过
5. 跑自检脚本 `scripts/audit_hardcoded.py` (如有)
6. 提 PR, 描述: 改了啥, 为啥, 测试结果
7. CI 全绿 + 1 个 review → merge

## 归档新版本

当 skill 发布新版本, 在仓库根做这些事:

1. 更新 `skills/<skill>/CHANGELOG.md` 顶部
2. 更新 `CHANGELOG.md` (仓库级) 顶部
3. GitHub Release 写 changelog
4. 发到 Telegram 群 (可选)

## 资源

- [Hermes Agent skill 文档](https://hermes-agent.nousresearch.com/docs/skills)
- [Unipython 编码规范](https://peps.python.org/pep-0008/)
- [Keep a Changelog 规范](https://keepachangelog.com/zh-CN/1.1.0/)
- [semver 语义化版本](https://semver.org/lang/zh-CN/)
