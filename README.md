# 前端项目迁移 Skill

这是一个面向 AI 编程代理的前端迁移 Skill，用于把现役页面、功能模块或完整前端能力迁入另一个项目，同时完成受控现代化。

它不是“把 Vue 文件翻成 React 文件”，也不是借迁移之名重新设计页面。默认目标是：

- **产品连续**：现役功能、Route、权限、状态、交互、视觉、响应式和关键 Accessibility 可验证地延续；
- **目标原生**：新实现符合目标项目的组件、状态、请求、样式、路由、测试和发布惯例；
- **迁移可控**：Deprecated / Removed 能力不被误恢复，差异有证据，实施可增量验证并可回滚。

## 适用范围

- React、Vue、Angular、Svelte 等框架互迁；
- JavaScript → TypeScript；
- SPA、SSR、SSG、RSC 和 Router 架构迁移；
- 状态管理、请求层、Form、权限和深链迁移；
- 组件库、Design System、CSS / Sass / Less / CSS Modules / CSS-in-JS / Tailwind 迁移；
- Vite、Webpack、Rspack、workspace 和构建发布迁移；
- 微前端拆分、合并和宿主迁移；
- Test、Storybook、E2E、Visual Regression 和 Accessibility 体系迁移。

纯后端、数据库或消息系统迁移不属于主范围，除非它们直接改变前端数据、权限或用户体验契约。

## 核心流程

```text
迁移分型与范围
→ 源功能 / 生命周期 / 运行时证据
→ 机器可读迁移清单 + 视觉交互基线
→ 目标前端项目画像
→ 目标原生蓝图 + 代表性试迁移
→ 增量 Rebuild / Codemod
→ 功能 + 运行时 + 视觉 + Accessibility 验证
→ 切换、回滚和旧实现清理
```

入口：[`project-migration/SKILL.md`](project-migration/SKILL.md)

## 结构

```text
project-migration/
├── SKILL.md              # 精简入口、门禁、执行闭环和按需路由
├── agents/openai.yaml    # 前端迁移默认提示
├── references/           # 生命周期、视觉、目标原生、自动化验证等方法
├── templates/            # Markdown 证据模板与 manifest 示例
├── scripts/              # 确定性项目盘点和清单校验
└── evals/                # 触发与行为回归用例
```

## 脚本

先查看参数：

```bash
python project-migration/scripts/inspect_frontend_project.py --help
python project-migration/scripts/validate_migration_manifest.py --help
```

典型使用：

```bash
python project-migration/scripts/inspect_frontend_project.py ./legacy-app --format markdown
python project-migration/scripts/inspect_frontend_project.py ./new-app --format json --output .migration/target-stack.json
cp project-migration/templates/00-前端迁移清单.json .migration/manifest.json
python project-migration/scripts/validate_migration_manifest.py .migration/manifest.json --strict
```

脚本只负责可重复的事实盘点与结构校验；迁移决策仍需要源/目标代码、运行时和产品证据。

## 兼容说明

Skill 名称暂时保留为 `project-migration`，避免破坏已有调用；它的工作重心已经明确收敛为前端项目迁移。
