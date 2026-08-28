---
name: project-migration
description: 用于审计、规划、实施和验收前端项目迁移：将页面、组件或功能在 React、Vue、Angular、Svelte、JavaScript/TypeScript、SPA/SSR/MPA、路由、状态、请求层、组件库、样式体系、构建工具或微前端之间迁移。凡用户提到前端迁移、框架升级或互迁、旧页面搬到新仓库、CRA/Vite/Next/Nuxt/SvelteKit 现代化、设计系统替换、视觉与交互等价重建、渐进切流、迁移审查或失败救援时使用。先建立源功能、生命周期和视觉交互证据，再按目标项目惯例重建；未经明确批准不 redesign，并用功能、视觉、响应式、交互、Accessibility 和运行质量证据验收。
---

# 前端项目迁移

把迁移当作“可观察产品能力的受控重建”，不要把它当作源文件的语法翻译。

## 1. 先确定工作模式

从用户请求推断模式；已有信息足够时不要重复询问。

| 模式 | 主要动作 | 默认是否改产品代码 |
|---|---|---|
| 评估 | 只读审计、风险与可行性结论 | 否 |
| 规划 | 建立证据、策略、蓝图、切片与验证计划 | 否 |
| 实施 | 规划后增量修改代码与测试 | 是 |
| 审查 | 检查已有迁移的遗漏、Copy-Smell、回归与发布风险 | 仅在用户要求修复时 |
| 救援 | 定位停滞或失败的上游原因，修正规则后继续 | 视请求而定 |

若用户只要求迁移一个组件，不要自动扩张成全项目治理；若用户要求整个应用迁移，也不要只给文件级 TODO。

## 2. 选择范围与产物强度

| 范围 | 典型任务 | 默认产物 |
|---|---|---|
| 组件 | 独立组件、Hook、样式模块 | 对话内简要契约、差异与验证记录 |
| 页面 | Route、页面及其数据和交互 | `small` 工作区 |
| 模块 | 一组页面、共享状态、权限或设计系统 | `standard` 工作区 |
| 应用 | 框架、Router、SSR、构建、微前端或整仓迁移 | `full` 工作区 |

可运行：

```bash
python project-migration/scripts/init_migration_workspace.py <repo-root> --profile small|standard|full
```

不要为了形式机械填满模板。只保留能影响决策、实现、验收或交接的事实。

## 3. 不可破坏的迁移约束

1. **先读仓库指令**：查找 `AGENTS.md`、`CLAUDE.md`、贡献指南、README、CI 和目标目录附近的局部约束。
2. **先保存基线**：记录当前分支、未提交改动、安装方式、可运行命令和初始失败；不要把源项目原有失败算成迁移回归。
3. **代码存在不等于功能现役**：检查 Route、导航、权限、Feature Flag、注释、隐藏样式、替代实现和测试调用。
4. **未经批准不 redesign**：内部结构可重建，现役布局、文案语义、响应式和交互默认保持。
5. **目标项目决定代码形状**：优先复用目标项目现有 Router、数据层、状态、组件、Token、错误处理和测试惯例。
6. **按垂直能力切片**：一个切片应从入口走到用户可观察结果及验证，不按源文件列表批量翻译。
7. **先有裁判再扩大迁移**：至少能证明旧行为、目标预期和差异分类；没有可靠裁判时只做研究或试迁移。
8. **保留用户改动**：不覆盖无关修改，不随意重置分支、锁文件或格式化全仓。
9. **所有结论带证据等级**：区分运行观察、测试/配置、静态代码和推断，未知项不得伪装成已确认。

## 4. 证据优先级

对功能、视觉和生命周期判断使用以下优先级：

```text
E3 真实运行观察、可复现用户路径、生产/预发布证据
E2 自动化测试、Storybook、Route/Flag/权限配置、契约或设计稿
E1 静态代码、样式、调用关系、提交历史
E0 推断或缺少证据
```

冲突时优先更高等级，但保留冲突记录。`E0` 只能形成假设和验证任务，不能直接成为删除功能、改变行为或发布的依据。

## 5. 开始前的只读侦察

先在源项目和目标项目分别执行只读盘点：

```bash
python project-migration/scripts/frontend_inventory.py <repo-root> --format markdown
```

然后确认：

- package manager、workspace、运行时与框架版本；
- build、typecheck、lint、test、Storybook、E2E 命令；
- Route、导航、页面入口、权限与 Feature Flag；
- 数据请求、缓存、状态、表单、样式、Design System、i18n；
- SSR/SSG/hydration、环境变量、静态资源和部署边界；
- 2～5 个目标项目中维护良好、测试充分的相似实现；
- 当前 Git 状态和基线命令结果。

