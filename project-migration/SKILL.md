---
name: project-migration
description: 专注于前端项目、页面、功能模块和用户体验的跨项目迁移与现代化，支持 React、Vue、Angular、Svelte 等框架之间迁移，以及 SPA、SSR、MPA、微前端、状态管理、路由、组件库和样式体系迁移。先从源前端真实入口递归理解现役功能，识别被注释、隐藏、禁用和废弃能力，建立页面视觉与交互基线，再研究目标项目的前端架构、语言、组件、状态和样式惯例，以目标原生方式 Rebuild，同时要求功能、视觉、响应式和交互与源项目现役体验对齐。大模块支持 Supervisor + Workstreams 多 Agent / 多会话协作。全过程使用中文。
---

# 前端项目迁移

## 1. 角色与最终目标

你是“前端迁移负责人”，不是代码翻译器、组件搬运器，也不是未经批准的 UI 设计师。

本 Skill 主要服务于：

- 一个前端项目的页面或功能迁到另一个前端项目；
- Vue / React / Angular / Svelte 等框架互迁；
- JavaScript → TypeScript；
- 老 SPA → 新 SPA / SSR / Router 架构；
- 老组件库 → 新组件库 / Design System；
- CSS / Less / Sass / CSS Modules / CSS-in-JS / Tailwind 等样式体系迁移；
- 状态管理、请求层、权限、路由和构建工具迁移；
- 微前端拆分、合并或现代化；
- 在迁移过程中清理废弃功能和不合理前端设计。

后端 API、数据库、消息和任务只在它们影响前端功能、数据契约、权限、状态或页面行为时继续追踪；它们不是本 Skill 的主要实现对象。

迁移成功同时要求：

1. **功能正确**：现役用户能力、业务规则和页面状态没有遗漏；
2. **生命周期正确**：Deprecated / Removed 功能没有被错误恢复，Conditional 功能没有被误删；
3. **视觉正确**：未经批准 redesign 时，关键页面布局和视觉结果跟随源项目现役界面对齐；
4. **交互正确**：Loading、Empty、Error、Disabled、Modal、表单、滚动等状态和反馈符合源行为；
5. **响应式正确**：源项目真实支持的 viewport / breakpoint 行为得到保留；
6. **目标原生**：目标代码符合目标前端项目的组件、状态、样式、路由和测试惯例，不是旧框架换语法；
7. **可验证**：功能、视觉、交互和关键 Accessibility 都有验收证据。

## 2. 强制语言规则

整个 Skill 的工作语言始终为中文。

- 分析、计划、风险、功能文档、视觉基线、审查结果和阶段报告全部使用中文；
- 代码符号、文件路径、Route、CSS selector、技术产品名和命令保持原样；
- 引用英文资料后，用中文说明迁移意义；
- `.migration/` 下迁移记录默认使用中文。

## 3. 前端迁移默认模型

默认采用：

```text
Research Source
→ Lifecycle Classification
→ Recursive Feature Discovery
→ Visual & Interaction Baseline
→ Semantic Distillation
→ Review Target Frontend
→ Target-native Blueprint
→ Pilot
→ Rebuild
→ Functional + Visual + Interaction Verification
```

也就是：

```text
源代码 / 源页面
↓
先判断哪些功能现在真的存在
↓
递归下钻理解功能和状态
↓
记录用户实际看到的页面与交互
↓
蒸馏技术无关语义
↓
研究目标前端项目怎样组织代码
↓
形成目标页面 / 模块蓝图
↓
按目标项目方式重建
↓
与源现役功能和视觉基线对照
```

**源代码回答“旧产品现在做什么和长什么样”；目标项目回答“新代码应该怎么写”。**

## 4. 七类前端可观察契约

每个迁移能力都至少检查以下适用项。

### 4.1 功能契约

- 用户能做什么；
- 功能入口在哪里；
- 前置条件；
- 成功 / 失败结果；
- 业务规则。

### 4.2 导航契约

- Route；
- Menu / Sidebar / Navbar；
- Tab；
- Deep Link；
- Redirect；
- Guard / Permission；
- Modal / Drawer / Popover 入口。

### 4.3 状态契约

至少检查适用的：

```text
Default
Loading / Skeleton
Empty
Error
Partial Data
Disabled
Read-only
Hover
Focus / Focus-visible
Active / Pressed
Selected
Expanded / Collapsed
Editing
Validation Error
Submitting
Success Feedback
Permission Denied
Offline / Timeout
Long Content / Overflow
```

### 4.4 交互契约

- Click / Input / Submit；
- Keyboard；
- Focus；
- Scroll；
- Drag / Drop；
- Debounce / Throttle；
- Optimistic Update；
- Modal close；
- Unsaved changes；
- Pagination / Infinite scroll。

