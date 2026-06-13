# 编译错误路径 → Git Root 推断方法论 (通用模板)

> **v1.2.0 通用化重写**: 之前 `bp-workspace-git-structure.md` 绑了 SM68B / boot_images 等特定项目, 现改为**通用方法论 + 模板**, 用户按项目结构填具体路径.

## 核心问题

编译错误日志里报的**报错文件路径**往往是**绝对路径**, 但 `git blame` 需要:
1. 知道 `.git` 目录在哪 (git root)
2. 知道相对 git root 的**文件相对路径**

## 通用方法 (4 步)

### Step 1: 从编译日志提取报错文件路径

匹配模式 (按优先级):

| 模式 | 示例 | 语言 |
|------|------|------|
| `fatal error:.*? file not found` | `fatal error: 'Uefixx.h' file not found` | C/C++ |
| `make: \*\*\* \[(.+?)\] Error` | `make: *** [ChargerLibCommon.o] Error 1` | Make |
| `error F\d+:.*` | `error F002: Failed to build module` | 通用 |
| `FileNotFoundError:.*?([\w/.-]+\.\w+)` | `FileNotFoundError: [Errno 2] No such file or directory: 'xxx.txt'` | Python |
| `\.go:\d+:\d+:` | `./main.go:10:5: undefined: foo` | Go |
| `error\[E\d+\]:.*?([\w/.-]+\.rs)` | `error[E0432]: unresolved import ./module` | Rust |

### Step 2: 识别 .git 所在目录

**通用规律**: 大型项目通常 `.git` 在**根目录**或**次级目录**.

常见模式:

| 项目类型 | 示例 | .git 位置 |
|----------|------|-----------|
| Android (QCOM/MTK) | `boot_images/`, `vendor/qcom/`, `kernel/` | `boot_images/.git` (每个模块独立) |
| Android (AOSP) | `frameworks/base/`, `packages/apps/Settings/` | `frameworks/base/.git` |
| iOS | `MyApp.xcodeproj`, `Pods/` | 仓库根 `.git` |
| 前端 monorepo | `packages/web/`, `packages/mobile/` | 每个 package 独立 `.git` |
| 后端微服务 | `services/user/`, `services/order/` | 仓库根 `.git` (monorepo) 或每个服务独立 |
| C++ 单体 | `src/`, `include/`, `third_party/` | 仓库根 `.git` |
| 嵌入式 | `app/`, `driver/`, `middleware/` | 仓库根或 app/ 独立 |

**判断方法** (任意一个满足即可):
1. 从 sub-job workspace 路径开始, 逐级向上找 `.git` (即 `test -d <path>/.git`)
2. 匹配项目专用规则 (见下文 "项目专用规则模板")
3. 询问: 该路径下 `git log` 能跑通吗? 跑通说明对了

### Step 3: 计算报错文件的 git 相对路径

**核心**: `git relative path = (报错文件绝对路径 - git root)`

```python
import os.path
import posixpath

def make_relative_path(error_file_abs, git_root):
    """计算报错文件相对 git root 的路径"""
    # 标准化路径
    error_file_abs = os.path.normpath(error_file_abs)
    git_root = os.path.normpath(git_root)

    # 用 posixpath 保证用 / 分隔 (跨平台)
    if error_file_abs.startswith(git_root):
        rel = posixpath.relpath(error_file_abs, git_root)
        return rel
    return None
```

### Step 4: git blame 验证

```python
cmd = f"cd {git_root} && git blame -L {line_num},{line_num} {rel_path}"
```

如果 `git blame` 输出 `fatal: no such path`, 说明 git root 算错了.

## 项目专用规则模板

**把你的项目结构填这里**, 然后用**:

```python
# 项目规则示例: Android QCOM 多仓库
GIT_ROOT_RULES = [
    # 路径前缀 → git root (从 workspace 起始)
    ("boot_images/", "boot_images"),
    ("vendor/qcom-proprietary/", "vendor/qcom-proprietary"),
    ("vendor/qcom/", "vendor/qcom"),
    ("kernel/", "kernel"),
    ("trustzone_images/", "trustzone_images"),
    ("common/", "common"),
    # 默认
    ("", ""),  # workspace 根
]

def find_git_root(error_file_abs: str, workspace: str) -> str:
    """根据项目规则找 git root"""
    rel_to_workspace = os.path.relpath(error_file_abs, workspace)
    for prefix, git_subdir in GIT_ROOT_RULES:
        if rel_to_workspace.startswith(prefix):
            if git_subdir:
                return os.path.join(workspace, git_subdir)
            return workspace
    return workspace  # fallback
```

## 实际案例

### 案例 1: Android QCOM (SM68B / SM6650)

