---
name: code-migration
description: 用于将一个或多个现有项目中的功能、业务规则和用户能力迁移、融合或重构到目标项目。适用于前端项目迁入新仓库、跨框架或技术栈重实现、多个旧项目能力合并、模块整合、功能删改融合、目标架构适配与渐进切流。迁移以功能语义和用户意图为中心：先用源项目恢复真实行为与约束，再确定目标系统期望能力，最后按目标仓库已有架构和技术栈重新实现；默认不按源文件、目录、组件或状态结构一比一翻译，并按结构切片与可验证功能切片逐步推进。
---

# Code Migration

把代码迁移视为“业务能力在新上下文中的受控重建”，不是文件搬运、语法翻译，也不是旧架构复制。

核心模型：

```text
Source Evidence
  源项目真实行为、业务规则、数据契约、历史约束
                     ↓
Desired Target Behavior
  用户迁移意图 + 目标产品要求 + 必须保留的 Invariant
                     ↓
Target-native Design
  目标仓库架构 + 技术栈 + 已有公共能力
                     ↓
Incremental Implementation & Verification
```

## 1. 核心原则

1. **迁移的是能力，不是文件。** 文件、组件、Store、Hook、Service 只是理解源能力的证据，不是迁移边界。
2. **Source 是事实证据，不是目标规范。** 源项目回答“旧系统实际做了什么”；它不能自动决定新系统必须继续怎样做。
3. **先确定目标期望行为，再设计代码。** 用户意图和目标产品要求决定保留、调整、融合、拆分、删除或新增什么；必须保留的业务 Invariant 不能因技术迁移丢失。
4. **Target 决定实现形状。** Router、状态、数据层、组件、目录、错误处理、测试和工程模式优先遵循目标项目已有惯例。
5. **默认禁止一比一结构翻译。** 不把 Vuex 自动翻成 Redux，不把 `.vue` 文件树映射成 React 文件树，也不为每个旧 abstraction 创建一个新 abstraction。
6. **机械变化自动化，语义变化分析，产品变化显式决策。** Codemod 只负责可证明安全的 Mechanical 变化。
7. **一次只保持一个主要迁移焦点。** 优先完成一个可验收能力，不同时铺开大量半成品。
8. **先验证迁移规则，再扩大范围。** 大型或高风险迁移优先做代表性切片。
9. **迁移验证面向目标行为。** `KEEP` 要证明关键旧能力没有回归；`ADAPT/MERGE/REPLACE/NEW` 要证明批准后的目标行为正确，不能把有意变化误报成回归。
10. **迁移完成不等于新代码能跑。** 还要处理切流、临时结构、旧入口、旧依赖和遗留清理。

## 2. 适用场景

使用本 Skill 处理：

- 一个前端项目迁入另一个已有架构的项目；
- Vue / React / Angular / Svelte 等跨框架或大版本迁移；
- JavaScript 到 TypeScript、旧状态方案迁入目标项目既有方案；
- 多个后台、门户或业务项目融合为一个目标应用；
- 旧项目中的部分模块、页面或功能迁入新仓库；
- 迁移过程中同时修改、融合、替换或淘汰部分旧功能；
- 新旧系统需要渐进共存、灰度、回滚或临时 Adapter；
- 审查已有迁移是否复制旧架构、遗漏业务规则或失去迁移焦点。

如果没有需要理解、迁移或融合的源能力，应使用普通开发/架构流程。

## 3. 先区分三类变化

| 类型 | 含义 | 默认处理 |
|---|---|---|
| Mechanical | import、API rename、确定性的语法/结构变化 | Codemod 或小批量自动化 |
| Semantic | 业务行为、状态语义、生命周期、数据、副作用 | 理解语义后按目标架构重实现 |
| Product | 功能增加、删除、融合、规则或 UX 改变 | 依据用户意图和目标产品要求决策 |

不得用 Mechanical 工具替代 Semantic / Product 判断。