### 4.5 视觉契约

- 页面框架；
- Grid / Flex / Position；
- 宽高与 max/min；
- margin / padding / gap；
- 字体；
- 颜色；
- 边框 / 圆角 / 阴影；
- Icon / Image；
- z-index；
- overflow / scroll owner；
- Theme / Design Token。

### 4.6 响应式契约

- breakpoint；
- mobile / tablet / desktop 布局变化；
- hide / show；
- wrap；
- navigation transformation；
- table / card transformation；
- viewport / container query。

### 4.7 平台与质量契约

- Accessibility；
- i18n / locale；
- date / number format；
- analytics；
- SEO / metadata；
- SSR / hydration；
- asset / font；
- build / code splitting；
- 性能和运行错误。

## 5. 功能存在不等于需要迁移

### 5.1 必须建立功能生命周期

仓库中的组件、Route、API 和 CSS 只能证明代码存在，不能证明功能当前仍有效。

每个关键功能分类为：

- **Active**：现役；
- **Conditional**：条件现役；
- **Hidden**：默认隐藏但可能可达；
- **Disabled**：明确关闭但可能恢复；
- **Deprecated**：有废弃 / 替代证据；
- **Removed**：产品能力已移除，只剩残留；
- **Unknown**：证据不足。

详见 `references/14-功能生命周期与废弃识别.md`，使用 `templates/04-功能生命周期清单.md`。

### 5.2 前端必须主动检查这些“非现役信号”

- JSX / TSX 注释块；
- Vue / Angular / HTML 注释；
- Route 被注释或未注册；
- Menu / Tab 被注释；
- Feature Flag 长期关闭；
- 永假条件；
- CSS `display:none` / `hidden`；
- 权限永不可达；
- 旧组件已有新替代；
- deprecated / legacy / old 标记；
- skip / disabled tests；
- API 已无调用方。

看到注释代码时：

> 研究它表达过什么功能，但默认不要恢复并迁移。

同时不能因为 UI 被隐藏就直接判定废弃，必须继续查 Route、Flag、权限、替代实现和调用关系。

## 6. 先递归生成功能文档

对源前端先枚举真实入口：

- 页面 Route；
- Menu / Navigation；
- Tab；
- 页面按钮和交互动作；
- Modal / Drawer；
- Deep Link；
- Event / WebSocket；
- Store action；
- Background refresh；
- Micro-frontend entry。

然后沿：

```text
UI 入口
→ 条件显示 / 权限
→ 页面 / 容器逻辑
→ 状态管理
→ 数据请求
→ 业务判断
→ UI 状态变化
→ 后续交互 / 页面跳转
→ 用户最终可观察结果
```

不断向下研究。

只要仍出现新的功能点、状态、条件、数据语义、交互或副作用就继续；纯 UI plumbing 或无业务意义工具函数可以停止。

先形成：

```text
.migration/功能文档.md
.migration/功能生命周期清单.md
```

再形成：

```text
.migration/迁移语义规格.md
```

详见 `references/01-源系统理解.md` 和 `references/13-功能文档与递归下钻.md`。

## 7. 前端视觉基线是正式迁移输入

### 7.1 默认不是 redesign

如果用户没有明确要求重新设计页面：

> **目标代码结构可以重建，目标视觉与交互默认跟随源项目现役页面。**

不能因为：

- 换了 React / Vue；
- 换了组件库；
- 换了 CSS 技术；
- 目标项目有不同默认样式；

就静默改变页面布局和展示。

### 7.2 为关键页面建立基线

使用 `templates/10-前端视觉基线.md`，记录：

- viewport / breakpoint；
- page shell；
- header / sidebar / main；
- 宽高和滚动；
- Grid / Flex；
- spacing；
- font；
- color；
- border / radius / shadow；
- icon / image；
- UI 状态矩阵；
- responsive behavior；
- interaction flow；
- Accessibility。

优先视觉证据：

```text
源项目可运行页面真实截图
→ Storybook / 组件示例
→ 产品截图 / 设计稿
→ DOM + CSS + 组件结构
```

详见 `references/15-前端视觉与交互还原.md`。

## 8. 建立前端语义防火墙

正式实现前优先形成：

```text
.migration/功能文档.md
.migration/功能生命周期清单.md
.migration/前端视觉基线.md
.migration/迁移语义规格.md
.migration/目标项目画像.md
.migration/目标实现蓝图.md
```

目标实现蓝图不能从源文件树直接生成。

开始写目标代码后，上下文优先级：

```text
1. 目标前端项目真实代码和优秀范例
2. 目标实现蓝图
3. 源页面视觉 / 交互基线
4. 迁移语义规格
5. 技术栈迁移规则
6. 源代码：只用于具体事实回查
```

## 9. 目标前端项目必须先研究

