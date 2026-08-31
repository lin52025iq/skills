---
name: code-migration
description: 用于将一个或多个现有项目中的功能、业务规则和用户能力迁移、融合或重构到目标项目。适用于前端项目迁入新仓库、跨框架或技术栈重实现、多个旧项目能力合并、模块整合、功能删改融合、目标架构适配与渐进切流。迁移以功能语义和用户意图为中心：先理解源项目真实行为与业务规则，再结合目标仓库已有架构、技术栈和既有能力设计目标实现；默认不按源文件、目录、组件或状态结构一比一翻译，并按布局/结构切片与可验证功能切片逐步推进。
---

# Code Migration

把代码迁移视为“业务能力在新上下文中的受控重建”，而不是文件搬运、语法翻译或旧架构复制。

核心公式：

```text
源项目真实行为 + 用户迁移意图 + 目标项目架构
                 ↓
          目标功能设计与实现
```

## 1. 核心原则

1. **迁移的是能力，不是文件。** 文件、组件、Store、Hook、Service 只是源实现证据，不是迁移边界。
2. **Source 决定做什么，Target 决定怎么做。** 源项目用于恢复功能语义；目标项目决定 Router、状态、数据层、组件、目录、错误处理和测试形状。
3. **用户意图高于源实现。** 允许保留、调整、融合、拆分、删除、替换、复用目标能力或新增功能。
4. **默认禁止一比一结构翻译。** 不把 Vuex 自动翻成 Redux，不把 `.vue` 文件树原样映射成 React 文件树，也不复制只因旧技术栈存在的抽象。
5. **机械变化自动化，语义变化分析，产品变化按意图决策。** Codemod 只负责可证明安全的机械转换。
6. **一次只保持一个主要迁移焦点。** 迁移发现的问题不等于必须立即修复；范围外问题进入 Deferred。
7. **先有可验证切片，再扩大范围。** 大迁移优先做代表性切片验证目标架构和迁移规则。
8. **迁移完成不是“新代码能跑”。** 目标能力完成后，还要处理切流、临时结构、旧入口、旧依赖和遗留清理。

## 2. 适用场景

使用本 Skill 处理：

- 一个前端项目迁入另一个已有架构的项目；
- Vue / React / Angular / Svelte 等跨框架或大版本迁移；
- JavaScript 到 TypeScript、旧状态方案到目标项目既有方案；
- 多个后台、门户或业务项目融合为一个目标应用；
- 旧项目中的部分模块、页面或功能迁入新仓库；
- 迁移过程中同时修改、融合或淘汰部分旧功能；
- 新旧系统需要渐进共存、灰度、回滚或临时 Adapter；
- 审查已有迁移是否复制旧架构、遗漏业务规则或同时铺开过多半成品。

不要把它用于纯绿地功能设计；如果没有任何源能力需要理解或迁移，应使用普通开发/架构流程。

## 3. 三类迁移变化

对计划修改先分类：

| 类型 | 含义 | 默认处理 |
|---|---|---|
| Mechanical | import、API rename、可确定的语法与结构转换 | 可用 Codemod/批量自动化 |
| Semantic | 业务行为、状态语义、生命周期、数据与副作用 | Agent 理解后按目标架构重实现 |
| Product | 功能增加、删除、融合、规则改变、UX 改变 | 依据用户意图和目标产品约束决策 |

不得用 Mechanical 工具替代 Semantic / Product 判断。

## 4. 迁移决策枚举

对每个能力明确决策：

- `KEEP`：能力与行为保持，目标实现可变化；
- `ADAPT`：功能语义保留，但按目标架构、技术栈或需求调整；
- `MERGE`：多个来源融合为统一能力；
- `SPLIT`：一个源能力拆成多个目标能力；
- `REMOVE`：明确不迁移；
- `REPLACE`：被新的实现或产品能力替代；
- `REUSE_TARGET`：目标项目已有能力，优先复用而不是再迁一份；
- `NEW`：迁移过程中明确新增；
- `DEFER`：相关但不属于当前迁移范围；
- `UNKNOWN`：证据不足，不能伪装成已决策。

重大 `REMOVE`、`MERGE`、`REPLACE` 或业务行为变化应记录到 `templates/04-迁移决策记录.md`。

## 5. 证据与置信度

关键判断使用轻量证据等级：

```text
C3  Runtime：真实运行、可复现用户路径、E2E 或生产/预发布证据
C2  Contract：自动化测试、API/配置/设计契约、明确文档
C1  Static：静态代码、调用关系、样式、提交历史
C0  Unknown：推断或缺少可靠证据
```

重点标记功能是否现役、业务规则、删除判断、冲突决策和兼容行为。`REMOVE + C0` 默认不可直接实施。

## 6. 范围控制