## 4. 迁移决策

每个能力使用一个明确决策：

- `KEEP`：目标仍需保持该能力和关键行为，实现方式可以变化；
- `ADAPT`：能力保留，但目标行为或实现需按新要求调整；
- `MERGE`：多个来源融合成一个目标能力；
- `SPLIT`：一个源能力拆成多个目标能力；
- `REMOVE`：目标系统明确不需要；
- `REPLACE`：由新的产品能力或实现替代；
- `REUSE_TARGET`：目标项目已有能力可直接复用；
- `NEW`：迁移范围内明确新增；
- `DEFER`：相关但不属于当前迁移范围；
- `UNKNOWN`：当前证据不足，尚未做出安全决策。

重大 `REMOVE / MERGE / REPLACE`、Invariant 变化或高风险产品行为变化应记录 Decision。

## 5. 证据与 Invariant

关键判断使用轻量证据等级：

```text
C3 Runtime  ：真实运行、用户路径、E2E、生产/预发布证据
C2 Contract ：测试、API/配置/设计契约、明确文档
C1 Static   ：静态代码、调用关系、样式、提交历史
C0 Unknown  ：推断或缺少可靠证据
```

优先把证据用于：

- 功能是否现役；
- Business Rule / Invariant；
- 删除与融合判断；
- 多源冲突；
- 兼容行为。

`REMOVE + C0` 默认不可直接实施。

Invariant 是迁移中必须显式保护的约束，例如：权限边界、金额规则、状态流转、幂等性、数据一致性。只有用户或目标产品明确修改时才能改变，并应记录 Decision。

## 6. 范围控制

发现额外问题时分类：

- `IN_SCOPE`：当前迁移必须处理；
- `RELATED_BUT_DEFERRED`：相关但不阻塞当前能力；
- `OUT_OF_SCOPE`：与迁移目标无关。

不复制无必要技术债，也不借迁移之名清理所有技术债。

## 7. 八阶段迁移流程

### Phase 1 — 确定迁移意图与范围

明确：

- 为什么迁、迁到哪里；
- 一个还是多个源项目；
- 用户希望保留、修改、融合、删除、新增什么；
- 目标项目和技术栈；
- 允许改变与禁止改变的范围；
- 性能、Accessibility、SEO、SSR、浏览器、i18n、安全、监控等非功能约束；
- 发布、共存、灰度和回滚要求。

已有信息足够时不要重复询问。

### Phase 2 — 恢复源项目真实能力

先读仓库指令、README、依赖、Route、入口、状态、请求层、权限、测试和部署配置，再从真实入口递归跟踪用户行为。

不要用“代码存在”证明“功能现役”。检查 Route、导航、权限、Feature Flag、调用方、注释、隐藏入口、替代实现和测试。

详见 `references/01-迁移上下文与源项目理解.md`。

### Phase 3 — 建立功能语义、业务规则与 Invariant

把代码语言转成产品/领域语言：

```text
Actor → Entry → Precondition → Action → Business Rule
→ Data → Side Effect → Result → Failure → Lifecycle
```

把旧代码区分为：业务规则、用户可观察行为、集成契约、框架机制、基础设施机制、Workaround、Bug Compatibility、技术债、Dead Code 或 Unknown。

这一步回答“旧能力是什么”，不自动等同于“目标必须原样保留什么”。

详见 `references/02-功能语义与业务规则.md`。

### Phase 4 — 形成目标能力模型并解决多源冲突

单源也要从 Source Feature 推导 `Desired Target Behavior`；多源则先做语义归一化：

```text
Source A ─┐
Source B ─┼→ Canonical Feature / Domain Model
Source C ─┘
                 ↓
         Desired Target Behavior
```

识别 Naming、Data Model、Business Rule、Lifecycle、Permission、UX、Integration 和 Architecture 冲突。

决策顺序：用户明确意图 → 目标产品要求 → 必须保留的 Invariant → 目标系统稳定约束 → C3/C2 源证据 → C1 → 推断。