**项目结构**:
```
/home/ontim/BP_SPACE/SM6650_do/BP/BOOT.MXF.2.1/boot_images/  ← git root
                                                       boot/QcomPkg/Library/ChargerLib/ChargerLibCommon.c
```

**报错**:
```
fatal error: 'Uefixx.h' file not found
#include <Uefixx.h>  (ChargerLibCommon.c 第 88 行)
```

**推断**:
- 报错文件 abs: `/home/ontim/BP_SPACE/SM6650_do/BP/BOOT.MXF.2.1/boot_images/boot/QcomPkg/Library/ChargerLib/ChargerLibCommon.c`
- `.git` 目录: `boot_images/`
- 相对路径: `boot/QcomPkg/Library/ChargerLib/ChargerLibCommon.c`

**git blame**:
```bash
cd /home/ontim/BP_SPACE/SM6650_do/BP/BOOT.MXF.2.1/boot_images
git blame -L 88,88 boot/QcomPkg/Library/ChargerLib/ChargerLibCommon.c
```

### 案例 2: iOS 单仓库

**项目结构**:
```
/Users/builder/iOS/MyApp/  ← git root
                       MyApp/ViewController.m
                       Pods/AFNetworking/...
```

**报错**:
```
Undefined symbols for architecture arm64:
  "_OBJC_CLASS_$_AFHTTPRequestOperation", referenced from:
```

**推断**:
- 报错文件 abs: `/Users/builder/iOS/MyApp/Pods/AFNetworking/AFNetworking/AFHTTPRequestOperation.m`
- `.git` 目录: 仓库根 `MyApp/` (因为 Pods/ 是 git submodule, 但 submodule 本身有独立 .git)
- 相对路径: `Pods/AFNetworking/AFNetworking/AFHTTPRequestOperation.m`

### 案例 3: Go 微服务

**项目结构**:
```
/home/builder/services/user-service/  ← git root
                                  cmd/main.go
                                  internal/user/handler.go
```

**报错**:
```
./main.go:10:5: undefined: foo
```

**推断**:
- 报错文件 abs: `/home/builder/services/user-service/cmd/main.go`
- `.git` 目录: 仓库根
- 相对路径: `cmd/main.go`

### 案例 4: Web monorepo

**项目结构**:
```
/home/builder/web-monorepo/  ← 顶层 .git
                         packages/
                           web/src/App.tsx
                           mobile/src/screen.tsx
                           shared/utils/date.ts
```

**报错**:
```
TypeError: date.format is not a function
  at App.tsx:42:15
```

**推断**:
- 报错文件 abs: `/home/builder/web-monorepo/packages/web/src/App.tsx`
- `.git` 目录: monorepo 根
- 相对路径: `packages/web/src/App.tsx`

## 验证清单

填好项目规则后, 验证:

- [ ] 用一个已知失败的 build, 看报错文件路径
- [ ] 用项目规则推断 git root
- [ ] 在推断的 git root 跑 `git status`, 应有内容
- [ ] 跑 `git blame -L <line>,<line> <rel_path>`, 应有输出
- [ ] 输出格式: `<hash> (<author> <date> <line>) <code>`

如果**任何一步失败**, 调整规则.

## 高级: 跨项目自学习

**用配置驱动**, 不写代码:

```bash
# ~/.hermes/.env 追加
# 格式: <路径前缀>=<git_subdir> (多行, 用 ; 分隔)
# 例: Android QCOM 多仓库
WORKSPACE_GIT_RULES=boot_images=boot_images;vendor/qcom=vendor/qcom;kernel=kernel;
```

**读取并用**:
```python
def load_git_rules():
    rules_str = os.environ.get("WORKSPACE_GIT_RULES", "")
    if not rules_str:
        return [("", "")]  # 默认
    rules = []
    for pair in rules_str.split(";"):
        if not pair:
            continue
        key, val = pair.split("=", 1)
        rules.append((key, val))
    return rules
```

## 错误处理

| 情况 | 表现 | 解决 |
|------|------|------|
| 路径含 `~` (home 展开) | 找不到 | 用 `os.path.expanduser()` 展开 |
| 路径含相对路径 (`.` `..`) | 路径比对失败 | 用 `os.path.normpath()` 标准化 |
| 路径跨平台分隔符 (`\` vs `/`) | 比对失败 | 用 `posixpath` 或 `os.path.relpath` |
| 报错文件在 .git 之外 (构建产物) | 找不到 .git | 跳过 git blame, 归类为构建产物问题 |
| git root 推断错 | `fatal: no such path` | 用 `test -d $git_root/.git` 验证 |

## 通用化变更历史

- **v1.0 (SM68B 专属)**: 写死 SM68B / boot_images 路径
- **v1.2.0 (通用化)**: 改为模板 + 配置驱动, 任何项目可用
