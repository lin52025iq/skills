# 前端项目迁移 Skill

`project-migration` 是一个面向 AI 编程代理的前端迁移 Skill，用于把已有页面、Feature 和用户体验迁移到新的前端项目或技术栈，并用可复现证据判断迁移是否完整。

适用场景包括：

- Vue / React / Angular / Svelte 之间迁移；
- JavaScript → TypeScript；
- Webpack → Vite / Rspack；
- SPA → SSR、文件路由或微前端；
- Router、State、Data Fetching、Form、组件库、Design System 和 Styling 替换；
- 页面或 Feature 跨仓库迁移；
- 迁移后的功能、视觉、交互、响应式、Accessibility 和运行质量验收。

核心工作方式：

```text
确认真实迁移前状态
→ 自动盘点源与目标前端
→ 识别现役 / 条件 / 隐藏 / 废弃能力
→ 固化功能、视觉与交互基线
→ 按目标项目惯例设计目标原生蓝图
→ 试迁移与分波实施
→ 功能 + 视觉 + 交互 + 响应式 + Accessibility 对照
→ 发布、回滚与旧路径清理
```

## 关键原则

- **先确认 before state**：依赖或配置已被升级时，不能把当前工作树当作迁移前基线。
- **迁移用户契约，不迁移源组件树**：保持现役能力与体验，按目标项目方式重建代码。
- **代码存在不等于需要迁移**：注释、隐藏、Flag、权限、替代实现和废弃证据必须结合判断。
- **未经批准不 redesign**：代码结构可以现代化，页面视觉与交互默认跟随现役基线。
- **自动化负责重复事实，模型负责语义判断**：盘点与差异比较使用确定性脚本，生命周期和产品取舍保留证据。
- **小任务走轻量路径，大项目才启用完整 Workstreams**：不机械生成大量空文档。
- **Build 通过不是完成条件**：最终结论必须附带功能、视觉、交互、响应式和质量证据。

## 快速入口

主 Skill：[`project-migration/SKILL.md`](project-migration/SKILL.md)

最小迁移包：[`project-migration/templates/00-最小前端迁移包.md`](project-migration/templates/00-最小前端迁移包.md)

自动盘点：

```bash
python3 project-migration/scripts/inventory_frontend.py /path/to/frontend \
  --output .migration/source-inventory.json
```

盘点对比：

```bash
python3 project-migration/scripts/compare_frontend_inventory.py \
  .migration/source-inventory.json \
  .migration/final-inventory.json
```

脚本只使用 Python 标准库。

## 目录

```text
project-migration/
├── SKILL.md
├── agents/
├── scripts/        # 确定性盘点与对比
├── references/     # 按阶段渐进加载的方法与规则
├── templates/      # 迁移过程中的输出模板
├── examples/       # 完整工作流示例
└── tests/          # 脚本回归测试
```

## 建议触发语句

- “把这个 Vue 页面迁到目标 React 项目，保持现有视觉和交互。”
- “评估 AngularJS 管理后台迁到 React + Vite 的风险与波次。”
- “把 Webpack 项目升级到 Vite，并证明所有 Route 没有回归。”
- “审查这次前端迁移是否漏了隐藏入口、Loading/Error 状态和移动端行为。”
