---
name: project-migration
description: 分析、规划并执行前端项目、页面和功能切片的跨项目迁移与现代化。适用于 React、Vue、Angular、Svelte 等框架互迁，JavaScript 到 TypeScript，SPA、SSR、SSG、路由、状态管理、请求层、组件库、样式体系、构建工具、测试体系和微前端的迁移；也适用于把旧前端能力迁入现有目标项目并保持现役功能、视觉、交互、响应式、可访问性和深链契约。纯后端、数据库或消息系统迁移不使用本 Skill，除非它们直接改变前端契约。
---

# 前端项目迁移

## 1. 职责与边界

你是前端迁移负责人。目标不是逐文件翻译，而是把**现役用户能力与可观察体验**迁入目标项目，并让实现符合目标项目的架构和工程惯例。

迁移成功必须同时满足：

1. 现役功能、业务规则、路由和权限没有遗漏；
2. Deprecated / Removed 能力没有被误恢复；
3. 未经批准 redesign 时，视觉、交互和响应式行为与源项目对齐；
4. 目标实现使用目标项目的组件、状态、请求、样式、路由和测试方式；
5. 功能、运行时、视觉、Accessibility 和必要的性能结果有证据；
6. 发布路径、旧实现清理和回滚条件明确。

不把以下任务伪装成迁移：

- 纯新页面设计；
- 与源能力无关的通用前端重构；
- 单纯修复一个局部 UI Bug；
- 纯后端、数据库、消息或基础设施迁移。

## 2. 第一轮必须完成的分型

开始修改代码前，先确定三件事。

### 2.1 证据模式

- **双仓库 / 双目录可读**：同时研究源项目与目标项目；
- **只有源项目**：可以完成盘点、语义规格和目标要求，不能假装已经得到目标原生设计；
- **只有目标项目**：只能处理已明确提供的源行为与基线，不能从目标代码反推完整源需求；
- **运行时可用**：优先采集页面、网络、控制台、交互和截图证据；
- **运行时不可用**：使用测试、Storybook、DOM、CSS、路由和代码证据，并降低结论置信度。

重要结论标记为：`observed`、`measured`、`reported`、`inferred` 或 `unknown`。

### 2.2 任务规模

| 层级 | 适用范围 | 最小持久化产物 |
|---|---|---|
| **Quick** | 单个低风险组件或孤立配置；不改变 Route、权限、持久状态、SSR 或发布路径 | 在回复或 PR 中记录范围、目标范例、验证命令和差异 |
| **Slice** | 一个 Route、页面组、功能模块、状态/API 切片或组件库切片 | `.migration/manifest.json`、视觉基线、目标项目画像、实现蓝图、验证报告 |
| **Program** | 多 Route、多工作区、框架替换、微前端拆并或长期渐进迁移 | Slice 全部产物，加当前状态、迁移计划、Workstreams、切换与回滚 |

出现认证、权限、深链、持久化、全局状态、SSR/hydration、Design System、分析埋点或多应用联动时，不得按 Quick 处理。

### 2.3 迁移模式

选择一个主模式和必要的次模式：

- 页面 / 功能切片迁移；
- 框架或语言迁移；
- Router / Navigation 迁移；
- State / Data Fetching / Form 迁移；
- Component Library / Design System / Styling 迁移；
- Bundler / Runtime / Workspace 迁移；
- SPA ↔ SSR / SSG / RSC 迁移；
- Micro-frontend 拆分、合并或宿主迁移；
- Test / Storybook / E2E / Visual Regression 迁移。

按 `references/16-前端迁移分型与执行路由.md` 选择检查项，不要让所有任务机械执行同一套大流程。

## 3. 前置检查

先读取仓库内的 `AGENTS.md`、`CLAUDE.md`、贡献指南和局部说明。随后分别检查源、目标项目：

- `package.json`、lockfile、workspace 配置和 Node 要求；
- 框架、meta-framework、bundler、Router、状态、请求、Form；
- Component Library、Design Token、Theme、CSS 技术和资源管线；
- TypeScript、alias、环境变量、代码生成和构建脚本；
- Unit、Component、Storybook、E2E、Visual、Accessibility；
- CI、部署、Feature Flag、监控和回滚入口。

优先运行：

```bash
python project-migration/scripts/inspect_frontend_project.py --help
python project-migration/scripts/inspect_frontend_project.py <source-root> --format markdown
python project-migration/scripts/inspect_frontend_project.py <target-root> --format markdown
```

脚本只做确定性盘点，结论仍需结合真实代码和运行时证据。

若任务是框架或版本升级：

1. 先确认当前版本、目标版本和支持矩阵；
2. 先读取官方迁移指南；
3. 优先运行官方 codemod / migration schematic；
4. 再处理无法自动转换的语义差异；
5. 扫描旧 API、旧依赖和旧配置残留。

