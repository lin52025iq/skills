---
name: project-migration
description: 当前端代码库需要迁移或升级时使用，包括页面或功能跨项目搬迁，Vue、React、Angular、Svelte 之间改写，JavaScript 到 TypeScript，Webpack 到 Vite，SPA 到 SSR 或微前端，以及路由、状态管理、请求层、组件库、样式体系或 Design System 替换；也用于审查迁移前后功能、视觉、交互、响应式、可访问性和运行质量是否等价。纯后端或数据库迁移、从零新建且没有既有行为基线的页面不使用。
metadata:
  author: lin52025iq
  version: "2.0.0"
---

# 前端项目迁移

把前端迁移视为**用户可观察契约的重建与验证**，而不是源组件、目录或语法的一对一翻译。

默认使用中文输出；用户明确指定其他语言时遵从用户要求。代码符号、路径、命令和产品名保持原样。

## 1. 先选择执行模式

根据请求选择最小充分模式，不把所有任务都升级成大型迁移项目。

| 模式 | 适用请求 | 默认产出 | 是否改代码 |
|---|---|---|---|
| 评估 | “能不能迁”“风险多大”“选什么方案” | 范围、风险、可行性、建议路径 | 否 |
| 规划 | “给迁移方案/拆任务/排阶段” | 契约、目标蓝图、波次计划、验收方案 | 否 |
| 执行 | “把这个页面/项目迁过去” | 代码、迁移记录、验证证据 | 是 |
| 验收 | “检查迁移是否完整/有没有回归” | 差异清单、证据、结论 | 默认否 |

再按范围选择工作量：

- **小型**：单组件、单页面或不超过一个独立用户流程。只保留必要记录。
- **标准**：一个 Feature、页面组、路由域或技术子系统。
- **大型**：多应用、微前端、多个路由域或跨团队迁移。使用 Workstreams 和持久化状态。

缺少信息时先检查仓库和现有证据；仍无法确认的事实写入假设与未知项，不凭空补全。

## 2. Rule Zero：确认真实迁移前状态

在规划、安装依赖或改代码之前，先确认工作树和基线来源：

```bash
git status --short
git rev-parse HEAD
git diff -- package.json pnpm-lock.yaml yarn.lock package-lock.json bun.lock bun.lockb
```

同时检查框架、构建、路由和测试配置是否已被修改。

记录基线可信度：

- **exact**：存在可运行的迁移前 commit、tag、branch、worktree 或发布制品；
- **partial**：只能恢复部分依赖、页面或数据；
- **unavailable**：没有可靠迁移前状态，只能依赖截图、设计稿、历史测试或产品说明。

禁止在未获明确批准时执行 `reset`、`checkout`、`clean`、`stash`、覆盖 lockfile 或删除用户改动。工作树已处于迁移中时，先识别“旧状态”和“当前状态”，不要把当前状态误当作 before baseline。

详见 `references/16-自动化盘点与迁移证据.md`。

## 3. 六阶段执行闭环

### 阶段 A：限定范围并自动盘点

明确：

- 源项目与目标项目位置；
- 迁移页面、Route、Feature 或技术子系统；
- 是否允许 redesign、行为修正或技术现代化；
- 浏览器、设备、locale、theme、权限和数据范围；
- 明确不迁移的内容。

先运行确定性盘点，再做人工语义判断：

```bash
python3 <skill-root>/scripts/inventory_frontend.py <source-root> \
  --output .migration/source-inventory.json

python3 <skill-root>/scripts/inventory_frontend.py <target-root> \
  --output .migration/target-inventory.json
```

盘点结果用于发现 package manager、框架、构建工具、Router、State、UI、Styling、测试配置、入口、Route 候选和生命周期信号。脚本输出的是**线索**，不是产品决策。

继续检查真实入口：Route、Menu、Tab、Deep Link、Modal、Drawer、Feature Flag、Permission、Store action、WebSocket/Event、后台刷新和微前端入口。

**阶段门禁：** 范围、基线来源和关键入口已明确；无法确认的项目已显式标记。

### 阶段 B：建立源契约与基线

从用户路径向下追踪：

