# hqgaofeng/skills

> Hermes / OpenClaw 通用 skills 归档仓库 — 跨项目, 跨公司, 跨平台

## ✨ 这是什么

这是一个**通用 skill 归档仓库**. 每个 skill 都是独立可用的, 可以直接下载放到任何 Hermes 或 OpenClaw 实例的 `~/.hermes/skills/<category>/` 目录下使用.

**核心原则**:
- 🎯 **零硬编码** — 所有 IP / Token / 用户名 / 公司名 走环境变量
- 🌐 **跨平台** — Hermes / OpenClaw / 其他兼容 runtime 都用
- 🏢 **跨公司** — 同一份 skill 任何公司部署都不需改代码
- 📦 **独立可装** — 每个 skill 是独立目录, 不依赖其他 skill
- 🧪 **可测试** — 自带单测, 不依赖任何特定环境就能跑
- 📚 **文档最全** — SKILL.md + README.md + INSTALL.md + CHANGELOG.md + references/

## 📦 包含的 Skills

| Skill | 类别 | 适用场景 | 状态 |
|-------|------|----------|------|
| [jenkins-build-monitor](./skills/jenkins-build-monitor/) | DevOps / CI | 监控任意 Jenkins 编译任务, 自动分析失败根因 | ✅ v1.2.0 (通用化) |
| [jenkins-user-sync-monitor](./skills/jenkins-user-sync-monitor/) | DevOps / 监控 | 监控任意 Jenkins 用户同步任务, 提取失败记录 | ✅ v1.1.0 (通用化) |

## 🚀 快速使用

### 方式 1: git clone (推荐, 完整仓库)

```bash
git clone https://github.com/hqgaofeng/skills.git
cp -r skills/<skill-name> ~/.hermes/skills/devops/
```

### 方式 2: 直接下载单个 skill

去 [Releases](https://github.com/hqgaofeng/skills/releases) 下载对应 skill 的 tarball, 解压到 `~/.hermes/skills/devops/`.

### 方式 3: 单独 clone 目录 (用 sparse checkout)

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/hqgaofeng/skills.git
cd skills
git sparse-checkout set skills/jenkins-build-monitor
cp -r skills/jenkins-build-monitor ~/.hermes/skills/devops/
```

## 📥 安装配置

每个 skill 都有自己独立的 INSTALL.md, 详细说明:
- 环境要求
- 必需的环境变量
- Jenkins / Git / 飞书 等第三方配置
- 验证步骤

[查看通用安装指南 →](./INSTALL.md)

## 🤝 贡献

欢迎贡献新 skill! 阅读 [CONTRIBUTING.md](./CONTRIBUTING.md).

## 📜 许可证

[MIT](./LICENSE) — 自由使用, 修改, 分发.

## 📚 文档

- [INSTALL.md](./INSTALL.md) — 通用安装
- [CONTRIBUTING.md](./CONTRIBUTING.md) — 贡献流程
- [CHANGELOG.md](./CHANGELOG.md) — 仓库变更记录
- [docs/](./docs/) — 通用方法论文档 (FAQ, 故障排查, 设计原则)

## 关联项目

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Skill 体系原始 runtime
- [OpenClaw](https://github.com/) — 兼容 runtime (Gerrit 已迁移, 见 CHANGELOG)
