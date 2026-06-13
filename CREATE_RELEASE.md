# 创建 v1.0.1 Release (5 秒手工操作)

## 现状

✅ v1.0.1 tag 已推送到 GitHub
✅ tarball 已生成在 `~/projects/hqgaofeng-skills-archive/dist/`
✅ CI 自动跑过 48 测试
❌ Release 没自动创建 (助手无 GitHub API PAT)

## 你只需 5 秒钟

1. 打开 https://github.com/hqgaofeng/skills/releases/new?tag=v1.0.1
2. 浏览器已自动填好 tag `v1.0.1` + target `main`
3. Release title 填: `v1.0.1: 仓库打磨 + CI/CD + Issue 模板`
4. 描述 (下面内容, 整段复制粘贴):
   ```
   # v1.0.1 - 仓库打磨: CI/CD + Issue 模板 + Badge

   ## 🎉 首次 CI 跑通
   [Tests workflow](https://github.com/hqgaofeng/skills/actions) 已配置:
   - Python 3.11 / 3.12 matrix
   - 48 个单测全过 (26 + 22)
   - 每次 push / PR 自动验证

   ## ✨ 新增
   - 🟢 **CI**: `.github/workflows/test.yml` 自动跑 48 测试
   - 🟢 **Issue 模板**: `bug` / `new-skill` / `improvement` 三种
   - 🟢 **README badges**: Tests / Skills / License / 零硬编码
   - 🟢 **PUSH.md**: 推送记录 (用了哪把 SSH key, 命令模板)

   ## 📋 验证
   - ✅ 本地: 48/48 测试通过
   - ✅ 远程: `72e4979` on `main`  
   - ✅ CI: https://github.com/hqgaofeng/skills/actions/runs/27466348684
   - ✅ 2 个 matrix (py3.11 + py3.12) 全 success
   ```
5. 底部点 **Publish release**

完成 ✅

## 或者 (可选) 想要附件

如果你想附加 tarball 让人直接下载:
- 下载 `~/projects/hqgaofeng-skills-archive/dist/jenkins-build-monitor-v1.2.0.tar.gz` 到本地
- 下载 `~/projects/hqgaofeng-skills-archive/dist/jenkins-user-sync-monitor-v1.1.0.tar.gz` 到本地
- 在 Release 页面底部拖进 "Attach binaries"

不附也行, 大家 clone 仓库就够用了.

## 如果想自动化 (下次)

需要给助手一个 GitHub PAT (fine-grained token, `contents: write` 范围).
加到 `~/.hermes/.env`:
```
GITHUB_TOKEN=github_pat_xxx
```

以后我就能 `curl -H "Authorization: Bearer $GITHUB_TOKEN" ...` 直接发 Release.