不要扫描或提交 `node_modules`、构建产物、缓存、覆盖率目录和密钥文件。不要为了侦察先安装新的迁移依赖或改写锁文件。

## 6. 前端迁移闭环

### 阶段 A：定界与基线

1. 明确源根目录、目标根目录、迁移单位、允许的产品变化、浏览器/设备范围和发布约束。
2. 运行现有安装、构建、类型、Lint 和测试命令；记录原有失败。
3. 选择范围、工作模式和产物 profile。

**Gate A**：范围、基线和“允许改变什么”可被复述；未知项已显式列出。

### 阶段 B：源功能与生命周期

从真实入口递归研究：

```text
Route / Navigation / UI Action
→ 显示条件、权限与 Flag
→ 页面或容器
→ State / Query / Form
→ API、缓存与副作用
→ Loading / Empty / Error / Success
→ 后续导航与最终用户结果
```

每项关键能力分类为 `Active`、`Conditional`、`Hidden`、`Disabled`、`Deprecated`、`Removed` 或 `Unknown`，并记录证据。

**Gate B**：现役能力、条件、关键 UI 状态和不迁移项均有证据；`Unknown` 有处理计划。

需要详细方法时读取：

- `references/13-功能文档与递归下钻.md`
- `references/14-功能生命周期与废弃识别.md`

### 阶段 C：视觉与交互基线

关键页面至少覆盖：

- Page Shell、布局、滚动所有者、宽高、spacing、字体、颜色、图标和资源；
- Default、Loading、Empty、Error、Disabled、Validation、Modal/Drawer 等状态；
- Desktop、Tablet、Mobile 或源项目真实支持的 breakpoint；
- keyboard、focus、hover、scroll、submit、取消和错误恢复；
- locale、theme、权限和长内容边界。

证据优先顺序：运行截图/录屏 → Storybook/设计稿 → DOM/CSS/代码推导。无法运行时可以继续，但必须标记基线等级和视觉风险。

详见 `references/15-前端视觉与交互还原.md`。

**Gate C**：未经批准的视觉变化有可比较基线；批准差异已单独记录。

### 阶段 D：迁移策略与目标蓝图

先研究目标项目，再选择策略：

| 条件 | 优先策略 |
|---|---|
| 同一应用、升级路径清晰、兼容层短 | 原地增量升级 |
| Route/Feature 可独立切流 | 路由或功能 Strangler |
| 高风险路径可同时运行并比较 | Parallel/Shadow Run |
| 组件库或接口替换、调用方多 | Adapter / Branch by Abstraction |
| 小型、边界封闭、裁判和回滚都强 | 一次性替换 |
| 独立部署、团队或运行时边界明确 | Micro-frontend Bridge |

策略必须同时给出：迁移单位、依赖顺序、共存方式、切流开关、回滚路径、兼容层删除条件和验证裁判。详见 `references/17-迁移策略与共存回滚.md`。

蓝图从功能契约、视觉基线和目标项目范例推导，不从源组件树推导。跨框架、Router、SSR、状态、样式或构建迁移时读取 `references/18-框架与工程迁移策略.md`。

**Gate D**：目标结构有目标项目依据；没有未经解释的一对一源结构映射；回滚可执行。

### 阶段 E：先做代表性试迁移

选择一个能暴露主要风险的垂直切片，而不是最简单的静态组件。优先包含：

- 权限或条件入口；
- 异步数据与错误路径；
- 关键响应式布局；
- 表单、Modal、复杂交互或 SSR/hydration；
- 目标项目核心组件与测试方式。

试迁移可以被丢弃。保留的是修正后的规则、蓝图、fixtures 和验收标准。

**Gate E**：裁判能在源行为上成立，也能识别故意或已知差异；高风险假设已验证。

### 阶段 F：按垂直切片实施

每个切片执行：

```text
确认契约与生命周期
→ 引用目标范例
→ 实现最小闭环
→ 补齐状态与响应式
→ 运行最近层级测试
→ 运行页面/端到端验证
→ 分类差异
→ 更新迁移状态
```

默认顺序：共享边界和适配层 → 代表性页面 → 同类页面批次 → 全局路由/主题/构建切换 → 旧实现清理。

若同类失败重复出现，暂停扩大批次，先修正功能理解、目标蓝图、迁移规则或任务拆分；不要继续线性修补生成出来的错误代码。

### 阶段 G：验证、切流与清理

按风险组合运行：

- build、typecheck、lint；
- unit、component、integration、E2E；
- visual regression 与人工视觉检查；
- keyboard、focus 与自动化 Accessibility；
- SSR/hydration、console、network、runtime error；
- bundle、关键交互和 Web Vitals/现有性能门禁；
- old/new 行为对照、feature flag/route 回滚演练。

