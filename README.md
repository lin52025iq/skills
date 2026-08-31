# Skills

这个仓库用于维护面向 AI 编程代理的工程 Skill。

## code-migration

`code-migration` 用于将一个或多个现有项目中的功能、业务规则和用户能力迁移、融合或重构到目标项目。

它不是文件搬运或框架语法翻译工具，而是按以下模型工作：

```text
Source Evidence
→ Desired Target Behavior
→ Target-native Design
→ Incremental Implementation & Verification
```

核心能力包括：

- 从源项目恢复真实功能、Business Rule、Invariant、数据契约与生命周期；
- 根据用户迁移意图和目标产品要求确定真正需要的目标行为；
- 多项目场景下建立 Canonical Feature Model，处理重复能力与冲突；
- 复用目标项目已有 Router、状态、数据、组件、权限和测试惯例，而不是复制源架构；
- 支持 Layout-first、Feature-first、Representative-slice-first 等前端迁移顺序；
- 按可验证功能切片推进，区分 `IMPLEMENTING / VERIFYING / MIGRATED / ELIMINATED`；
- 使用 `.code-migration/` 持久化长周期迁移状态，支持新对话恢复、澄清、Handoff 和 Reconcile；
- 区分 Mechanical / Semantic / Product 变化，限制 Codemod 自动化边界；
- 对批准的目标变化使用 `APPROVED_CHANGE`，验证面向目标行为而不是默认追求旧系统等价。

主入口：[`code-migration/SKILL.md`](code-migration/SKILL.md)

## project-migration

`project-migration` 是面向 AI 编程代理的前端迁移执行 Skill。它覆盖从只读审计、迁移规划、跨框架实施，到视觉回归、渐进切流、回滚和旧实现清理的完整闭环。

它解决的不是“把 `.vue` 改写成 `.tsx`”，而是：

```text
源前端真实功能与运行证据
→ 生命周期与视觉交互契约
→ 迁移策略和目标原生蓝图
→ 代表性试迁移
→ 垂直切片重建
→ 功能、视觉、交互、Accessibility 与运行质量验收
→ 切流、回滚和清理
```

## 适用场景

- React、Vue、Angular、Svelte 等框架互迁或大版本升级；
- CRA/Webpack 到 Vite，SPA 到 SSR/SSG，Pages Router 到新 Router 架构；
- 页面、Route、状态管理、请求层、表单、组件库和样式体系迁移；
- JavaScript 到 TypeScript；
- 微前端拆分、合并、渐进替换或回收；
- 旧页面迁入新仓库，并保持现役功能、视觉、响应式和交互；
- 审查已有迁移是否遗漏功能、恢复废弃能力或复制了源框架结构；
- 救援卡住、回归频发或缺少回滚路径的迁移。

它不用于纯绿地 UI 设计；除非用户明确要求 redesign，迁移默认保持源项目现役体验。

## 快速使用

```text
使用 $project-migration，把 source-app 的订单页面迁到 target-app。
先只读审计两个项目，确认功能生命周期、视觉基线、目标项目惯例和回滚策略；
再按垂直切片实施，并给出功能、截图、响应式、Accessibility 和构建测试证据。
```

主入口：[`project-migration/SKILL.md`](project-migration/SKILL.md)

## 工作模式

| 模式 | 结果 |
|---|---|
| 评估 | 可行性、范围、风险、未知项，不改产品代码 |
| 规划 | 功能契约、视觉基线、策略、蓝图、切片和验证计划 |
| 实施 | 目标原生代码、测试、差异记录、切流与清理 |
| 审查 | 按严重度报告遗漏、回归、Copy-Smell 和发布风险 |
| 救援 | 找到反复失败的上游原因并恢复迁移闭环 |

## 工作区强度

- `small`：单页面或边界清晰的小迁移；
- `standard`：多页面或模块级迁移；
- `full`：整应用、框架、构建、SSR 或微前端迁移。

```bash
python project-migration/scripts/init_migration_workspace.py <repo-root> --profile standard --dry-run
python project-migration/scripts/init_migration_workspace.py <repo-root> --profile standard
python project-migration/scripts/validate_migration_workspace.py <repo-root> --profile standard
```

## 静态盘点工具

`frontend_inventory.py` 只读检查 package manager、workspace、框架、Router、状态、数据层、样式、测试、配置、入口候选和生命周期风险信号，不执行项目代码，也不读取 `.env` 值。

```bash
python project-migration/scripts/frontend_inventory.py <repo-root> --format markdown
python project-migration/scripts/frontend_inventory.py <repo-root> --format json --output inventory.json
```

盘点结果是侦察线索，不是最终产品事实；关键页面仍应通过运行、测试和浏览器证据确认。

## 核心原则

- **代码存在不等于功能现役**：检查 Route、导航、Flag、权限、隐藏样式、注释与替代实现。
- **未经批准不 redesign**：内部架构可以重建，用户可观察体验默认保持。
- **目标项目决定代码形状**：复用目标 Router、状态、数据、组件、Token 和测试惯例。
- **按垂直能力切片**：不按源文件树机械翻译。
- **先有裁判再批量实施**：功能和视觉都要能比较，Unknown 不能伪装成完成。
- **迁移必须可退出**：共存、切流、回滚和兼容层删除条件属于设计的一部分。

## 目录

```text
project-migration/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── frontend_inventory.py
│   ├── init_migration_workspace.py
│   └── validate_migration_workspace.py
├── references/
│   ├── 16-前端迁移执行协议.md
│   ├── 17-迁移策略与共存回滚.md
│   ├── 18-框架与工程迁移策略.md
│   └── 19-验证与视觉回归执行.md
├── templates/
└── evals/evals.json
```

已有 `references/00-15` 和 `templates/` 继续提供详细方法和迁移证据模板；主 `SKILL.md` 只保留决策、Gate 和按需路由，避免一次加载全部材料。

## 验证 Skill 本身

```bash
python tools/validate_skill.py project-migration
python tools/validate_skill.py code-migration
```

仓库 CI 会检查 Skill frontmatter、主文件长度、内部链接、`agents/openai.yaml`、脚本和评测集结构。