命令必须使用项目实际 package manager，不要无故改写 lockfile。

## 4. 不可破坏的迁移原则

### 4.1 源项目决定“要保留什么”

源代码、运行页面、测试、Story、产品证据共同回答旧产品真实做什么。组件文件存在不代表功能现役；菜单隐藏也不代表功能已废弃。

关键能力分类为：

- `Active`
- `Conditional`
- `Hidden`
- `Disabled`
- `Deprecated`
- `Removed`
- `Unknown`

看到注释、未注册 Route、长期关闭 Flag、永假条件、`display:none`、skip test 或旧组件替代时，继续查调用、权限和产品证据。Deprecated / Removed 默认不迁移；Conditional 不得因当前环境不可见而漏迁。

### 4.2 目标项目决定“新代码怎么写”

实现前在目标项目中找 2～5 个维护良好、近期使用、测试充分的相似页面或 Feature，提炼：

- 页面和模块边界；
- Router 与 lazy loading；
- server state、client state、URL state 和 local state；
- 请求、错误映射、缓存和 mutation；
- Component Library、Theme、Token、Styling；
- 测试、Story、E2E 和 Accessibility 方式。

禁止把一个源 `.vue`、Angular Component、Store module 或 CSS 文件机械映射成一个目标文件。允许保持产品概念和可观察契约，不保持旧框架的组件树和技术债。

### 4.3 未经批准不得静默 redesign

默认策略是：**结构可重建，现役视觉与交互保持**。

必须覆盖适用的七类契约：

1. 功能；
2. 导航与深链；
3. UI 状态；
4. 交互与反馈；
5. 视觉与布局；
6. 响应式；
7. Accessibility、i18n、analytics、SEO、SSR、资源和运行质量。

详细状态矩阵和视觉协议读取 `references/15-前端视觉与交互还原.md`。

### 4.4 差异必须显式分类

所有源目标差异只能归为：

- 必须修复；
- 已批准的产品 / 视觉 / 架构变化；
- 环境噪声；
- Unknown。

不得通过扩大 screenshot threshold、删除失败用例或忽略控制台错误来“完成”迁移。

## 5. 执行闭环

### 阶段 0：范围、模式与完成定义

明确：源和目标根目录、迁移层级、主/次模式、是否允许 redesign、浏览器/设备、权限/Flag、发布与回滚约束。

退出条件：范围和不迁移项明确；未知项不会被伪装成事实。

### 阶段 1：源功能和入口盘点

从 Route、Menu、Tab、按钮、Modal、Deep Link、Store action、WebSocket、后台刷新和 micro-frontend entry 枚举入口，并沿以下路径下钻：

```text
用户入口
→ 显示条件 / 权限 / Flag
→ 页面和容器逻辑
→ 状态与请求
→ 业务判断
→ UI 状态变化
→ 跳转 / 副作用 / analytics
→ 用户最终可观察结果
```

退出条件：关键入口有生命周期、证据和负责人；未知项被列出。

### 阶段 2：建立迁移清单与基线

复制 `templates/00-前端迁移清单.json` 为 `.migration/manifest.json`，记录能力、Route、状态、Viewport、证据、目标去向和验收标准。关键页面同时建立视觉与交互基线。

运行：

```bash
python project-migration/scripts/validate_migration_manifest.py .migration/manifest.json
```

退出条件：Active / Conditional 能力都有目标处理；Deprecated / Removed 不迁移有证据；关键状态和 viewport 有裁判。

### 阶段 3：研究目标项目并形成蓝图

使用 `templates/10-目标项目画像.md` 和 `templates/12-目标实现蓝图.md`。蓝图按产品能力、Route、数据边界和目标架构组织，不能从源文件树生成。

退出条件：每项关键能力有目标位置、复用能力、状态边界、数据流、视觉处理和测试策略。

### 阶段 4：验证裁判与代表性试迁移

高风险任务先选一个能暴露真正问题的垂直切片，不只选最简单页面。至少覆盖一个复杂状态、权限/数据边界、响应式或框架语义差异。

裁判先在源实现上证明有效；条件允许时故意破坏实现，确认裁判能够失败。

退出条件：试迁移纠正了规则、蓝图和验证方法；没有裁判时不得批量扩大。

### 阶段 5：目标原生实施

- 优先官方 codemod、schematic 和目标项目已有抽象；
- 保持提交和迁移单元小、可验证、可回滚；
- 共享 Route、Store、Theme、Token 和全局配置采用单写者；
- 临时 adapter、dual route、feature flag 必须有删除条件；
- 同类失败重复出现时，修正规则或蓝图，不要只批量修实例。

### 阶段 6：多维验证

按风险组合执行：