无法安全决定时保持 `UNKNOWN`；真正影响当前目标行为的关键问题进入 Clarification Loop。

详见 `references/03-多项目融合与冲突决策.md`。

### Phase 5 — 理解目标项目并设计 Target-native 方案

先研究目标项目已有相似实现和公共能力，再决定目标模块、Route、Data、State、UI、Permission、Testing。

核心问题：

> 如果按照已经确定的目标行为，今天在这个仓库里原生开发，该怎样实现？

已有能力优先 `REUSE_TARGET`；目标确实缺失时只补最小必要 Foundation。

详见 `references/04-目标项目架构理解.md`。

### Phase 6 — 选择迁移策略

根据风险选择最小足够策略：Direct Rewrite、Strangler、Branch by Abstraction、Adapter、Parallel/Shadow、Incremental Upgrade、Codemod-assisted 等。

方案至少说明：

- Feature → Target Mapping；
- 依赖顺序；
- Temporary Architecture；
- 共存/切流方式；
- 回滚；
- 临时结构删除条件。

详见 `references/05-迁移设计与策略选择.md`。

### Phase 7 — 按结构与功能切片实施

前端允许两层切片：

1. `Structural Slice`：只建立当前范围必要的 Page Shell、布局 Region、响应式骨架和 Design System 基础；
2. `Functional Slice`：逐个完成可以独立解释、实现和验证的用户能力。

顺序根据场景选择：

- `Layout-first`：多个功能依赖共同的新布局结构；
- `Feature-first`：目标页面已经存在；
- `Representative-slice-first`：大型、高风险、跨技术栈迁移。

不要把 Layout-first 变成“先搭全应用所有空页面”。

详见 `references/06-分阶段迁移与功能切片.md`。

### Phase 8 — 验证目标行为、切流与清理

验证不只看 build，而要证明 `Desired Target Behavior`：

- `KEEP`：关键行为和 Invariant 未丢失；
- `ADAPT/MERGE/REPLACE/NEW`：批准后的目标行为正确；
- 权限、API/数据、关键 UI 状态和错误路径正确；
- 适用的 unit/component/integration/E2E、视觉、响应式、Accessibility、SSR、性能、安全与可观测性通过。

把差异分成 `MUST_FIX / APPROVED_CHANGE / ENVIRONMENT_NOISE / UNKNOWN`。

详见 `references/08-验证切流与遗留清理.md`。

## 8. 当前迁移焦点与状态

每次实施必须能说明：

```text
Overall Goal
Desired Target Behavior
Current Phase
Current Module / Region
Current Slice
Why Now
Dependencies
Do Not Touch
Definition of Done
Next Candidate
```

一次只保持一个主要 `NOW`。其他能力进入 `READY / BLOCKED / DEFERRED / DONE`。

功能生命周期建议使用：

```text
DISCOVERED → DESIGNED → IMPLEMENTING → VERIFYING → MIGRATED → ELIMINATED
```

- `IMPLEMENTING`：当前能力正在开发，不能当成完成；
- `VERIFYING`：主要实现完成，但验证 Gate 尚未完成；
- `MIGRATED`：目标能力已经实现并通过当前迁移 Gate；
- `ELIMINATED`：旧入口、旧实现和临时结构已按计划安全退出。

`BLOCKED` 是附加状态，不替代生命周期。

## 9. Ready Gate / Done Gate

### Ready Gate

开始一个 Slice 前确认：

- 已理解相关源能力；
- `Desired Target Behavior` 足够明确；
- Target 落点与项目惯例明确；
- 必要依赖已满足；
- 验证方法存在；
- 没有会导致当前实现方向失真的关键 `UNKNOWN`。

### Done Gate

一个 Slice 至少满足：

