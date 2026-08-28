# 前端迁移 Skill Evals

`cases.json` 同时覆盖：

- **触发准确性**：前端迁移请求应触发，纯后端、纯新设计、局部 Bugfix 和通用性能审查不应触发；
- **行为质量**：评估输出是否完成迁移分型、证据化源研究、目标原生设计、试迁移和多维验证；
- **反模式**：是否出现逐文件翻译、只跑 build、静默 redesign、恢复 Removed 功能或放宽视觉阈值。

建议在修改 `SKILL.md`、frontmatter description、分型规则或默认 prompt 后回归这些用例。新增高频失败时，先把失败写成 eval，再修改规则或脚本。

最低回归集合：

1. Vue → React 页面切片；
2. CRA → Vite 构建迁移；
3. Design System 迁移；
4. 源运行时不可用；
5. Program 级微前端迁移；
6. 至少三条负触发用例。