发现问题时先分类：

- `IN_SCOPE`：当前迁移必须处理；
- `RELATED_BUT_DEFERRED`：相关但不阻塞当前能力；
- `OUT_OF_SCOPE`：与迁移目标无关。

不要因为迁移发现技术债，就默认重构整个目标项目。原则是：**不复制不必要的技术债，也不借迁移之名清理所有技术债。**

## 7. 八阶段迁移流程

### Phase 1 — 理解迁移意图与范围

明确：

- 为什么迁、迁到哪里；
- 一个还是多个源项目；
- 用户明确希望保留、修改、融合、删除的能力；
- 目标项目和技术栈；
- 允许改变与禁止改变的范围；
- 性能、Accessibility、SEO、SSR、浏览器、i18n、安全、监控等非功能约束；
- 发布、共存、灰度和回滚要求。

已有信息足够时不要重复询问。复杂任务使用 `templates/01-迁移任务上下文.md`。

### Phase 2 — 理解源项目与真实功能

先读仓库指令、README、依赖、Route、入口、状态、请求层、权限、测试和部署配置，再从真实入口递归跟踪用户行为。

不要用“代码存在”证明“功能现役”。检查 Route、导航、权限、Feature Flag、调用方、注释、隐藏入口、替代实现和测试。

详见 `references/01-迁移上下文与源项目理解.md`。

### Phase 3 — 建立功能语义和业务规则

把代码语言转成产品/领域语言。每个关键能力至少回答：

```text
Actor → Entry → Precondition → Action → Business Rule
→ Data → Side Effect → Result → Failure → Lifecycle
```

额外识别不可破坏的 **Invariant**，例如权限、金额、状态流转和数据一致性约束。

源代码中的逻辑应分类为业务规则、用户可观察行为、集成契约、框架机制、基础设施机制、Workaround、Bug Compatibility、技术债、Dead Code 或 Unknown。

详见 `references/02-功能语义与业务规则.md`，复杂模块使用 `templates/02-功能清单.md`。

### Phase 4 — 多源归一化与冲突决策

多项目迁移时，不要分别把 A/B/C 项目直接映射到 Target。先形成与技术栈无关的 Canonical Feature Model：

```text
Source A ─┐
Source B ─┼→ Canonical Feature Model → Target
Source C ─┘
```

识别 Naming、Data Model、Business Rule、Lifecycle、Permission、UX、Integration、Architecture 冲突，并依据：用户明确意图 → 目标产品约束 → 目标系统约束 → 高等级源证据 → 推断，逐级处理。

无法安全决定时保持 `UNKNOWN`，不要随机选择某个源实现。

详见 `references/03-多项目融合与冲突决策.md`，使用 `templates/03-功能融合映射.md` 与必要的决策记录。

### Phase 5 — 理解目标项目架构

迁移编码前，研究目标项目中 2～5 个维护良好、相似度高的实现，回答：

> 如果这是一个全新功能，由目标项目原维护者实现，它大概率会怎么写？

重点理解 Router、模块边界、Server/Client state、数据请求与缓存、表单、Design System、权限、错误处理、Analytics、测试、目录、SSR/构建和已有公共能力。

源项目告诉你“要实现什么”，目标项目告诉你“应该怎样实现”。已有能力优先 `REUSE_TARGET`。

详见 `references/04-目标项目架构理解.md`。

### Phase 6 — 设计迁移方案

从 Direct Rewrite、Strangler、Branch by Abstraction、Adapter、Parallel/Shadow、Incremental Upgrade、Codemod-assisted 等策略中选择最小足够方案。

设计：

- Feature → Target Module / Route / Data / State / UI；
- 依赖顺序；
- Temporary Architecture；
- 共存与切流方式；
- 回滚；
- 临时 Adapter / Flag 的删除条件。

临时架构必须有目的和退出条件，不能默认为永久结构。

详见 `references/05-迁移设计与策略选择.md`。

### Phase 7 — 按结构和功能切片实施

前端默认采用“两层切片”：

1. **Structural Slice**：只建立当前迁移范围必要的 Page Shell、布局区域、响应式骨架、Design System 基础和稳定边界；
2. **Functional Slice**：按一个个可独立解释、实现、验证的用户能力推进。

不要同时把所有功能都做成 20%～30%。一个区域进入深度开发后，优先推进到可验收状态，再开启下一个同级区域。

允许三种顺序：

- `Layout-first`：整体布局差异大、多个功能依赖共同结构；
- `Feature-first`：目标页面已存在，只迁某个能力；
- `Representative-slice-first`：整应用或高风险迁移，先选代表性完整切片验证规则。

每个 Slice 开始前通过 Ready Gate，完成后通过 Done Gate，再更新知识和选择下一 Slice。