```text
入口
→ 可见条件 / 权限
→ 页面与组件行为
→ 状态所有权
→ Query / Mutation / Event
→ 业务判断
→ UI 状态变化
→ 跳转、反馈与副作用
```

对每项能力分类：

- Active
- Conditional
- Hidden
- Disabled
- Deprecated
- Removed
- Unknown

默认不恢复注释代码、未注册 Route、长期关闭 Flag 或已有替代实现。隐藏不等于废弃，必须结合可达性、权限、调用方、版本历史和产品证据判断。

至少建立适用的六类契约：

1. **功能与导航**：用户能力、Route、Deep Link、Guard、跳转和失败结果；
2. **数据与状态**：Server State、Global State、Local UI State、缓存、并发和取消；
3. **交互**：Click、Keyboard、Focus、Form、Modal、Scroll、Drag、Optimistic Update；
4. **视觉与响应式**：布局、spacing、字体、颜色、图标、断点、overflow 和 z-index；
5. **平台**：SSR/Hydration、SEO、i18n、analytics、asset、font、browser support；
6. **质量**：测试、console error、Accessibility、性能和 bundle 行为。

关键页面优先记录：

- 固定数据与账号条件；
- desktop / tablet / mobile viewport；
- Default、Loading、Empty、Error、Disabled、Validation、Permission Denied；
- 截图、DOM 尺寸、console、network 和测试结果。

**阶段门禁：** Active / Conditional 能力和关键 UI 状态都有证据；Deprecated / Removed 有不迁移依据；视觉基线可重复。

详见 `references/13-功能文档与递归下钻.md`、`references/14-功能生命周期与废弃识别.md`、`references/15-前端视觉与交互还原.md`。

### 阶段 C：研究目标项目并形成目标原生蓝图

先找目标项目中 2～5 个维护良好、近期使用、测试充分的相似范例，覆盖：

- Router 与 Page / Feature 边界；
- Server / Client data fetching；
- cache、state、form、error boundary 和 permission；
- Component Library、Design System、Token、Icon 和 Styling；
- unit、component、Storybook、E2E、visual regression 和 a11y 测试。

从“源契约 + 目标项目范例”推导目标结构，不从源文件树推导。

蓝图至少说明：

- Route、页面和组件边界；
- 状态所有权与数据流；
- API / Event / Cache 适配；
- UI 状态与响应式实现；
- 复用目标组件和 Design Token 的位置；
- 临时 bridge / adapter 及删除条件；
- 批准的行为或视觉差异；
- 验证方式。

**阶段门禁：** 蓝图符合目标项目惯例；不存在明显 `.vue → .tsx`、旧 Store → 新 Store、旧 CSS 树 → 新 CSS 树的一对一投影。

详见 `references/07-跨技术栈迁移.md`、`references/11-目标原生重建.md`。

### 阶段 D：选择试迁移与实施波次

按风险而不是目录排序：

- 用户影响；
- 状态与副作用复杂度；
- 第三方组件和 API 耦合；
- SSR / hydration / micro-frontend 风险；
- 视觉和响应式敏感度；
- 测试与基线完整度。

标准或大型迁移先选一个**有代表性但边界可控**的试迁移，验证规则、目标结构和验收手段。不要先挑最简单页面制造虚假信心，也不要一开始迁全仓库。

按用户能力、Route 域或可独立验收的 Feature 切波次。共享 Router、Global Store、Theme、Design Token 和核心 Layout 默认单写者维护。

**阶段门禁：** 试迁移能暴露主要风险；每个波次都有输入、所有者、退出条件和回滚边界。

### 阶段 E：小步实施并逐单元验证

每次只迁移一个可解释、可验证的单元：

1. 阅读目标范例、蓝图和契约；
2. 实现目标原生代码；
3. 运行 format、lint、typecheck 和相关测试；
4. 检查页面、console、network、交互和截图；
5. 记录差异与新事实；
6. 通过门禁后再进入下一单元。

Codemod 只作为候选变更生成器：

- 先 dry-run；
- 保存工具版本和命令；
- 分小批审查 diff；
- 不自动接受生命周期、状态所有权、事件、slot/children、effect 或样式语义变化；
- 每批保留回退点。

