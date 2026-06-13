# 仓库变更日志

本仓库的版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范.
每个 skill 单独管理版本, 见 `skills/<skill-name>/CHANGELOG.md`.

## [Unreleased]

### 计划
- 添加 `feishu-sheets-writer` skill (通用飞书 Sheets 写入)
- 添加 `webhook-receiver-template` skill (通用 webhook 接收模板)
- 完善 `docs/troubleshooting.md` 通用故障排查

## [1.0.0] - 2026-06-13

### 新增
- **仓库门面**
  - `README.md` — 项目简介 + 快速使用
  - `LICENSE` — MIT
  - `INSTALL.md` — 通用安装指南 (单 skill / 批量 / 多机 / K8s)
  - `CONTRIBUTING.md` — 贡献流程 + 通用化 7 大原则
  - `CHANGELOG.md` (本文件)

- **skills/jenkins-build-monitor v1.2.0 (通用化重写)**
  - 去除所有硬编码 (IP, Token, 用户名, 公司名, 项目名, SSH 公钥)
  - 路径自定位 (`Path(__file__).parent`)
  - 配置走 `~/.hermes/.env` 环境变量
  - 文档: SKILL.md + README.md + INSTALL.md + CHANGELOG.md + .env.example
  - 测试: 11 场景 + 5 边界 case, 全部独立可跑
  - references/ 拆分为通用方法论 + 可选模板

- **skills/jenkins-user-sync-monitor v1.1.0 (通用化重写)**
  - 去除所有硬编码 (Jenkins215 IP, 公司名 "西安中诺通讯有限公司", etc.)
  - 公司名 / 关键词 走环境变量
  - 分析器拆为通用 parser + 业务 classifier
  - 测试: 12 场景 + 5 边界 case, 全部独立可跑
  - 完整文档

### 通用化原则 (入库要求)
1. 零硬编码
2. 路径自定位
3. 方法论与数据分离
4. 跨平台兼容 (Hermes / OpenClaw)
5. 可独立测试
6. 完整文档 (SKILL.md + README + INSTALL + CHANGELOG + .env.example)
7. 真实可跑 (用真 Jenkins / 飞书测过)

[Unreleased]: https://github.com/hqgaofeng/skills/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/hqgaofeng/skills/releases/tag/v1.0.0