设计目标页面前至少研究：

### 工程

- package manager；
- bundler / dev server；
- TypeScript config；
- module / alias；
- lint / format；
- build / deploy；
- environment config。

### 应用架构

- Router；
- Page / Feature / Module 边界；
- Server / Client component（如适用）；
- data fetching；
- cache；
- global / local state；
- form；
- error boundary；
- permission。

### UI

- Component library；
- Design System；
- CSS / styling 技术；
- Theme；
- Token；
- Icon；
- Typography；
- Layout component；
- responsive conventions。

### 测试

- unit / component；
- Storybook；
- E2E；
- visual regression；
- accessibility testing。

先找 2～5 个目标项目中维护良好、近期活跃、测试充分的相似页面 / 模块作为范例。

## 10. 禁止按源前端结构一对一复制

除非有明确产品或契约理由，默认禁止：

- 一个源 `.vue` → 一个目标 `.tsx`；
- 一个 Angular Component → 一个 React Component；
- 一个旧 Page → 按旧组件树完整复刻；
- 一个 Store module → 一个目标 Store module；
- 一个旧 mixin / hook → 一个目标 hook；
- 一个旧 CSS / Less 文件 → 一个目标样式文件；
- 批量复制 utils / helpers / base components；
- Controller-shaped React、Angular-shaped React、Vue-shaped React 等结构。

允许保持的是产品概念、页面语义、视觉和交互契约，不是旧框架的实现分解。

## 11. 样式迁移：视觉保持，CSS 架构可重建

可以：

- Less / Sass → CSS Modules；
- CSS → Tailwind；
- styled-components → 目标项目样式方案；
- float / clearfix → Grid / Flex；
- magic values → 目标 Design Token；
- 老组件库 → 目标组件库。

但要验证：

- 页面布局没有意外变化；
- 间距和尺寸对齐；
- 字体和图标对齐；
- responsive 对齐；
- Loading / Empty / Error / Disabled 等状态对齐；
- 新组件库没有静默改变交互。

## 12. 九阶段前端迁移状态机

```text
阶段 0：前端迁移接入与范围
    ↓
阶段 1：源功能发现 + 生命周期判断
    ↓
阶段 2：功能文档 + 视觉 / 交互基线
    ↓
阶段 3：迁移边界 + 技术无关语义
    ↓
阶段 4：目标前端项目研究 + 目标蓝图
    ↓
阶段 5：验证裁判 + 试迁移
    ↓
阶段 6：目标原生 Rebuild
    ↓
阶段 7：功能 + 视觉 + 交互 + Accessibility 审查
    ↓
阶段 8：发布、灰度与旧前端清理
```

### 阶段门禁

| 阶段 | 前端关键退出条件 |
|---|---|
| 0 | 页面 / 功能范围、源与目标技术栈、是否允许 redesign、浏览器/设备范围明确 |
| 1 | 关键页面和入口已发现；功能生命周期已分类；注释 / 隐藏 / Flag / 权限已检查 |
| 2 | 功能树完整；关键页面有视觉基线；主要 UI 状态与 responsive 行为有记录 |
| 3 | Active / Conditional 能力有明确迁移去向；Deprecated / Removed 有不迁移证据；语义规格不依赖源组件结构 |
| 4 | 已研究目标前端范例、组件、状态、样式、路由、测试；目标蓝图不是源组件树投影 |
| 5 | 关键功能有功能裁判；关键页面有视觉裁判；高风险页面完成试迁移 |
| 6 | 实现主要依据目标项目范例、蓝图和视觉基线；源代码只做事实回查 |
| 7 | 功能、视觉、交互、响应式、关键 Accessibility 通过；无阻断 Copy-Smell |
| 8 | 新页面真实可用；旧 Route / component / CSS / Flag / asset 清理条件满足 |

## 13. 前端验证裁判

不能只跑 unit test。

按风险组合：

### 功能

- component test；
- integration；
- E2E；
- API mock / contract；
- old/new behavior comparison。

### 视觉

- 页面截图基线；
- component screenshot；
- Storybook visual test；
- Playwright `toHaveScreenshot()` 等现有项目能力；
- 人工视觉确认。

视觉比较尽量固定 browser、OS/rendering environment、viewport、字体、locale、theme、数据和 animation；环境不同产生的像素差异不要误判为产品差异。

### 交互

- hover / focus；
- keyboard；
- form validation；
- modal / drawer；
- loading / empty / error；
- permission；
- scroll；
- responsive navigation。

### 差异分类

所有差异归类：

- 必须修复；
- 批准的产品 / 视觉变化；
- 环境噪声；
- Unknown。

不要通过无限扩大视觉 diff threshold 掩盖真实回归。

## 14. 前端多 Agent / 多会话

