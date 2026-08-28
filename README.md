# 前端项目迁移 Skill

`project-migration` 是一个面向 AI 编程代理的**前端项目迁移与现代化 Skill**，用于把已有前端项目中的页面、功能模块和用户体验迁移到新的前端项目，并支持 React、Vue、Angular、Svelte、JavaScript / TypeScript、SPA / SSR、微前端、状态管理、组件库和样式体系之间的迁移。

它不把迁移理解成“把旧组件换一种语法复制过去”。默认工作方式是：

```text
研究源前端真实入口
→ 识别现役 / 隐藏 / 禁用 / 废弃功能
→ 递归下钻生成功能文档
→ 建立页面视觉、响应式和交互基线
→ 蒸馏技术无关的迁移语义
→ 研究目标前端项目架构与惯例
→ 形成目标原生页面 / 模块蓝图
→ Rebuild
→ 功能 + 视觉 + 交互 + Accessibility 验收
```

核心原则：

- **代码存在不等于功能需要迁移**：必须检查被注释的 JSX / Template、未注册 Route、隐藏 Menu、Feature Flag、Permission、CSS hidden、替代实现和废弃证据。
- **未经批准不做 redesign**：目标内部实现可以重建，但现役页面的布局、样式、响应式和交互默认跟随源项目对齐。
- **先建立视觉基线再迁移页面**：关键页面要记录 viewport、Page Shell、Grid / Flex、spacing、字体、颜色、Icon、Loading / Empty / Error 等状态。
- **目标前端项目决定代码形状**：优先复用目标项目已有 Router、State、API Client、组件库、Design System、Styling 和测试方式。
- **禁止源结构一对一翻译**：不默认执行 `.vue → .tsx`、旧 Component → 新 Component、旧 Store → 新 Store、旧 CSS → 新 CSS 的机械映射。
- **视觉和功能都是验收条件**：Build 成功、页面能打开、API 能调用，都不能单独代表迁移完成。
- **大模块支持 Supervisor + Workstreams**：可以按页面能力、视觉基线、状态模型、数据层和独立验收拆给多个子 Agent / Agent Team / 独立对话。
- Skill 工作语言始终为中文。

入口：[`project-migration/SKILL.md`](project-migration/SKILL.md)

前端视觉与交互：[`project-migration/references/15-前端视觉与交互还原.md`](project-migration/references/15-前端视觉与交互还原.md)

功能生命周期：[`project-migration/references/14-功能生命周期与废弃识别.md`](project-migration/references/14-功能生命周期与废弃识别.md)

功能递归理解：[`project-migration/references/13-功能文档与递归下钻.md`](project-migration/references/13-功能文档与递归下钻.md)

目标原生重建：[`project-migration/references/11-目标原生重建.md`](project-migration/references/11-目标原生重建.md)

多 Agent / 多会话编排：[`project-migration/references/12-多Agent与多会话编排.md`](project-migration/references/12-多Agent与多会话编排.md)