同类失败重复出现时，暂停批量迁移，先修正规则、蓝图或自动化流程，再修实例。

### 阶段 F：迁移后对照、发布与清理

组合使用：

- build、lint、typecheck；
- component / integration / E2E；
- Route 与 Deep Link 对照；
- old/new behavior comparison；
- screenshot / Storybook visual test；
- keyboard、focus、form、modal、scroll 和 responsive 流程；
- Accessibility；
- console、network、hydration 和性能证据。

所有差异归类为：

- 必须修复；
- 已批准的产品或视觉变化；
- 环境噪声；
- Unknown。

可使用：

```bash
python3 <skill-root>/scripts/compare_frontend_inventory.py \
  .migration/source-inventory.json \
  .migration/final-inventory.json
```

只有功能、视觉、交互、响应式、平台和质量门禁都满足，才允许声明完成。Build 成功、页面能打开或 API 能请求都不能单独代表迁移完成。

## 4. 最小迁移包

优先使用 `templates/00-最小前端迁移包.md`。标准任务只强制维护以下产物：

```text
.migration/
├── context.md                 # 范围、模式、基线来源、假设
├── source-inventory.json      # 源项目自动盘点
├── target-inventory.json      # 目标项目自动盘点
├── contract.md                # 功能、视觉、交互与生命周期契约
├── plan.md                    # 目标蓝图、试迁移与波次
└── verification.md            # 命令、结果、差异与结论
```

小型任务可以把 Markdown 合并为一个文件。大型任务再按需使用现有详细模板、`workstreams/`、`tests/`、`fixtures/` 和 `results/`。不要为了“流程完整”机械创建空文档。

## 5. 硬门禁

以下任一项不满足时，不扩大实施范围：

- 未确认真实迁移前状态或基线可信度；
- 未完成关键功能生命周期判断；
- 未建立关键页面和状态基线；
- 未研究目标项目范例；
- 未定义可执行的验证裁判；
- 试迁移暴露系统性问题但规则尚未修正；
- 迁移后差异仍未归类；
- 临时 bridge、旧 Route、Flag、CSS、asset 或依赖没有清理决策。

## 6. 多 Agent / 多会话

仅在范围确实大型时启用 Supervisor + Workstreams。按稳定产品能力拆分，不按目录平均分配。

推荐 Workstream：

- Route / Lifecycle Research；
- Feature Contract Research；
- Visual Baseline；
- Data / State / API；
- Page Group Implementation；
- Responsive / Interaction Review；
- Visual / Accessibility / Copy-Smell Review。

共享架构和全局资源保持单写者。每个 Workstream 使用明确输入、禁止修改范围、交接证据和集成门禁。

详见 `references/12-多Agent与多会话编排.md`。

## 7. 最终输出格式

每次阶段性或最终交付都按以下顺序报告：

1. **模式与范围**：评估 / 规划 / 执行 / 验收，包含与排除项；
2. **基线可信度**：exact / partial / unavailable，证据位置；
3. **已完成变更**：按用户能力或 Route 描述，不按文件数量描述进度；
4. **验证证据**：命令、exit code、测试数、截图/console/a11y/visual 结果；
5. **差异与风险**：必须修复、批准变化、环境噪声、Unknown；
6. **清理与回滚**：旧路径、临时 bridge、Flag、依赖和回退方式；
7. **结论**：通过、有限通过或不通过，以及阻断原因。

## 8. 按需读取路由

- 总体方法：`references/00-项目迁移方法论.md`
- 前端跨栈规则与 Codemod：`references/07-跨技术栈迁移.md`
- 目标原生页面 / Feature 设计：`references/11-目标原生重建.md`
- 功能递归理解：`references/13-功能文档与递归下钻.md`
- 功能生命周期：`references/14-功能生命周期与废弃识别.md`
- 视觉、交互和响应式：`references/15-前端视觉与交互还原.md`
- 自动盘点、基线和证据：`references/16-自动化盘点与迁移证据.md`
- 多 Agent：`references/12-多Agent与多会话编排.md`，仅大型任务读取
- 快速示例：`examples/vue-to-react-page-migration.md`

详细模板仅在对应阶段需要持久化证据时读取，不在 Skill 触发时一次性加载。