大前端项目优先按稳定产品能力拆 Workstream，而不是按目录平均分。

推荐角色：

- Route / Navigation / Lifecycle Research Worker；
- Page Feature Research Worker；
- Visual Baseline Worker；
- Data / State / API Worker；
- Page Group Implementation Worker；
- Responsive / Interaction Worker；
- Visual Regression Reviewer；
- Accessibility / Copy-Smell Reviewer。

示例：

```text
Supervisor
├── WS-FE-01 路由与功能生命周期
├── WS-FE-02 订单页面功能和状态
├── WS-FE-03 订单页面视觉基线
├── WS-FE-04 请求层 / 状态模型
├── WS-FE-05 页面 Rebuild
└── WS-FE-06 Visual + Interaction Review
```

同一核心页面、共享 Route、全局 Store、Theme、Design Token 默认使用单写者。

详见 `references/12-多Agent与多会话编排.md`。

## 15. `.migration/` 前端工作区

中大型前端迁移优先维护：

```text
.migration/
├── 迁移上下文.md
├── 当前状态.md
├── 源系统理解.md
├── 功能文档.md
├── 功能生命周期清单.md
├── 前端视觉基线.md
├── 迁移语义规格.md
├── 业务规则台账.md
├── 能力迁移矩阵.md
├── 迁移边界.md
├── 目标项目画像.md
├── 目标实现蓝图.md
├── 技术栈迁移规则.md
├── 设计改进台账.md
├── 迁移计划.md
├── 多Agent编排总览.md
├── 差异与失败队列.md
├── 验证报告.md
└── 切换与回滚.md
```

必要时：

```text
.migration/workstreams/
.migration/tests/
.migration/fixtures/
.migration/results/
.migration/scripts/
```

`.migration/` 根目录保持声明式；可执行代码只进入受控子目录。详见 `references/10-.migration目录边界.md`。

## 16. 前端完成定义

只有同时满足以下条件，才允许声明迁移完成：

- Active / Conditional 关键功能都有明确终态；
- Deprecated / Removed 功能没有被错误恢复；
- Hidden / Disabled / Unknown 功能已有明确决策；
- 页面、Route、Menu、Deep Link 和权限可达性符合要求；
- 关键业务功能已验证；
- Loading / Empty / Error / Disabled 等关键 UI 状态已验证；
- 主要交互流程已验证；
- 源项目真实支持的主要 viewport / breakpoint 已验证；
- 未经批准 redesign 的页面与视觉基线对齐；
- 字体、Icon、图片、Theme、关键 spacing 无未解释漂移；
- 目标实现符合目标项目组件、路由、状态、样式和测试惯例；
- 无阻断级源框架 Copy-Smell；
- Accessibility 阻断项关闭或明确接受；
- visual diff 均已修复、批准或解释；
- 多 Workstream 已完成统一集成验证；
- 临时迁移代码和旧前端路径有清理决策；
- `.migration/当前状态.md` 与实际前端项目一致。

构建通过、页面能打开、API 能请求，都不能单独作为完成依据。

## 17. 参考文档路由

前端迁移优先读取：

- `references/01-源系统理解.md`：源代码递归理解；
- `references/13-功能文档与递归下钻.md`：功能树和下钻停止条件；
- `references/14-功能生命周期与废弃识别.md`：注释、隐藏、禁用、废弃和替代功能；
- `references/15-前端视觉与交互还原.md`：布局、视觉、响应式、UI 状态和视觉验收；
- `references/11-目标原生重建.md`：目标项目驱动 Rebuild 和 Copy-Smell；
- `references/07-跨技术栈迁移.md`：语言 / 框架语义；
- `references/09-设计现代化与代码质量.md`：受控现代化；
- `references/12-多Agent与多会话编排.md`：Supervisor / Workstreams；
- `references/05-验证与审查.md`：验证裁判；
- `references/08-最终检查清单.md`：最终总体验收；
- `references/10-.migration目录边界.md`：工作区约束。

其他 references 只在前端依赖确实涉及对应系统能力时读取。

## 18. 模板路由

源前端研究优先使用：

- `templates/04-功能文档.md`；
- `templates/04-功能生命周期清单.md`；
- `templates/05-迁移语义规格.md`。

视觉和目标设计优先使用：

- `templates/10-前端视觉基线.md`；
- `templates/10-目标项目画像.md`；
- `templates/12-目标实现蓝图.md`。

大模块、多 Agent / 多对话使用：

- `templates/16-多Agent编排总览.md`；
- `templates/17-子Agent工作包.md`；
- `templates/18-子Agent交接.md`。

最终验证使用：

- `templates/23-验证报告.md`；
- `templates/24-切换与回滚.md`。

模板用于统一证据和状态，不要求机械填满所有字段。
