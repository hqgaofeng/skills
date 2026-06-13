# 推送到 GitHub

本地已 `git init` + `git add` + `git commit` 完成. 仓库在 `~/projects/hqgaofeng-skills-archive/`, 1 个 commit, 28 个文件.

由于助手**没有 GitHub 凭据**, 需要你**手动推一次**.

## 选项 1: HTTPS + Personal Access Token (推荐)

```bash
cd ~/projects/hqgaofeng-skills-archive

# 1. 创建 Personal Access Token
#    https://github.com/settings/tokens
#    - 选 "Fine-grained tokens" 或 "Personal access tokens (classic)"
#    - Scope: 勾 `repo` (完整仓库权限)
#    - 复制 token (形如 ghp_xxxxx)

# 2. 配置 remote (用 token 替换)
git remote set-url origin https://<TOKEN>@github.com/hqgaofeng/skills.git

# 3. 推送
git push -u origin main

# 4. 验证
#    https://github.com/hqgaofeng/skills 应该有 28 个文件
```

## 选项 2: SSH Key

```bash
# 1. 检查 / 生成 SSH key
ls ~/.ssh/id_rsa.pub  # 如果不存在:
ssh-keygen -t ed25519 -C "your.email@company.com"
# 密码留空

# 2. 把公钥加到 GitHub
#    https://github.com/settings/keys
#    点 "New SSH key", 粘贴 ~/.ssh/id_rsa.pub 内容

# 3. 改 remote
cd ~/projects/hqgaofeng-skills-archive
git remote set-url origin git@github.com:hqgaofeng/skills.git

# 4. 推送
git push -u origin main
```

## 选项 3: GitHub CLI

```bash
# 1. 安装 gh (如果没装)
#    https://cli.github.com/manual/installation

# 2. 登录
gh auth login
# 选 HTTPS, 浏览器登录

# 3. 推送
cd ~/projects/hqgaofeng-skills-archive
git push -u origin main
```

## 推送后

### 验证

访问 https://github.com/hqgaofeng/skills, 看到:
- README.md 渲染正常
- 28 个文件
- 1 个 commit

### 创建 Release (可选)

```bash
# 打 tag
cd ~/projects/hqgaofeng-skills-archive
git tag v1.0.0 -m "v1.0.0: 通用化归档, 2 个 skill 零硬编码"
git push origin v1.0.0

# 在 GitHub 上:
# https://github.com/hqgaofeng/skills/releases/new
# 选 v1.0.0 tag, 写 changelog (从 CHANGELOG.md 复制)
```

### 下次更新 (后续)

```bash
# 拉新版本
cd ~/projects/hqgaofeng-skills-archive
git pull origin main

# 改代码 / 加 skill

# 提交
git add -A
git commit -m "feat: 新增 xxx skill"
git push origin main
```

## 失败排查

### Q: `could not read Username` 错误

凭据没配, 见上面选项 1/2/3.

### Q: `Permission denied`

- HTTPS: 检查 token 有 `repo` scope
- SSH: 检查 `~/.ssh/id_rsa.pub` 在 GitHub 里

### Q: 推送大文件 (>100MB) 报错

- LFS: `git lfs install` + `git lfs track "*.psd"` 等
- 我们的 skill 文件都很小, 应该不会

## 资源

- [GitHub Personal Access Token 文档](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [GitHub SSH 文档](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [GitHub CLI 文档](https://cli.github.com/manual/)