详见 `references/06-分阶段迁移与功能切片.md`。

### Phase 8 — 验证、切流与遗留清理

验证不只看 build。按风险覆盖：

- 业务行为、Invariant、权限、Loading/Empty/Error/Success；
- API 与数据契约；
- unit/component/integration/E2E；
- 视觉、响应式、Accessibility；
- SSR/hydration、console/network/runtime；
- 性能、bundle、SEO、安全、埋点和可观测性；
- 新旧行为对照和回滚演练。

功能状态建议区分：`DISCOVERED → DESIGNED → MIGRATED → ELIMINATED`。`MIGRATED` 只表示目标能力完成，`ELIMINATED` 才表示旧 Route、Flag、Adapter、重复依赖和旧实现已安全退出。

详见 `references/08-验证切流与遗留清理.md`。

## 8. 当前迁移焦点

长周期任务中，Agent 在任何时刻都必须能说明：

```text
Overall Goal
Current Phase
Current Module / Region
Current Slice
Why Now
Dependencies
Do Not Touch
Definition of Done
Next Candidate
```

一次只允许一个主要迁移焦点。完成当前切片允许修改必要依赖，但不得顺势开启无关迁移、全局重构或批量升级。

复杂迁移在 `templates/05-迁移执行计划.md` 中维护：

- `NOW`：唯一主要焦点；
- `READY`：已满足 Ready Gate；
- `BLOCKED`：缺少依赖或决策；
- `DEFERRED`：相关但当前不做；
- `DONE`：通过 Done Gate。

## 9. Ready Gate 与 Done Gate

### Ready Gate

开始一个 Slice 前确认：

- 功能语义和生命周期已理解；
- 用户迁移意图明确或风险可接受；
- Target 落点和目标惯例明确；
- 必要依赖已满足；
- 验证方法存在；
- 当前不存在会让实现方向失真的关键 `UNKNOWN`。

不满足时继续研究、记录 Blocked 或缩小试迁移，不要盲目扩张代码。

### Done Gate

一个 Slice 至少满足：

- 主流程和关键状态完成；
- 业务规则与 Invariant 有验证；
- 权限、数据契约和错误路径符合目标；
- 使用目标架构，而非复制源结构；
- 对应测试/运行验证通过或已记录基线差异；
- 没有静默扩大 Scope；
- 新发现已反馈到后续迁移模型。

## 10. Migration Learning Loop

每完成一个代表性切片执行：

```text
Understand → Implement → Verify → Learn → Update Model → Next Slice
```

如果第一个切片证明最初的目标架构假设、字段映射、状态模型、组件选择或测试方式不对，先更新迁移模型和后续计划，再继续批量实施。不要把同一种错误复制到更多页面后再统一修复。

## 11. 自动化约束

Codemod、正则替换或批量脚本仅用于可证明的 Mechanical 变化。自动化修改应同时给出：

```text
What / Why / Evidence / Scope / Expected Change / Validation / Rollback
```

同类自动化先在代表性样本验证，再扩大批次。遇到语义差异、复杂状态、权限、业务规则或多个合法目标实现时，停止机械转换，进入人工/Agent 设计。

详见 `references/07-自动化与增量实施.md`。

## 12. 禁止的迁移方式

- 不按文件一一迁移；
- 不按源目录树创建目标目录树；
- 不把旧 Store/API abstraction/组件层机械复刻；
- 不因为旧代码存在就恢复废弃能力；
- 不把多个源项目中的重复能力分别迁入目标；
- 不为了“兼容”复制无必要的 Workaround 和技术债；
- 不同时铺开大量半成品页面或功能；
- 不以“改了多少文件”衡量迁移进度；
- 不以 build 通过作为唯一完成标准；
- 不通过放宽测试阈值、删除断言或隐藏错误证明迁移成功。

## 13. 文档强度按规模自适应

文档用于保存影响迁移的事实，不是迁移目的：

| 范围 | 默认产物 |
|---|---|
| 单组件/小 Hook | 对话内功能契约、目标实现与验证即可 |
| 单页面 | 功能清单 + 简化执行计划 |
| 业务模块 | 上下文 + 功能清单 + 执行计划 |
| 多项目融合 | 五个模板按需完整使用 |
| 整应用迁移 | 完整上下文、融合映射、决策记录、执行队列与切流清理计划 |

不要为了形式机械创建全部模板。

## 14. 结束报告

实施或审查结束时至少说明：

1. 总体目标与本轮实际完成的能力；
2. 当前处于 `MIGRATED` 还是 `ELIMINATED`；
3. 验证证据与已知差异；
4. Blocked / Deferred / Unknown；
5. Temporary Architecture 和清理条件；
6. 下一推荐 Slice 及其选择原因。