详细执行规范见 `references/19-验证与视觉回归执行.md`。

所有差异分类为：`必须修复`、`批准变化`、`环境噪声`、`Unknown`。不得通过扩大截图阈值、跳过测试或删除断言掩盖迁移回归。

**Gate G**：功能、视觉、交互、响应式和关键 Accessibility 有证据；回滚已验证；旧 Route、Flag、Adapter、CSS、资源和依赖有明确删除条件。

## 7. 暂停扩大范围的条件

出现以下任一情况时，继续研究和修复，但不要批量扩张：

- 源或目标基线失败且无法区分原有问题与迁移问题；
- 关键能力仍为 `Unknown`，却准备删除、替换或切流；
- 视觉敏感页面没有可稳定比较的基线；
- 目标 Router、状态所有权、SSR 边界或 Design System 方向未定；
- 迁移切片导致权限、数据写入、Deep Link、hydration 或回滚失效；
- 同一种失败在多个切片重复出现；
- 兼容层没有 owner、期限或删除条件；
- 验证只能证明“能打开”，不能证明核心用户结果。

暂停不是放弃任务。输出当前证据、根因、已安全完成的部分和恢复路径。

## 8. 多 Agent / 多会话规则

仅在模块足够大且边界稳定时并行。按产品能力拆 Workstream，不按目录平均分。

- Route、全局 Store、Theme、Design Token、共享类型和构建配置采用单写者；
- Worker 先获得同一版本的功能契约、蓝图、迁移规则和验收标准；
- 每个 Worker 交付代码、验证证据、差异、未知项和影响面；
- Supervisor 负责依赖顺序、冲突、统一验证和最终切流；
- 边界仍在变化时先串行做试迁移，不要提前并行放大错误。

详见 `references/12-多Agent与多会话编排.md`。

## 9. 工具与脚本使用

先运行 `--help`，把脚本当作稳定工具使用；只有能力不足时再阅读和修改脚本。

```bash
# 源/目标前端静态盘点
python project-migration/scripts/frontend_inventory.py <repo-root> --format markdown

# 初始化迁移证据工作区
python project-migration/scripts/init_migration_workspace.py <repo-root> --profile standard --dry-run
python project-migration/scripts/init_migration_workspace.py <repo-root> --profile standard

# 检查迁移工作区完整性与明显风险
python project-migration/scripts/validate_migration_workspace.py <repo-root> --profile standard
```

这些脚本只辅助发现和一致性检查，不能代替运行页面、阅读关键代码和工程判断。

## 10. 完成定义

只有同时满足以下条件，才声明迁移完成：

- `Active` / `Conditional` 能力都有目标终态；其他生命周期状态有明确决策；
- Route、Menu、Deep Link、权限和 Feature Flag 可达性符合要求；
- 关键 UI 状态、主要交互和真实支持的 viewport 已验证；
- 未经批准 redesign 的页面与视觉基线一致；
- 目标实现符合目标项目架构与技术栈惯例，无阻断 Copy-Smell；
- build、类型、测试、运行错误、Accessibility 和适用性能门禁通过；
- 所有差异已修复、批准、解释或保留为明确阻断项；
- 切流、监控、回滚、兼容层和旧代码清理都有 owner 与条件；
- `.migration/当前状态.md` 与仓库真实状态一致。

## 11. 最终报告格式

使用以下结构，避免只说“已完成”：

```markdown
## 迁移结论
## 范围、生命周期与批准差异
## 目标架构与实施切片
## 已修改内容
## 验证证据
## 未解决风险与 Unknown
## 切流、回滚与清理
```

审查模式下，先按严重度报告问题并给出文件/路径证据，再给总体评价。

## 12. 按需读取路由

- 执行模式、范围、证据和失败恢复：`references/16-前端迁移执行协议.md`
- 共存、切流、回滚和策略选择：`references/17-迁移策略与共存回滚.md`
- 框架、Router、SSR、状态、样式和构建迁移：`references/18-框架与工程迁移策略.md`
- Playwright、视觉回归、Accessibility 和性能验收：`references/19-验证与视觉回归执行.md`
- 目标原生重建与 Copy-Smell：`references/11-目标原生重建.md`
- 功能递归与生命周期：`references/13-功能文档与递归下钻.md`、`references/14-功能生命周期与废弃识别.md`
- 视觉与交互基线：`references/15-前端视觉与交互还原.md`
- 多 Agent：`references/12-多Agent与多会话编排.md`

后端、数据库、消息和任务仅在它们改变前端数据契约、权限、状态、SSR 或用户结果时继续追踪；不要把本 Skill 扩张为通用后端迁移。