- 目标主流程和关键状态完成；
- Business Rule / Invariant 或批准后的变化有验证；
- Permission / Data Contract / Error Path 符合目标；
- 使用 Target-native 架构而非复制 Source；
- 对应测试/运行验证完成或差异被明确分类；
- 没有静默扩大 Scope；
- 新发现已反馈到后续迁移模型。

## 10. Clarification Loop

只有当一个 Unknown 同时满足“证据不足”且“会实质改变当前目标行为或不可逆方向”时才使用 `MUST_ASK`。

- `MUST_ASK`：高风险产品规则、关键业务语义、权限/数据含义、明确范围取舍、不可安全推断的不可逆方向；
- `CAN_INFER`：目标仓库已有稳定惯例、已有高等级证据或低风险默认值可安全推断；
- `CAN_DEFER`：不阻塞当前 Slice。

不要把普通代码组织、命名、组件选择、目标仓库已有明确范例的问题都抛给用户。每轮只问最影响当前 Slice 的少量问题，回答后更新 Decision 和 Ready Gate；必要时可继续下一轮。

## 11. Migration Workspace 与跨会话恢复

复杂或长周期迁移把必要状态写入目标仓库根目录 `.code-migration/`。`00-迁移状态总览.md` 是恢复入口，不是高于真实代码、测试和已确认 Decision 的绝对事实源。

新对话先恢复状态，再核对当前 Slice 的真实代码/Git 状态；不一致时先做最小 Reconcile。

详细的 Workspace 结构、事实源优先级、交接、澄清持久化和恢复协议见 `references/09-迁移状态与跨会话协作.md`。

## 12. Migration Learning Loop

```text
Understand → Design → Implement → Verify → Learn → Update Model → Next Slice
```

一个代表性切片发现的通用规律，应先修正目标模型和后续迁移规则，再扩大范围。不要把同一种错误复制到更多页面后统一返工。

## 13. 自动化约束

Codemod、正则替换或批量脚本只用于可证明的 Mechanical 变化。先在代表性样本验证，再扩大批次。

自动修改至少能说明：`What / Why / Scope / Expected Change / Validation / Rollback`。

遇到复杂状态、权限、业务规则、产品变化或多个合法目标实现时停止机械转换。

详见 `references/07-自动化与增量实施.md`。

## 14. 禁止的迁移方式

- 不按文件或源目录树一一迁移；
- 不把旧 Store/API abstraction/组件层机械复刻；
- 不因为旧代码存在就自动恢复废弃能力；
- 不把多个源项目中的重复能力分别搬进目标；
- 不为了兼容复制无必要 Workaround 和技术债；
- 不同时铺开大量半成品页面或功能；
- 不用文件数量衡量迁移进度；
- 不以 build 通过作为唯一完成标准；
- 不把批准的目标变化当成需要“修回旧行为”的回归；
- 不通过放宽阈值、删除断言或隐藏错误证明迁移成功。

## 15. 文档强度按规模自适应

文档只保存会影响迁移决策、实现、验证和跨会话恢复的事实：

| 范围 | 默认产物 |
|---|---|
| 单组件/短任务 | 对话内契约和验证即可 |
| 单页面且单会话 | 功能清单 + 简化执行计划，可不建完整 Workspace |
| 长周期页面/业务模块 | 状态总览 + 上下文 + 功能清单 + 执行计划 |
| 多项目融合 | 再增加融合映射和必要 Decision |
| 整应用迁移 | 完整模块队列、交接、切流与清理记录 |

不要为了形式机械创建全部模板。

## 16. 结束报告

至少说明：

1. 总体目标与本轮实际完成的 Target Capability；
2. 当前能力处于 `IMPLEMENTING / VERIFYING / MIGRATED / ELIMINATED` 哪个阶段；
3. 验证证据和 `APPROVED_CHANGE`；
4. Blocked / Deferred / Unknown / MUST_ASK；
5. Temporary Architecture 和退出条件；
6. 下一推荐 Slice 及原因；
7. 长周期任务的 `.code-migration/` 是否已同步。