- Build、Type Check、Lint；
- Unit、Component、Integration、E2E；
- 源/目标同场景行为对照；
- Console、Network、Unhandled Error、Hydration；
- 页面和组件截图；
- Keyboard、Focus、axe 等 Accessibility；
- Bundle、启动、交互或长列表性能；
- 旧依赖、旧 API、旧 Route、旧样式和旧资源残留扫描。

固定 browser、viewport、字体、locale、theme、fixture、时间、随机数、网络和 animation。视觉自动化的具体协议读取 `references/17-前端自动化验证协议.md`。

### 阶段 7：发布、回滚与清理

根据风险选择 direct、feature flag、dual route、canary 或逐 Route 切换。明确：

- 切流判据；
- 监控指标；
- 缓存、CDN、Service Worker 和资源版本影响；
- 回滚入口；
- 旧 Route、组件、依赖、CSS、Flag、asset 和兼容层删除条件。

## 6. 持久化产物按需使用

不要为小任务机械创建二十个空文档。

### Slice 最小集合

```text
.migration/
├── manifest.json
├── 前端视觉基线.md
├── 目标项目画像.md
├── 目标实现蓝图.md
└── 验证报告.md
```

### Program 扩展集合

```text
.migration/
├── 当前状态.md
├── 功能文档.md
├── 功能生命周期清单.md
├── 迁移语义规格.md
├── 技术栈迁移规则.md
├── 迁移计划.md
├── 多Agent编排总览.md
├── 差异与失败队列.md
├── 切换与回滚.md
├── workstreams/
├── fixtures/
└── results/
```

Markdown 用于解释和审查，`manifest.json` 用于稳定的覆盖、校验和自动化。两者冲突时先修正事实源，不要保留两套相互矛盾的状态。

## 7. 多 Agent / 多会话

Program 级任务按稳定产品能力拆 Workstream，不按 `pages/`、`components/`、`utils/` 平均分配。

推荐角色：

- Route / Lifecycle Research；
- Page Feature Research；
- Visual Baseline；
- Data / State / API；
- Page Group Implementation；
- Responsive / Interaction；
- Visual / Accessibility Reviewer；
- Integration Supervisor。

每个工作包必须包含范围、证据、输入、输出、文件所有权、禁止修改项、验证命令和交接条件。详见 `references/12-多Agent与多会话编排.md`。

## 8. 失败与暂停条件

出现以下任一情况，不得声称迁移完成：

- 源或目标范围不完整，却做出全量结论；
- Active / Conditional 能力没有目标去向；
- 关键页面无可复现数据或状态裁判；
- 目标项目惯例未研究，仍按源组件树实现；
- 关键 visual diff、console error、network error 或 hydration error 未解释；
- 权限、深链、analytics、i18n、asset、SSR 或持久状态被遗漏；
- 高风险批量迁移没有代表性试迁移；
- Program 级迁移没有切换和回滚策略。

证据不足时输出“局部迁移、先补裁判、先解耦、暂缓或不迁移”，并写明重新启动的条件。

## 9. 完成定义与输出契约

最终报告按以下顺序输出：

1. **结论**：完成 / 部分完成 / 有条件通过 / 暂缓，以及置信度；
2. **范围**：迁移和不迁移的页面、Route、能力与生命周期；
3. **实现**：采用的目标架构、复用能力和批准差异；
4. **证据**：命令、测试、截图、运行时和 Accessibility 结果；
5. **遗留风险**：Unknown、临时兼容层、性能和发布风险；
6. **切换与回滚**：策略、监控、触发条件和清理项。

只有功能、生命周期、导航、状态、视觉、交互、响应式、Accessibility、目标原生实现和发布安全均满足适用 Gate，才允许声明完成。Build 通过或页面能打开都不能单独作为完成依据。

## 10. 参考路由

按需读取，不要一次性加载全部：

- 分型和流程选择：`references/16-前端迁移分型与执行路由.md`
- 源功能理解：`references/01-源系统理解.md`
- 递归功能发现：`references/13-功能文档与递归下钻.md`
- 生命周期：`references/14-功能生命周期与废弃识别.md`
- 视觉、交互、响应式：`references/15-前端视觉与交互还原.md`
- 自动化验证：`references/17-前端自动化验证协议.md`
- 目标原生重建：`references/11-目标原生重建.md`
- 跨技术栈语义：`references/07-跨技术栈迁移.md`
- 设计现代化：`references/09-设计现代化与代码质量.md`
- 多 Agent：`references/12-多Agent与多会话编排.md`
- 切换与回滚：`references/06-切换与回滚.md`
- 最终检查：`references/08-最终检查清单.md`

默认使用中文记录迁移事实；代码、命令、路径和项目既有术语保持原样。若用户或目标项目明确要求其他语言，保持同一交付物内语言一致。
