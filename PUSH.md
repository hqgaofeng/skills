# GitHub 推送记录

## ✅ 状态: 已推送

仓库已成功推送到 `git@github.com:hqgaofeng/skills.git`, 主分支 `main`.

## 推送详情

| 项 | 值 |
|----|----|
| 仓库 | https://github.com/hqgaofeng/skills |
| 远程 URL | `git@github.com:hqgaofeng/skills.git` |
| 推送时间 | 2026-06-13 |
| 推送方式 | SSH (`~/.ssh/id_rsa_bu3bj`) |
| 推送命令 | `GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa_bu3bj -o IdentitiesOnly=yes" git push -u origin main` |
| commit 数 | 2 (通用化 + 文档) |
| 文件数 | 29 |

## 推送流程 (留作参考)

### 1. 选 SSH key

本机有 4 把 SSH key, 测下来 `~/.ssh/id_rsa_bu3bj` (5/19, RSA 4096) 是 GitHub 唯一认可的那把:

```bash
for k in id_ed25519 id_rsa id_rsa_bu3bj id_rsa_2048_bu3bj; do
  ssh -i ~/.ssh/$k -o IdentitiesOnly=yes -T git@github.com 2>&1 | head -1
done
# id_rsa_bu3bj → Hi hqgaofeng!  ← 这把通过
```

fingerprint: `SHA256:1+twcnPQrlgg3aIB3mhFtbZCrTHLtAwlJTajrTDqJHg`

### 2. 配 remote + 推

```bash
cd ~/projects/hqgaofeng-skills-archive
git remote set-url origin git@github.com:hqgaofeng/skills.git
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa_bu3bj -o IdentitiesOnly=yes" git push -u origin main
```

### 3. 验证

```bash
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa_bu3bj -o IdentitiesOnly=yes" git ls-remote origin main
# 5a3c667...refs/heads/main  ← 远程 HEAD
```

## 推送后的后续操作 (CI 自动化)

仓库根目录已加 `.github/workflows/test.yml`, push 后会**自动**跑:
- Python 3.11 / 3.12 matrix
- jenkins-build-monitor 26 测试
- jenkins-user-sync-monitor 22 测试
- 汇总到 GitHub Actions summary

首次 push 后 CI 会自动触发, 在 https://github.com/hqgaofeng/skills/actions 可看.

## 本机 SSH 命令模板 (以后都用这个)

```bash
# ~/.bashrc 或临时
export GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa_bu3bj -o IdentitiesOnly=yes"
```

或者在仓库 `.git/config` 写死:

```ini
[core]
    sshCommand = ssh -i ~/.ssh/id_rsa_bu3bj -o IdentitiesOnly=yes
```

## 备选方案 (本仓库未使用)

如果以后 SSH 不通, 可降级到 HTTPS + PAT:

```bash
git remote set-url origin https://<TOKEN>@github.com/hqgaofeng/skills.git
git push origin main
```

## 失败排查

| 现象 | 原因 | 解法 |
|------|------|------|
| `Permission denied (publickey)` | 用的 key GitHub 不认 | 换 `id_rsa_bu3bj` 或重加公钥到 GitHub |
| `could not read Username` | HTTPS 没配 token | 改用 SSH, 或加 token 到 URL |
| `repository not found` | 没权限 / 仓库不存在 | 确认是仓库 owner, 有写权限 |
